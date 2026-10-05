from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.incidents import router as incidents_router
from app.api.agent import router as agent_router
from app.api.operations import router as operations_router
from app.api.sla import router as sla_router
from app.api.applications import router as application_router
from app.api.audit import router as audit_router
from app.api.demo import router as demo_router
from app.database.database import SessionLocal, ensure_schema
from app.services.demo_service import seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_schema()

    db = SessionLocal()

    try:
        seed_if_empty(db)
    finally:
        db.close()

    yield


app = FastAPI(
    title="BankOps AI",
    description="AI-powered banking operations assistant",
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(incidents_router)
app.include_router(agent_router)
app.include_router(operations_router)
app.include_router(sla_router)
app.include_router(application_router)
app.include_router(audit_router)
app.include_router(demo_router)


@app.get("/")
def root():
    return {
        "application": "BankOps AI",
        "status": "running"
    }
