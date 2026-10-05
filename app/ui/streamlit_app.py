import html
import os
import time
from datetime import datetime

import requests
import streamlit as st

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------

API_URL = os.getenv("BANKOPS_API_URL", "http://127.0.0.1:8000")

# Recorded in the audit trail as the person who approved an escalation.
OPERATOR = os.getenv("BANKOPS_OPERATOR", "operations.engineer")

SUGGESTIONS = [
    ("Investigate INC-1042", "Investigate INC-1042 and tell me what I should do.", ":material/troubleshoot:"),
    ("Which P1s are closest to breaching SLA?", "Which P1 incidents are closest to breaching SLA?", ":material/timer:"),
    ("Is the payments gateway healthy?", "Is the payments gateway healthy right now?", ":material/monitor_heart:"),
    ("SOP for a failed NEFT batch", "What is the SOP for a failed NEFT batch?", ":material/menu_book:"),
]

st.set_page_config(
    page_title="BankOps AI",
    page_icon=":material/account_balance:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.session_state.setdefault("messages", [])
st.session_state.setdefault("pending", None)
st.session_state.setdefault("incident_id", "INC-1042")
st.session_state.setdefault("kpi_filter", None)
st.session_state.setdefault("investigation", None)
# Request ID of the latest agent investigation per incident, so an approved
# escalation is linked to the recommendation that led to it.
st.session_state.setdefault("request_ids", {})
st.session_state.setdefault("notice", None)


# ---------------------------------------------------------
# STYLES  (needs Streamlit >= 1.39)
# ---------------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500&display=swap');

    :root {
        color-scheme: dark;
        --bg: #0A0F1A;
        --panel: #111827;
        --panel-2: #161F32;
        --inset: #0C1322;
        --line: #232F48;
        --line-2: #2C3A58;
        --text: #E6EAF2;
        --text-2: #C5CEDF;
        --muted: #98A4BC;
        --accent: #6EA8FF;
        --amber: #F5B14C;
        --red: #FF6B6B;
        --green: #4ADE9A;
    }

    html, body, .stApp, [class*="css"] { font-family: 'Manrope', system-ui, sans-serif; }

    /* =====================================================
       THEME ENFORCEMENT
       Keeps every piece of text readable on the dark page,
       even if .streamlit/config.toml is missing or not loaded.
       ===================================================== */
    .stApp {
        background:
            radial-gradient(900px 420px at 85% -10%, rgba(110,168,255,.10), transparent 60%),
            var(--bg);
        color: var(--text);
    }
    [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: transparent; color: var(--text); }
    .stApp [data-testid="stMarkdownContainer"] { color: var(--text); }
    .stApp [data-testid="stMarkdownContainer"] a { color: var(--accent); }

    /* Widget labels and captions */
    .stApp [data-testid="stWidgetLabel"],
    .stApp [data-testid="stWidgetLabel"] * { color: var(--muted) !important; }
    .stApp [data-testid="stCaptionContainer"],
    .stApp [data-testid="stCaptionContainer"] * { color: var(--muted) !important; }

    /* Top bar, status widget, sidebar toggle */
    header[data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stHeader"] button, [data-testid="stHeader"] a,
    [data-testid="stStatusWidget"], [data-testid="stStatusWidget"] *,
    [data-testid="stSidebarCollapseButton"] *, [data-testid="stExpandSidebarButton"] * {
        color: var(--muted) !important;
    }
    #MainMenu, footer { visibility: hidden; }
    .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 7rem; }

    /* Alerts: st.error / st.warning / st.info */
    .stApp [data-testid="stAlert"] {
        background: #1B2236 !important; border: 1px solid #34415F; border-radius: 12px;
    }
    .stApp [data-testid="stAlert"] > div,
    .stApp [data-testid="stAlert"] [data-baseweb="notification"] { background: transparent !important; }
    .stApp [data-testid="stAlert"], .stApp [data-testid="stAlert"] * { color: var(--text) !important; }

    /* Spinner */
    .stApp [data-testid="stSpinner"], .stApp [data-testid="stSpinner"] * { color: var(--muted) !important; }

    /* Text input */
    .stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"] {
        background: var(--inset) !important; border-radius: 12px !important;
    }
    .stApp [data-baseweb="input"] { border: 1px solid var(--line-2) !important; }
    .stApp .stTextInput input {
        background: var(--inset) !important; color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important; caret-color: var(--accent);
        font-family: 'JetBrains Mono', monospace; padding: 10px 12px; border-radius: 12px;
    }
    .stApp .stTextInput input::placeholder { color: #8190AB !important; -webkit-text-fill-color: #8190AB !important; opacity: 1; }
    .stApp [data-baseweb="input"]:focus-within {
        border-color: var(--accent) !important; box-shadow: 0 0 0 3px rgba(110,168,255,.18);
    }

    /* Chat input (pinned bottom bar) */
    [data-testid="stBottom"], [data-testid="stBottom"] > div { background: transparent !important; }
    [data-testid="stBottomBlockContainer"] { background: linear-gradient(180deg, transparent, var(--bg) 40%) !important; }
    [data-testid="stChatInput"] {
        background: var(--panel) !important; border: 1px solid var(--line-2); border-radius: 16px;
    }
    [data-testid="stChatInput"] > div,
    [data-testid="stChatInput"] [data-baseweb="textarea"],
    [data-testid="stChatInput"] [data-baseweb="base-input"] { background: transparent !important; border: none !important; }
    [data-testid="stChatInput"]:focus-within {
        border-color: var(--accent); box-shadow: 0 0 0 3px rgba(110,168,255,.18);
    }
    [data-testid="stChatInput"] textarea {
        background: transparent !important; color: var(--text) !important;
        -webkit-text-fill-color: var(--text) !important; caret-color: var(--accent);
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: var(--muted) !important; -webkit-text-fill-color: var(--muted) !important; opacity: 1;
    }
    [data-testid="stChatInput"] button { background: transparent !important; color: var(--accent) !important; }
    [data-testid="stChatInput"] button svg { fill: var(--accent) !important; color: var(--accent) !important; }
    [data-testid="stChatInput"] button:disabled svg { fill: #4A5875 !important; }

    /* Buttons: set colour on the button and its inner text node */
    .stApp .stButton > button, .stApp .stDownloadButton > button,
    .stApp button[data-testid="stBaseButton-secondary"] {
        border-radius: 12px; font-weight: 600;
        background: var(--panel-2) !important; color: var(--text) !important;
        border: 1px solid var(--line-2) !important; transition: border-color .15s, transform .05s;
    }
    .stApp .stButton > button *, .stApp .stDownloadButton > button *,
    .stApp button[data-testid="stBaseButton-secondary"] * { color: var(--text) !important; }
    .stApp .stButton > button:hover, .stApp .stDownloadButton > button:hover,
    .stApp button[data-testid="stBaseButton-secondary"]:hover { border-color: var(--accent) !important; }
    .stApp .stButton > button:active { transform: translateY(1px); }
    .stApp .stButton > button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

    .stApp .stButton > button[kind="primary"],
    .stApp button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #7FB2FF, #5B93F0) !important;
        border: none !important; color: #07101F !important;
    }
    .stApp .stButton > button[kind="primary"] *,
    .stApp button[data-testid="stBaseButton-primary"] * { color: #07101F !important; }
    .stApp .stButton > button[kind="primary"]:hover,
    .stApp button[data-testid="stBaseButton-primary"]:hover { filter: brightness(1.08); }

    hr { border-color: var(--line) !important; }

    /* =====================================================
       LAYOUT AND COMPONENTS
       ===================================================== */

    /* ---------- Hero ---------- */
    .hero { display: flex; align-items: center; gap: 16px; margin-bottom: 26px; flex-wrap: wrap; }
    .mark {
        width: 46px; height: 46px; border-radius: 13px; display: grid; place-items: center;
        font-weight: 800; font-size: 1.3rem; color: #07101F !important;
        background: linear-gradient(135deg, #9CC4FF, #6EA8FF 55%, #4F86E8);
    }
    .stApp .hero-title {
        font-size: 1.9rem !important; font-weight: 800; letter-spacing: -0.03em;
        margin: 0 !important; padding: 0 !important; color: var(--text) !important; line-height: 1.2;
    }
    .stApp .hero-sub { margin: 2px 0 0 !important; color: var(--muted) !important; font-size: .95rem; }
    .hero .grow { flex: 1; }

    .pill {
        display: inline-flex; align-items: center; gap: 8px; padding: 7px 14px;
        border-radius: 999px; font-size: .8rem; font-weight: 600;
        background: var(--panel); border: 1px solid var(--line);
    }
    .pill .dot { width: 8px; height: 8px; border-radius: 50%; }
    .pill.ok { color: var(--green) !important; }
    .pill.ok .dot { background: var(--green); animation: pulse 2.4s ease-out infinite; }
    .pill.down { color: var(--red) !important; }
    .pill.down .dot { background: var(--red); }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(74,222,154,.5); }
        70% { box-shadow: 0 0 0 8px rgba(74,222,154,0); }
        100% { box-shadow: 0 0 0 0 rgba(74,222,154,0); }
    }
    @media (prefers-reduced-motion: reduce) { .pill .dot { animation: none !important; } }

    /* ---------- KPI tiles ---------- */
    .kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 28px; }
    .tile {
        position: relative; overflow: hidden; padding: 18px 20px; border-radius: 16px;
        background: linear-gradient(180deg, #141D31, #0F1727); border: 1px solid var(--line);
    }
    .tile::after {
        content: ""; position: absolute; right: -40px; top: -40px; width: 130px; height: 130px;
        border-radius: 50%; background: var(--tone); opacity: .14; filter: blur(22px);
    }
    .tile .n { font-size: 2.5rem; font-weight: 800; letter-spacing: -0.03em; line-height: 1; color: var(--tone) !important; display: block; position: relative; z-index: 1; }
    .tile .l { display: block; margin-top: 8px; color: var(--muted) !important; font-size: .85rem; font-weight: 500; position: relative; z-index: 1; }
    @media (max-width: 800px) { .kpis { grid-template-columns: repeat(2, 1fr); } }

    /* ---------- Chat ---------- */
    [data-testid="stChatMessage"] {
        background: var(--panel) !important; border: 1px solid var(--line);
        border-radius: 16px; padding: 18px 20px; margin-bottom: 12px; color: var(--text);
    }
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background: var(--panel-2) !important; border-color: var(--line-2);
    }
    [data-testid^="stChatMessageAvatar"] { background: #2A3B5E !important; border: none !important; }
    [data-testid^="stChatMessageAvatar"], [data-testid^="stChatMessageAvatar"] * { color: #E6EAF2 !important; }
    [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li { line-height: 1.7; }
    [data-testid="stChatMessage"] h1, [data-testid="stChatMessage"] h2, [data-testid="stChatMessage"] h3,
    [data-testid="stChatMessage"] h4 { font-weight: 700; letter-spacing: -0.01em; color: var(--text); }
    [data-testid="stChatMessage"] strong { color: #FFFFFF; }
    [data-testid="stChatMessage"] code {
        font-family: 'JetBrains Mono', monospace; background: #1B2740 !important; color: #BFD6FF !important;
        padding: 2px 6px; border-radius: 6px;
    }
    [data-testid="stChatMessage"] pre {
        background: var(--inset) !important; border: 1px solid var(--line); border-radius: 10px;
    }
    [data-testid="stChatMessage"] pre code { background: transparent !important; color: #D6E4FF !important; padding: 0; }
    [data-testid="stChatMessage"] table { border-collapse: collapse; width: 100%; }
    [data-testid="stChatMessage"] th, [data-testid="stChatMessage"] td {
        border: 1px solid var(--line-2) !important; padding: 8px 12px; color: var(--text) !important;
        background: transparent !important;
    }
    [data-testid="stChatMessage"] th { background: var(--panel-2) !important; font-weight: 700; }
    [data-testid="stChatMessage"] blockquote { border-left: 3px solid var(--accent); color: var(--text-2); }

    .chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
    .chip {
        font-family: 'JetBrains Mono', monospace; font-size: .78rem; color: #BFD6FF !important;
        background: #1B2740; border: 1px solid #2A3A5C; padding: 3px 10px; border-radius: 8px;
    }
    .meta { color: var(--muted) !important; font-size: .8rem; margin-top: 10px; }

    /* ---------- Welcome ---------- */
    .stApp .welcome-title {
        font-size: 1.5rem !important; font-weight: 700; letter-spacing: -0.02em;
        margin: 0 0 6px !important; padding: 0 !important; color: var(--text) !important;
    }
    .stApp .welcome-sub { color: var(--muted) !important; margin: 0 0 4px; max-width: 60ch; line-height: 1.6; }

    /* ---------- Side panels ---------- */
    .notice {
        display: flex; align-items: center; gap: 10px; margin: 4px 0 12px;
        padding: 12px 14px; border-radius: 12px; font-weight: 700; font-size: .95rem;
    }
    .notice .ic { width: 18px; height: 18px; flex: none; }
    .notice.success { background: rgba(74,222,154,.14); border: 1px solid var(--green); }
    .notice.success, .notice.success * { color: var(--green) !important; }
    .notice.error { background: rgba(255,107,107,.14); border: 1px solid var(--red); }
    .notice.error, .notice.error * { color: var(--red) !important; }
    .st-key-action {
        background: var(--panel); border: 1px solid var(--accent); border-radius: 16px;
        padding: 6px 18px 18px; margin-bottom: 8px;
    }
    .st-key-investigate, .st-key-sources {
        background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 20px;
    }
    .panel-h { font-size: 1rem; font-weight: 700; margin: 0 0 4px; color: var(--text) !important; }
    .panel-s { font-size: .85rem; color: var(--muted) !important; margin: 0 0 14px; line-height: 1.5; }
    .src { display: flex; align-items: center; gap: 10px; padding: 7px 0; color: var(--text-2) !important; font-size: .9rem; }
    .src i { width: 7px; height: 7px; border-radius: 50%; background: var(--accent); display: inline-block; }

    /* ---------- Investigation panel ---------- */
    .investigation-head {
        margin-top: 16px; padding: 16px 18px; border: 1px solid var(--line-2);
        border-radius: 14px; background: var(--inset);
    }
    .investigation-title { font-size: 1.1rem; font-weight: 700; color: #FFFFFF !important; font-family: 'JetBrains Mono', monospace; }
    .investigation-sub { font-size: .9rem; color: var(--text-2) !important; margin-top: 5px; line-height: 1.5; }
    .investigation-card {
        background: var(--inset); border: 1px solid var(--line); border-radius: 12px;
        padding: 11px 14px; margin-bottom: 10px;
    }
    .investigation-label { font-size: .75rem; font-weight: 600; color: var(--muted) !important; }
    .investigation-value { font-size: 1rem; font-weight: 700; color: var(--text) !important; margin-top: 2px; word-break: break-word; }
    .investigation-application {
        background: var(--inset); border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px;
        color: var(--text) !important;
    }
    .investigation-application .investigation-value { display: inline; margin: 0; }
    .investigation-application .investigation-label { display: inline; }
    .investigation-description {
        background: var(--inset); border: 1px solid var(--line); border-radius: 12px;
        padding: 12px 14px; color: var(--text-2) !important; line-height: 1.6; font-size: .9rem;
    }

    /* ---------- Sidebar ---------- */
    section[data-testid="stSidebar"], section[data-testid="stSidebar"] > div,
    [data-testid="stSidebarContent"] { background: #070B14 !important; }
    section[data-testid="stSidebar"] { border-right: 1px solid var(--line); color: var(--text); }
    .sb-title { font-size: 1.2rem; font-weight: 800; letter-spacing: -0.02em; margin: 0; color: #FFFFFF !important; }
    .sb-text { color: var(--muted) !important; font-size: .86rem; line-height: 1.6; margin: 8px 0 0; }
    .sb-h { color: #FFFFFF !important; font-size: .85rem; font-weight: 700; margin: 24px 0 8px; }
    .sb-api { font-family: 'JetBrains Mono', monospace; font-size: .75rem; color: var(--muted) !important; word-break: break-all; }

    /* =====================================================
       ICONS: inline SVG (see ICONS in the Python helpers)
       ===================================================== */
    .ic { width: 18px; height: 18px; flex: none; display: inline-block; vertical-align: middle; }
    .ic.sm { width: 14px; height: 14px; }
    .ic.lg { width: 22px; height: 22px; }

    .mark .ic { width: 24px; height: 24px; color: #07101F; stroke-width: 2.2; }
    .mark.sm { width: 34px; height: 34px; border-radius: 10px; }
    .mark.sm .ic { width: 18px; height: 18px; }
    .sb-brand { display: flex; align-items: center; gap: 10px; }
    .sb-brand .sb-title { margin: 0 !important; }

    .panel-h, .sb-h { display: flex; align-items: center; gap: 8px; line-height: 1.3; }
    .panel-h .ic { color: var(--accent); }
    .sb-h .ic { width: 16px; height: 16px; color: var(--muted); }

    .src { display: flex; align-items: center; gap: 12px; }
    .src-ic {
        width: 32px; height: 32px; border-radius: 9px; flex: none;
        display: grid; place-items: center; background: #1B2740; color: var(--accent);
    }
    .src-ic .ic { width: 17px; height: 17px; }

    .chip { display: inline-flex; align-items: center; gap: 6px; }
    .chip .ic { color: #8FB6FF; }
    .meta { display: flex; align-items: center; gap: 6px; }

    /* ---------- KPI cards: HTML tile with an invisible full-size button on top ---------- */
    .st-key-kpirow { margin-bottom: 20px; }
    .tile { min-height: 132px; margin: 0; transition: border-color .15s, transform .12s; }
    .tile .kpi-ic {
        position: absolute; top: 16px; right: 16px; z-index: 1;
        width: 36px; height: 36px; border-radius: 10px; display: grid; place-items: center;
        color: var(--tone); background: rgba(255,255,255,.05);
        background: color-mix(in srgb, var(--tone) 15%, transparent);
    }
    .tile .kpi-ic .ic { width: 19px; height: 19px; }
    .tile .n { padding-right: 46px; }
    .tile .more {
        display: flex; align-items: center; gap: 3px; margin-top: 12px; position: relative; z-index: 1;
        font-size: .78rem; font-weight: 600; color: var(--muted) !important;
    }
    .tile .more .ic { width: 14px; height: 14px; }
    .tile.active { border-color: var(--tone); box-shadow: inset 0 0 0 1px var(--tone); }
    .tile.active .more { color: var(--tone) !important; }

    [class*="st-key-kpicard_"] { position: relative; gap: 0 !important; }
    [class*="st-key-kpicard_"] [data-testid="stElementContainer"]:has(.stButton) {
        position: absolute !important; inset: 0; z-index: 4;
        width: 100% !important; height: 100% !important; margin: 0 !important;
    }
    .stApp [class*="st-key-kpicard_"] .stButton,
    .stApp [class*="st-key-kpicard_"] .stButton > button {
        width: 100% !important; height: 100% !important; min-height: 100% !important;
    }
    .stApp [class*="st-key-kpicard_"] .stButton > button {
        opacity: 0 !important; cursor: pointer; padding: 0 !important; border-radius: 16px !important;
    }
    [class*="st-key-kpicard_"]:has(.stButton > button:hover) .tile { border-color: #3A4A6E; transform: translateY(-1px); }
    [class*="st-key-kpicard_"]:has(.stButton > button:focus-visible) .tile { outline: 2px solid var(--accent); outline-offset: 2px; }
    @media (prefers-reduced-motion: reduce) { .tile { transition: none; } }

    /* ---------- KPI detail list ---------- */
    .st-key-kpidetail {
        background: var(--panel); border: 1px solid var(--line); border-radius: 16px;
        padding: 18px 20px; margin-bottom: 24px;
    }
    .kpi-detail-row {
        display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) minmax(0, 1fr);
        gap: 16px; align-items: center; padding: 12px 16px; margin: 8px 0 6px;
        background: var(--inset); border: 1px solid var(--line); border-radius: 12px;
    }
    .kpi-detail-row > div { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
    .kpi-detail-row strong { color: var(--text) !important; font-family: 'JetBrains Mono', monospace; font-size: .9rem; }
    .kpi-detail-row span { color: var(--muted) !important; font-size: .82rem; overflow-wrap: anywhere; }
    .kpi-detail-row b { color: var(--text) !important; font-size: .9rem; }
    @media (max-width: 700px) { .kpi-detail-row { grid-template-columns: 1fr; gap: 8px; } }

    /* ---------- Starter questions: left-aligned with accent icon ---------- */
    .stApp .st-key-suggestions .stButton > button {
        justify-content: flex-start !important; text-align: left; min-height: 54px; padding: 10px 14px;
    }
    .stApp .st-key-suggestions .stButton > button > div { justify-content: flex-start !important; gap: 10px; width: 100%; }
    .stApp .st-key-suggestions .stButton > button p { text-align: left; }
    .stApp .st-key-suggestions .stButton > button [data-testid="stIconMaterial"] { color: var(--accent) !important; }

    /* ---------- Investigation panel: label/value rows ---------- */
    .investigation-title { display: flex; align-items: center; gap: 8px; }
    .investigation-title .ic { color: var(--accent); }
    .kv-list {
        margin-top: 12px; padding: 2px 14px; border: 1px solid var(--line);
        border-radius: 12px; background: var(--inset);
    }
    .kv-row {
        display: grid; grid-template-columns: 16px minmax(0, auto) minmax(45%, 1fr); align-items: center;
        column-gap: 10px; padding: 10px 0; border-bottom: 1px solid var(--line);
    }
    .kv-row:last-child { border-bottom: none; }
    .kv-row .ic { width: 16px; height: 16px; color: var(--accent); }
    .kv-label { color: var(--muted) !important; font-size: .85rem; }
    .kv-value { color: var(--text) !important; font-weight: 700; font-size: .88rem; text-align: right; overflow-wrap: break-word; }
    .kv-value.red { color: var(--red) !important; }
    .kv-value.amber { color: var(--amber) !important; }
    .kv-value.green { color: var(--green) !important; }
    .audit-row {
        display: grid; grid-template-columns: 16px minmax(0, 1fr); column-gap: 10px;
        padding: 10px 0; border-bottom: 1px solid var(--line);
    }
    .audit-row:last-child { border-bottom: none; }
    .audit-row .ic { width: 16px; height: 16px; margin-top: 2px; color: var(--accent); }
    .audit-title { color: var(--text) !important; font-weight: 700; font-size: .88rem; overflow-wrap: anywhere; }
    .audit-meta { color: var(--muted) !important; font-size: .8rem; overflow-wrap: anywhere; }
    .desc-h {
        display: flex; align-items: center; gap: 8px; margin: 14px 0 6px;
        font-size: .9rem; font-weight: 700; color: var(--text) !important;
    }
    .desc-h .ic { width: 16px; height: 16px; color: var(--accent); }

    /* ---------- Chat avatars ---------- */
    [data-testid="stChatMessage"] [data-testid^="stChatMessageAvatar"] { border-radius: 10px !important; }

    /* You */
    [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) {
        background: var(--panel-2) !important; border-color: var(--line-2);
    }
    [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) [data-testid^="stChatMessageAvatar"] {
        background: #2A3B5E !important;
    }
    [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) [data-testid^="stChatMessageAvatar"],
    [data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) [data-testid^="stChatMessageAvatar"] * {
        color: #D6E4FF !important;
    }

    /* BankOps AI */
    [data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid^="stChatMessageAvatar"] {
        background: linear-gradient(135deg, #9CC4FF, #6EA8FF) !important;
    }
    [data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid^="stChatMessageAvatar"],
    [data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) [data-testid^="stChatMessageAvatar"] * {
        color: #07101F !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

@st.cache_data(ttl=10, show_spinner=False)
def api_is_up(url: str) -> bool:
    """FastAPI serves /docs by default, so it works as a cheap liveness check."""
    try:
        return requests.get(f"{url}/docs", timeout=1.5).status_code < 500
    except requests.exceptions.RequestException:
        return False


def get_operations_summary() -> dict:
    """Fetch live dashboard KPI values from FastAPI/PostgreSQL."""
    try:
        resp = requests.get(f"{API_URL}/operations/summary", timeout=10)
        if resp.status_code == 200:
            return resp.json()
        st.warning(f"Unable to load live operations metrics (API status {resp.status_code}).", icon=":material/warning:")
    except requests.exceptions.RequestException:
        st.warning("FastAPI is unavailable. Start FastAPI on port 8000 to load live dashboard metrics.", icon=":material/cloud_off:")
    return {"p1_incidents": 0, "at_risk": 0, "sla_breached": 0, "degraded_applications": 0}




def get_filtered_incidents(filter_type: str) -> list[dict]:
    """Fetch incident records and filter them by KPI/SLA state."""
    try:
        resp = requests.get(f"{API_URL}/incidents", timeout=10)
        if resp.status_code != 200:
            return []

        data = resp.json()
        if isinstance(data, list):
            incidents = data
        elif isinstance(data, dict):
            incidents = data.get("items", data.get("incidents", []))
        else:
            incidents = []
    except requests.exceptions.RequestException:
        return []

    if not isinstance(incidents, list):
        return []

    if filter_type == "p1":
        incidents = [
            incident for incident in incidents
            if str(incident.get("priority", "")).upper() == "P1"
            and str(incident.get("status", "")).upper() not in {"RESOLVED", "CLOSED"}
        ]

    filtered = []
    for incident in incidents:
        incident_id = incident.get("incident_id")
        if not incident_id:
            continue

        try:
            sla_resp = requests.get(
                f"{API_URL}/sla/{incident_id}",
                timeout=5,
            )
        except requests.exceptions.RequestException:
            continue

        if sla_resp.status_code != 200:
            continue

        sla = sla_resp.json()
        sla_status = str(sla.get("sla_status", "")).upper()

        if (
            filter_type == "p1"
            or (filter_type == "at_risk" and sla_status == "AT_RISK")
            or (filter_type == "breached" and sla_status == "BREACHED")
        ):
            filtered.append({**incident, "sla": sla})

    return filtered


def render_kpi_details(filter_type: str) -> None:
    """Render the records behind the selected KPI card."""
    titles = {
        "p1": "Open P1 incidents",
        "at_risk": "Incidents at risk of breaching SLA",
        "breached": "Incidents that breached SLA",
        "degraded": "Degraded applications",
    }

    st.markdown(
        f'<div class="panel-h">{icon("list")}{titles[filter_type]}</div>',
        unsafe_allow_html=True,
    )

    if filter_type == "degraded":
        try:
            resp = requests.get(f"{API_URL}/applications", timeout=10)
            data = resp.json() if resp.status_code == 200 else []
            if isinstance(data, dict):
                data = data.get("items", data.get("applications", []))
        except requests.exceptions.RequestException:
            data = []

        degraded = [
            app for app in data
            if str(app.get("status", "")).upper() == "DEGRADED"
        ]

        if not degraded:
            st.info("No degraded applications found.", icon=":material/check_circle:")
            return

        for app in degraded:
            st.markdown(
                f"""
                <div class="kpi-detail-row">
                    <div>
                        <strong>{esc(app.get("application_name", "Unknown"))}</strong>
                        <span>{esc(app.get("description", ""))}</span>
                    </div>
                    <b>{esc(app.get("status", "N/A"))}</b>
                </div>
                """,
                unsafe_allow_html=True,
            )
        return

    incidents = get_filtered_incidents(filter_type)

    if not incidents:
        st.info(
            "No matching incident records were returned. "
            "Make sure GET /incidents is available in FastAPI.",
            icon=":material/info:",
        )
        return

    for incident in incidents:
        sla = incident.get("sla", {})
        remaining = sla.get("remaining_minutes", "N/A")
        incident_id = incident.get("incident_id", "N/A")

        st.markdown(
            f"""
            <div class="kpi-detail-row">
                <div>
                    <strong>{esc(incident_id)}</strong>
                    <span>{esc(incident.get("title", ""))}</span>
                </div>
                <div>
                    <b>{esc(incident.get("priority", "N/A"))}</b>
                    <span>{esc(incident.get("assigned_team", "N/A"))}</span>
                </div>
                <div>
                    <b>{esc(str(remaining))} min</b>
                    <span>SLA remaining</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Runs the same flow as the main Investigate button (details panel + AI answer).
        st.button(
            f"Investigate {incident_id}",
            key=f"kpi_incident_{incident_id}",
            icon=":material/search:",
            use_container_width=True,
            on_click=investigate_from_kpi,
            args=(incident_id,),
        )


def get_incident_details(incident_id: str) -> dict:
    """Fetch incident, SLA and application details for the investigation panel."""
    result = {"incident": None, "sla": None, "application": None, "errors": []}

    try:
        resp = requests.get(f"{API_URL}/incidents/{incident_id}", timeout=10)
        if resp.status_code == 200:
            result["incident"] = resp.json()
        elif resp.status_code == 404:
            result["errors"].append("Incident not found.")
            return result
        else:
            result["errors"].append(f"Incident API returned status {resp.status_code}.")
            return result
    except requests.exceptions.RequestException:
        result["errors"].append("Unable to reach the incident API.")
        return result

    try:
        resp = requests.get(f"{API_URL}/sla/{incident_id}", timeout=10)
        if resp.status_code == 200:
            result["sla"] = resp.json()
        elif resp.status_code != 404:
            result["errors"].append(f"SLA API returned status {resp.status_code}.")
    except requests.exceptions.RequestException:
        result["errors"].append("Unable to reach the SLA API.")

    application_id = result["incident"].get("application_id")
    if application_id is not None:
        try:
            resp = requests.get(f"{API_URL}/applications/{application_id}", timeout=10)
            if resp.status_code == 200:
                result["application"] = resp.json()
            elif resp.status_code != 404:
                result["errors"].append(
                    f"Application API returned status {resp.status_code}."
                )
        except requests.exceptions.RequestException:
            result["errors"].append("Unable to reach the application API.")

    return result


# Inline SVG icons (paths from Lucide, ISC licence). They are drawn as SVG, so
# they render instantly, align exactly with text and don't depend on a web font.
ICONS = {
    "account_balance": '<line x1="3" x2="21" y1="22" y2="22"/><line x1="6" x2="6" y1="18" y2="11"/><line x1="10" x2="10" y1="18" y2="11"/><line x1="14" x2="14" y1="18" y2="11"/><line x1="18" x2="18" y1="18" y2="11"/><polygon points="12 2 20 7 4 7"/>',
    "crisis_alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "hourglass_top": '<path d="M5 22h14"/><path d="M5 2h14"/><path d="M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22"/><path d="M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2"/>',
    "timer_off": '<polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
    "monitor_heart": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "troubleshoot": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "fact_check": '<path d="m3 17 2 2 4-4"/><path d="m3 7 2 2 4-4"/><path d="M13 6h8"/><path d="M13 12h8"/><path d="M13 18h8"/>',
    "receipt_long": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    "policy": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="m9 12 2 2 4-4"/>',
    "menu_book": '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
    "confirmation_number": '<path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/><path d="M13 5v2"/><path d="M13 17v2"/><path d="M13 11v2"/>',
    "flag": '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" x2="4" y1="22" y2="15"/>',
    "pending": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/>',
    "groups": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "timer": '<line x1="10" x2="14" y1="2" y2="2"/><line x1="12" x2="15" y1="14" y2="11"/><circle cx="12" cy="14" r="8"/>',
    "support_agent": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    "dns": '<rect width="20" height="8" x="2" y="2" rx="2" ry="2"/><rect width="20" height="8" x="2" y="14" rx="2" ry="2"/><line x1="6" x2="6.01" y1="6" y2="6"/><line x1="6" x2="6.01" y1="18" y2="18"/>',
    "notes": '<line x1="21" x2="3" y1="6" y2="6"/><line x1="15" x2="3" y1="12" y2="12"/><line x1="17" x2="3" y1="18" y2="18"/>',
    "build": '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    "schedule": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "api": '<path d="M12 22v-5"/><path d="M9 8V2"/><path d="M15 8V2"/><path d="M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z"/>',
    "forum": '<path d="M14 9a2 2 0 0 1-2 2H6l-4 4V4c0-1.1.9-2 2-2h8a2 2 0 0 1 2 2v5Z"/><path d="M18 9h2a2 2 0 0 1 2 2v11l-4-4h-6a2 2 0 0 1-2-2v-1"/>',
    "list": '<line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/><line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/>',
    "chevron_right": '<path d="m9 18 6-6-6-6"/>',
    "chevron_down": '<path d="m6 9 6 6 6-6"/>',
}


def icon(name: str, size: str = "") -> str:
    """Inline SVG icon for HTML blocks. size: "" (18px), "sm" (14px) or "lg" (22px)."""
    paths = ICONS.get(name, ICONS["notes"])
    return (
        f'<svg class="ic {size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f'{paths}</svg>'
    )


def esc(value) -> str:
    """Escape API values before they go into HTML."""
    return html.escape(str(value))


def tone_class(value) -> str:
    """Colour for status-like values."""
    v = str(value).upper()
    if "BREACH" in v or v in {"DOWN", "OUTAGE", "FAILED", "P1"}:
        return "red"
    if "RISK" in v or "DEGRADED" in v or v == "P2":
        return "amber"
    if v in {"ON_TRACK", "WITHIN_SLA", "MET", "HEALTHY", "UP", "OPERATIONAL", "OK", "RESOLVED", "CLOSED"}:
        return "green"
    return ""


def kv_row(icon_name: str, label: str, value, tone: str = "") -> str:
    return (
        f'<div class="kv-row">{icon(icon_name)}'
        f'<span class="kv-label">{label}</span>'
        f'<span class="kv-value {tone}">{esc(str(value).replace("_", " "))}</span></div>'
    )


def render_investigation(details: dict) -> None:
    """Render live incident investigation as icon / label / value rows."""
    incident = details.get("incident")
    sla = details.get("sla")
    application = details.get("application")

    if not incident:
        for error in details.get("errors", []):
            st.error(error, icon=":material/error:")
        return

    priority = incident.get("priority", "N/A")
    rows = [
        kv_row("flag", "Priority", priority, tone_class(priority)),
        kv_row("pending", "Status", incident.get("status", "N/A")),
        kv_row("groups", "Assigned team", incident.get("assigned_team", "N/A")),
    ]
    if sla:
        sla_status = sla.get("sla_status", "N/A")
        rows += [
            kv_row("timer", "SLA status", sla_status, tone_class(sla_status)),
            kv_row("hourglass_top", "Time remaining", f'{sla.get("remaining_minutes", 0)} min'),
            kv_row("support_agent", "Escalation", sla.get("escalation_team", "N/A")),
        ]
    else:
        rows.append(kv_row("timer", "SLA status", "Unavailable"))
    if application:
        app_status = application.get("status", "N/A")
        rows += [
            kv_row("dns", "Application", application.get("application_name", "Unknown")),
            kv_row("monitor_heart", "App status", app_status, tone_class(app_status)),
        ]

    parts = [
        '<div class="investigation-head">',
        f'<div class="investigation-title">{icon("confirmation_number")}'
        f'{esc(incident.get("incident_id", "Unknown"))}</div>',
        f'<div class="investigation-sub">{esc(incident.get("title", "Incident"))}</div>',
        "</div>",
        f'<div class="kv-list">{"".join(rows)}</div>',
    ]
    description = incident.get("description")
    if description:
        parts.append(f'<div class="desc-h">{icon("notes")}Description</div>')
        parts.append(f'<div class="investigation-description">{esc(description)}</div>')

    st.markdown("".join(parts), unsafe_allow_html=True)

    for error in details.get("errors", []):
        st.warning(error, icon=":material/warning:")


def get_json(path: str, params: dict | None = None):
    """GET a JSON resource from the API, or None when it is unavailable."""
    try:
        resp = requests.get(f"{API_URL}{path}", params=params, timeout=10)
    except requests.exceptions.RequestException:
        return None
    return resp.json() if resp.status_code == 200 else None


def short_time(value) -> str:
    """Format an API timestamp (UTC) as 'DD Mon HH:MM UTC'."""
    try:
        return datetime.fromisoformat(str(value)).strftime("%d %b %H:%M UTC")
    except ValueError:
        return str(value)


def escalate_cb(incident_id: str) -> None:
    """Escalate an incident. Clicking the button is the human approval."""
    payload = {
        "approved": True,
        "approved_by": OPERATOR,
        "request_id": st.session_state.request_ids.get(incident_id),
    }
    try:
        resp = requests.post(
            f"{API_URL}/incidents/{incident_id}/escalate", json=payload, timeout=10
        )
        if resp.status_code == 200:
            team = resp.json().get("escalation_team", "the escalation team")
            st.session_state.notice = ("success", f"{incident_id} escalated to {team}.")
        else:
            try:
                detail = resp.json().get("detail", resp.text)
            except ValueError:
                detail = resp.text
            st.session_state.notice = ("error", f"Escalation was not carried out. {detail}")
    except requests.exceptions.RequestException:
        st.session_state.notice = ("error", "Unable to reach the API. Nothing was escalated.")
    st.session_state.investigation = get_incident_details(incident_id)


def render_escalation(incident_id: str) -> None:
    """Escalation status and the Approve & escalate action for an incident."""
    state = get_json(f"/incidents/{incident_id}/escalation")
    if not state:
        return

    st.markdown(
        f'<div class="desc-h">{icon("support_agent")}Escalation · {esc(incident_id)}</div>',
        unsafe_allow_html=True,
    )

    notice = st.session_state.notice
    if notice:
        # Drawn by hand: the theme restyles st.success / st.error as plain
        # dark boxes, which made the confirmation easy to miss.
        kind, text = notice
        st.markdown(
            f'<div class="notice {kind}">{icon("fact_check")}<span>{esc(text)}</span></div>',
            unsafe_allow_html=True,
        )

    escalation = state.get("escalation")
    if escalation:
        rows = [
            kv_row("groups", "Escalated to", escalation.get("escalation_team", "N/A")),
            kv_row("schedule", "Escalated at", short_time(escalation.get("created_at"))),
        ]
        st.markdown(f'<div class="kv-list">{"".join(rows)}</div>', unsafe_allow_html=True)
    elif state.get("eligible"):
        team = state.get("escalation_team", "the escalation team")
        st.markdown(
            f'<div class="investigation-description">{esc(state.get("reason", ""))} '
            f"Escalation changes the incident, so it needs your approval.</div>",
            unsafe_allow_html=True,
        )
        st.button(
            f"Approve & escalate to {team}",
            type="primary",
            icon=":material/arrow_upward:",
            use_container_width=True,
            key=f"escalate_{incident_id}",
            on_click=escalate_cb,
            args=(incident_id,),
        )
    else:
        st.markdown(
            f'<div class="investigation-description">{esc(state.get("reason", ""))}</div>',
            unsafe_allow_html=True,
        )


def render_audit_trail(incident_id: str) -> None:
    """What the agent recommended and what was approved for an incident."""
    entries = get_json("/audit", {"incident_id": incident_id, "limit": 5})
    if not entries:
        return

    st.markdown(f'<div class="desc-h">{icon("fact_check")}Audit trail</div>', unsafe_allow_html=True)

    rows = []
    for entry in entries:
        if entry.get("action_taken"):
            label = f'{entry["action_taken"]} to {entry.get("escalation_team") or "N/A"}'
            who = f' · approved by {entry["approved_by"]}' if entry.get("approved_by") else ""
            row_icon = "support_agent"
        else:
            label = "Agent investigation"
            who = ""
            row_icon = "troubleshoot"
        request_id = str(entry.get("request_id") or "")[:8]
        rows.append(
            f'<div class="audit-row">{icon(row_icon)}<div>'
            f'<div class="audit-title">{esc(label)}</div>'
            f'<div class="audit-meta">{esc(short_time(entry.get("created_at")))}{esc(who)}</div>'
            f'<div class="audit-meta">Request {esc(request_id)}</div>'
            f"</div></div>"
        )
    st.markdown(f'<div class="kv-list">{"".join(rows)}</div>', unsafe_allow_html=True)


def reset_demo_cb() -> None:
    """Restore the synthetic incidents and clear the audit trail for a fresh demo."""
    try:
        resp = requests.post(f"{API_URL}/demo/reset", params={"clear_audit": True}, timeout=15)
        ok = resp.status_code == 200
    except requests.exceptions.RequestException:
        ok = False
    st.session_state.messages = []
    st.session_state.investigation = None
    st.session_state.request_ids = {}
    st.session_state.notice = None
    st.session_state.kpi_filter = None
    st.session_state.reset_result = ok


def tool_names(data: dict) -> list[str]:
    raw = data.get("tools_called") or data.get("tools_used") or data.get("tool_calls") or []
    names = []
    for t in raw:
        if isinstance(t, str):
            names.append(t)
        elif isinstance(t, dict):
            names.append(str(t.get("name") or t.get("tool") or t))
    return names


def call_agent(question: str) -> dict:
    started = time.time()
    result = {"role": "assistant", "content": "", "tools": [], "error": None, "secs": 0.0}
    try:
        resp = requests.post(
            f"{API_URL}/agent/chat", json={"question": question}, timeout=120
        )
        if resp.status_code == 200:
            data = resp.json()
            result["content"] = data.get("answer", "")
            result["tools"] = tool_names(data)
            if data.get("incident_id") and data.get("request_id"):
                st.session_state.request_ids[data["incident_id"]] = data["request_id"]
        else:
            result["error"] = f"The API returned status {resp.status_code}.\n\n{resp.text}"
    except requests.exceptions.ConnectionError:
        result["error"] = (
            f"Can't reach the API at {API_URL}. "
            "Start FastAPI on port 8000, then ask again."
        )
    except requests.exceptions.Timeout:
        result["error"] = "The request timed out after 120 seconds. Try a narrower question."
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"Unexpected error: {exc}"
    result["secs"] = time.time() - started
    return result


def word_stream(text: str):
    for chunk in text.split(" "):
        yield chunk + " "
        time.sleep(0.012)


def render_assistant(msg: dict, animate: bool = False) -> None:
    if msg["error"]:
        st.error(msg["error"], icon=":material/error:")
        return
    if animate:
        st.write_stream(word_stream(msg["content"]))
    else:
        st.markdown(msg["content"])
    if msg["tools"]:
        chips = "".join(f'<span class="chip">{icon("build", "sm")}{esc(t)}</span>' for t in msg["tools"])
        st.markdown(f'<div class="chips">{chips}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="meta">{icon("schedule", "sm")}Answered in {msg["secs"]:.1f}s</div>', unsafe_allow_html=True)


def ask(text: str) -> None:
    st.session_state.pending = text


def investigate_cb() -> None:
    inc = st.session_state.incident_id.strip().upper()
    if inc:
        # A new investigation replaces the previous one instead of stacking below it.
        st.session_state.messages = []
        st.session_state.notice = None
        st.session_state.investigation = get_incident_details(inc)
        ask(f"Investigate {inc} and tell me what I should do.")


def investigate_from_kpi(incident_id: str) -> None:
    """Investigate an incident picked from a KPI card's list.

    Runs as a button callback, so the Incident ID box can be updated safely.
    The list is closed so the details panel and the AI answer are in view.
    """
    st.session_state.incident_id = incident_id
    st.session_state.kpi_filter = None
    investigate_cb()


def clear_chat() -> None:
    st.session_state.messages = []


def transcript() -> str:
    lines = []
    for m in st.session_state.messages:
        who = "You" if m["role"] == "user" else "BankOps AI"
        body = m.get("error") or m["content"]
        lines.append(f"{who}:\n{body}\n")
    return "\n".join(lines)


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

with st.sidebar:
    st.markdown(
        f"""
        <div class="sb-brand">
            <div class="mark sm">{icon("account_balance")}</div>
            <p class="sb-title">BankOps AI</p>
        </div>
        <p class="sb-text">Investigate incidents, check SLA exposure, review
        application health and find the right SOP.</p>
        <p class="sb-h">{icon("api")}API</p>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="sb-api">{API_URL}</div>', unsafe_allow_html=True)

    st.markdown(f'<p class="sb-h">{icon("forum")}Conversation</p>', unsafe_allow_html=True)
    st.button("New conversation", icon=":material/add_comment:", on_click=clear_chat, use_container_width=True)
    if st.session_state.messages:
        st.download_button(
            "Download transcript",
            icon=":material/download:",
            data=transcript(),
            file_name="bankops_conversation.txt",
            use_container_width=True,
        )

    st.markdown(f'<p class="sb-h">{icon("build")}Demo data</p>', unsafe_allow_html=True)
    st.button("Reset demo data", icon=":material/restart_alt:", on_click=reset_demo_cb, use_container_width=True)
    reset_result = st.session_state.pop("reset_result", None)
    if reset_result is True:
        st.caption("Incidents restored and audit trail cleared.")
    elif reset_result is False:
        st.caption("Reset failed. Check that the API is running.")

    st.divider()
    st.caption("BankOps AI v0.4.0 · Simulated data")


# ---------------------------------------------------------
# HERO + KPIs
# ---------------------------------------------------------

online = api_is_up(API_URL)
pill = (
    '<span class="pill ok"><span class="dot"></span>API connected</span>'
    if online
    else '<span class="pill down"><span class="dot"></span>API unreachable</span>'
)

st.markdown(
    f"""
    <div class="hero">
        <div class="mark">{icon("account_balance")}</div>
        <div>
            <h1 class="hero-title">BankOps AI</h1>
            <p class="hero-sub">Triage incidents and protect SLAs with evidence from your own systems.</p>
        </div>
        <div class="grow"></div>
        {pill}
    </div>
    """,
    unsafe_allow_html=True,
)

metrics = get_operations_summary()

overview = [
    {"label": "P1 incidents open", "value": metrics.get("p1_incidents", 0), "tone": "#6EA8FF", "icon": "crisis_alert"},
    {"label": "SLA at risk", "value": metrics.get("at_risk", 0), "tone": "#F5B14C", "icon": "hourglass_top"},
    {"label": "SLA breached", "value": metrics.get("sla_breached", 0), "tone": "#FF6B6B", "icon": "timer_off"},
    {"label": "Degraded applications", "value": metrics.get("degraded_applications", 0), "tone": "#F5B14C", "icon": "monitor_heart"},
]

def toggle_kpi(filter_type: str) -> None:
    current = st.session_state.kpi_filter
    st.session_state.kpi_filter = None if current == filter_type else filter_type


# Clickable KPI cards: each card is an HTML tile with an invisible,
# full-size button laid over it, so the whole card is clickable.
kpi_filters = ["p1", "at_risk", "breached", "degraded"]
kpi_more = {
    "p1": "View incidents",
    "at_risk": "View incidents",
    "breached": "View incidents",
    "degraded": "View applications",
}

with st.container(key="kpirow"):
    kpi_cols = st.columns(4, gap="small")
    for col, metric, filter_type in zip(kpi_cols, overview, kpi_filters):
        active = st.session_state.kpi_filter == filter_type
        more = (
            f'Showing below{icon("chevron_down", "sm")}'
            if active
            else f'{kpi_more[filter_type]}{icon("chevron_right", "sm")}'
        )
        with col:
            with st.container(key=f"kpicard_{filter_type}"):
                st.markdown(
                    f'<div class="tile{" active" if active else ""}" style="--tone:{metric["tone"]}">'
                    f'<span class="kpi-ic">{icon(metric["icon"])}</span>'
                    f'<span class="n">{esc(metric["value"])}</span>'
                    f'<span class="l">{esc(metric["label"])}</span>'
                    f'<span class="more">{more}</span>'
                    "</div>",
                    unsafe_allow_html=True,
                )
                st.button(
                    f'{"Hide" if active else "Show"} list for {metric["label"]}',
                    key=f"kpibtn_{filter_type}",
                    on_click=toggle_kpi,
                    args=(filter_type,),
                    use_container_width=True,
                )


# ---------------------------------------------------------
# KPI DETAIL VIEW
# ---------------------------------------------------------
if st.session_state.kpi_filter:
    with st.container(key="kpidetail"):
        render_kpi_details(st.session_state.kpi_filter)
        st.button(
            "Close list",
            key="clear_kpi_filter",
            icon=":material/close:",
            on_click=toggle_kpi,
            args=(st.session_state.kpi_filter,),
        )


# ---------------------------------------------------------
# INPUT (chat box is pinned to the bottom of the page)
# ---------------------------------------------------------

typed = st.chat_input("Ask about an incident, SLA, application or SOP…")
question = typed or st.session_state.pop("pending", None)


# ---------------------------------------------------------
# MAIN LAYOUT
# ---------------------------------------------------------

left, right = st.columns([2.1, 1], gap="large")

with left:
    investigated = ((st.session_state.investigation or {}).get("incident") or {}).get("incident_id")

    if not st.session_state.messages and not question:
        st.markdown(
            """
            <div class="welcome">
                <h2 class="welcome-title">What should we look into?</h2>
                <p class="welcome-sub">Ask in plain language. The agent pulls incident records, SLA policy,
                application status and SOPs, then tells you what to do next.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        with st.container(key="suggestions"):
            sg_cols = st.columns(2)
            for i, (label, prompt, ic) in enumerate(SUGGESTIONS):
                sg_cols[i % 2].button(
                    label,
                    key=f"sg_{i}",
                    icon=ic,
                    on_click=ask,
                    args=(prompt,),
                    use_container_width=True,
                )

    for m in st.session_state.messages:
        if m["role"] == "user":
            with st.chat_message("user", avatar=":material/person:"):
                st.markdown(m["content"])
        else:
            with st.chat_message("assistant", avatar=":material/account_balance:"):
                render_assistant(m)

    if question:
        user_msg = {"role": "user", "content": question}
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown(question)

        with st.chat_message("assistant", avatar=":material/account_balance:"):
            with st.spinner("Checking incident data, SLA policy and SOPs…"):
                reply = call_agent(question)
            render_assistant(reply, animate=True)

        st.session_state.messages.extend([user_msg, reply])

    # The action and its audit trail follow the agent's answer. They are
    # rendered after it so the audit trail includes the answer just given.
    if investigated:
        with st.container(key="action"):
            render_escalation(investigated)
            render_audit_trail(investigated)

with right:
    with st.container(key="investigate"):
        st.markdown(
            f'<p class="panel-h">{icon("troubleshoot")}Investigate an incident</p>'
            '<p class="panel-s">Enter an ID to get status, SLA exposure and next steps.</p>',
            unsafe_allow_html=True,
        )
        st.text_input("Incident ID", key="incident_id", placeholder="INC-1042")
        st.button(
            "Investigate",
            type="primary",
            icon=":material/search:",
            use_container_width=True,
            on_click=investigate_cb,
        )

        if st.session_state.investigation is not None:
            render_investigation(st.session_state.investigation)
            if st.button(
                "Refresh investigation",
                icon=":material/refresh:",
                use_container_width=True,
                key="refresh_investigation",
            ):
                inc = st.session_state.incident_id.strip().upper()
                if inc:
                    st.session_state.investigation = get_incident_details(inc)
                    st.rerun()

    st.write("")

    with st.container(key="sources"):
        st.markdown(
            f"""
            <p class="panel-h">{icon("fact_check")}What the agent checks</p>
            <p class="panel-s">Answers are built from these sources.</p>
            <div class="src"><span class="src-ic">{icon("receipt_long")}</span>Incident records</div>
            <div class="src"><span class="src-ic">{icon("policy")}</span>SLA policy</div>
            <div class="src"><span class="src-ic">{icon("monitor_heart")}</span>Application status</div>
            <div class="src"><span class="src-ic">{icon("menu_book")}</span>SOP knowledge base</div>
            """,
            unsafe_allow_html=True,
        )

    st.caption("AI-assisted decision support. Verify critical actions in the source systems.")
