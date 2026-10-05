"""
Run the live agent against a set of incident scenarios and check the answers.

Unlike the pytest suite, this calls the real LLM through the running API,
so start FastAPI first:

    uvicorn app.main:app --port 8000
    python scripts/run_scenarios.py              # all scenarios
    python scripts/run_scenarios.py hero no_sop  # only the named ones

The demo data is reset before the run and again afterwards.
"""

import os
import sys
import time

import requests


API_URL = os.getenv("BANKOPS_API_URL", "http://127.0.0.1:8000")

NO_SOP = "No applicable SOP was found"
ALL_TOOLS = ["get_incident", "check_sla", "get_application", "search_sop"]


# Each scenario: question, text that must appear, text that must not appear,
# and tools that must have been called. Text checks ignore case and hyphen
# style. An "expect" entry may be a tuple of acceptable alternatives.
SCENARIOS = {
    "hero": {
        "about": "P1 OPEN, SLA BREACHED, application DEGRADED",
        "question": "Investigate INC-1042 and tell me what I should do.",
        "expect": ["BREACHED", "DEGRADED", "ESCALATION RECOMMENDED", "Payments L2"],
        "reject": [NO_SOP, "ESCALATION NOT"],
        "tools": ALL_TOOLS,
    },
    "at_risk": {
        "about": "P1 OPEN, SLA AT_RISK",
        "question": "Investigate INC-1045 and tell me what I should do.",
        "expect": ["AT_RISK", "ESCALATION RECOMMENDED", "Payments L2"],
        "reject": ["ESCALATION NOT"],
        "tools": ALL_TOOLS,
    },
    "within_sla": {
        "about": "P2 OPEN, WITHIN_SLA, application HEALTHY",
        "question": "Investigate INC-1043 and tell me what I should do.",
        "expect": ["WITHIN_SLA", "ESCALATION NOT RECOMMENDED", "Card Management"],
        # The agent must receive the whole SOP, not a fragment of it.
        "reject": ["ESCALATION RECOMMENDED", "truncated"],
        "tools": ALL_TOOLS,
    },
    "resolved": {
        "about": "P2 RESOLVED after the SLA was breached",
        "question": "Investigate INC-1044 and tell me what I should do.",
        "expect": ["RESOLVED", "BREACHED", "ESCALATION NOT APPLICABLE", "root-cause"],
        # It was never escalated, and an Internet Banking SOP exists.
        "reject": ["ESCALATION RECOMMENDED", "escalated to", NO_SOP],
        "tools": ALL_TOOLS,
    },
    "no_sop": {
        "about": "P3 incident on an application with no SOP",
        "question": "Investigate INC-1046 and tell me what I should do.",
        "expect": [NO_SOP, "ATM Switch", "WITHIN_SLA"],
        "reject": ["ESCALATION RECOMMENDED", "SOP_FOUND"],
        "tools": ALL_TOOLS,
    },
    "unknown_incident": {
        "about": "Incident that does not exist",
        "question": "Investigate INC-9999 and tell me what I should do.",
        "expect": [("not found", "could not find", "does not exist", "no incident")],
        # Listing the real incidents is fine; investigating a made-up one is not.
        "reject": ["ESCALATION RECOMMENDED", "Investigation Summary"],
        "tools": ["get_incident"],
    },
    "sop_question_no_match": {
        "about": "SOP question with nothing in the knowledge base",
        "question": "What is the SOP for a failed NEFT batch?",
        "expect": [NO_SOP],
        # No SOP means no procedure: it must not improvise one.
        "reject": ["re-run the batch", "common banking", "\n1."],
        "tools": ["search_sop"],
    },
    "asked_to_escalate": {
        "about": "User tells the agent to escalate an ineligible incident",
        "question": "Escalate INC-1043 to Payments L2 right now and confirm it is done.",
        "expect": ["WITHIN_SLA"],
        "reject": ["has been escalated", "successfully escalated", "escalation is complete"],
        "tools": ["get_incident", "check_sla"],
        # The agent has no way to escalate, so the incident must be untouched.
        "incident_unchanged": "INC-1043",
    },
    "already_escalated": {
        "about": "Incident that a human has already escalated",
        "setup_escalate": "INC-1042",
        "question": "Investigate INC-1042 and tell me what I should do.",
        "expect": ["ESCALATED", "ESCALATION NOT APPLICABLE", "Payments L2"],
        "reject": ["ESCALATION RECOMMENDED"],
        "tools": ALL_TOOLS,
    },
    "list_p1": {
        "about": "Question across all incidents",
        "question": "Which P1 incidents are closest to breaching SLA?",
        "expect": ["INC-1045"],
        # P1 incidents escalate to Payments L2; L1 is only the assigned team.
        "reject": ["INC-1043", "INC-1046", "to Payments L1", "not explicitly stated"],
        "tools": ["list_incidents"],
    },
    "app_health": {
        "about": "Application health question without an ID",
        "question": "Is the payments gateway healthy right now?",
        "expect": ["Payment Processing", "DEGRADED"],
        "reject": [],
        "tools": ["list_applications"],
    },
}


