---
application: Internet Banking
priority: P2
---

# P2 Internet Banking Incident SOP

## Scope

This SOP applies to P2 incidents affecting Internet Banking, including login failures, authentication problems, and customer access issues.

## Initial Investigation

For a P2 Internet Banking incident:

1. Confirm the incident ID and priority.
2. Review the incident description and affected customer symptoms.
3. Check the current Internet Banking application status.
4. Check authentication and login-related dependencies where available.
5. Review recent deployments, configuration changes, and known incidents.
6. Check the current SLA status and remaining resolution time.

## SLA

The standard resolution SLA for a P2 incident is 240 minutes.

- More than 30 minutes remaining: WITHIN_SLA
- 30 minutes or less remaining: AT_RISK
- 0 minutes remaining: BREACHED

## SLA At Risk

If the incident is OPEN and the SLA is AT_RISK:

1. Prioritize investigation of the login or authentication issue.
2. Verify current Internet Banking health.
3. Investigate authentication failures and relevant dependencies.
4. Notify the incident owner.
5. Prepare escalation if resolution is unlikely within the remaining SLA.
6. Record investigation actions.

## SLA Breach

If the incident is OPEN and the SLA is BREACHED:

1. Escalate according to the approved Internet Banking escalation path.
2. Include incident ID, priority, SLA status, elapsed time, and application status.
3. Continue remediation.
4. Record escalation and investigation actions.
5. Provide regular stakeholder updates until resolution.

## Resolved Incident With SLA Breach

If the incident is RESOLVED but the SLA was BREACHED:

1. Document the SLA breach.
2. Verify that the customer-facing issue has been resolved.
3. Conduct a post-incident review.
4. Perform root-cause analysis.
5. Identify corrective and preventive actions.
6. Document lessons learned.

## Application Status

A current HEALTHY application status does not by itself prove that the application was healthy during the incident.

For a resolved incident, distinguish between:

- current application health
- application health during the incident

Historical application status should be verified where available.

## Evidence and Traceability

Record investigation findings, escalation actions, resolution details, and corrective actions for operational traceability.
