from sqlalchemy import Column, Integer, String

from app.database.database import Base


class Application(Base):
    __tablename__ = "applications"

    application_id = Column(Integer, primary_key=True)
    application_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    description = Column(String)
    application_code = Column(String)
