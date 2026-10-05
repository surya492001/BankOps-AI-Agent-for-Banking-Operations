from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.sla import SLAPolicy


def calculate_sla(
    incident: Incident,
    sla: SLAPolicy
):
    """
    Calculate the current SLA status for an incident.
    """

    # Get current UTC time
    current_time = datetime.now(timezone.utc).replace(tzinfo=None)

    # Calculate how long the incident has been open
    elapsed_minutes = int(
        (current_time - incident.created_at).total_seconds() / 60
    )

    # Calculate remaining SLA time
    remaining_minutes = (
        sla.resolution_minutes - elapsed_minutes
    )

    # Determine SLA status
    if remaining_minutes <= 0:
        sla_status = "BREACHED"

    elif remaining_minutes <= 30:
        sla_status = "AT_RISK"

    else:
        sla_status = "WITHIN_SLA"

    return {
        "incident_id": incident.incident_id,
        "priority": incident.priority,
        "elapsed_minutes": elapsed_minutes,
        "sla_limit_minutes": sla.resolution_minutes,
        "remaining_minutes": max(remaining_minutes, 0),
        "sla_status": sla_status,
        "escalation_team": sla.escalation_team
    }


def get_incident_sla(
    db: Session,
    incident_id: str
):
    """
    Find an incident and its SLA policy,
    then calculate the current SLA status.
    """

    # Find incident
    incident = (
        db.query(Incident)
        .filter(
            Incident.incident_id == incident_id
        )
        .first()
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    # Find SLA policy based on priority
    sla = (
        db.query(SLAPolicy)
        .filter(
            SLAPolicy.priority == incident.priority
        )
        .first()
    )

    if not sla:
        raise HTTPException(
            status_code=404,
            detail="SLA policy not found"
        )

    return calculate_sla(
        incident,
        sla
    )
