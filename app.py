"""
GNSC Monthly KPI Dashboard - Phase 1 + Phase 2 (Enterprise Edition)
====================================================================
A Streamlit enterprise dashboard that reads the Monthly KPI Summary Sheet
directly from a GitHub RAW url and renders Power-BI style KPI cards with
sparklines, month-over-month comparison, growth %, and trend indicators.

Phase 2 adds a full Executive Dashboard section (Plotly powered) below
the KPI cards: HSE performance score, target-vs-actual gauges, monthly
trend charts, safety/environment/production summaries, month-over-month
comparisons and FY cumulative statistics — all computed live from the
same parsed workbook, with zero hardcoded values.

Deployment requirements (create a requirements.txt alongside this file):
    streamlit
    pandas
    openpyxl
    requests
    plotly

Deploy on Streamlit Community Cloud by pointing it at this app.py.
"""

import re
import time
import base64
from io import BytesIO
from datetime import datetime

import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =========================================================================
# CONFIGURATION
# =========================================================================
# Replace this with the RAW GitHub URL of your uploaded Excel file, e.g.:
# https://raw.githubusercontent.com/<user>/<repo>/main/Monthly_KPI_Summary_Sheet_April_GNSC.xlsx
GITHUB_RAW_URL = "https://raw.githubusercontent.com/AayuGo1/energy_dashboard/main/Monthly%20KPI%20Summary%20Sheet_April_GNSC.xlsx"

COMPANY_NAME = "GNSC"
CACHE_TTL_SECONDS = 300  # data auto-revalidates every 5 minutes

