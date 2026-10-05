from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.services.demo_service import reset_demo_data


router = APIRouter(
    prefix="/demo",
    tags=["Demo"]
)


@router.post("/reset")
def reset(
    clear_audit: bool = False,
    db: Session = Depends(get_db)
):
    return {
        "status": "reset",
        "audit_cleared": clear_audit,
        **reset_demo_data(db, clear_audit=clear_audit)
    }
