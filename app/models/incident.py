from sqlalchemy import Column, DateTime, Integer, String, Text

from app.database.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    incident_id = Column(String, primary_key=True)
    title = Column(String)
    description = Column(Text)
    priority = Column(String)
    status = Column(String)
    application_id = Column(Integer)
    created_at = Column(DateTime)
    assigned_team = Column(String)


class IncidentHistory(Base):
    __tablename__ = "incident_history"

    history_id = Column(Integer, primary_key=True)
    incident_id = Column(String)
    status = Column(String)
    comment = Column(Text)
    created_at = Column(DateTime, nullable=False)
