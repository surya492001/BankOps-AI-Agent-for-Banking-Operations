import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langgraph.prebuilt import create_react_agent

from app.agents import graph
from app.api.agent import find_incident_id


class ScriptedModel(GenericFakeChatModel):
    """A stand-in LLM that replays a fixed list of responses."""

    def bind_tools(self, tools, **kwargs):
        return self


def tool_call(name, **args):
    return {"name": name, "args": args, "id": f"call-{name}", "type": "tool_call"}


@pytest.fixture
def scripted_agent(monkeypatch):
    """Run the real agent graph and tools against scripted LLM output."""

    def _use(*responses):
        model = ScriptedModel(messages=iter(responses))

        monkeypatch.setattr(
            graph,
            "agent",
            create_react_agent(
                model=model,
                tools=graph.tools,
                prompt=graph.SYSTEM_PROMPT,
            ),
        )

    return _use


def test_agent_investigation_runs_all_tools(scripted_agent):
    scripted_agent(
        AIMessage(
            content="",
            tool_calls=[
                tool_call("get_incident", incident_id="INC-1042"),
                tool_call("check_sla", incident_id="INC-1042"),
            ],
        ),
        AIMessage(
            content="",
            tool_calls=[
                tool_call("get_application", application_id=1),
                tool_call(
                    "search_sop",
                    query="P1 payment processing incident SLA breached escalation",
                ),
            ],
        ),
        AIMessage(content="ESCALATION RECOMMENDED - to Payments L2"),
    )

    result = graph.ask_agent("Investigate INC-1042")

    assert result["answer"] == "ESCALATION RECOMMENDED - to Payments L2"
    assert result["tools_called"] == [
        "get_incident",
        "check_sla",
        "get_application",
        "search_sop",
    ]
    assert result["sources"] == [
        "Incident Database",
        "SLA Database",
        "Application Database",
        "Knowledge Base / SOP",
    ]

    # The tools returned real data to the agent, not placeholders.
    tool_results = "\n".join(result["tool_results"])

    assert "Payment processing delays" in tool_results
    assert "BREACHED" in tool_results
    assert "DEGRADED" in tool_results
    assert "SOP_FOUND" in tool_results


def test_agent_is_told_when_no_sop_applies(scripted_agent):
    scripted_agent(
        AIMessage(
            content="",
            tool_calls=[
                tool_call(
                    "search_sop",
                    query="P3 incident escalation procedure",
                    application="ATM Switch",
                ),
            ],
        ),
        AIMessage(
            content="No applicable SOP was found in the knowledge base for this incident."
        ),
    )

    result = graph.ask_agent("Investigate INC-1046")

    assert result["tool_results"] == ["search_sop: NO_APPLICABLE_SOP"]


def test_agent_cannot_escalate_on_its_own():
    # Escalation is a human-approved API action, never an agent tool.
    assert [tool.name for tool in graph.tools] == [
        "get_incident",
        "check_sla",
        "get_application",
        "list_incidents",
        "list_applications",
        "search_sop",
    ]


def test_agent_answers_without_tools(scripted_agent):
    scripted_agent(AIMessage(content="Hello, how can I help?"))

    result = graph.ask_agent("hi")

    assert result["tools_called"] == []
    assert result["sources"] == []


def test_chat_endpoint_records_audit_log(client, scripted_agent):
    scripted_agent(
        AIMessage(
            content="",
            tool_calls=[tool_call("get_incident", incident_id="INC-1042")],
        ),
        AIMessage(content="ESCALATION RECOMMENDED - to Payments L2"),
    )

    response = client.post(
        "/agent/chat",
        json={"question": "Investigate inc-1042 and tell me what I should do."},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["answer"] == "ESCALATION RECOMMENDED - to Payments L2"
    assert body["incident_id"] == "INC-1042"
    assert body["tools_called"] == ["get_incident"]

    audit = client.get("/audit", params={"incident_id": "INC-1042"}).json()

    assert len(audit) == 1
    assert audit[0]["request_id"] == body["request_id"]
    assert audit[0]["tools_called"] == "get_incident"
    assert audit[0]["sources"] == "Incident Database"
    assert audit[0]["recommendation"] == body["answer"]
    assert audit[0]["action_taken"] is None


def test_investigate_then_escalate_end_to_end(client, scripted_agent):
    scripted_agent(
        AIMessage(
            content="",
            tool_calls=[
                tool_call("get_incident", incident_id="INC-1042"),
                tool_call("check_sla", incident_id="INC-1042"),
            ],
        ),
        AIMessage(content="ESCALATION RECOMMENDED - to Payments L2"),
    )

    investigation = client.post(
        "/agent/chat",
        json={"question": "Investigate INC-1042"},
    ).json()

    # Investigating must not change the incident.
    assert client.get("/incidents/INC-1042").json()["status"] == "OPEN"

    escalation = client.post(
        "/incidents/INC-1042/escalate",
        json={
            "approved": True,
            "approved_by": "surya",
            "request_id": investigation["request_id"],
        },
    ).json()

    assert escalation["escalation_team"] == "Payments L2"
    assert client.get("/incidents/INC-1042").json()["status"] == "ESCALATED"

    audit = client.get("/audit", params={"incident_id": "INC-1042"}).json()

    assert len(audit) == 2
    assert {entry["request_id"] for entry in audit} == {investigation["request_id"]}
    assert audit[0]["action_taken"] == "ESCALATE"
    assert audit[0]["recommendation"] == "ESCALATION RECOMMENDED - to Payments L2"


def test_chat_endpoint_requires_question(client):
    assert client.post("/agent/chat", json={}).status_code == 422


@pytest.mark.parametrize(
    "question, expected",
    [
        ("Investigate INC-1042 and tell me what to do", "INC-1042"),
        ("what about inc-1045?", "INC-1045"),
        ("INC-1042 again, still INC-1042", "INC-1042"),
        ("Compare INC-1042 and INC-1043", None),
        ("Which P1 incidents are closest to breaching SLA?", None),
        ("ZINC-1042 is not an incident", None),
    ],
)
def test_find_incident_id(question, expected):
    assert find_incident_id(question) == expected
