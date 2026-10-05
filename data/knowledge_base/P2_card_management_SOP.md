---
application: Card Management
priority: P2
---

# P2 Card Management Incident SOP

## Scope

This SOP applies to P2 incidents affecting the Card Management application, including card servicing delays, latency, and degraded card-management operations.

## Initial Investigation

For a P2 Card Management incident:

1. Confirm the incident ID and priority.
2. Review the incident description and reported symptoms.
3. Check the current Card Management application status.
4. Review recent deployments, configuration changes, and known incidents.
5. Check the current SLA status and remaining resolution time.

## SLA

The standard resolution SLA for a P2 incident is 240 minutes.

- More than 30 minutes remaining: WITHIN_SLA
- 30 minutes or less remaining: AT_RISK
- 0 minutes remaining: BREACHED

## SLA At Risk

If the incident is OPEN and the SLA is AT_RISK:

1. Prioritize investigation.
2. Confirm the current application health.
3. Notify the incident owner.
4. Prepare escalation if the issue cannot be resolved within the remaining SLA.
5. Record important investigation actions.

## SLA Breach

If the incident is OPEN and the SLA is BREACHED:

1. Escalate according to the approved Card Management escalation path.
2. Include the incident ID, priority, SLA status, elapsed time, and application status.
3. Continue investigation and remediation.
4. Record the escalation and actions taken.
5. Provide stakeholder updates until resolution.

## Application Degradation

If Card Management is DEGRADED or DOWN:

1. Validate application health.
2. Check recent deployments and configuration changes.
3. Review known incidents and dependencies.
4. Follow applicable troubleshooting procedures.
5. Escalate when required.

## Resolved Incident With SLA Breach

If the incident is RESOLVED but the SLA was BREACHED:

1. Document the SLA breach.
2. Conduct a post-incident review.
3. Perform root-cause analysis.
4. Identify corrective and preventive actions.
5. Document lessons learned.

## Evidence and Traceability

Incident actions, escalations, and important decisions should be recorded for operational traceability.
