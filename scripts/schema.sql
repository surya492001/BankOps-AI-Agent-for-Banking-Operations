-- The API creates these tables and seeds the demo data on startup, so
-- running this file by hand is optional. It documents the schema.

CREATE TABLE applications (
    application_id SERIAL PRIMARY KEY,
    application_name VARCHAR(100) NOT NULL,
    status VARCHAR(30) NOT NULL,
    description TEXT,
    application_code VARCHAR(50)
);

CREATE TABLE sla_policies (
    sla_id SERIAL PRIMARY KEY,
    priority VARCHAR(10) NOT NULL,
    resolution_minutes INTEGER NOT NULL,
    escalation_team VARCHAR(100) NOT NULL
);

CREATE TABLE incidents (
    incident_id VARCHAR(20) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    priority VARCHAR(10) NOT NULL,
    status VARCHAR(30) NOT NULL,
    application_id INTEGER REFERENCES applications(application_id),
    created_at TIMESTAMP NOT NULL,
    assigned_team VARCHAR(100)
);

CREATE TABLE incident_history (
    history_id SERIAL PRIMARY KEY,
    incident_id VARCHAR(20) REFERENCES incidents(incident_id),
    status VARCHAR(30),
    comment TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE escalations (
    escalation_id SERIAL PRIMARY KEY,
    incident_id VARCHAR(20) REFERENCES incidents(incident_id),
    escalation_team VARCHAR(100) NOT NULL,
    reason TEXT,
    created_at TIMESTAMP NOT NULL,
    status VARCHAR(30) NOT NULL
);

CREATE TABLE audit_logs (
    audit_id SERIAL PRIMARY KEY,
    request_id VARCHAR(100),
    incident_id VARCHAR(50),
    user_question TEXT,
    tools_called TEXT,
    sources TEXT,
    recommendation TEXT,
    approved BOOLEAN,
    approved_by VARCHAR(100),
    action_taken TEXT,
    escalation_team VARCHAR(100),
    created_at TIMESTAMP NOT NULL
);