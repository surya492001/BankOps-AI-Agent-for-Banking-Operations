from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database.database import Base


class Escalation(Base):
    __tablename__ = "escalations"

    escalation_id = Column(Integer, primary_key=True)
    incident_id = Column(String, nullable=False)
    escalation_team = Column(String, nullable=False)
    reason = Column(Text)
    created_at = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)
