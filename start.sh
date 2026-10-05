#!/usr/bin/env bash
# Container entrypoint: build the SOP index, start the API, then the UI.
set -euo pipefail

PORT="${PORT:-7860}"

python -m app.rag.ingest

uvicorn app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!

# Wait for the API (it creates the tables and seeds the demo data on start-up).
for _ in $(seq 1 60); do
  if python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/incidents', timeout=2)" 2>/dev/null; then
    break
  fi
  sleep 1
done

trap 'kill "$API_PID" 2>/dev/null || true' EXIT

exec streamlit run app/ui/streamlit_app.py \
  --server.port "$PORT" \
  --server.address 0.0.0.0 \
  --server.headless true \
  --browser.gatherUsageStats false
