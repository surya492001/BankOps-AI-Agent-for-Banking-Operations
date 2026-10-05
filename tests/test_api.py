def test_root(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_get_all_incidents(client):
    response = client.get("/incidents")

    assert response.status_code == 200
    assert [incident["incident_id"] for incident in response.json()] == [
        "INC-1042",
        "INC-1043",
        "INC-1044",
        "INC-1045",
        "INC-1046",
    ]


def test_get_incident(client):
    response = client.get("/incidents/INC-1042")

    assert response.status_code == 200

    incident = response.json()

    assert incident["title"] == "Payment processing delays"
    assert incident["priority"] == "P1"
    assert incident["status"] == "OPEN"
    assert incident["application_id"] == 1
    assert incident["assigned_team"] == "Payments L1"


def test_get_incident_not_found(client):
    response = client.get("/incidents/INC-9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Incident not found"


def test_get_applications(client):
    response = client.get("/applications")

    assert response.status_code == 200
    assert len(response.json()) == 4


def test_get_application(client):
    response = client.get("/applications/1")

    assert response.status_code == 200

    application = response.json()

    assert application["application_name"] == "Payment Processing"
    assert application["application_code"] == "APP-PAY-001"
    assert application["status"] == "DEGRADED"


def test_get_application_not_found(client):
    assert client.get("/applications/999").status_code == 404


def test_get_application_rejects_non_numeric_id(client):
    assert client.get("/applications/payments").status_code == 422


def test_sla_endpoint(client):
    response = client.get("/sla/INC-1042")

    assert response.status_code == 200

    sla = response.json()

    assert sla["sla_status"] == "BREACHED"
    assert sla["sla_limit_minutes"] == 120
    assert sla["remaining_minutes"] == 0
    assert sla["escalation_team"] == "Payments L2"


def test_sla_endpoint_incident_not_found(client):
    assert client.get("/sla/INC-9999").status_code == 404


def test_operations_summary(client):
    response = client.get("/operations/summary")

    assert response.status_code == 200
    assert response.json() == {
        "p1_incidents": 2,
        "at_risk": 1,
        "sla_breached": 2,
        "degraded_applications": 2,
    }


def test_operations_summary_ignores_resolved_p1(client, set_incident):
    set_incident("INC-1045", status="RESOLVED")

    summary = client.get("/operations/summary").json()

    assert summary["p1_incidents"] == 1


def test_operations_summary_still_counts_escalated_p1(client):
    client.post("/incidents/INC-1042/escalate", json={"approved": True})

    summary = client.get("/operations/summary").json()

    assert summary["p1_incidents"] == 2


def test_demo_reset_restores_incidents_and_keeps_audit(client):
    client.post("/incidents/INC-1042/escalate", json={"approved": True})

    assert client.get("/incidents/INC-1042").json()["status"] == "ESCALATED"

    response = client.post("/demo/reset")

    assert response.status_code == 200
    assert response.json()["incidents"] == 5

    incident = client.get("/incidents/INC-1042").json()

    assert incident["status"] == "OPEN"
    assert incident["assigned_team"] == "Payments L1"
    assert client.get("/incidents/INC-1042/escalation").json()["escalation"] is None

    # The audit trail is a record of what happened, so a reset keeps it.
    audit = client.get("/audit", params={"incident_id": "INC-1042"}).json()

    assert len(audit) == 1
    assert audit[0]["action_taken"] == "ESCALATE"


def test_demo_reset_can_clear_audit_trail(client):
    client.post("/incidents/INC-1042/escalate", json={"approved": True})

    response = client.post("/demo/reset", params={"clear_audit": True})

    assert response.json()["audit_cleared"] is True
    assert client.get("/audit").json() == []
