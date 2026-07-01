"""
GNSC Monthly KPI Dashboard - Phase 1
=====================================
A Streamlit enterprise dashboard that reads the Monthly KPI Summary Sheet
directly from a GitHub RAW url and renders Power-BI style KPI cards.

Deployment requirements (create a requirements.txt alongside this file):
    streamlit
    pandas
    openpyxl
    requests

Deploy on Streamlit Community Cloud by pointing it at this app.py.
"""

import re
import time
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
# PAGE CONFIG + THEME
# =========================================================================
st.set_page_config(
    page_title=f"{COMPANY_NAME} | Monthly KPI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .stApp {
        background: linear-gradient(180deg, #0a1128 0%, #0d1b3e 45%, #0a1128 100%);
        color: #e8ecf7;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #060b1f 0%, #0c1636 100%);
        border-right: 1px solid #1c2c5c;
    }
    section[data-testid="stSidebar"] * {
        color: #cfd8f0 !important;
    }

    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 18px 26px;
        margin-bottom: 22px;
        background: linear-gradient(120deg, #101f4a 0%, #16296b 60%, #101f4a 100%);
        border-radius: 14px;
        border: 1px solid #24346e;
        box-shadow: 0 4px 18px rgba(0,0,0,0.35);
    }
    .app-header h1 {
        margin: 0;
        font-size: 26px;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: 0.3px;
    }
    .app-header p {
        margin: 2px 0 0 0;
        font-size: 13px;
        color: #9db0e8;
    }
    .header-badge {
        background: rgba(88, 130, 255, 0.15);
        border: 1px solid #3a55a8;
        color: #a9c0ff;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }

    .logo-box {
        width: 100%;
        height: 76px;
        border: 1.5px dashed #33469c;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #7f92d6;
        font-weight: 700;
        letter-spacing: 1px;
        font-size: 13px;
        margin-bottom: 18px;
        background: rgba(255,255,255,0.02);
    }

    .section-label {
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        color: #6f83c9;
        font-weight: 700;
        margin: 18px 0 10px 2px;
    }

    .kpi-card {
        position: relative;
        background: linear-gradient(145deg, #101c40 0%, #0c1633 100%);
        border: 1px solid #1f2e63;
        border-left: 4px solid var(--accent, #4f7cff);
        border-radius: 12px;
        padding: 16px 18px 14px 18px;
        min-height: 118px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.30);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.45);
        border-color: var(--accent, #4f7cff);
    }
    .kpi-icon {
        font-size: 20px;
        opacity: 0.85;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 30px;
        font-weight: 800;
        color: #ffffff;
        line-height: 1.15;
    }
    .kpi-label {
        margin-top: 4px;
        font-size: 12.5px;
        font-weight: 600;
        color: #a6b3de;
        text-transform: uppercase;
        letter-spacing: 0.4px;
    }
    .kpi-sub {
        margin-top: 6px;
        font-size: 11px;
        color: #5f70a8;
    }

    .status-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 14px;
        background: rgba(255,255,255,0.03);
        border: 1px solid #1c2c5c;
        border-radius: 8px;
        font-size: 12px;
        color: #8fa0d9;
        margin-bottom: 18px;
    }

    div.stButton > button {
        background: linear-gradient(120deg, #2f4fd6, #4f7cff);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 14px;
        font-weight: 600;
        width: 100%;
    }
    div.stButton > button:hover {
        background: linear-gradient(120deg, #3a5be0, #6089ff);
        color: white;
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

    # month -> column offset (0-based within the 12-month block)
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
# SIDEBAR - FILTERS
# =========================================================================
with st.sidebar:
    st.markdown('<div class="logo-box">COMPANY LOGO</div>', unsafe_allow_html=True)
    st.markdown(f"### {COMPANY_NAME}")
    st.caption("Monthly KPI Summary")
    st.divider()

    refresh_clicked = st.button("🔄  Refresh Data")
    if refresh_clicked:
        fetch_workbook_bytes.clear()
        parse_workbook.clear()
        st.rerun()

    st.markdown('<div class="section-label">Filters</div>', unsafe_allow_html=True)

# =========================================================================
# LOAD + PARSE (with spinner & error handling)
# =========================================================================
parsed = None
load_error = None

with st.spinner("Fetching latest KPI data from GitHub..."):
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
    st.caption("This workbook contains a single site/BU. BU and Plant filters "
               "will actively segment KPIs once multi-site data is available.")
    st.divider()
    st.caption(f"Last data refresh: {parsed['loaded_at']}")

# =========================================================================
# HEADER
# =========================================================================
st.markdown(
    f"""
    <div class="app-header">
        <div>
            <h1>{COMPANY_NAME} Monthly KPI Dashboard</h1>
            <p>Health, Safety &amp; Environment Performance Overview</p>
        </div>
        <div class="header-badge">FY {selected_fy} &nbsp;•&nbsp; {selected_month}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="status-bar">
        <span>📍 BU: <b>{selected_bu}</b> &nbsp;|&nbsp; Plant: <b>{selected_plant}</b></span>
        <span>🕒 Auto-refresh every {CACHE_TTL_SECONDS // 60} min &nbsp;|&nbsp; Synced: {parsed['loaded_at']}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================================================================
# KPI VALUE FORMATTING HELPERS
# =========================================================================
def fmt_count(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    try:
        return f"{int(round(float(value))):,}"
    except (ValueError, TypeError):
        return str(value)


def fmt_percent(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    try:
        v = float(value)
        # values are stored as fractions (0-1)
        return f"{v * 100:.1f}%"
    except (ValueError, TypeError):
        return str(value)


def fmt_decimal(value, decimals=2):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    try:
        return f"{float(value):,.{decimals}f}"
    except (ValueError, TypeError):
        return str(value)


def get_val(kpi_key):
    return kpis.get(kpi_key, {}).get(selected_month)


# =========================================================================
# KPI CARD DEFINITIONS
# =========================================================================
CARD_DEFS = [
    ("fatalities", "Fatalities", "💀", "#ff4d4f", fmt_count, ""),
    ("lti", "LTI", "🩹", "#ff7a45", fmt_count, ""),
    ("tra", "TRA", "📋", "#faad14", fmt_count, ""),
    ("first_aid", "First Aid Cases", "🧰", "#ffc53d", fmt_count, ""),
    ("near_miss", "Near Miss", "⚠️", "#ffe58f", fmt_count, ""),
    ("uauc_closure_pct", "UA/UC Closure %", "✅", "#36cfc9", fmt_percent, ""),
    ("worker_participation", "Worker Participation %", "🧑‍🤝‍🧑", "#40a9ff", fmt_percent, ""),
    ("energy_intensity", "Energy Intensity", "⚡", "#9254de", fmt_decimal, "kWh/t"),
    ("water_intensity", "Water Intensity", "💧", "#597ef7", fmt_decimal, "m³/t"),
    ("waste_intensity", "Waste Intensity", "🗑️", "#73d13d", fmt_decimal, "kg/t"),
    ("production_volume", "Production Volume", "🏭", "#4f7cff", fmt_decimal, "t (Metric)"),
]

st.markdown('<div class="section-label">Key Performance Indicators</div>', unsafe_allow_html=True)

cols_per_row = 4
for row_start in range(0, len(CARD_DEFS), cols_per_row):
    row_defs = CARD_DEFS[row_start:row_start + cols_per_row]
    cols = st.columns(len(row_defs))
    for col, (key, label, icon, accent, formatter, unit) in zip(cols, row_defs):
        raw_val = get_val(key)
        display_val = formatter(raw_val)
        sub_text = unit if (unit and display_val != "N/A") else ""
        with col:
            st.markdown(
                f"""
                <div class="kpi-card" style="--accent:{accent};">
                    <div class="kpi-icon">{icon}</div>
                    <div class="kpi-value">{display_val}</div>
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-sub">{sub_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

st.markdown("<br>", unsafe_allow_html=True)
st.caption(
    f"Data source: GitHub RAW Excel workbook • Financial Year {selected_fy} • "
    f"Values shown reflect the '{selected_month}' column of the source sheet."
)
