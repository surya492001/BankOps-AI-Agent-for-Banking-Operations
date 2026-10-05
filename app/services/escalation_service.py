from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.escalation import Escalation
from app.models.incident import Incident, IncidentHistory
from app.services.audit_service import create_audit_log
from app.services.sla_service import get_incident_sla


ESCALATED = "ESCALATED"

# The escalation decision for an incident. The agent reports this
# decision rather than working it out itself.
RECOMMENDED = "ESCALATION RECOMMENDED"
NOT_RECOMMENDED = "ESCALATION NOT RECOMMENDED"
NOT_APPLICABLE = "ESCALATION NOT APPLICABLE"

# Incidents in these states are finished, so escalation no longer applies.
CLOSED_STATUSES = {"RESOLVED", "CLOSED"}

# Escalation is only allowed once the SLA is under pressure.
ESCALATION_SLA_STATUSES = {"AT_RISK", "BREACHED"}


def serialize_escalation(escalation: Escalation) -> dict:
    return {
        "escalation_id": escalation.escalation_id,
        "incident_id": escalation.incident_id,
        "escalation_team": escalation.escalation_team,
        "reason": escalation.reason,
        "status": escalation.status,
        "created_at": escalation.created_at
    }


def get_latest_escalation(
    db: Session,
    incident_id: str
):
    return (
        db.query(Escalation)
        .filter(Escalation.incident_id == incident_id)
        .order_by(Escalation.created_at.desc(), Escalation.escalation_id.desc())
        .first()
    )


def get_escalation_state(
    db: Session,
    incident_id: str
):
    """
    Decide whether an incident can be escalated right now.

    This is the single rule used by both the API and the UI, so the
    Approve & Escalate button is only offered when the escalation
    would actually be accepted.
    """

    incident = (
        db.query(Incident)
        .filter(Incident.incident_id == incident_id)
        .first()
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    sla = get_incident_sla(db, incident_id)

    escalation = get_latest_escalation(db, incident_id)

    status = (incident.status or "").upper()

    if status == ESCALATED:
        decision = NOT_APPLICABLE
        reason = "Incident has already been escalated."

    elif status in CLOSED_STATUSES:
        decision = NOT_APPLICABLE
        reason = f"Incident is {status}; escalation is not applicable."

    elif sla["sla_status"] not in ESCALATION_SLA_STATUSES:
        decision = NOT_RECOMMENDED
        reason = (
            "SLA is WITHIN_SLA; escalation requires an AT_RISK "
            "or BREACHED SLA."
        )

    else:
        decision = RECOMMENDED
        reason = (
            f"Incident is {status} and SLA is {sla['sla_status']}."
        )

    eligible = decision == RECOMMENDED

    return {
        "incident_id": incident.incident_id,
        "incident_status": incident.status,
        "sla_status": sla["sla_status"],
        "eligible": eligible,
        "decision": decision,
        "reason": reason,
        "escalation_team": sla["escalation_team"],
        "escalation": (
            serialize_escalation(escalation)
            if escalation
            else None
        )
    }


def escalate_incident(
    db: Session,
    incident_id: str,
    approved_by: str,
    reason: str | None = None,
    request_id: str | None = None
):
    """
    Escalate an incident after a human operator has approved it.

    Updates the incident, records the escalation and incident history,
    and writes an audit entry linked to the agent recommendation.
    """

    state = get_escalation_state(db, incident_id)

    if not state["eligible"]:
        raise HTTPException(
            status_code=409,
            detail=state["reason"]
        )

    incident = (
        db.query(Incident)
        .filter(Incident.incident_id == incident_id)
        .first()
    )

    team = state["escalation_team"]
    previous_team = incident.assigned_team
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    reason = reason or (
        f"{incident.priority} incident with SLA {state['sla_status']}."
    )

    escalation = Escalation(
        incident_id=incident_id,
        escalation_team=team,
        reason=reason,
        created_at=now,
        status="OPEN"
    )

    incident.status = ESCALATED
    incident.assigned_team = team

    history = IncidentHistory(
        incident_id=incident_id,
        status=ESCALATED,
        comment=(
            f"Escalated from {previous_team} to {team}. "
            f"Approved by {approved_by}. Reason: {reason}"
        ),
        created_at=now
    )

    db.add(escalation)
    db.add(history)
    db.commit()
    db.refresh(escalation)

    # Carry the agent recommendation that led to this action, when the
    # escalation was approved from an agent investigation.
    recommendation = None

    if request_id:
        investigation = (
            db.query(AuditLog)
            .filter(AuditLog.request_id == request_id)
            .order_by(AuditLog.audit_id)
            .first()
        )

        if investigation:
            recommendation = investigation.recommendation

    audit = create_audit_log(
        db=db,
        user_question=f"Approve escalation of {incident_id} to {team}",
        recommendation=recommendation,
        incident_id=incident_id,
        approved=True,
        approved_by=approved_by,
        action_taken="ESCALATE",
        escalation_team=team,
        request_id=request_id
    )

    return {
        "incident_id": incident_id,
        "status": ESCALATED,
        "previous_team": previous_team,
        "escalation_team": team,
        "escalation": serialize_escalation(escalation),
        "audit_id": audit.audit_id,
        "request_id": audit.request_id
    }
