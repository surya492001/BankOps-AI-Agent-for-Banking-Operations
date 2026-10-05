from sqlalchemy import Column, Integer, String

from app.database.database import Base


class SLAPolicy(Base):
    __tablename__ = "sla_policies"

    sla_id = Column(Integer, primary_key=True)
    priority = Column(String)
    resolution_minutes = Column(Integer)
    escalation_team = Column(String)
