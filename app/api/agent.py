import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.graph import ask_agent
from app.database.database import get_db
from app.services.audit_service import create_audit_log


router = APIRouter(
    prefix="/agent",
    tags=["AI Agent"]
)


INCIDENT_ID_PATTERN = re.compile(r"\bINC-\d+\b", re.IGNORECASE)


class AgentRequest(BaseModel):
    question: str


def find_incident_id(question: str) -> str | None:
    """Return the incident a question is about, when it names exactly one."""
    incident_ids = {
        match.upper()
        for match in INCIDENT_ID_PATTERN.findall(question)
    }

    if len(incident_ids) == 1:
        return incident_ids.pop()

    return None


@router.post("/chat")
def chat(
    request: AgentRequest,
    db: Session = Depends(get_db)
):

    result = ask_agent(request.question)

    answer = result["answer"]

    incident_id = find_incident_id(request.question)

    audit = create_audit_log(
        db=db,
        user_question=request.question,
        recommendation=answer,
        incident_id=incident_id,
        tools_called=", ".join(result["tools_called"]),
        sources=", ".join(result["sources"])
    )

    return {
        "question": request.question,
        "answer": answer,
        "audit_id": audit.audit_id,
        "request_id": audit.request_id,
        "incident_id": incident_id,
        "model": result.get("model"),
        "tools_called": result["tools_called"],
        "tool_inputs": result.get("tool_inputs", []),
        "sources": result["sources"]
    }
