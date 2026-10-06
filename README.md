# BankOps AI

**AI Agent for Banking Operations**

BankOps AI helps banking operations teams investigate and respond to incidents faster.

In a typical bank, an engineer checks incident records, SLA status, application health and operational SOPs across several systems before deciding what to do. BankOps AI brings those checks into one investigation: the agent reads the incident, checks its SLA, looks up the affected application, retrieves the applicable SOP with RAG, and produces an evidence-backed recommendation.

The agent only reads. It cannot change anything. If escalation is warranted, a person reviews the recommendation and approves it, and every step is written to an audit trail.

## Demo scenario

**INC-1042** is a P1 *Payment processing delays* incident that is open and past its SLA.

1. Open the dashboard and click **Investigate INC-1042**.
2. The agent gathers the incident, SLA, application status and the payment SOP, then writes an investigation summary and an escalation decision.
3. A card appears under the answer: *"Incident is OPEN and SLA is BREACHED. Escalation changes the incident, so it needs your approval."*
4. Click **Approve & escalate to Payments L2**. The incident becomes `ESCALATED`, is reassigned to Payments L2, and a green confirmation appears.
5. The **Audit trail** in the same card shows the investigation and the approved escalation, linked by one request ID.

The sidebar has **Reset demo data** to start again.

## Key capabilities

- **Incident investigation**: priority, status, description, application and assigned team.
- **SLA monitoring**: elapsed and remaining time, SLA status (`WITHIN_SLA`, `AT_RISK`, `BREACHED`) and the escalation team from the SLA policy.
- **Application health lookup**: current status and details of the affected application.
- **RAG-based SOP retrieval**: searches the SOP knowledge base (Chroma) and returns guidance only when an applicable SOP exists. If none applies, the agent says so and gives no steps, instead of inventing them.
- **Evidence-based recommendations**: the answer lists the tools it called and the facts they returned, separate from its own recommendation.
- **Controlled escalation**: a deterministic rule decides whether escalation is recommended (incident `OPEN` and SLA `AT_RISK` or `BREACHED`). The agent reports that decision but cannot act on it. A person approves with a button, and the API enforces the same rule, so an ineligible incident cannot be escalated.
- **Audit trail**: records the question, tools used, sources, recommendation, approver, action taken and team, for traceability.
- **Operations dashboard**: Streamlit UI with incident and SLA overview, application health, investigation chat, escalation and audit trail.

## Architecture

```text
User
  │
  ▼
Streamlit dashboard ───────────────┐
  │                                │ Approve & escalate
  ▼                                ▼ (human approval)
FastAPI ──────────────► POST /incidents/{id}/escalate
  │                              │
  ▼                              │ same eligibility rule
LangGraph agent (read-only)      │
  │                              ▼
  ├──► Tools: get_incident · check_sla · get_application
  │           list_incidents · list_applications · search_sop
  │                │
  │                ├──► PostgreSQL: incidents, applications, SLA policies,
  │                │                escalations, audit logs
  │                └──► Chroma RAG ──► banking SOPs (markdown)
  │
  ▼
Evidence + recommendation ──► audit log
```

## Technology stack

- Python, FastAPI, SQLAlchemy
- LangGraph and LangChain (tool-calling agent)
- LLM through OpenRouter (model set by `LLM_MODEL`, default `openrouter/free`)
- PostgreSQL (Docker)
- Chroma with ONNX embeddings (`all-MiniLM-L6-v2`, no torch)
- Streamlit
- pytest

## Getting started

