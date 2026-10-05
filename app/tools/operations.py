from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.models.incident import Incident
from app.models.sla import SLAPolicy
from app.models.application import Application
from app.services.escalation_service import get_escalation_state
from app.services.sla_service import calculate_sla
from langchain_core.tools import tool

@tool
def get_incident(incident_id: str) -> dict:
    """
    Retrieve an incident from PostgreSQL.
    """

    db: Session = SessionLocal()

    try:
        incident = (
            db.query(Incident)
            .filter(Incident.incident_id == incident_id)
            .first()
        )

        if not incident:
            return {
                "error": f"Incident {incident_id} not found"
            }

        return {
            "incident_id": incident.incident_id,
            "title": incident.title,
            "priority": incident.priority,
            "status": incident.status,
            "description": incident.description,
            "application_id": incident.application_id,
            "assigned_team": incident.assigned_team
        }

    finally:
        db.close()

@tool
def check_sla(incident_id: str) -> dict:


    """
    Check the SLA status of an incident.
    """

    db: Session = SessionLocal()

    try:
        # Find incident
        incident = (
            db.query(Incident)
            .filter(Incident.incident_id == incident_id)
            .first()
        )

        if not incident:
            return {
                "error": f"Incident {incident_id} not found"
            }

        # Find SLA policy based on priority
        sla = (
            db.query(SLAPolicy)
            .filter(SLAPolicy.priority == incident.priority)
            .first()
        )

        if not sla:
            return {
                "error": f"No SLA policy found for priority {incident.priority}"
            }

        # Current UTC time
        current_time = datetime.now(timezone.utc).replace(tzinfo=None)

        # Calculate elapsed time
        elapsed_minutes = int(
            (current_time - incident.created_at).total_seconds() / 60
        )

        # Calculate remaining SLA
        remaining_minutes = (
            sla.resolution_minutes - elapsed_minutes
        )

        # Determine status
        if remaining_minutes <= 0:
            sla_status = "BREACHED"
        elif remaining_minutes <= 30:
            sla_status = "AT_RISK"
        else:
            sla_status = "WITHIN_SLA"

        # The escalation decision comes from the same rule the API
        # enforces, so the agent's recommendation and the Approve &
        # Escalate action can never disagree.
        escalation = get_escalation_state(db, incident_id)

        return {
            "incident_id": incident.incident_id,
            "priority": incident.priority,
            "elapsed_minutes": elapsed_minutes,
            "sla_limit_minutes": sla.resolution_minutes,
            "remaining_minutes": max(remaining_minutes, 0),
            "sla_status": sla_status,
            "escalation_team": sla.escalation_team,
            "escalation_decision": escalation["decision"],
            "escalation_reason": escalation["reason"],
            "already_escalated": escalation["escalation"] is not None
        }

    finally:
        db.close()

@tool
def get_application(application_id: int) -> dict:
    """
    Retrieve application details from PostgreSQL.
    """

    db: Session = SessionLocal()

    try:
        application = (
            db.query(Application)
            .filter(Application.application_id == application_id)
            .first()
        )

        if not application:
            return {
                "error": f"Application {application_id} not found"
            }

        return {
            "application_id": application.application_id,
            "application_code": application.application_code,
            "application_name": application.application_name,
            "status": application.status,
            "description": application.description
        }

    finally:
        db.close()


@tool
def list_incidents(priority: str | None = None) -> list[dict]:
    """
    List incidents with their current SLA status.

    Use this for questions that span several incidents, such as which
    incidents are open, at risk or closest to breaching SLA.
    Optionally filter by priority (P1, P2 or P3).
    """

    db: Session = SessionLocal()

    try:
        query = db.query(Incident)

        if priority:
            query = query.filter(Incident.priority == priority.upper())

        policies = {
            sla.priority: sla
            for sla in db.query(SLAPolicy).all()
        }

        incidents = []

        for incident in query.order_by(Incident.incident_id).all():

            summary = {
                "incident_id": incident.incident_id,
                "title": incident.title,
                "priority": incident.priority,
                "status": incident.status,
                "application_id": incident.application_id,
                "assigned_team": incident.assigned_team
            }

            sla = policies.get(incident.priority)

            if sla:
                result = calculate_sla(incident, sla)

                summary["sla_status"] = result["sla_status"]
                summary["remaining_minutes"] = result["remaining_minutes"]
                summary["escalation_team"] = result["escalation_team"]

            incidents.append(summary)

        return incidents

    finally:
        db.close()


@tool
def list_applications() -> list[dict]:
    """
    List all applications with their current status.

    Use this to find an application by name when its ID is not known.
    """

    db: Session = SessionLocal()

    try:
        applications = (
            db.query(Application)
            .order_by(Application.application_id)
            .all()
        )

        return [
            {
                "application_id": application.application_id,
                "application_code": application.application_code,
                "application_name": application.application_name,
                "status": application.status,
                "description": application.description
            }
            for application in applications
        ]

    finally:
        db.close()
