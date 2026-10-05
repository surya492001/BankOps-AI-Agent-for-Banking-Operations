from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.services.sla_service import get_incident_sla


router = APIRouter(
    prefix="/sla",
    tags=["SLA"]
)


@router.get("/{incident_id}")
def check_sla(
    incident_id: str,
    db: Session = Depends(get_db)
):
    return get_incident_sla(
        db,
        incident_id
    )
