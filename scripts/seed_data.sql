-- Demo data. The API seeds an empty database with this same data on
-- startup, and POST /demo/reset restores it (app/services/demo_service.py),
-- so running this file by hand is optional.
--
-- Incident ages are relative to NOW(), so each scenario starts in a known
-- SLA state.

INSERT INTO applications
(application_id, application_code, application_name, status, description)
VALUES
(1, 'APP-PAY-001', 'Payment Processing', 'DEGRADED',
 'Handles domestic and international payment transactions'),
(2, 'APP-CARD-001', 'Card Management', 'HEALTHY',
 'Handles card lifecycle and card servicing operations'),
(3, 'APP-IB-001', 'Internet Banking', 'HEALTHY',
 'Customer internet banking application'),
(4, 'APP-ATM-001', 'ATM Switch', 'DEGRADED',
 'Routes ATM cash withdrawal and balance enquiry transactions');


INSERT INTO sla_policies
(sla_id, priority, resolution_minutes, escalation_team)
VALUES
(1, 'P1', 120, 'Payments L2'),
(2, 'P2', 240, 'Payments L1'),
(3, 'P3', 480, 'Operations Support');


INSERT INTO incidents
(
    incident_id,
    title,
    description,
    priority,
    status,
    application_id,
    created_at,
    assigned_team
)
VALUES
-- P1, OPEN, SLA BREACHED, application DEGRADED -> escalate to Payments L2
(
    'INC-1042',
    'Payment processing delays',
    'Multiple payment transactions are experiencing delays.',
    'P1', 'OPEN', 1,
    (NOW() AT TIME ZONE 'UTC') - INTERVAL '150 minutes',
    'Payments L1'
),
-- P2, OPEN, WITHIN_SLA -> monitor, no escalation
(
    'INC-1043',
    'Card management latency',
    'Users are experiencing slow response times.',
    'P2', 'OPEN', 2,
    (NOW() AT TIME ZONE 'UTC') - INTERVAL '60 minutes',
    'Cards L1'
),
-- P2, RESOLVED after the SLA expired -> post-incident review
(
    'INC-1044',
    'Internet banking login issue',
    'Some users are unable to log in.',
    'P2', 'RESOLVED', 3,
    (NOW() AT TIME ZONE 'UTC') - INTERVAL '300 minutes',
    'Digital Banking L2'
),
-- P1, OPEN, SLA AT_RISK -> proactive escalation
(
    'INC-1045',
    'UPI payment failures',
    'A rising share of UPI payments are failing with timeout errors.',
    'P1', 'OPEN', 1,
    (NOW() AT TIME ZONE 'UTC') - INTERVAL '100 minutes',
    'Payments L1'
),
-- P3 on an application with no SOP in the knowledge base
(
    'INC-1046',
    'ATM cash withdrawal failures',
    'Cash withdrawals are intermittently declined at some ATMs.',
    'P3', 'OPEN', 4,
    (NOW() AT TIME ZONE 'UTC') - INTERVAL '45 minutes',
    'ATM Operations L1'
);


INSERT INTO incident_history
(incident_id, status, comment, created_at)
VALUES
(
    'INC-1042',
    'OPEN',
    'Incident assigned to Payments L1 for investigation.',
    (NOW() AT TIME ZONE 'UTC') - INTERVAL '140 minutes'
),
(
    'INC-1042',
    'INVESTIGATING',
    'Payment application health checked. Application is degraded.',
    (NOW() AT TIME ZONE 'UTC') - INTERVAL '90 minutes'
),
(
    'INC-1043',
    'OPEN',
    'Incident assigned to Cards L1.',
    (NOW() AT TIME ZONE 'UTC') - INTERVAL '50 minutes'
);