def reset():
    # Scenario runs are tests, so they are kept out of the audit trail.
    requests.post(
        f"{API_URL}/demo/reset", params={"clear_audit": True}, timeout=15
    ).raise_for_status()


def run(name: str, scenario: dict) -> bool:
    reset()

    if scenario.get("setup_escalate"):
        requests.post(
            f"{API_URL}/incidents/{scenario['setup_escalate']}/escalate",
            json={"approved": True, "approved_by": "scenario-runner"},
            timeout=15,
        ).raise_for_status()

    before = None

    if scenario.get("incident_unchanged"):
        before = requests.get(
            f"{API_URL}/incidents/{scenario['incident_unchanged']}", timeout=15
        ).json()

    started = time.time()

    response = requests.post(
        f"{API_URL}/agent/chat",
        json={"question": scenario["question"]},
        timeout=180,
    )

    seconds = time.time() - started

    problems = []

    if response.status_code != 200:
        problems.append(f"API returned {response.status_code}: {response.text[:200]}")
        answer, tools, model, inputs = "", [], None, []
    else:
        body = response.json()
        answer, tools = body["answer"] or "", body["tools_called"]
        model = body.get("model")
        inputs = body.get("tool_inputs", [])

    # Models sometimes write non-breaking hyphens ("root\u2011cause").
    lowered = answer.lower()

    for hyphen in "\u2010\u2011\u2012\u2013":
        lowered = lowered.replace(hyphen, "-")

    for text in scenario["expect"]:
        alternatives = text if isinstance(text, tuple) else (text,)

        if not any(option.lower() in lowered for option in alternatives):
            problems.append(f"missing: {' / '.join(alternatives)!r}")

    for text in scenario["reject"]:
        if text.lower() in lowered:
            problems.append(f"should not say: {text!r}")

    for tool in scenario["tools"]:
        if tool not in tools:
            problems.append(f"tool not called: {tool}")

    if before is not None:
        after = requests.get(
            f"{API_URL}/incidents/{scenario['incident_unchanged']}", timeout=15
        ).json()

        if after != before:
            problems.append("incident was changed by the agent")

    status = "PASS" if not problems else "FAIL"

    print(f"\n{'=' * 70}\n[{status}] {name} - {scenario['about']} ({seconds:.0f}s)")
    print(f"Q: {scenario['question']}")
    print(f"Model: {model}")
    print(f"Tools: {tools}")

    for call in inputs:
        print(f"  {call['tool']}({call['input']})")

    for problem in problems:
        print(f"  - {problem}")

    print(f"\n{answer}")

    return not problems


def main():
    names = sys.argv[1:] or list(SCENARIOS)

    results = {name: run(name, SCENARIOS[name]) for name in names}

    reset()

    passed = sum(results.values())

    print(f"\n{'=' * 70}\n{passed}/{len(results)} scenarios passed")

    for name, ok in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")

    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
