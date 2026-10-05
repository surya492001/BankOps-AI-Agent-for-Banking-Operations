from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.escalation import Escalation
from app.models.incident import Incident, IncidentHistory
from app.models.sla import SLAPolicy


APPLICATIONS = [
    (1, "APP-PAY-001", "Payment Processing", "DEGRADED",
     "Handles domestic and international payment transactions"),
    (2, "APP-CARD-001", "Card Management", "HEALTHY",
     "Handles card lifecycle and card servicing operations"),
    (3, "APP-IB-001", "Internet Banking", "HEALTHY",
     "Customer internet banking application"),
    (4, "APP-ATM-001", "ATM Switch", "DEGRADED",
     "Routes ATM cash withdrawal and balance enquiry transactions"),
]

SLA_POLICIES = [
    (1, "P1", 120, "Payments L2"),
    (2, "P2", 240, "Payments L1"),
    (3, "P3", 480, "Operations Support"),
]

# (incident_id, title, description, priority, status, application_id,
#  minutes since creation, assigned_team)
# Ages are relative to "now" so each scenario is in a known SLA state
# straight after a reset.
INCIDENTS = [
    # P1, OPEN, SLA BREACHED, application DEGRADED -> escalate to Payments L2
    ("INC-1042", "Payment processing delays",
     "Multiple payment transactions are experiencing delays.",
     "P1", "OPEN", 1, 150, "Payments L1"),
    # P2, OPEN, WITHIN_SLA -> monitor, no escalation
    ("INC-1043", "Card management latency",
     "Users are experiencing slow response times.",
     "P2", "OPEN", 2, 60, "Cards L1"),
    # P2, RESOLVED after the SLA expired -> post-incident review
    ("INC-1044", "Internet banking login issue",
     "Some users are unable to log in.",
     "P2", "RESOLVED", 3, 300, "Digital Banking L2"),
    # P1, OPEN, SLA AT_RISK -> proactive escalation
    ("INC-1045", "UPI payment failures",
     "A rising share of UPI payments are failing with timeout errors.",
     "P1", "OPEN", 1, 100, "Payments L1"),
    # P3 on an application with no SOP in the knowledge base
    ("INC-1046", "ATM cash withdrawal failures",
     "Cash withdrawals are intermittently declined at some ATMs.",
     "P3", "OPEN", 4, 45, "ATM Operations L1"),
]

# (incident_id, status, comment, minutes ago)
HISTORY = [
    ("INC-1042", "OPEN",
     "Incident assigned to Payments L1 for investigation.", 140),
    ("INC-1042", "INVESTIGATING",
     "Payment application health checked. Application is degraded.", 90),
    ("INC-1043", "OPEN", "Incident assigned to Cards L1.", 50),
]


def reset_demo_data(db: Session, clear_audit: bool = False) -> dict:
    """
    Restore the synthetic incident data to its starting state.

    Audit logs are the record of what was done, so they are kept unless
    clear_audit is set (used to start a demo from a clean slate).
    """

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if clear_audit:
        db.query(AuditLog).delete()

    db.query(Escalation).delete()
    db.query(IncidentHistory).delete()
    db.query(Incident).delete()
    db.query(SLAPolicy).delete()
    db.query(Application).delete()

    for application_id, code, name, status, description in APPLICATIONS:
        db.add(
            Application(
                application_id=application_id,
                application_code=code,
                application_name=name,
                status=status,
                description=description
            )
        )

    for sla_id, priority, minutes, team in SLA_POLICIES:
        db.add(
            SLAPolicy(
                sla_id=sla_id,
                priority=priority,
                resolution_minutes=minutes,
                escalation_team=team
            )
        )

    # Applications must exist before the incidents that reference them.
    db.flush()

    for (incident_id, title, description, priority, status,
         application_id, age_minutes, team) in INCIDENTS:
        db.add(
            Incident(
                incident_id=incident_id,
                title=title,
                description=description,
                priority=priority,
                status=status,
                application_id=application_id,
                created_at=now - timedelta(minutes=age_minutes),
                assigned_team=team
            )
        )

    db.flush()

    for incident_id, status, comment, minutes_ago in HISTORY:
        db.add(
            IncidentHistory(
                incident_id=incident_id,
                status=status,
                comment=comment,
                created_at=now - timedelta(minutes=minutes_ago)
            )
        )

    db.commit()

    return {
        "applications": len(APPLICATIONS),
        "sla_policies": len(SLA_POLICIES),
        "incidents": len(INCIDENTS)
    }


def seed_if_empty(db: Session) -> bool:
    """Seed a new database so the app is usable on first start."""
    if db.query(Incident).first():
        return False

    reset_demo_data(db)

    return True
