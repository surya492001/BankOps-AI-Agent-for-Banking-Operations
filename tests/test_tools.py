import pytest

from app.tools.operations import (
    check_sla,
    get_application,
    get_incident,
    list_applications,
    list_incidents,
)


def test_get_incident_tool():
    incident = get_incident.invoke({"incident_id": "INC-1042"})

    assert incident == {
        "incident_id": "INC-1042",
        "title": "Payment processing delays",
        "priority": "P1",
        "status": "OPEN",
        "description": "Multiple payment transactions are experiencing delays.",
        "application_id": 1,
        "assigned_team": "Payments L1",
    }


def test_get_incident_tool_not_found():
    result = get_incident.invoke({"incident_id": "INC-9999"})

    assert result == {"error": "Incident INC-9999 not found"}


def test_get_incident_tool_reflects_escalation(client):
    client.post("/incidents/INC-1042/escalate", json={"approved": True})

    incident = get_incident.invoke({"incident_id": "INC-1042"})

    assert incident["status"] == "ESCALATED"
    assert incident["assigned_team"] == "Payments L2"


def test_check_sla_tool():
    sla = check_sla.invoke({"incident_id": "INC-1042"})

    assert sla["sla_status"] == "BREACHED"
    assert sla["sla_limit_minutes"] == 120
    assert sla["remaining_minutes"] == 0
    assert sla["escalation_team"] == "Payments L2"
    assert sla["escalation_decision"] == "ESCALATION RECOMMENDED"
    assert sla["already_escalated"] is False


@pytest.mark.parametrize(
    "incident_id, decision",
    [
        ("INC-1042", "ESCALATION RECOMMENDED"),      # OPEN, BREACHED
        ("INC-1045", "ESCALATION RECOMMENDED"),      # OPEN, AT_RISK
        ("INC-1043", "ESCALATION NOT RECOMMENDED"),  # OPEN, WITHIN_SLA
        ("INC-1046", "ESCALATION NOT RECOMMENDED"),  # OPEN, WITHIN_SLA
        ("INC-1044", "ESCALATION NOT APPLICABLE"),   # RESOLVED
    ],
)
def test_check_sla_tool_gives_the_escalation_decision(incident_id, decision):
    sla = check_sla.invoke({"incident_id": incident_id})

    assert sla["escalation_decision"] == decision
    assert sla["escalation_reason"]


def test_check_sla_tool_after_escalation(client):
    client.post("/incidents/INC-1042/escalate", json={"approved": True})

    sla = check_sla.invoke({"incident_id": "INC-1042"})

    assert sla["escalation_decision"] == "ESCALATION NOT APPLICABLE"
    assert sla["already_escalated"] is True


def test_agent_decision_always_agrees_with_escalation_api(client):
    # What the agent is told and what the API will accept come from one rule.
    for incident_id in ["INC-1042", "INC-1043", "INC-1044", "INC-1045", "INC-1046"]:
        told = check_sla.invoke({"incident_id": incident_id})
        state = client.get(f"/incidents/{incident_id}/escalation").json()

        assert (told["escalation_decision"] == "ESCALATION RECOMMENDED") is state["eligible"]


def test_check_sla_tool_matches_sla_api(client):
    for incident_id in ["INC-1042", "INC-1043", "INC-1044", "INC-1045", "INC-1046"]:
        tool_result = check_sla.invoke({"incident_id": incident_id})
        api_result = client.get(f"/sla/{incident_id}").json()

        assert tool_result["sla_status"] == api_result["sla_status"]
        assert tool_result["escalation_team"] == api_result["escalation_team"]


def test_check_sla_tool_not_found():
    result = check_sla.invoke({"incident_id": "INC-9999"})

    assert result == {"error": "Incident INC-9999 not found"}


def test_check_sla_tool_no_policy(set_incident):
    set_incident("INC-1042", priority="P9")

    result = check_sla.invoke({"incident_id": "INC-1042"})

    assert result == {"error": "No SLA policy found for priority P9"}


def test_get_application_tool():
    application = get_application.invoke({"application_id": 4})

    assert application["application_name"] == "ATM Switch"
    assert application["application_code"] == "APP-ATM-001"
    assert application["status"] == "DEGRADED"


def test_get_application_tool_not_found():
    result = get_application.invoke({"application_id": 999})

    assert result == {"error": "Application 999 not found"}


def test_list_incidents_tool_includes_sla_status():
    incidents = list_incidents.invoke({})

    assert {
        incident["incident_id"]: incident["sla_status"]
        for incident in incidents
    } == {
        "INC-1042": "BREACHED",
        "INC-1043": "WITHIN_SLA",
        "INC-1044": "BREACHED",
        "INC-1045": "AT_RISK",
        "INC-1046": "WITHIN_SLA",
    }


def test_list_incidents_tool_filters_by_priority():
    incidents = list_incidents.invoke({"priority": "p1"})

    assert [incident["incident_id"] for incident in incidents] == [
        "INC-1042",
        "INC-1045",
    ]

    at_risk = incidents[1]

    assert at_risk["status"] == "OPEN"
    assert at_risk["remaining_minutes"] == 20
    assert at_risk["assigned_team"] == "Payments L1"
    assert at_risk["escalation_team"] == "Payments L2"


def test_list_incidents_tool_unknown_priority():
    assert list_incidents.invoke({"priority": "P9"}) == []


def test_list_applications_tool():
    applications = list_applications.invoke({})

    assert [
        (application["application_name"], application["status"])
        for application in applications
    ] == [
        ("Payment Processing", "DEGRADED"),
        ("Card Management", "HEALTHY"),
        ("Internet Banking", "HEALTHY"),
        ("ATM Switch", "DEGRADED"),
    ]
