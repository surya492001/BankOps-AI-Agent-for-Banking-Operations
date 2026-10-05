"""
Single-process entry point for hosts that run only one app, such as
Streamlit Community Cloud.

It builds the SOP index, starts the FastAPI backend on localhost in a
background thread, and then runs the dashboard in app/ui/streamlit_app.py.
Locally, run the API and the dashboard separately as the README describes.
"""

import os
import runpy
import threading
import time
import urllib.request
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent

# Streamlit Cloud keeps secrets in st.secrets. Expose them as environment
# variables, which is where the rest of the app reads its settings.
try:
    for _key in (
        "OPENROUTER_API_KEY",
        "LLM_MODEL",
        "APP_PASSWORD",
        "BANKOPS_OPERATOR",
        "DATABASE_URL",
    ):
        if _key in st.secrets:
            os.environ.setdefault(_key, str(st.secrets[_key]))
except Exception:  # noqa: BLE001 - no secrets file, e.g. when running locally
    pass

# Demo defaults: SQLite with freshly seeded data and a throwaway SOP index.
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/bankops.db?check_same_thread=false")
os.environ.setdefault("CHROMA_PATH", "/tmp/chroma_db")
os.environ.setdefault("BANKOPS_API_URL", "http://127.0.0.1:8000")

API_PORT = 8000


@st.cache_resource(show_spinner=False)
def start_backend() -> bool:
    """Index the SOPs and start the API once per server process."""
    from app.rag.ingest import ingest

    ingest()

    import uvicorn

    from app.main import app

    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=API_PORT, log_level="warning")
    )
    threading.Thread(target=server.run, daemon=True).start()

    for _ in range(120):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{API_PORT}/incidents", timeout=2)
            return True
        except Exception:  # noqa: BLE001 - API still starting
            time.sleep(0.5)
    return False


start_backend()

runpy.run_path(str(ROOT / "app" / "ui" / "streamlit_app.py"), run_name="__main__")
