# BankOps AI

**AI Agent for Banking Operations**

BankOps AI is an AI-powered operations assistant designed to help banking operations teams investigate and respond to incidents faster.

In a typical banking environment, operations teams may need to manually check incident records, SLA status, application health, and operational SOPs across multiple sources before deciding what action to take. BankOps AI brings these steps together into an AI-driven investigation workflow.

The agent retrieves verified incident and operational data, checks SLA status, evaluates the affected application's health, searches the SOP knowledge base using RAG, and generates an evidence-backed recommendation.

The system also includes an **audit trail** for recording agent investigations and recommendations, along with an **escalation capability** to support operational incident escalation workflows.

## Key Capabilities

- **Incident Investigation** – Retrieves incident details including priority, status, description, application, and assigned team.
- **SLA Monitoring** – Calculates elapsed time, remaining time, SLA status, and escalation requirements.
- **Application Health Check** – Retrieves the current status and details of affected banking applications.
- **RAG-based SOP Retrieval** – Searches the banking knowledge base using Chroma and returns SOP guidance only when an applicable document is found.
- **Evidence-based Recommendations** – Separates retrieved operational facts from AI-generated recommendations.
- **Incident Escalation** – Supports escalation workflows for incidents requiring operational intervention.
- **Audit Trail** – Records investigation requests, tools used, sources, recommendations, approvals, and actions for traceability.
- **Operations Dashboard** – Provides a Streamlit interface for viewing incidents, SLA status, application health, investigations, and agent activity.

## Architecture

```text
User
  │
  ▼
Streamlit Operations Dashboard
  │
  ▼
FastAPI
  │
  ▼
LangGraph AI Agent
  │
  ├──────────────► PostgreSQL
  │                 ├── Incidents
  │                 ├── Applications
  │                 ├── SLA
  │                 └── Audit Logs
  │
  ├──────────────► Operational Tools
  │                 ├── Incident Retrieval
  │                 ├── SLA Check
  │                 ├── Application Check
  │                 └── Escalation
  │
  └──────────────► Chroma RAG
                    │
                    ▼
               Banking SOPs

                    │
                    ▼
        Evidence + Recommendation
```

## Technology Stack

- Python
- FastAPI
- LangGraph
- LangChain
- PostgreSQL
- Chroma
- Hugging Face Embeddings
- Streamlit
- SQLAlchemy
- Docker
- LLM / Tool Calling

## Example Use Case

A user can ask:

> **Investigate INC-1042**

The agent retrieves the incident, checks its SLA, identifies the affected application, searches the relevant SOP, evaluates the operational situation, and produces an evidence-backed recommendation.

For example, when a P1 payment-processing incident is open and its SLA is breached, the agent can identify the breach, retrieve the applicable payment incident SOP, recommend escalation to the appropriate team, and record the investigation in the audit trail.

## Project Goal

The goal of BankOps AI is not simply to provide a chatbot. It is designed as an **AI-powered operational agent** that can retrieve enterprise data, reason over operational context, use tools, ground recommendations in organizational knowledge, and maintain traceability of its decisions and actions.