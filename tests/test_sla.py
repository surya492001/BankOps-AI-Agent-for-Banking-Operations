import pytest
from fastapi import HTTPException

from app.services.sla_service import get_incident_sla


# INC-1042 is P1, so its SLA limit is 120 minutes.
@pytest.mark.parametrize(
    "age_minutes, expected_status, expected_remaining",
    [
        (0, "WITHIN_SLA", 120),
        (89, "WITHIN_SLA", 31),
        (90, "AT_RISK", 30),
        (119, "AT_RISK", 1),
        (120, "BREACHED", 0),
        (500, "BREACHED", 0),
    ],
)
def test_sla_status_boundaries(
    db,
    set_incident,
    age_minutes,
    expected_status,
    expected_remaining,
):
    set_incident("INC-1042", age_minutes=age_minutes)

    sla = get_incident_sla(db, "INC-1042")

    assert sla["sla_status"] == expected_status
    assert sla["remaining_minutes"] == expected_remaining
    assert sla["elapsed_minutes"] == age_minutes


@pytest.mark.parametrize(
    "priority, limit, team",
    [
        ("P1", 120, "Payments L2"),
        ("P2", 240, "Payments L1"),
        ("P3", 480, "Operations Support"),
    ],
)
def test_sla_policy_follows_priority(db, set_incident, priority, limit, team):
    set_incident("INC-1042", age_minutes=10, priority=priority)

    sla = get_incident_sla(db, "INC-1042")

    assert sla["sla_limit_minutes"] == limit
    assert sla["escalation_team"] == team
    assert sla["sla_status"] == "WITHIN_SLA"


def test_same_age_breaches_p1_but_not_p2(db, set_incident):
    set_incident("INC-1042", age_minutes=150, priority="P1")
    assert get_incident_sla(db, "INC-1042")["sla_status"] == "BREACHED"

    set_incident("INC-1042", age_minutes=150, priority="P2")
    assert get_incident_sla(db, "INC-1042")["sla_status"] == "WITHIN_SLA"


def test_sla_incident_not_found(db):
    with pytest.raises(HTTPException) as error:
        get_incident_sla(db, "INC-9999")

    assert error.value.status_code == 404
    assert error.value.detail == "Incident not found"


def test_sla_policy_not_found(db, set_incident):
    set_incident("INC-1042", priority="P9")

    with pytest.raises(HTTPException) as error:
        get_incident_sla(db, "INC-1042")

    assert error.value.status_code == 404
    assert error.value.detail == "SLA policy not found"


def test_seeded_scenarios_have_expected_sla_states(db):
    expected = {
        "INC-1042": "BREACHED",
        "INC-1043": "WITHIN_SLA",
        "INC-1044": "BREACHED",
        "INC-1045": "AT_RISK",
        "INC-1046": "WITHIN_SLA",
    }

    for incident_id, sla_status in expected.items():
        assert get_incident_sla(db, incident_id)["sla_status"] == sla_status