MONTH_ORDER = ["Apr", "May", "Jun", "Jul", "Aug", "Sep",
               "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]

# =========================================================================
# PAGE CONFIG
# =========================================================================
st.set_page_config(
    page_title=f"{COMPANY_NAME} | Monthly KPI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================================
# GLOBAL STYLE — ENTERPRISE GLASSMORPHIC DARK-BLUE THEME
# =========================================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap');

    :root{
        --bg-0:#060a1a;
        --bg-1:#0a1230;
        --bg-2:#0d1a44;
        --panel:rgba(255,255,255,0.045);
        --panel-border:rgba(255,255,255,0.09);
        --panel-border-hover:rgba(120,150,255,0.55);
        --text-hi:#f3f6ff;
        --text-mid:#aab6e3;
        --text-lo:#6d7ab0;
        --accent-blue:#4f7cff;
        --accent-blue-2:#7aa2ff;
        --accent-indigo:#7c6bff;
        --accent-teal:#22d3c5;
        --accent-green:#2fd487;
        --accent-red:#ff5c72;
        --accent-amber:#ffb547;
        --shadow-soft:0 8px 24px rgba(0,0,0,0.35);
        --shadow-hover:0 18px 40px rgba(15,30,90,0.55);
    }

    html, body, [class*="css"]  {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {background: transparent;}

    .stApp {
        background:
            radial-gradient(1100px 550px at 12% -8%, rgba(79,124,255,0.16), transparent 60%),
            radial-gradient(900px 500px at 100% 0%, rgba(124,107,255,0.14), transparent 55%),
            radial-gradient(800px 500px at 50% 110%, rgba(34,211,197,0.08), transparent 60%),
            linear-gradient(180deg, var(--bg-0) 0%, var(--bg-1) 45%, var(--bg-0) 100%);
        color: var(--text-hi);
    }

    /* ---------------- SIDEBAR ---------------- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #050914 0%, #0a1230 55%, #070c1e 100%);
        border-right: 1px solid rgba(120,150,255,0.14);
    }
    section[data-testid="stSidebar"] * { color: var(--text-mid) !important; }

    .sb-brand {
        display:flex; align-items:center; gap:12px;
        padding: 4px 2px 14px 2px;
        border-bottom: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 16px;
    }
    .sb-brand-name {
        font-size: 17px; font-weight: 800; color: var(--text-hi) !important;
        letter-spacing: 0.2px; line-height:1.1;
    }
    .sb-brand-sub {
        font-size: 11px; color: var(--text-lo) !important; letter-spacing: 0.6px;
        text-transform: uppercase; font-weight:600;
    }

    .logo-box {
        width: 100%;
        height: 84px;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        margin-bottom: 6px;
        background: linear-gradient(135deg, rgba(79,124,255,0.14), rgba(124,107,255,0.10));
        border: 1.4px dashed rgba(120,150,255,0.4);
    }
    .logo-box img { max-height: 100%; max-width: 100%; object-fit: contain; }
    .logo-box span {
        color: #8ea0e6 !important; font-weight: 700; font-size: 12px;
        letter-spacing: 1.4px; text-transform: uppercase;
    }

    .sb-section-title {
        font-size: 11px; text-transform: uppercase; letter-spacing: 1.4px;
        color: var(--text-lo) !important; font-weight: 800;
        margin: 20px 0 8px 2px;
        display:flex; align-items:center; gap:6px;
    }

    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background: rgba(255,255,255,0.045) !important;
        border: 1px solid rgba(120,150,255,0.28) !important;
        border-radius: 10px !important;
        transition: border-color .15s ease, box-shadow .15s ease;
    }
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div:hover {
        border-color: var(--accent-blue-2) !important;
        box-shadow: 0 0 0 3px rgba(79,124,255,0.14);
    }
    section[data-testid="stSidebar"] label {
        font-weight: 700 !important; font-size: 12.5px !important;
        color: var(--text-mid) !important; letter-spacing: 0.3px;
    }

    div.stButton > button {
        background: linear-gradient(120deg, #3a5be0, #6089ff 55%, #7c6bff);
        background-size: 160% 160%;
        color: white !important;
        border: none;
        border-radius: 10px;
        padding: 10px 14px;
        font-weight: 700;
        letter-spacing: 0.2px;
        width: 100%;
        box-shadow: 0 6px 18px rgba(79,124,255,0.35);
        transition: transform .15s ease, box-shadow .15s ease, background-position .3s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 26px rgba(79,124,255,0.5);
        background-position: 100% 0%;
        color: white !important;
    }
    div.stButton > button:active { transform: translateY(0px) scale(0.99); }

    section[data-testid="stSidebar"] .stFileUploader section {
        background: rgba(255,255,255,0.03);
        border: 1.2px dashed rgba(120,150,255,0.35);
        border-radius: 10px;
    }

    .sb-footnote {
        font-size: 11px; line-height:1.5; color: var(--text-lo) !important;
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 10px; padding: 10px 12px; margin-top: 4px;
    }

    /* ---------------- HEADER ---------------- */
    .app-header {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
        padding: 22px 30px;
        margin-bottom: 20px;
        background: linear-gradient(120deg, rgba(16,31,74,0.85) 0%, rgba(22,41,107,0.85) 55%, rgba(16,31,74,0.85) 100%);
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
        border-radius: 18px;
        border: 1px solid rgba(120,150,255,0.22);
        box-shadow: var(--shadow-soft);
        overflow: hidden;
        flex-wrap: wrap;
    }
    .app-header::before{
        content:"";
        position:absolute; inset:0;
        background: linear-gradient(120deg, rgba(79,124,255,0.10), transparent 40%, rgba(124,107,255,0.10));
        pointer-events:none;
    }
    .app-header-left { display:flex; align-items:center; gap:14px; z-index:1; }
    .app-header-icon {
        width:48px; height:48px; border-radius:14px;
        display:flex; align-items:center; justify-content:center;
        background: linear-gradient(135deg, var(--accent-blue), var(--accent-indigo));
        font-size:22px; box-shadow: 0 6px 16px rgba(79,124,255,0.45);
        flex-shrink:0;
    }
    .app-header h1 {
        margin: 0; font-size: 25px; font-weight: 800; color: #ffffff;
        letter-spacing: 0.2px; line-height:1.2;
    }
    .app-header p {
        margin: 3px 0 0 0; font-size: 13px; color: var(--text-mid);
        font-weight: 500;
    }
    .app-header-right {
        display:flex; flex-direction:column; align-items:flex-end; gap:8px; z-index:1;
    }
    .header-badge-row { display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
    .header-badge {
        background: rgba(79,124,255,0.14);
        border: 1px solid rgba(120,150,255,0.4);
        color: #cddaff;
        padding: 6px 13px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.2px;
        white-space: nowrap;
    }
    .header-badge.live { background: rgba(47,212,135,0.14); border-color: rgba(47,212,135,0.45); color:#a9f3cd; }
    .header-badge.live .dot {
        display:inline-block; width:7px; height:7px; border-radius:50%;
        background: var(--accent-green); margin-right:6px;
        box-shadow: 0 0 0 0 rgba(47,212,135,0.6);
        animation: pulseDot 1.6s infinite;
    }
    @keyframes pulseDot {
        0% { box-shadow: 0 0 0 0 rgba(47,212,135,0.55); }
        70% { box-shadow: 0 0 0 7px rgba(47,212,135,0); }
        100% { box-shadow: 0 0 0 0 rgba(47,212,135,0); }
    }
    .header-meta { font-size: 11.5px; color: var(--text-lo); font-weight:600; }

    /* ---------------- STATUS STRIP ---------------- */
    .status-strip {
        display:flex; flex-wrap:wrap; gap:10px;
        justify-content:space-between; align-items:center;
        padding: 10px 18px;
        background: rgba(255,255,255,0.035);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        font-size: 12.5px;
        color: var(--text-mid);
        margin-bottom: 22px;
    }
    .status-strip b { color: var(--text-hi); }
    .status-chip {
        display:inline-flex; align-items:center; gap:6px;
        padding: 4px 10px; border-radius: 8px;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.06);
    }

    /* ---------------- SECTION LABEL ---------------- */
    .section-label {
        font-size: 12.5px;
        text-transform: uppercase;
        letter-spacing: 1.6px;
        color: #8fa0da;
        font-weight: 800;
        margin: 6px 0 16px 2px;
        display:flex; align-items:center; gap:10px;
    }
    .section-label::after{
        content:"";
        flex:1; height:1px;
        background: linear-gradient(90deg, rgba(120,150,255,0.35), transparent);
    }

    /* ---------------- KPI GRID / CARDS ---------------- */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(258px, 1fr));
        gap: 20px;
        margin-bottom: 8px;
    }

    .kpi-card {
        position: relative;
        background: linear-gradient(160deg, rgba(255,255,255,0.055) 0%, rgba(255,255,255,0.02) 100%);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid var(--panel-border);
        border-radius: 16px;
        padding: 20px 20px 16px 20px;
        overflow: hidden;
        box-shadow: var(--shadow-soft);
        transition: transform .22s cubic-bezier(.2,.8,.2,1), box-shadow .22s ease, border-color .22s ease;
    }
    .kpi-card::before{
        content:"";
        position:absolute; left:0; top:0; bottom:0; width:4px;
        background: linear-gradient(180deg, var(--accent), var(--accent-2, var(--accent)));
        box-shadow: 0 0 14px var(--accent);
    }
    .kpi-card::after{
        content:"";
        position:absolute; right:-40px; top:-40px; width:120px; height:120px;
        background: radial-gradient(circle, var(--accent) 0%, transparent 70%);
        opacity: 0.10; pointer-events:none;
    }
    .kpi-card:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-hover);
        border-color: var(--panel-border-hover);
    }

    .kpi-top-row {
        display:flex; align-items:flex-start; justify-content:space-between;
        margin-bottom: 10px;
    }
    .kpi-icon-badge {
        width:38px; height:38px; border-radius: 11px;
        display:flex; align-items:center; justify-content:center;
        font-size: 18px;
        background: linear-gradient(135deg, rgba(255,255,255,0.16), rgba(255,255,255,0.04));
        border: 1px solid rgba(255,255,255,0.18);
    }
    .kpi-trend-pill {
        display:flex; align-items:center; gap:4px;
        font-size: 11.5px; font-weight: 800;
        padding: 4px 9px; border-radius: 20px;
        white-space: nowrap;
    }
    .kpi-trend-pill.good { background: rgba(47,212,135,0.14); color:#7ce8b3; border:1px solid rgba(47,212,135,0.35); }
    .kpi-trend-pill.bad  { background: rgba(255,92,114,0.14); color:#ff9aa8; border:1px solid rgba(255,92,114,0.35); }
    .kpi-trend-pill.flat { background: rgba(255,255,255,0.06); color:#9fb0e0; border:1px solid rgba(255,255,255,0.12); }

    .kpi-value {
        font-size: 32px;
        font-weight: 900;
        color: var(--text-hi);
        line-height: 1.08;
        letter-spacing: -0.5px;
        font-variant-numeric: tabular-nums;
    }
    .kpi-unit { font-size: 13px; font-weight: 700; color: var(--text-lo); margin-left: 4px; }
    .kpi-label {
        margin-top: 5px;
        font-size: 12.5px;
        font-weight: 700;
        color: var(--text-mid);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .kpi-compare {
        margin-top: 3px;
        font-size: 11px;
        color: var(--text-lo);
        font-weight: 500;
    }
    .kpi-spark-wrap {
        margin-top: 14px;
        padding-top: 12px;
        border-top: 1px solid rgba(255,255,255,0.07);
        display:flex; align-items:center; justify-content:space-between;
        gap: 10px;
    }
    .kpi-spark-wrap svg { display:block; }
    .kpi-spark-label {
        font-size: 10px; color: var(--text-lo); font-weight:700;
        text-transform: uppercase; letter-spacing: 0.6px; white-space:nowrap;
    }

    /* skeleton shimmer */
    .skel-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(258px, 1fr));
        gap: 20px;
    }
    .skel-card {
        height: 168px;
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.07);
        background: linear-gradient(100deg, rgba(255,255,255,0.03) 30%, rgba(255,255,255,0.09) 50%, rgba(255,255,255,0.03) 70%);
        background-size: 300% 100%;
        animation: shimmer 1.6s ease-in-out infinite;
    }
    @keyframes shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }

    @media (max-width: 640px) {
        .app-header { flex-direction: column; align-items: flex-start; }
        .app-header-right { align-items: flex-start; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================================
# DATA LOADING
# =========================================================================
def get_remote_etag(url: str):
    """Lightweight HEAD request used only to build a cache-busting key."""
    try:
        resp = requests.head(url, timeout=10, allow_redirects=True)
        tag = resp.headers.get("ETag") or resp.headers.get("Last-Modified")
        if tag:
            return tag
    except requests.RequestException:
        pass
    # Fallback: bucket by 5-minute window so cache still periodically refreshes
    return str(int(time.time() // CACHE_TTL_SECONDS))


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_workbook_bytes(url: str, cache_key: str) -> bytes:
    resp = requests.get(url, timeout=25)
    resp.raise_for_status()
    return resp.content


def normalize(text) -> str:
    if not isinstance(text, str):
        return ""
    return re.sub(r"\s+", " ", text).strip().lower()


def find_row_index(series: pd.Series, target_label: str):
    target = normalize(target_label)
    for idx, val in series.items():
        if normalize(val) == target:
            return idx
    return None


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def parse_workbook(file_bytes: bytes):
    """Parse the H&S and Environment sheets into a flat lookup dict:
    {kpi_key: {month_abbr: value}}"""
    sheets = pd.read_excel(BytesIO(file_bytes), sheet_name=None, header=None, engine="openpyxl")

    hs = sheets.get("H&S")
    env = sheets.get("Environment")
    if hs is None or env is None:
        raise ValueError("Expected sheets 'H&S' and 'Environment' were not found in the workbook.")

    # Detect the two calendar years spanning the financial year (Apr-Mar)
    hs_year_row = hs.iloc[0]
    year_start = None
    year_end = None
    for v in hs_year_row:
        if isinstance(v, (int, float)) and not pd.isna(v) and 2000 < v < 2100:
            if year_start is None:
                year_start = int(v)
            else:
                year_end = int(v)
    if year_start is None:
        year_start = datetime.now().year
    if year_end is None:
        year_end = year_start + 1
    fy_label = f"{year_start}-{year_end}"

    hs_label_col = hs[2]
    env_label_col = env[3]

    def month_series(row, start_col, n_months=12):
        return {MONTH_ORDER[i]: row[start_col + i] for i in range(n_months)}

    kpi_defs = {
        "fatalities":            ("hs", "Fatalities", 3),
        "lti":                   ("hs", "Lost Time Injury", 3),
        "tra":                   ("hs", "Total recordable accidents", 3),
        "first_aid":             ("hs", "First Aid Accident", 3),
        "near_miss":             ("hs", "Near miss", 3),
        "uauc_closure_pct":      ("hs", "% of UA/UC Closure", 3),
        "worker_participation":  ("hs", "Safety observation worker involvement % [%]", 3),
        "energy_intensity":      ("env", "Total energy consumption [kWh/Gross Weight (t Metric)]", 4),
        "water_intensity":       ("env", "Total water withdrawal [m³/Gross Weight (t Metric)]", 4),
        "waste_intensity":       ("env", "Total waste per t(Metrics) [kg/Gross Weight (t Metric)]", 4),
        "production_volume":     ("env", "Production Volume - Gross Weight [Gross Weight (t Metric)]", 4),
    }

    results = {}
    for key, (sheet_key, label, start_col) in kpi_defs.items():
        if sheet_key == "hs":
            row_idx = find_row_index(hs_label_col, label)
            row = hs.iloc[row_idx] if row_idx is not None else None
        else:
            row_idx = find_row_index(env_label_col, label)
            row = env.iloc[row_idx] if row_idx is not None else None

        if row is None:
            results[key] = {m: None for m in MONTH_ORDER}
        else:
            results[key] = month_series(row, start_col)

    return {
        "fy_label": fy_label,
        "kpis": results,
        "loaded_at": datetime.now().strftime("%d %b %Y, %H:%M:%S"),
    }


# =========================================================================
# SIDEBAR — BRAND, LOGO, FILTERS
# =========================================================================
with st.sidebar:
    st.markdown(
        f"""
        <div class="sb-brand">
            <div>
                <div class="sb-brand-name">{COMPANY_NAME} Analytics</div>
                <div class="sb-brand-sub">Enterprise KPI Console</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    logo_file = st.file_uploader("Company Logo", type=["png", "jpg", "jpeg", "svg"], label_visibility="collapsed")
    if logo_file is not None:
        logo_b64 = base64.b64encode(logo_file.getvalue()).decode()
        mime = logo_file.type or "image/png"
        st.markdown(
            f'<div class="logo-box"><img src="data:{mime};base64,{logo_b64}" /></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="logo-box"><span>Upload Company Logo</span></div>', unsafe_allow_html=True)

    st.divider()

    refresh_clicked = st.button("🔄  Refresh Data")
    if refresh_clicked:
        fetch_workbook_bytes.clear()
        parse_workbook.clear()
        st.rerun()

    st.markdown('<div class="sb-section-title">⚙️ &nbsp;Filters</div>', unsafe_allow_html=True)

# =========================================================================
# LOAD + PARSE (animated skeleton loading + error handling)
# =========================================================================
skeleton_placeholder = st.empty()
skeleton_placeholder.markdown(
    """
    <div class="section-label">Key Performance Indicators</div>
    <div class="skel-grid">
        <div class="skel-card"></div><div class="skel-card"></div>
        <div class="skel-card"></div><div class="skel-card"></div>
        <div class="skel-card"></div><div class="skel-card"></div>
        <div class="skel-card"></div><div class="skel-card"></div>
        <div class="skel-card"></div><div class="skel-card"></div>
        <div class="skel-card"></div>
    </div>
    """,
    unsafe_allow_html=True,
)

parsed = None
load_error = None

with st.spinner("⏳ Fetching latest KPI data from GitHub..."):
    try:
        etag_key = get_remote_etag(GITHUB_RAW_URL)
        wb_bytes = fetch_workbook_bytes(GITHUB_RAW_URL, etag_key)
        parsed = parse_workbook(wb_bytes)
    except requests.RequestException as e:
        load_error = f"Could not reach the GitHub RAW URL. Please check your network / URL. Details: {e}"
    except ValueError as e:
        load_error = f"Workbook structure issue: {e}"
    except Exception as e:
        load_error = f"Unexpected error while loading the workbook: {e}"

skeleton_placeholder.empty()

if load_error:
    st.error(f"⚠️ {load_error}")
    st.info(
        "Verify that `GITHUB_RAW_URL` at the top of app.py points to a valid, "
        "publicly accessible RAW Excel file, and that the workbook contains the "
        "'H&S' and 'Environment' sheets."
    )
    st.stop()

fy_label = parsed["fy_label"]
kpis = parsed["kpis"]

with st.sidebar:
    selected_fy = st.selectbox("Financial Year", options=[fy_label], index=0)
    selected_month = st.selectbox("Month", options=MONTH_ORDER, index=0)
    selected_bu = st.selectbox("Business Unit (BU)", options=["All"], index=0)
    selected_plant = st.selectbox("Plant", options=[COMPANY_NAME], index=0)

    st.markdown(
        """
        <div class="sb-footnote">
        ℹ️ This workbook contains a single site/BU. BU and Plant filters will
        actively segment KPIs once multi-site data is available.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown('<div class="sb-section-title">🕒 &nbsp;Sync Status</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="sb-footnote">
        <b style="color:var(--text-hi) !important;">Last refresh</b><br/>{parsed['loaded_at']}<br/><br/>
        Auto-revalidates every {CACHE_TTL_SECONDS // 60} minutes, or instantly via
        the Refresh Data button.
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================================================================
# HEADER
# =========================================================================
now = datetime.now()
current_date_str = now.strftime("%A, %d %B %Y")

st.markdown(
    f"""
    <div class="app-header">
        <div class="app-header-left">
            <div class="app-header-icon">📊</div>
            <div>
                <h1>{COMPANY_NAME} Monthly KPI Dashboard</h1>
                <p>Health, Safety &amp; Environment Performance Overview</p>
            </div>
        </div>
        <div class="app-header-right">
            <div class="header-badge-row">
                <div class="header-badge">📅 {current_date_str}</div>
                <div class="header-badge">FY {selected_fy} · {selected_month}</div>
                <div class="header-badge live"><span class="dot"></span>Live</div>
            </div>
            <div class="header-meta">Last refreshed {parsed['loaded_at']}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="status-strip">
        <span class="status-chip">📍 BU: <b>&nbsp;{selected_bu}</b></span>
        <span class="status-chip">🏭 Plant: <b>&nbsp;{selected_plant}</b></span>
        <span class="status-chip">🗓️ Period: <b>&nbsp;{selected_month} · FY{selected_fy}</b></span>
        <span class="status-chip">♻️ Auto-refresh: <b>&nbsp;{CACHE_TTL_SECONDS // 60} min</b></span>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================================
# KPI VALUE FORMATTING + TREND HELPERS
# =========================================================================
def is_missing(v):
    return v is None or (isinstance(v, float) and pd.isna(v))


def fmt_count(value):
    if is_missing(value):
        return "N/A"
    try:
        return f"{int(round(float(value))):,}"
    except (ValueError, TypeError):
        return str(value)


def fmt_percent(value):
    if is_missing(value):
        return "N/A"
    try:
        return f"{float(value) * 100:.1f}%"
    except (ValueError, TypeError):
        return str(value)


def fmt_decimal(value, decimals=2):
    if is_missing(value):
        return "N/A"
    try:
        return f"{float(value):,.{decimals}f}"
    except (ValueError, TypeError):
        return str(value)


def get_series(kpi_key):
    return kpis.get(kpi_key, {})


def get_val(kpi_key, month):
    return get_series(kpi_key).get(month)


def make_sparkline_svg(values, accent="#4f7cff", width=110, height=34):
    """Build a minimal inline SVG sparkline with gradient fill + end dot."""
    clean = [v for v in values if not is_missing(v)]
    if len(clean) < 2:
        y = height / 2
        return (
            f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<line x1="4" y1="{y}" x2="{width-4}" y2="{y}" stroke="{accent}" '
            f'stroke-width="2" stroke-linecap="round" stroke-dasharray="2,4" opacity="0.5"/>'
            f'</svg>'
        )

    nums = [float(v) if not is_missing(v) else None for v in values]
    valid_nums = [n for n in nums if n is not None]
    lo, hi = min(valid_nums), max(valid_nums)
    rng = (hi - lo) or 1.0

    pad_x, pad_y = 4, 5
    n = len(nums)
    step = (width - 2 * pad_x) / (n - 1)

    points = []
    for i, val in enumerate(nums):
        if val is None:
            continue
        x = pad_x + i * step
        y = height - pad_y - ((val - lo) / rng) * (height - 2 * pad_y)
        points.append((x, y))

    if len(points) < 2:
        y = height / 2
        return (
            f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<line x1="4" y1="{y}" x2="{width-4}" y2="{y}" stroke="{accent}" stroke-width="2" opacity="0.5"/>'
            f'</svg>'
        )

    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    area = f"{pad_x:.1f},{height-pad_y:.1f} " + poly + f" {points[-1][0]:.1f},{height-pad_y:.1f}"
    last_x, last_y = points[-1]
    uid = f"sg{abs(hash(str(values) + accent)) % 100000}"

    return f"""
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
        <defs>
            <linearGradient id="{uid}" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="{accent}" stop-opacity="0.45"/>
                <stop offset="100%" stop-color="{accent}" stop-opacity="0"/>
            </linearGradient>
        </defs>
        <polygon points="{area}" fill="url(#{uid})"/>
        <polyline points="{poly}" fill="none" stroke="{accent}" stroke-width="2.2"
            stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="3.2" fill="{accent}"
            stroke="#0a1230" stroke-width="1.4"/>
    </svg>
    """


HIGHER_IS_BETTER = {
    "fatalities": False, "lti": False, "tra": False, "first_aid": False, "near_miss": False,
    "uauc_closure_pct": True, "worker_participation": True,
    "energy_intensity": False, "water_intensity": False, "waste_intensity": False,
    "production_volume": True,
}

PERCENT_KPIS = {"uauc_closure_pct", "worker_participation"}


def compute_trend(kpi_key, current_val, previous_val):
    """Return (pill_class, arrow, comparison_text)."""
    if is_missing(current_val) or is_missing(previous_val):
        return "flat", "▬", "No prior month data"

    cur = float(current_val)
    prev = float(previous_val)
    diff = cur - prev
    higher_better = HIGHER_IS_BETTER.get(kpi_key, True)

    if abs(diff) < 1e-9:
        return "flat", "▬", "No change vs previous month"

    arrow = "▲" if diff > 0 else "▼"
    improved = (diff > 0) == higher_better
    pill_class = "good" if improved else "bad"

    if kpi_key in PERCENT_KPIS:
        delta_str = f"{diff*100:+.1f} pp"
    else:
        if abs(prev) > 1e-9:
            growth = (diff / abs(prev)) * 100
            delta_str = f"{growth:+.1f}%"
        else:
            delta_str = "N/A"

    return pill_class, arrow, delta_str


# =========================================================================
# KPI CARD DEFINITIONS
# =========================================================================
CARD_DEFS = [
    ("fatalities", "Fatalities", "💀", "#ff5c72", fmt_count, ""),
    ("lti", "LTI", "🩹", "#ff7a59", fmt_count, ""),
    ("tra", "TRA", "📋", "#ffb547", fmt_count, ""),
    ("first_aid", "First Aid Cases", "🧰", "#ffd166", fmt_count, ""),
    ("near_miss", "Near Miss", "⚠️", "#f4e04d", fmt_count, ""),
    ("uauc_closure_pct", "UA/UC Closure %", "✅", "#22d3c5", fmt_percent, ""),
    ("worker_participation", "Worker Participation %", "🧑‍🤝‍🧑", "#4fd1ff", fmt_percent, ""),
    ("energy_intensity", "Energy Intensity", "⚡", "#a78bfa", fmt_decimal, "kWh/t"),
    ("water_intensity", "Water Intensity", "💧", "#60a5fa", fmt_decimal, "m³/t"),
    ("waste_intensity", "Waste Intensity", "🗑️", "#34d399", fmt_decimal, "kg/t"),
    ("production_volume", "Production Volume", "🏭", "#4f7cff", fmt_decimal, "t (Metric)"),
]

st.markdown('<div class="section-label">Key Performance Indicators</div>', unsafe_allow_html=True)

sel_idx = MONTH_ORDER.index(selected_month)
prev_month = MONTH_ORDER[sel_idx - 1] if sel_idx > 0 else None
window_months = MONTH_ORDER[max(0, sel_idx - 5): sel_idx + 1]

cards_html = ['<div class="kpi-grid">']

for key, label, icon, accent, formatter, unit in CARD_DEFS:
    series = get_series(key)
    current_val = series.get(selected_month)
    previous_val = series.get(prev_month) if prev_month else None

    display_val = formatter(current_val)
    unit_html = f'<span class="kpi-unit">{unit}</span>' if (unit and display_val != "N/A") else ""

    pill_class, arrow, delta_str = compute_trend(key, current_val, previous_val)
    prev_display = formatter(previous_val) if prev_month else "N/A"

    spark_values = [series.get(m) for m in window_months]
    spark_svg = make_sparkline_svg(spark_values, accent=accent)

    compare_text = (
        f"vs {prev_month}: {prev_display}" if prev_month else "First month of FY — no prior comparison"
    )

    cards_html.append(f"""
        <div class="kpi-card" style="--accent:{accent};">
            <div class="kpi-top-row">
                <div class="kpi-icon-badge">{icon}</div>
                <div class="kpi-trend-pill {pill_class}">{arrow} {delta_str}</div>
            </div>
            <div class="kpi-value">{display_val}{unit_html}</div>
            <div class="kpi-label">{label}</div>
            <div class="kpi-compare">{compare_text}</div>
            <div class="kpi-spark-wrap">
                {spark_svg}
                <div class="kpi-spark-label">{len(window_months)}-Month&nbsp;Trend</div>
            </div>
        </div>
    """)

cards_html.append("</div>")

st.markdown("".join(cards_html), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
if prev_month:
    st.caption(
        f"Data source: GitHub RAW Excel workbook • Financial Year {selected_fy} • "
        f"Values reflect the '{selected_month}' column of the source sheet, compared against '{prev_month}'."
    )
else:
    st.caption(
        f"Data source: GitHub RAW Excel workbook • Financial Year {selected_fy} • "
        f"Values reflect the '{selected_month}' column of the source sheet."
    )


# =========================================================================
# PHASE 2 — EXECUTIVE DASHBOARD (Power BI style, Plotly powered)
# =========================================================================
# Everything below reads exclusively from `kpis` (the same parsed workbook
# used by the KPI cards above), so it refreshes automatically whenever the
# GitHub source file changes and the cache revalidates. No values are
# hardcoded — targets, scores and cumulative stats are all derived from the
# workbook data itself.
# =========================================================================

st.markdown(
    """
    <style>
    .exec-section-gap { margin-top: 34px; }

    .exec-card {
        background: linear-gradient(160deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.018) 100%);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
        border: 1px solid rgba(255,255,255,0.09);
        border-radius: 16px;
        padding: 18px 20px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.30);
        transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
        margin-bottom: 20px;
    }
    .exec-card:hover {
        transform: translateY(-3px);
        border-color: rgba(120,150,255,0.5);
        box-shadow: 0 16px 36px rgba(15,30,90,0.5);
    }

    .stat-mini {
        display:flex; flex-direction:column; gap:2px;
        padding: 12px 14px;
        border-radius: 12px;
        background: rgba(255,255,255,0.035);
        border: 1px solid rgba(255,255,255,0.07);
    }
    .stat-mini .stat-label {
        font-size: 10.5px; font-weight:800; letter-spacing:0.6px;
        text-transform:uppercase; color:#6d7ab0;
    }
    .stat-mini .stat-value {
        font-size: 21px; font-weight:900; color:#f3f6ff;
        font-variant-numeric: tabular-nums;
    }

    .score-hero {
        display:flex; align-items:center; justify-content:center; flex-direction:column;
        text-align:center; padding: 6px 0 0 0;
    }
    .score-band {
        font-size: 11px; font-weight:800; letter-spacing:0.6px; text-transform:uppercase;
        padding: 4px 12px; border-radius:20px; margin-top:2px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------------
# Plotly enterprise theme helpers
# -------------------------------------------------------------------------
PLOTLY_BG = "rgba(0,0,0,0)"
PLOTLY_FONT_COLOR = "#aab6e3"
PLOTLY_GRID_COLOR = "rgba(255,255,255,0.07)"


def hex_to_rgba(hex_color: str, alpha: float = 0.15) -> str:
    hex_color = (hex_color or "").lstrip("#")
    if len(hex_color) != 6:
        return f"rgba(79,124,255,{alpha})"
    r, g, b = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def apply_enterprise_layout(fig, height=320, title=None, legend=True):
    fig.update_layout(
        paper_bgcolor=PLOTLY_BG,
        plot_bgcolor=PLOTLY_BG,
        font=dict(family="Inter, sans-serif", color=PLOTLY_FONT_COLOR, size=12),
        title=dict(
            text=title, font=dict(size=14, color="#f3f6ff", family="Inter"),
            x=0.01, xanchor="left",
        ) if title else None,
        margin=dict(l=10, r=14, t=48 if title else 16, b=10),
        height=height,
        showlegend=legend,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.0,
            xanchor="right", x=1, font=dict(size=10.5, color="#aab6e3"),
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(bgcolor="#0d1a44", font_size=12, font_family="Inter",
                         bordercolor="rgba(120,150,255,0.4)"),
        transition=dict(duration=600, easing="cubic-in-out"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, color=PLOTLY_FONT_COLOR,
                      linecolor="rgba(255,255,255,0.08)")
    fig.update_yaxes(showgrid=True, gridcolor=PLOTLY_GRID_COLOR, zeroline=False,
                      color=PLOTLY_FONT_COLOR)
    return fig


# -------------------------------------------------------------------------
# Score / target / cumulative statistics — all computed from parsed data
# -------------------------------------------------------------------------
def normalize_score(value, history_values, higher_is_better):
    valid = [float(v) for v in history_values if not is_missing(v)]
    if is_missing(value) or not valid:
        return None
    lo, hi = min(valid), max(valid)
    val = float(value)
    if hi == lo:
        return 100.0
    pct = (val - lo) / (hi - lo)
    return round((pct if higher_is_better else (1 - pct)) * 100, 1)


def compute_hse_score(months_upto, month):
    weights = {
        "fatalities": 3.0, "lti": 2.5, "tra": 1.5, "first_aid": 1.0, "near_miss": 1.0,
        "uauc_closure_pct": 1.5, "worker_participation": 1.5,
        "energy_intensity": 1.0, "water_intensity": 1.0, "waste_intensity": 1.0,
    }
    weighted = []
    for key, w in weights.items():
        series = get_series(key)
        history = [series.get(m) for m in months_upto]
        s = normalize_score(series.get(month), history, HIGHER_IS_BETTER.get(key, True))
        if s is not None:
            weighted.append((s, w))
    if not weighted:
        return None
    total_w = sum(w for _, w in weighted)
    return round(sum(s * w for s, w in weighted) / total_w, 1)


def fy_target(key, months_upto, exclude_current=None):
    """Target benchmark = FY-to-date average excluding the selected month."""
    series = get_series(key)
    vals = [series.get(m) for m in months_upto if m != exclude_current]
    valid = [float(v) for v in vals if not is_missing(v)]
    if not valid:
        return None
    return sum(valid) / len(valid)


def fy_sum(key, months_upto):
    series = get_series(key)
    valid = [float(series.get(m)) for m in months_upto if not is_missing(series.get(m))]
    return sum(valid) if valid else None


def fy_avg(key, months_upto):
    series = get_series(key)
    valid = [float(series.get(m)) for m in months_upto if not is_missing(series.get(m))]
    return (sum(valid) / len(valid)) if valid else None


# -------------------------------------------------------------------------
# Chart builders
# -------------------------------------------------------------------------
def make_gauge(value, target, title, accent="#4f7cff", suffix=""):
    display_value = 0 if value is None else value
    ref = target if target is not None else display_value
    axis_max = max(display_value, ref, 1) * 1.35
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=display_value,
        number={"suffix": suffix, "font": {"size": 24, "color": "#f3f6ff"}},
        delta={
            "reference": ref, "relative": False,
            "increasing": {"color": "#2fd487"}, "decreasing": {"color": "#ff5c72"},
            "font": {"size": 12},
        },
        title={"text": title, "font": {"size": 12.5, "color": "#aab6e3"}},
        gauge={
            "axis": {"range": [0, axis_max], "tickcolor": "#6d7ab0", "tickfont": {"color": "#6d7ab0", "size": 9}},
            "bar": {"color": accent, "thickness": 0.65},
            "bgcolor": "rgba(255,255,255,0.03)",
            "borderwidth": 1,
            "bordercolor": "rgba(255,255,255,0.12)",
            "threshold": {
                "line": {"color": "#ffb547", "width": 3},
                "thickness": 0.8,
                "value": ref,
            } if target is not None else None,
        },
    ))
    apply_enterprise_layout(fig, height=210, legend=False)
    return fig


def make_score_gauge(score):
    score = 0 if score is None else score
    color = "#2fd487" if score >= 75 else ("#ffb547" if score >= 50 else "#ff5c72")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": " / 100", "font": {"size": 26, "color": "#f3f6ff"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#6d7ab0", "tickfont": {"color": "#6d7ab0", "size": 9}},
            "bar": {"color": color, "thickness": 0.68},
            "bgcolor": "rgba(255,255,255,0.03)",
            "borderwidth": 1,
            "bordercolor": "rgba(255,255,255,0.12)",
            "steps": [
                {"range": [0, 50], "color": "rgba(255,92,114,0.12)"},
                {"range": [50, 75], "color": "rgba(255,181,71,0.12)"},
                {"range": [75, 100], "color": "rgba(47,212,135,0.12)"},
            ],
        },
    ))
    apply_enterprise_layout(fig, height=230, legend=False)
    return fig


def make_multiline_chart(months, series_defs, title, yaxis_title=""):
    fig = go.Figure()
    for key, label, color in series_defs:
        y = [get_val(key, m) for m in months]
        fig.add_trace(go.Scatter(
            x=months, y=y, mode="lines+markers", name=label,
            line=dict(color=color, width=2.5, shape="spline"),
            marker=dict(size=6, line=dict(width=1, color="#0a1230")),
            connectgaps=True,
        ))
    apply_enterprise_layout(fig, height=340, title=title)
    fig.update_yaxes(title_text=yaxis_title, title_font=dict(size=11, color="#6d7ab0"))
    return fig


def make_single_trend_chart(months, key, label, color, unit=""):
    y = [get_val(key, m) for m in months]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=months, y=y, mode="lines+markers", fill="tozeroy",
        line=dict(color=color, width=2.5, shape="spline"),
        fillcolor=hex_to_rgba(color, 0.16),
        marker=dict(size=6, line=dict(width=1, color="#0a1230")),
        connectgaps=True,
        name=label,
    ))
    title_suffix = f" · {unit}" if unit else ""
    apply_enterprise_layout(fig, height=250, title=f"{label}{title_suffix}", legend=False)
    return fig


def make_mom_bar_chart(labels, current_vals, previous_vals, current_label, previous_label):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=previous_label, x=labels, y=previous_vals,
        marker_color="rgba(170,182,227,0.32)", marker_line_width=0,
    ))
    fig.add_trace(go.Bar(
        name=current_label, x=labels, y=current_vals,
        marker_color="#4f7cff", marker_line_width=0,
    ))
    fig.update_layout(barmode="group", bargap=0.28, bargroupgap=0.12)
    apply_enterprise_layout(fig, height=320, title="Month-over-Month · Safety Incident Counts")
    return fig


