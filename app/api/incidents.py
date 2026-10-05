from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.incident import Incident
from app.services.escalation_service import (
    escalate_incident,
    get_escalation_state
)


router = APIRouter(
    prefix="/incidents",
    tags=["Incidents"]
)


class EscalationRequest(BaseModel):
    # Escalation changes incident state, so it needs explicit human approval.
    approved: bool
    approved_by: str = "operations.engineer"
    reason: str | None = None
    # Request ID of the agent investigation that recommended this action.
    request_id: str | None = None


def serialize_incident(incident: Incident) -> dict:
    return {
        "incident_id": incident.incident_id,
        "title": incident.title,
        "description": incident.description,
        "priority": incident.priority,
        "status": incident.status,
        "application_id": incident.application_id,
        "created_at": incident.created_at,
        "assigned_team": incident.assigned_team
    }


@router.get("/{incident_id}")
def get_incident(
    incident_id: str,
    db: Session = Depends(get_db)
):
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

    return serialize_incident(incident)


@router.get("")
def get_all_incidents(
    db: Session = Depends(get_db)
):
    incidents = (
        db.query(Incident)
        .order_by(Incident.incident_id)
        .all()
    )

    return [
        serialize_incident(incident)
        for incident in incidents
    ]


@router.get("/{incident_id}/escalation")
def get_escalation(
    incident_id: str,
    db: Session = Depends(get_db)
):
    return get_escalation_state(
        db,
        incident_id
    )


@router.post("/{incident_id}/escalate")
def escalate(
    incident_id: str,
    request: EscalationRequest,
    db: Session = Depends(get_db)
):
    if not request.approved:
        raise HTTPException(
            status_code=400,
            detail="Escalation requires human approval."
        )

    return escalate_incident(
        db=db,
        incident_id=incident_id,
        approved_by=request.approved_by,
        reason=request.reason,
        request_id=request.request_id
    )
