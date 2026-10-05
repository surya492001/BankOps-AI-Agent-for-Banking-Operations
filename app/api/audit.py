from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.services.audit_service import get_audit_logs, serialize_audit_log


router = APIRouter(
    prefix="/audit",
    tags=["Audit"]
)


@router.get("")
def list_audit_logs(
    incident_id: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    return [
        serialize_audit_log(audit)
        for audit in get_audit_logs(db, incident_id, limit)
    ]