def make_production_chart(months):
    cum = []
    running = 0.0
    has_any = False
    for m in months:
        v = get_val("production_volume", m)
        if not is_missing(v):
            running += float(v)
            has_any = True
        cum.append(running if has_any else None)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=months, y=[get_val("production_volume", m) for m in months],
               name="Monthly Volume", marker_color=hex_to_rgba("#4f7cff", 0.55)),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=months, y=cum, name="Cumulative Volume", mode="lines+markers",
                   line=dict(color="#22d3c5", width=2.5, shape="spline"),
                   marker=dict(size=6)),
        secondary_y=True,
    )
    apply_enterprise_layout(fig, height=340, title="Production Volume · Monthly vs Cumulative")
    fig.update_yaxes(title_text="t (Metric) / month", secondary_y=False,
                      title_font=dict(size=10, color="#6d7ab0"))
    fig.update_yaxes(title_text="Cumulative t (Metric)", secondary_y=True, showgrid=False,
                      title_font=dict(size=10, color="#6d7ab0"))
    return fig


# -------------------------------------------------------------------------
# Render: Executive Dashboard
# -------------------------------------------------------------------------
st.markdown('<div class="exec-section-gap"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-label">Executive Dashboard</div>', unsafe_allow_html=True)

months_upto = MONTH_ORDER[: sel_idx + 1]
hse_score = compute_hse_score(months_upto, selected_month)

