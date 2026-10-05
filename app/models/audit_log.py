from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from datetime import datetime

from app.database.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id = Column(Integer, primary_key=True, index=True)

    request_id = Column(String(100), nullable=True)

    incident_id = Column(String(50), nullable=True)

    user_question = Column(Text, nullable=True)

    tools_called = Column(Text, nullable=True)

    sources = Column(Text, nullable=True)

    recommendation = Column(Text, nullable=True)

    approved = Column(Boolean, nullable=True)

    approved_by = Column(String(100), nullable=True)

    action_taken = Column(Text, nullable=True)

    escalation_team = Column(String(100), nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
