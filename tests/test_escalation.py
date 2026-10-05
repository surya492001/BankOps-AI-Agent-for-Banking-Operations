import pytest

from app.models.escalation import Escalation
from app.models.incident import Incident, IncidentHistory


APPROVAL = {"approved": True, "approved_by": "surya"}


@pytest.mark.parametrize(
    "incident_id, eligible, team",
    [
        ("INC-1042", True, "Payments L2"),          # P1 OPEN, BREACHED
        ("INC-1045", True, "Payments L2"),          # P1 OPEN, AT_RISK
        ("INC-1043", False, "Payments L1"),         # P2 OPEN, WITHIN_SLA
        ("INC-1044", False, "Payments L1"),         # P2 RESOLVED, BREACHED
        ("INC-1046", False, "Operations Support"),  # P3 OPEN, WITHIN_SLA
    ],
)
def test_escalation_eligibility(client, incident_id, eligible, team):
    response = client.get(f"/incidents/{incident_id}/escalation")

    assert response.status_code == 200

    state = response.json()

    assert state["eligible"] is eligible
    assert (state["decision"] == "ESCALATION RECOMMENDED") is eligible
    assert state["escalation_team"] == team
    assert state["escalation"] is None


def test_escalation_state_incident_not_found(client):
    assert client.get("/incidents/INC-9999/escalation").status_code == 404


def test_escalate_breached_p1_incident(client, db):
    response = client.post("/incidents/INC-1042/escalate", json=APPROVAL)

    assert response.status_code == 200

    result = response.json()

    assert result["status"] == "ESCALATED"
    assert result["previous_team"] == "Payments L1"
    assert result["escalation_team"] == "Payments L2"

    # Incident is updated.
    incident = db.query(Incident).filter_by(incident_id="INC-1042").one()

    assert incident.status == "ESCALATED"
    assert incident.assigned_team == "Payments L2"

    # Escalation is recorded.
    escalations = db.query(Escalation).filter_by(incident_id="INC-1042").all()

    assert len(escalations) == 1
    assert escalations[0].escalation_team == "Payments L2"
    assert "BREACHED" in escalations[0].reason

    # SOP: "Record the escalation action in the incident history."
    history = (
        db.query(IncidentHistory)
        .filter_by(incident_id="INC-1042", status="ESCALATED")
        .one()
    )

    assert "Payments L2" in history.comment
    assert "surya" in history.comment


def test_escalate_at_risk_incident(client):
    response = client.post("/incidents/INC-1045/escalate", json=APPROVAL)

    assert response.status_code == 200
    assert response.json()["escalation_team"] == "Payments L2"


def test_escalation_writes_audit_trail(client):
    result = client.post("/incidents/INC-1042/escalate", json=APPROVAL).json()

    audit = client.get("/audit", params={"incident_id": "INC-1042"}).json()

    assert len(audit) == 1

    entry = audit[0]

    assert entry["audit_id"] == result["audit_id"]
    assert entry["request_id"] == result["request_id"]
    assert entry["incident_id"] == "INC-1042"
    assert entry["action_taken"] == "ESCALATE"
    assert entry["escalation_team"] == "Payments L2"
    assert entry["approved"] is True
    assert entry["approved_by"] == "surya"
    assert entry["created_at"]


def test_escalation_is_linked_to_agent_recommendation(client, db):
    from app.services.audit_service import create_audit_log

    investigation = create_audit_log(
        db=db,
        user_question="Investigate INC-1042",
        recommendation="ESCALATION RECOMMENDED - to Payments L2",
        incident_id="INC-1042",
    )

    client.post(
        "/incidents/INC-1042/escalate",
        json={**APPROVAL, "request_id": investigation.request_id},
    )

    audit = client.get("/audit", params={"incident_id": "INC-1042"}).json()

    # Newest first: the action, then the investigation that led to it.
    assert [entry["action_taken"] for entry in audit] == ["ESCALATE", None]
    assert audit[0]["request_id"] == audit[1]["request_id"]
    assert audit[0]["recommendation"] == "ESCALATION RECOMMENDED - to Payments L2"


def test_escalation_with_unknown_request_id_still_works(client):
    response = client.post(
        "/incidents/INC-1042/escalate",
        json={**APPROVAL, "request_id": "no-such-request"},
    )

    assert response.status_code == 200

    audit = client.get("/audit", params={"incident_id": "INC-1042"}).json()

    assert audit[0]["recommendation"] is None


def test_escalation_uses_supplied_reason(client, db):
    client.post(
        "/incidents/INC-1042/escalate",
        json={**APPROVAL, "reason": "Payment gateway degraded for 2 hours"},
    )

    escalation = db.query(Escalation).filter_by(incident_id="INC-1042").one()

    assert escalation.reason == "Payment gateway degraded for 2 hours"


def test_cannot_escalate_twice(client, db):
    assert client.post("/incidents/INC-1042/escalate", json=APPROVAL).status_code == 200

    response = client.post("/incidents/INC-1042/escalate", json=APPROVAL)

    assert response.status_code == 409
    assert "already been escalated" in response.json()["detail"]
    assert db.query(Escalation).filter_by(incident_id="INC-1042").count() == 1

    state = client.get("/incidents/INC-1042/escalation").json()

    assert state["eligible"] is False
    assert state["escalation"]["escalation_team"] == "Payments L2"


@pytest.mark.parametrize(
    "incident_id, expected_detail",
    [
        ("INC-1043", "WITHIN_SLA"),
        ("INC-1046", "WITHIN_SLA"),
        ("INC-1044", "RESOLVED"),
    ],
)
def test_ineligible_incident_is_not_escalated(
    client,
    db,
    incident_id,
    expected_detail,
):
    before = db.query(Incident).filter_by(incident_id=incident_id).one()
    status, team = before.status, before.assigned_team

    response = client.post(f"/incidents/{incident_id}/escalate", json=APPROVAL)

    assert response.status_code == 409
    assert expected_detail in response.json()["detail"]

    db.expire_all()
    after = db.query(Incident).filter_by(incident_id=incident_id).one()

    assert (after.status, after.assigned_team) == (status, team)
    assert db.query(Escalation).count() == 0
    assert client.get("/audit").json() == []


def test_closed_incident_is_not_escalated(client, set_incident):
    set_incident("INC-1042", status="CLOSED")

    response = client.post("/incidents/INC-1042/escalate", json=APPROVAL)

    assert response.status_code == 409


def test_escalation_requires_approval(client, db):
    response = client.post(
        "/incidents/INC-1042/escalate",
        json={"approved": False},
    )

    assert response.status_code == 400
    assert "human approval" in response.json()["detail"]
    assert db.query(Escalation).count() == 0
    assert client.get("/incidents/INC-1042").json()["status"] == "OPEN"


def test_escalation_rejects_missing_approval_field(client):
    response = client.post("/incidents/INC-1042/escalate", json={})

    assert response.status_code == 422


def test_escalate_incident_not_found(client):
    response = client.post("/incidents/INC-9999/escalate", json=APPROVAL)

    assert response.status_code == 404


def test_incident_becomes_eligible_when_sla_runs_down(client, set_incident):
    assert client.get("/incidents/INC-1043/escalation").json()["eligible"] is False

    # P2 limit is 240 minutes, so 215 minutes leaves 25: AT_RISK.
    set_incident("INC-1043", age_minutes=215)

    state = client.get("/incidents/INC-1043/escalation").json()

    assert state["sla_status"] == "AT_RISK"
    assert state["eligible"] is True