# ---- Row 1: HSE Score + Target-vs-Actual Gauges ------------------------
score_col, gauge_col1, gauge_col2, gauge_col3 = st.columns([1.1, 1, 1, 1])

with score_col:
    st.markdown('<div class="exec-card score-hero">', unsafe_allow_html=True)
    st.markdown(
        '<div class="kpi-spark-label" style="margin-bottom:2px;">Monthly HSE Performance Score</div>',
        unsafe_allow_html=True,
    )
    st.plotly_chart(make_score_gauge(hse_score), use_container_width=True, config={"displayModeBar": False})
    score_val = hse_score or 0
    band = "Excellent" if score_val >= 75 else ("Watch" if score_val >= 50 else "At Risk")
    band_color = "#2fd487" if score_val >= 75 else ("#ffb547" if score_val >= 50 else "#ff5c72")
    st.markdown(
        f'<div class="score-band" style="background:{hex_to_rgba(band_color,0.14)};'
        f'color:{band_color};border:1px solid {hex_to_rgba(band_color,0.4)};display:inline-block;">{band}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

gauge_defs = [
    ("uauc_closure_pct", "UA/UC Closure %", "#22d3c5", "%"),
    ("worker_participation", "Worker Participation %", "#4fd1ff", "%"),
    ("energy_intensity", "Energy Intensity", "#a78bfa", ""),
]

for col, (key, label, color, suffix) in zip([gauge_col1, gauge_col2, gauge_col3], gauge_defs):
    with col:
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        actual = get_val(key, selected_month)
        target = fy_target(key, months_upto, exclude_current=selected_month)
        display_actual = actual * 100 if (key in PERCENT_KPIS and not is_missing(actual)) else actual
        display_target = target * 100 if (key in PERCENT_KPIS and not is_missing(target)) else target
        st.plotly_chart(
            make_gauge(display_actual, display_target, f"{label} · Target = FY Avg", accent=color, suffix=suffix),
            use_container_width=True, config={"displayModeBar": False},
        )
        st.markdown("</div>", unsafe_allow_html=True)

# ---- Row 2: Safety trend + Month-over-Month comparison ------------------
trend_col1, trend_col2 = st.columns([1.15, 1])

with trend_col1:
    st.markdown('<div class="exec-card">', unsafe_allow_html=True)
    st.plotly_chart(
        make_multiline_chart(
            months_upto,
            [
                ("lti", "LTI", "#ff7a59"),
                ("tra", "TRA", "#ffb547"),
                ("first_aid", "First Aid", "#ffd166"),
                ("near_miss", "Near Miss", "#f4e04d"),
            ],
            "Safety Incident Trend · FY To-Date",
            yaxis_title="Count",
        ),
        use_container_width=True, config={"displayModeBar": False},
    )
    st.markdown("</div>", unsafe_allow_html=True)

with trend_col2:
    st.markdown('<div class="exec-card">', unsafe_allow_html=True)
    safety_count_keys = ["fatalities", "lti", "tra", "first_aid", "near_miss"]
    current_counts = [get_val(k, selected_month) or 0 for k in safety_count_keys]
    previous_counts = (
        [get_val(k, prev_month) or 0 for k in safety_count_keys] if prev_month else [0] * len(safety_count_keys)
    )
    st.plotly_chart(
        make_mom_bar_chart(
            ["Fatalities", "LTI", "TRA", "First Aid", "Near Miss"],
            current_counts,
            previous_counts,
            selected_month,
            prev_month or "N/A",
        ),
        use_container_width=True, config={"displayModeBar": False},
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ---- Row 3: Environment intensity trends (small multiples) --------------
env_col1, env_col2, env_col3 = st.columns(3)
env_defs = [
    ("energy_intensity", "Energy Intensity", "#a78bfa", "kWh/t"),
    ("water_intensity", "Water Intensity", "#60a5fa", "m³/t"),
    ("waste_intensity", "Waste Intensity", "#34d399", "kg/t"),
]
for col, (key, label, color, unit) in zip([env_col1, env_col2, env_col3], env_defs):
    with col:
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        st.plotly_chart(
            make_single_trend_chart(months_upto, key, label, color, unit),
            use_container_width=True, config={"displayModeBar": False},
        )
        st.markdown("</div>", unsafe_allow_html=True)

# ---- Row 4: Production volume (monthly vs cumulative) -------------------
st.markdown('<div class="exec-card">', unsafe_allow_html=True)
st.plotly_chart(make_production_chart(months_upto), use_container_width=True, config={"displayModeBar": False})
st.markdown("</div>", unsafe_allow_html=True)

# ---- Row 5: Category summaries + FY cumulative statistics ---------------
st.markdown('<div class="section-label">FY Cumulative Statistics &amp; Category Summaries</div>',
            unsafe_allow_html=True)

sum_col1, sum_col2, sum_col3 = st.columns(3)

with sum_col1:
    st.markdown('<div class="exec-card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label" style="margin-bottom:10px;">🦺 Safety Summary (FY-to-Date)</div>',
                unsafe_allow_html=True)
    safety_stats = [
        ("Fatalities", fmt_count(fy_sum("fatalities", months_upto))),
        ("LTI", fmt_count(fy_sum("lti", months_upto))),
        ("TRA", fmt_count(fy_sum("tra", months_upto))),
        ("First Aid", fmt_count(fy_sum("first_aid", months_upto))),
        ("Near Miss", fmt_count(fy_sum("near_miss", months_upto))),
        ("Avg UA/UC Closure", fmt_percent(fy_avg("uauc_closure_pct", months_upto))),
        ("Avg Worker Participation", fmt_percent(fy_avg("worker_participation", months_upto))),
    ]
    for label, val in safety_stats:
        st.markdown(
            f'<div class="stat-mini" style="margin-bottom:8px;"><span class="stat-label">{label}</span>'
            f'<span class="stat-value">{val}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

with sum_col2:
    st.markdown('<div class="exec-card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label" style="margin-bottom:10px;">🌱 Environment Summary (FY-to-Date)</div>',
                unsafe_allow_html=True)
    env_stats = [
        ("Avg Energy Intensity", fmt_decimal(fy_avg("energy_intensity", months_upto)), "kWh/t"),
        ("Avg Water Intensity", fmt_decimal(fy_avg("water_intensity", months_upto)), "m³/t"),
        ("Avg Waste Intensity", fmt_decimal(fy_avg("waste_intensity", months_upto)), "kg/t"),
    ]
    for label, val, unit in env_stats:
        st.markdown(
            f'<div class="stat-mini" style="margin-bottom:8px;"><span class="stat-label">{label}</span>'
            f'<span class="stat-value">{val}<span class="kpi-unit" style="font-size:11px;"> {unit}</span></span></div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

with sum_col3:
    st.markdown('<div class="exec-card">', unsafe_allow_html=True)
    st.markdown('<div class="kpi-label" style="margin-bottom:10px;">🏭 Production Summary (FY-to-Date)</div>',
                unsafe_allow_html=True)
    total_prod = fy_sum("production_volume", months_upto)
    avg_prod = fy_avg("production_volume", months_upto)
    mom_prod_current = get_val("production_volume", selected_month)
    mom_prod_prev = get_val("production_volume", prev_month) if prev_month else None
    _, prod_arrow, prod_delta = compute_trend("production_volume", mom_prod_current, mom_prod_prev)
    prod_stats = [
        ("Total Production (FY)", fmt_decimal(total_prod), "t (Metric)"),
        ("Avg Monthly Production", fmt_decimal(avg_prod), "t (Metric)"),
        (f"MoM Change ({prod_arrow})", prod_delta, ""),
    ]
    for label, val, unit in prod_stats:
        st.markdown(
            f'<div class="stat-mini" style="margin-bottom:8px;"><span class="stat-label">{label}</span>'
            f'<span class="stat-value">{val}<span class="kpi-unit" style="font-size:11px;"> {unit}</span></span></div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

st.caption(
    f"Executive Dashboard reflects FY {selected_fy} data from '{months_upto[0]}' through "
    f"'{selected_month}' ({len(months_upto)} month(s)) · Sourced live from the same GitHub RAW "
    f"workbook and cache as the KPI cards above · Auto-refreshes every {CACHE_TTL_SECONDS // 60} minutes, "
    f"or instantly via the Refresh Data button."
)
