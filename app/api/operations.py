from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.incident import Incident
from app.models.application import Application
from app.services.sla_service import get_incident_sla


router = APIRouter(
    prefix="/operations",
    tags=["Operations"]
)


@router.get("/summary")
def operations_summary(
    db: Session = Depends(get_db)
):
    incidents = db.query(Incident).all()
    applications = db.query(Application).all()

    p1_count = 0
    at_risk_count = 0
    breached_count = 0

    for incident in incidents:

        # The KPI is "P1 incidents open", so finished incidents don't count.
        if (
            incident.priority == "P1"
            and incident.status not in ("RESOLVED", "CLOSED")
        ):
            p1_count += 1

        try:
            sla_result = get_incident_sla(
                db,
                incident.incident_id
            )

            if sla_result["sla_status"] == "AT_RISK":
                at_risk_count += 1

            elif sla_result["sla_status"] == "BREACHED":
                breached_count += 1

        except Exception:
            continue

    degraded_count = sum(
        1
        for application in applications
        if application.status == "DEGRADED"
    )

    return {
        "p1_incidents": p1_count,
        "at_risk": at_risk_count,
        "sla_breached": breached_count,
        "degraded_applications": degraded_count
    }

