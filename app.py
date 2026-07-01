"""
GNSC Monthly KPI Dashboard - Phase 1 (Enterprise Edition)
==========================================================
A Streamlit enterprise dashboard that reads the Monthly KPI Summary Sheet
directly from a GitHub RAW url and renders Power-BI style KPI cards with
sparklines, month-over-month comparison, growth %, and trend indicators.

Deployment requirements (create a requirements.txt alongside this file):
    streamlit
    pandas
    openpyxl
    requests

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

# =========================================================================
# CONFIGURATION
# =========================================================================
# Replace this with the RAW GitHub URL of your uploaded Excel file, e.g.:
# https://raw.githubusercontent.com/<user>/<repo>/main/Monthly_KPI_Summary_Sheet_April_GNSC.xlsx
GITHUB_RAW_URL = "https://raw.githubusercontent.com/<your-username>/<your-repo>/main/Monthly_KPI_Summary_Sheet_April_GNSC.xlsx"

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
