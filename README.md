# BankOps AI

**AI agent for banking operations** — investigates incidents, checks SLA
exposure, looks up application health, retrieves the right SOP, and
recommends an action that a human then approves.

All banking data and services in this project are simulated. It is a
self-initiated portfolio project; no real customer or bank data is used.

## The demo in one flow

`INC-1042` is the hero scenario: a P1 payment incident with a breached SLA
on a degraded application.

1. **Dashboard** shows open P1s, SLA at risk / breached, degraded applications.
2. **Investigate** — the agent calls its tools: incident, SLA, application, SOP.
3. **Evidence-backed conclusion** — "ESCALATION RECOMMENDED - to Payments L2",
   citing the P1 payment SOP.
4. **Approve & escalate** — a human clicks the button. The agent cannot
   escalate on its own.
5. **Action** — the incident becomes `ESCALATED` and moves to Payments L2.
6. **Audit trail** — the investigation and the approved action are recorded
   under the same request ID.

## Features

1. Incident investigation
2. SLA monitoring (`WITHIN_SLA` / `AT_RISK` / `BREACHED`)
3. Application health lookup
4. RAG-based SOP retrieval (Chroma)
5. Evidence-based agent reasoning (LangGraph + tool calling)
6. No-SOP protection — if no SOP is relevant, the agent says so instead of inventing one
7. Controlled incident escalation with human approval
8. Audit trail
9. Streamlit operations dashboard

## Architecture

```
Streamlit UI ──HTTP──> FastAPI
                         ├── /agent/chat ──> LangGraph agent ──> LLM (OpenRouter)
                         │                      ├── get_incident / list_incidents ──┐
                         │                      ├── check_sla ──────────────────────┤
                         │                      ├── get_application / list_applications ──> PostgreSQL
                         │                      └── search_sop ──> Chroma (SOP markdown)
                         ├── /incidents, /sla, /applications, /operations/summary
                         ├── /incidents/{id}/escalate   (human-approved write)
                         └── /audit
```

The agent only has **read** tools. Escalation is a separate API action that
requires `approved: true` and is only accepted when the incident is open and
its SLA is `AT_RISK` or `BREACHED`. The same rule produces the escalation
decision the agent reports, so its recommendation and the Approve & escalate
button can never disagree.

## Project structure

```
app/
  main.py          FastAPI app; creates tables and seeds demo data on startup
  api/             HTTP routes
  agents/graph.py  LangGraph agent and system prompt
  tools/           Agent tools (incident, SLA, application)
  rag/             SOP ingest and retrieval
  services/        SLA, escalation, audit and demo-data logic
  models/          SQLAlchemy models
  ui/              Streamlit dashboard
data/knowledge_base/   SOP documents
scripts/               SQL schema/seed reference, live scenario runner
tests/                 pytest suite
```

## Setup

Requirements: Python 3.12, Docker, an [OpenRouter](https://openrouter.ai) API key.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then add your OPENROUTER_API_KEY
```

Start PostgreSQL:

```bash
docker compose up -d
```

Build the SOP index (run again whenever the SOP files change):

```bash
python -m app.rag.ingest
```

Start the API. It creates the tables and seeds the demo incidents on first start:

```bash
uvicorn app.main:app --port 8000
```

Start the dashboard in a second terminal:

```bash
streamlit run app/ui/streamlit_app.py
```

Open http://localhost:8501. API docs are at http://localhost:8000/docs.

**Reset demo data** in the sidebar restores the incidents and clears the
audit trail. Use it before a demo: incident ages are relative to the reset
time, so SLA states drift as time passes (`INC-1045` is `AT_RISK` for about
20 minutes after a reset, then becomes `BREACHED`).

## Adding an SOP

Add a markdown file to `data/knowledge_base/` that starts with a header
saying what it applies to, then run `python -m app.rag.ingest` again:

```
---
application: Card Management
priority: P2
---

# P2 Card Management Incident SOP
```

During an investigation the agent searches only the SOPs written for the
incident's application. Vector similarity ranks SOPs well, but a distance
score alone cannot tell whether an SOP really applies (generic incident
wording scores close to every SOP), so applicability is decided by this
header. If the application has no SOP, the agent is told
`NO_APPLICABLE_SOP` and must say so.

## Demo incidents

| Incident | Scenario | Expected outcome |
|----------|----------|------------------|
| INC-1042 | P1, open, SLA breached, application degraded | Escalation recommended to Payments L2 |
| INC-1045 | P1, open, SLA at risk | Escalation recommended to Payments L2 |
| INC-1043 | P2, open, within SLA | Monitor; escalation not recommended |
| INC-1044 | P2, resolved after an SLA breach | Post-incident review; escalation not applicable |
| INC-1046 | P3 on ATM Switch, which has no SOP | "No applicable SOP was found" |

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/incidents`, `/incidents/{id}` | Incident records |
| GET | `/sla/{id}` | SLA status for an incident |
| GET | `/applications`, `/applications/{id}` | Application health |
| GET | `/operations/summary` | Dashboard KPIs |
| POST | `/agent/chat` | Ask the agent |
| GET | `/incidents/{id}/escalation` | Whether the incident can be escalated, and to whom |
| POST | `/incidents/{id}/escalate` | Escalate (requires `approved: true`) |
| GET | `/audit?incident_id=` | Audit trail |
| POST | `/demo/reset` | Restore demo data |

## Testing

Unit and API tests run on a temporary SQLite database and vector index, with
a scripted stand-in for the LLM, so they need no database, API key or network:

```bash
pytest
```

They cover the API, SLA boundaries, escalation rules, agent tools, SOP
retrieval (including the no-SOP cases) and the agent workflow.

Live scenarios call the real LLM through the running API and check the
answers for eleven cases (hero, at risk, within SLA, resolved, no SOP,
unknown incident, already escalated, a user telling the agent to escalate,
and others):

```bash
python scripts/run_scenarios.py
```

## Known limitations

- Escalation teams come from the SLA policy, which is keyed by priority only.
  A P2 Card Management incident would therefore escalate to "Payments L1".
  The agent flags this kind of mismatch, but the data model does not yet
  hold an escalation path per application.
- A resolved incident has no resolution timestamp, so its SLA is still
  measured against the current time.
- No authentication. The approver name comes from `BANKOPS_OPERATOR`.
- With the default `openrouter/free` model, OpenRouter may route each request
  to a different free model, so answer style varies and free-tier rate limits
  apply. Set `LLM_MODEL` to pin one.
- Runs locally. Only PostgreSQL is containerised.

## Tech stack

Python, FastAPI, PostgreSQL, SQLAlchemy, LangGraph, LangChain, Chroma,
sentence-transformers, OpenRouter, Streamlit, pytest, Docker.