Requirements: Python 3.12, Docker, and an [OpenRouter](https://openrouter.ai) API key.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`. For the bundled database the connection string is `postgresql://bankops:opsfde@localhost:5432/bankops`. Add your `OPENROUTER_API_KEY`. Optionally set `LLM_MODEL` to pin a model.

Start the database, ingest the SOPs, then run the API and the UI in two terminals:

```bash
docker compose up -d
python -m app.rag.ingest
```

```bash
uvicorn app.main:app --port 8000
```

```bash
streamlit run app/ui/streamlit_app.py
```

Open http://localhost:8501. On first start the API creates the tables and loads the demo data (4 applications, 3 SLA policies, 5 incidents).

## Deploying a demo link

```text
GitHub ──► Render PostgreSQL ──► Render FastAPI ──► Streamlit Community Cloud
 (code)      (incidents, audit)    (agent, tools,       (dashboard only)
                                    SOP search)
```

The code lives on GitHub. Render hosts the database and the API, and Streamlit Community Cloud hosts only the dashboard, which calls the API over HTTPS.

### 1. Backend on Render

`render.yaml` is a Render Blueprint that creates a free PostgreSQL database and the API service.

1. On [Render](https://render.com) choose **New → Blueprint**, connect your GitHub repository, and apply it.
2. When asked, enter `OPENROUTER_API_KEY`. The blueprint sets `LLM_MODEL` to `openrouter/free` (change it to a paid model such as `anthropic/claude-haiku-4.5` for steadier answers), wires `DATABASE_URL` to the database, and generates an `API_KEY`.
3. After the deploy, copy the service URL (`https://bankops-api-xxxx.onrender.com`) and open the service's **Environment** tab to copy the generated `API_KEY`.
4. Check `https://<your-service>.onrender.com/health`. It should return `{"status":"ok"}`.

On first start the API creates the tables and loads the demo data. Every route except `/health` needs the `X-API-Key` header, so only the dashboard can use the API and spend your LLM key.

### 2. Dashboard on Streamlit Community Cloud

1. On [Streamlit Community Cloud](https://streamlit.io/cloud) choose **Create app**, pick the repository and branch, and set the main file to `app/ui/streamlit_app.py`. It installs the small `app/ui/requirements.txt`, so the dashboard needs no ML libraries. Under **Advanced settings** choose Python 3.12.
2. Open **Secrets** and add:

```toml
BANKOPS_API_URL = "https://bankops-api-xxxx.onrender.com"
BANKOPS_API_KEY = "the API_KEY generated by Render"
APP_PASSWORD = "a password for visitors"
```

`APP_PASSWORD` puts a password prompt in front of the dashboard. Set it for any public link.

### What to expect on the free tiers

- **The API sleeps after about 15 minutes idle.** The first visit then waits up to a minute while it wakes, and the dashboard shows a "Waking the backend" message. Open the link a few minutes before a demo.
- **Render's free PostgreSQL expires after about 30 days.** Check Render's current terms, and recreate the database or upgrade it if you need the link for longer.
- **The API runs in 512 MB.** The app uses ONNX embeddings instead of torch, which should fit, but watch the first deploy for out-of-memory errors.
- **Set a spending limit** on the OpenRouter key. A public link spends your credit.

### Single-process alternatives

Two simpler options run the API and dashboard together on SQLite, with demo data that resets whenever the app restarts:

- **Streamlit Community Cloud alone:** set the main file to the root `streamlit_app.py`. It starts the API inside the Streamlit process. Secrets: `OPENROUTER_API_KEY`, `LLM_MODEL`, `APP_PASSWORD`, and optionally `DATABASE_URL` to use a hosted PostgreSQL.
- **Any Docker host:** the `Dockerfile` and `start.sh` build the same single container.

```bash
docker build -t bankops-ai .
docker run -p 7860:7860 -e OPENROUTER_API_KEY=... bankops-ai
```

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

The suite runs against a temporary SQLite database and a temporary Chroma store with a scripted fake LLM, so it needs no API key, Postgres or network. It covers the API, SLA logic, escalation rules, tools, SOP retrieval and the agent flow.

To exercise the real agent end to end, start the API and run the live scenarios. These call the real LLM, and reset the demo data before and after.

```bash
python scripts/run_scenarios.py              # all scenarios
python scripts/run_scenarios.py hero no_sop  # only the named ones
```

Scenarios cover a breached P1, an at-risk P1, an incident within SLA, a resolved incident, an incident with no SOP, an unknown incident, an SOP question with no match, a request to escalate, an already-escalated incident, a P1 list and an application health question.

## Project layout

```text
app/
  api/        FastAPI routes: agent, incidents, audit, operations, demo
  agents/     LangGraph agent and system prompt
  tools/      read-only tools the agent can call
  services/   escalation rule, audit log, demo data
  rag/        SOP parsing, ingestion and retrieval
  models/     SQLAlchemy models
  ui/         Streamlit dashboard
data/knowledge_base/   SOPs (markdown with application and priority front matter)
scripts/               schema.sql, seed_data.sql, live scenario runner
tests/                 pytest suite
```

## Known limitations

- **Escalation is simulated.** It updates the incident and the audit trail but does not notify anyone. A production version would reassign the ticket in the ticketing system and page the on-call engineer.
- **The escalation team depends on priority only** (from the SLA policy), not on the application.
- **No user accounts.** The API is protected by one shared key, and the dashboard by one password. The approver is a fixed name from the `BANKOPS_OPERATOR` environment variable (default `operations.engineer`).
- **Free models vary.** `openrouter/free` routes each request to a different free model, so wording and quality differ between runs. Decisions such as the escalation recommendation are computed in code to stay consistent. Pin `LLM_MODEL` before a demo.
- **Resolved incidents carry no resolution timestamp**, so their SLA is not evaluated.
- **Only PostgreSQL runs in Docker.** The API and UI run directly on the host.
- All data is simulated.

## Project goal

BankOps AI is not meant to be a chatbot. It is an operational agent that retrieves enterprise data, reasons over it with tools, grounds its recommendations in organisational knowledge, keeps a human in control of actions that change state, and records what it did.
