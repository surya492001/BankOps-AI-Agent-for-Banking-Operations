import uuid

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def create_audit_log(
    db: Session,
    user_question: str,
    recommendation: str | None,
    incident_id: str | None = None,
    tools_called: str | None = None,
    sources: str | None = None,
    approved: bool | None = None,
    action_taken: str | None = None,
    request_id: str | None = None,
    approved_by: str | None = None,
    escalation_team: str | None = None
):
    audit = AuditLog(
        request_id=request_id or str(uuid.uuid4()),
        incident_id=incident_id,
        user_question=user_question,
        tools_called=tools_called,
        sources=sources,
        recommendation=recommendation,
        approved=approved,
        approved_by=approved_by,
        action_taken=action_taken,
        escalation_team=escalation_team
    )

    db.add(audit)
    db.commit()
    db.refresh(audit)

    return audit


def get_audit_logs(
    db: Session,
    incident_id: str | None = None,
    limit: int = 20
):
    query = db.query(AuditLog)

    if incident_id:
        query = query.filter(AuditLog.incident_id == incident_id)

    return (
        query
        .order_by(AuditLog.created_at.desc(), AuditLog.audit_id.desc())
        .limit(limit)
        .all()
    )


def serialize_audit_log(audit: AuditLog) -> dict:
    return {
        "audit_id": audit.audit_id,
        "request_id": audit.request_id,
        "incident_id": audit.incident_id,
        "user_question": audit.user_question,
        "tools_called": audit.tools_called,
        "sources": audit.sources,
        "recommendation": audit.recommendation,
        "approved": audit.approved,
        "approved_by": audit.approved_by,
        "action_taken": audit.action_taken,
        "escalation_team": audit.escalation_team,
        "created_at": audit.created_at
    }
