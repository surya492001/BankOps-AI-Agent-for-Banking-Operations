---
application: Payment Processing
priority: P1
---

# P1 Payment Processing Incident SOP

## Purpose

This procedure defines the standard response for Priority-1 incidents affecting payment processing services.

## P1 Incident Criteria

A P1 incident is a critical production issue that significantly impacts payment processing or prevents customers from completing payment transactions.

## Initial Investigation

When a P1 payment incident is reported:

1. Confirm the incident ID and severity.
2. Check the affected application status.
3. Review the incident description and recent resolution history.
4. Check the current SLA status and remaining resolution time.

## SLA Escalation

For a P1 incident, the standard resolution SLA is 120 minutes.

If 30 minutes or less remain before the SLA deadline, the incident should be treated as **SLA AT RISK**.

If the SLA has expired, the incident is considered **SLA BREACHED**.

## Application Degradation

If the Payment Processing application is reported as DEGRADED or DOWN:

1. Validate the application status.
2. Check for recent deployments or known incidents.
3. Review relevant payment-processing troubleshooting procedures.
4. Escalate to the Payments L2 support team when required.

## Escalation

For a P1 payment-processing incident approaching or exceeding its SLA:

- Escalation team: Payments L2
- Include the incident ID.
- Include the current SLA status.
- Include the remaining SLA time.
- Include the affected application and current application status.
- Record the escalation action in the incident history.

## Communication

The incident owner should provide regular updates to relevant stakeholders until the incident is resolved.

## Resolution

After the application is restored:

1. Validate payment processing functionality.
2. Confirm that the incident is resolved.
3. Update the incident record.
4. Document the root cause and resolution.
5. Close the incident according to the operational closure procedure.
