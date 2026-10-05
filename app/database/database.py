import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# Columns added after the first version of the schema. Existing databases
# get them added in place so no manual migration is needed.
ADDED_COLUMNS = {
    "audit_logs": {
        "incident_id": "VARCHAR(50)",
        "approved_by": "VARCHAR(100)",
        "escalation_team": "VARCHAR(100)",
    },
    "applications": {
        "application_code": "VARCHAR(50)",
    },
}


def ensure_schema():
    """Create missing tables and add any columns the models expect."""
    # Imported here so every model is registered on Base before create_all.
    from app.models import application, audit_log, escalation, incident, sla  # noqa: F401

    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)

    with engine.begin() as connection:
        for table, columns in ADDED_COLUMNS.items():
            existing = {
                column["name"]
                for column in inspector.get_columns(table)
            }

            for name, column_type in columns.items():
                if name not in existing:
                    connection.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN {name} {column_type}")
                    )
