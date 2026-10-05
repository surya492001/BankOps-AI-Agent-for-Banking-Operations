from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.application import Application



router = APIRouter(
    prefix="/applications",
    tags=["Applications"]
)

@router.get("")
def get_applications(
    db: Session = Depends(get_db)
):
    applications = db.query(Application).all()

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
@router.get("/{application_id}")
def get_application(
    application_id: int,
    db: Session = Depends(get_db)
):
    application = (
        db.query(Application)
        .filter(Application.application_id == application_id)
        .first()
    )

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    return {
        "application_id": application.application_id,
        "application_code": application.application_code,
        "application_name": application.application_name,
        "status": application.status,
        "description": application.description
    }
