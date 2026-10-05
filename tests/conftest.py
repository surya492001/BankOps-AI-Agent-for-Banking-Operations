import os
import tempfile
from datetime import datetime, timedelta, timezone

# The app reads its configuration at import time, so the test settings
# must be in place before anything from `app` is imported. Tests run on a
# throwaway SQLite database and vector index, and never call a real LLM.
_TEST_DIR = tempfile.mkdtemp(prefix="bankops-test-")

os.environ["DATABASE_URL"] = (
    f"sqlite:///{_TEST_DIR}/test.db?check_same_thread=false"
)
os.environ["CHROMA_PATH"] = f"{_TEST_DIR}/chroma"
os.environ["OPENROUTER_API_KEY"] = "test-key"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.rag.ingest import ingest  # noqa: E402

# The retriever opens the index when it is imported, so build it first.
ingest()

from app.database.database import SessionLocal, ensure_schema  # noqa: E402
from app.main import app  # noqa: E402
from app.models.audit_log import AuditLog  # noqa: E402
from app.models.incident import Incident  # noqa: E402
from app.services.demo_service import reset_demo_data  # noqa: E402


ensure_schema()


@pytest.fixture(autouse=True)
def db():
    """A database session on freshly seeded data for every test."""
    session = SessionLocal()

    session.query(AuditLog).delete()
    reset_demo_data(session)

    yield session

    session.close()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def set_incident(db):
    """Change an incident's age, priority or status for a scenario."""

    def _set(incident_id, age_minutes=None, **fields):
        incident = (
            db.query(Incident)
            .filter(Incident.incident_id == incident_id)
            .one()
        )

        if age_minutes is not None:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            # A few seconds of margin keeps the whole-minute elapsed time
            # stable while the test runs.
            incident.created_at = now - timedelta(
                minutes=age_minutes,
                seconds=5
            )

        for name, value in fields.items():
            setattr(incident, name, value)

        db.commit()

        return incident

    return _set
