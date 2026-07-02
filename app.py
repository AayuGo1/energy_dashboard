"""
Enterprise KPI Analytics Dashboard — Core Runtime Orchestration File.
"""
import re
import time
from io import BytesIO
from datetime import datetime

import requests
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

import config
from data_pipeline import (
    get_logger,
    fetch_workbook_hardened,
    validate_schema,
    resolve_latest_file_url,
)
from kpi_engine import (
    _stable_kpi_hash,
    compute_kpi_derivatives,
    render_risk_panel,
    render_audit_log,
)
from helpers.formatting import (
    PAL,
    fmt_number,
    safe_icon_for,
    apply_enterprise_layout
)
from transformers.unpivot import melt_wide_sheet_to_long_cached
from charts.env_visuals import (
    render_waste_efficiency_hybrid_chart,
    render_waste_stream_stacked_chart,
    render_water_discharge_spline,
)

logger = get_logger()

CACHE_TTL_SECONDS = config.RAW_FILE_CACHE_TTL_SECONDS
PLOTLY_BG = "rgba(0,0,0,0)"


def compute_hse_score(kpis: dict, months_list: list, selected_month: str) -> float:
    """
    Computes a dynamic, real-time aggregate performance score 
    by validating lagging incidents and target fulfillment across historical sheets.
    """
    try:
        total_incidents = 0.0
        for indicator in ["fatalities", "lost time injury", "total recordable accidents", "near miss"]:
            if indicator in kpis and selected_month in kpis[indicator]:
                val = kpis[indicator].get(selected_month, 0)
                total_incidents += float(val) if val else 0.0
                
        closure_rate = 1.0
        if "% of ua/uc closure" in kpis and selected_month in kpis["% of ua/uc closure"]:
            rate = kpis["% of ua/uc closure"].get(selected_month, 1.0)
            closure_rate = float(rate) if rate else 1.0

        base_score = 100.0 - (total_incidents * 5.0)
        final_score = max(0.0, min(100.0, base_score * (0.5 + (0.5 * closure_rate))))
        return round(final_score, 1)
    except Exception as e:
        logger.error(f"Error evaluating structural mathematical hse calculations: {e}")
        return 100.0


def get_remote_cache_key(url: str) -> str:
    try:
        resp = requests.head(url, timeout=10, allow_redirects=True)
        tag = resp.headers.get("ETag") or resp.headers.get("Last-Modified")
        if tag:
            return tag
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch cache validation headers from endpoint: {e}")
    return str(int(time.time() // CACHE_TTL_SECONDS))


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_workbook_bytes(url: str, cache_key: str) -> bytes:
    resp = requests.get(url, timeout=25)
    resp.raise_for_status()
    return resp.content


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_all_sheets(file_bytes: bytes) -> dict:
    sheets = pd.read_excel(BytesIO(file_bytes), sheet_name=None, engine="openpyxl")
    cleaned = {}
    for name, df in sheets.items():
        if df is None or df.empty:
            continue
        cleaned[name] = df.dropna(axis=0, how="all")
    return cleaned


def render_sidebar():
    with st.sidebar:
        st.markdown(f"""
            <div class="sb-brand">
                <div class="sb-logo-chip">{config.COMPANY_NAME[:3].upper()}</div>
                <div>
                    <div class="sb-brand-name">{config.COMPANY_NAME} Analytics</div>
                    <div class="sb-brand-sub">{config.DASHBOARD_TITLE_SUB}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="sb-section-title">📡 &nbsp;Data Source Status</div>', unsafe_allow_html=True)
        status_placeholder = st.empty()
        
        if st.button("🔄  Refresh Data"):
            fetch_workbook_bytes.clear()
            load_all_sheets.clear()
            st.rerun()
            
        st.markdown('<div class="sb-section-title">🧭 &nbsp;Filters</div>', unsafe_allow_html=True)
    return status_placeholder


def render_status(placeholder, connected: bool, last_refresh: str, is_fallback: bool = False, note: str = ""):
    with placeholder.container():
        if connected and not is_fallback:
            st.markdown(f"""
                <div class="status-card">
                    <div class="status-row"><span class="status-dot"></span>Live · Connected</div>
                    <div class="status-sub">Refreshed: {last_refresh}</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="status-card" style="border-left:3px solid var(--warning);">
                    <div class="status-row" style="color:var(--warning) !important;">
                        <span class="status-dot" style="background:var(--warning); animation:none;"></span>Local Backup Active
                    </div>
                    <div class="status-sub">{note or 'Running on persistent backup metadata cache.'}</div>
                </div>
            """, unsafe_allow_html=True)


def render_kpi_card(col_name, value, prev_value, icon):
    display_val = fmt_number(value)
    pill_class, arrow, delta_str = "flat", "▬", "No prior period"

    if value is not None and prev_value is not None:
        try:
            v, p = float(value), float(prev_value)
            diff = v - p
            if abs(diff) < 1e-9:
                pill_class, arrow, delta_str = "flat", "▬", "No change"
            elif abs(p) > 1e-9:
                pct = (diff / abs(p)) * 100
                arrow = "▲" if diff > 0 else "▼"
                pill_class = "good" if diff > 0 else "bad"
                delta_str = f"{arrow} {abs(pct):.1f}%"
        except (ValueError, TypeError):
            pass

    st.markdown(f"""
    <div class="kpi-card">
        <div>
            <div class="kpi-top-row">
                <div class="kpi-icon-badge">{icon}</div>
                <div class="kpi-trend-pill {pill_class}">{delta_str}</div>
            </div>
            <div class="kpi-value">{display_val}</div>
            <div class="kpi-label">{col_name}</div>
        </div>
        <div class="kpi-compare">vs previous period: {fmt_number(prev_value)}</div>
    </div>
    """, unsafe_allow_html=True)


def render_executive_summary(df_long: pd.DataFrame, metrics: list, period: str, prev_period: str):
    st.markdown('<div class="section-label">Executive Summary</div>', unsafe_allow_html=True)
    top_metrics = metrics[:4]
    cols = st.columns(len(top_metrics))
    
    for col, metric in zip(cols, top_metrics):
        m_data = df_long[df_long["Metric"] == metric]
        cur_row = m_data[m_data["Period"] == period]
        prev_row = m_data[m_data["Period"] == prev_period] if prev_period else pd.DataFrame()
        
        cur_val = cur_row["Value"].iloc[0] if not cur_row.empty else None
        prev_val = prev_row["Value"].iloc[0] if not prev_row.empty else None
        
        with col:
            render_kpi_card(metric, cur_val, prev_val, safe_icon_for(metric))


def render_kpi_grid(df_long: pd.DataFrame, metrics: list, period: str, prev_period: str):
    st.markdown('<div class="section-label">All Tracked Structural Metrics Grid</div>', unsafe_allow_html=True)
    grid_metrics = metrics[4:]
    for i in range(0, len(grid_metrics), 4):
        chunk = grid_metrics[i:i+4]
        row_cols = st.columns(len(chunk))
        for col, m in zip(row_cols, chunk):
            m_data = df_long[df_long["Metric"] == m]
            cur_row = m_data[m_data["Period"] == period]
            prev_row = m_data[m_data["Period"] == prev_period] if prev_period else pd.DataFrame()
            
            c_v = cur_row["Value"].iloc[0] if not cur_row.empty else None
            p_v = prev_row["Value"].iloc[0] if not prev_row.empty else None
            with col:
                render_kpi_card(m, c_v, p_v, safe_icon_for(m))


def inject_css():
    p = PAL
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght=400;500;600;700;800&display=swap');
    :root {{
        --bg:{p['bg']}; --surface:{p['surface']}; --surface-alt:{p['surface-alt']};
        --border:{p['border']}; --text-hi:{p['text-hi']}; --text-mid:{p['text-mid']};
        --text-lo:{p['text-lo']}; --primary:{p['primary']}; --primary-2:{p['primary-2']};
        --success:{p['success']}; --warning:{p['warning']};
        --shadow:{p['shadow']}; --shadow-hover:{p['shadow-hover']};
    }}
    html, body, [class*="css"] {{ font-family:'Inter',sans-serif; }}
    #MainMenu, footer {{visibility:hidden;}}
    header[data-testid="stHeader"] {{background:transparent;}}
    .stApp {{ background:var(--bg); color:var(--text-hi); }}
    .main .block-container {{ padding-top:1.1rem; }}

    section[data-testid="stSidebar"] {{ background:var(--surface); border-right:1px solid var(--border); }}
    section[data-testid="stSidebar"] * {{ color:var(--text-mid) !important; }}

    .sb-brand {{ display:flex; align-items:center; gap:10px; padding:6px 2px 16px 2px;
        border-bottom:1px solid var(--border); margin-bottom:14px; }}
    .sb-logo-chip {{ width:38px; height:38px; border-radius:10px; flex-shrink:0;
        background:linear-gradient(135deg, var(--primary), var(--primary-2));
        display:flex; align-items:center; justify-content:center; color:#fff !important;
        font-weight:800; font-size:13px; }}
    .sb-brand-name {{ font-size:15px; font-weight:800; color:var(--text-hi) !important; }}
    .sb-brand-sub {{ font-size:10.5px; color:var(--text-lo) !important; letter-spacing:.5px;
        text-transform:uppercase; font-weight:700; }}
    .sb-section-title {{ font-size:10.5px; text-transform:uppercase; letter-spacing:1.2px;
        color:var(--text-lo) !important; font-weight:800; margin:18px 0 8px 2px; }}

    .status-card {{ background:var(--surface-alt); border:1px solid var(--border); border-radius:10px;
        padding:10px 12px; margin-bottom:6px; }}
    .status-row {{ display:flex; align-items:center; gap:7px; font-size:12.5px; font-weight:700;
        color:var(--text-hi) !important; }}
    .status-dot {{ height:8px; width:8px; border-radius:50%; background:var(--success);
        display:inline-block; animation:pulseDot 1.8s infinite; }}
    @keyframes pulseDot {{ 0%{{box-shadow:0 0 0 0 rgba(22,163,74,.5);}} 70%{{box-shadow:0 0 0 6px rgba(22,163,74,0);}}
        100%{{box-shadow:0 0 0 0 rgba(22,163,74,0);}} }}
    .status-sub {{ font-size:10.5px; color:var(--text-lo) !important; margin-top:4px; }}

    div.stButton > button {{ background:var(--primary); color:#fff !important; border:none;
        border-radius:8px; padding:9px 12px; font-weight:700; width:100%; box-shadow:var(--shadow); }}
    div.stButton > button:hover {{ background:var(--primary-2); }}

    .app-header {{ display:flex; align-items:center; justify-content:space-between; gap:16px;
        padding:18px 24px; margin-bottom:20px; background:var(--surface); border-radius:14px;
        border:1px solid var(--border); box-shadow:var(--shadow); flex-wrap:wrap; }}
    .app-header-left {{ display:flex; align-items:center; gap:14px; }}
    .app-header-icon {{ width:46px; height:46px; border-radius:12px; display:flex; align-items:center;
        justify-content:center; background:linear-gradient(135deg, var(--primary), var(--primary-2));
        color:#fff; font-size:20px; flex-shrink:0; }}
    .app-header h1 {{ margin:0; font-size:21px; font-weight:800; color:var(--text-hi); letter-spacing:-.2px; }}
    .app-header p {{ margin:2px 0 0 0; font-size:12.5px; color:var(--text-mid); font-weight:500; }}
    .header-badge-row {{ display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }}
    .header-badge {{ background:var(--surface-alt); border:1px solid var(--border); color:var(--text-mid);
        padding:5px 12px; border-radius:20px; font-size:11.5px; font-weight:700; white-space:nowrap; }}
    .header-badge.live {{ background:rgba(22,163,74,0.10); border-color:rgba(22,163,74,0.3); color:var(--success); }}

    .section-label {{ font-size:12.5px; text-transform:uppercase; letter-spacing:1.2px; color:var(--primary);
        font-weight:800; margin:26px 0 14px 2px; display:flex; align-items:center; gap:10px; }}
    .section-label::after {{ content:""; flex:1; height:1px; background:var(--border); }}

    .kpi-card {{ background:var(--surface); border:1px solid var(--border); border-radius:12px;
        padding:16px 16px 14px 16px; box-shadow:var(--shadow); height:158px;
        display:flex; flex-direction:column; justify-content:space-between;
        border-top:3px solid var(--primary); transition:transform .15s ease, box-shadow .15s ease; }}
    .kpi-card:hover {{ transform:translateY(-2px); box-shadow:var(--shadow-hover); }}
    .kpi-top-row {{ display:flex; align-items:flex-start; justify-content:space-between; }}
    .kpi-icon-badge {{ width:32px; height:32px; border-radius:8px; display:flex; align-items:center;
        justify-content:center; font-size:15px; background:var(--surface-alt); border:1px solid var(--border); }}
    .kpi-trend-pill {{ display:flex; align-items:center; gap:4px; font-size:10.8px; font-weight:800;
        padding:3px 9px; border-radius:20px; white-space:nowrap; }}
    .kpi-trend-pill.good {{ background:rgba(22,163,74,0.10); color:var(--success); border:1px solid rgba(22,163,74,0.3); }}
    .kpi-trend-pill.bad  {{ background:rgba(185,137,0,0.12); color:var(--warning); border:1px solid rgba(185,137,0,0.3); }}
    .kpi-trend-pill.flat {{ background:var(--surface-alt); color:var(--text-mid); border:1px solid var(--border); }}
    .kpi-value {{ font-size:24px; font-weight:800; color:var(--text-hi); line-height:1.1; font-variant-numeric:tabular-nums; }}
    .kpi-label {{ margin-top:3px; font-size:11.2px; font-weight:700; color:var(--text-mid);
        text-transform:uppercase; letter-spacing:.3px; }}
    .kpi-compare {{ margin-top:2px; font-size:10.3px; color:var(--text-lo); font-weight:600; }}

    .exec-card {{ background:var(--surface); border:1px solid var(--border); border-radius:12px;
        padding:16px 18px; box-shadow:var(--shadow); margin-bottom:18px; }}

    .stat-mini {{ display:flex; align-items:center; justify-content:space-between; gap:8px;
        padding:10px 12px; border-radius:8px; background:var(--surface-alt);
        border:1px solid var(--border); margin-bottom:7px; }}
    .stat-mini .stat-label {{ font-size:11.5px; font-weight:700; color:var(--text-mid); }}
    .stat-mini .stat-value {{ font-size:14.5px; font-weight:800; color:var(--text-hi); font-variant-numeric:tabular-nums; }}
    </style>
    """, unsafe_allow_html=True)


def main():
    inject_css()
    status_placeholder = render_sidebar()
    
    sheets, load_error = None, None
    fetch_meta = {"source": "live", "fetched_at": "—", "source_url": config.GITHUB_RAW_URL_OVERRIDE, "warning": None}
    schema_warnings = []

    with st.spinner("⏳ Accessing data pipeline..."):
        try:
            target_endpoint = resolve_latest_file_url(config.GITHUB_RAW_URL_OVERRIDE)
            cache_sig = get_remote_cache_key(target_endpoint)
            raw_bytes, fetch_meta = fetch_workbook_hardened(target_endpoint, cache_sig, fetch_workbook_bytes)
            
            if fetch_meta.get("source") == "fallback":
                st.warning("⚠️ Running from cached snapshot because GitHub is unavailable.")
                logger.warning("Live endpoint unreachable. Activated persistent backup data cache assets.")
            else:
                logger.info("Successfully established connection to live GitHub contents stream.")

            schema_warnings = validate_schema(raw_bytes)
            if schema_warnings:
                st.warning("⚠️ Workbook structural variances detected. Check Audit Panel logs for validation details.")
                logger.warning(f"Workbook template variation flags raised: {schema_warnings}")
            
            sheets = load_all_sheets(raw_bytes)
        except Exception as e:
            load_error = f"Pipeline execution fault: {e}"
            logger.critical(load_error)

    if load_error or not sheets:
        st.error(f"⚠️ Critical Ingestion Failure: {load_error}")
        st.stop()

    render_status(
        status_placeholder, 
        connected=(load_error is None), 
        last_refresh=fetch_meta.get("fetched_at", "—"), 
        is_fallback=(fetch_meta.get("source") == "fallback"), 
        note=str(fetch_meta.get("warning") or "")
    )

    with st.sidebar:
        selected_sheet = st.selectbox("Operational Domain Sheet", options=list(sheets.keys()), index=0)

    df_raw = sheets.get(selected_sheet)
    if df_raw is None or df_raw.empty:
        st.warning("The selected workspace has no structured rows available.")
        st.stop()
        
    df_long = melt_wide_sheet_to_long_cached(df_raw)
    if df_long.empty:
        st.warning("No structured monthly data columns found.")
        st.stop()

    timeline_periods = sorted(df_long["Period"].unique().tolist(), key=lambda x: ("2026" in x, x))
    selected_period = timeline_periods[-1] if timeline_periods else "Global"
    previous_period = timeline_periods[-2] if len(timeline_periods) >= 2 else None

    unique_metrics = df_long["Metric"].unique().tolist()
    card_meta_dictionary = {m: (m, fmt_number, "") for m in unique_metrics}
    
    kpi_dict_payload = {}
    for m in unique_metrics:
        m_subset = df_long[df_long["Metric"] == m]
        kpi_dict_payload[m.lower().strip()] = m_subset.set_index("Period")["Value"].to_dict()
        
    stable_payload_hash = _stable_kpi_hash(kpi_dict_payload)
    derivatives = compute_kpi_derivatives(
        stable_payload_hash, kpi_dict_payload, compute_hse_score, tuple(timeline_periods), selected_period
    )

    st.markdown(f"""
        <div class="app-header">
            <div class="app-header-left">
                <div class="app-header-icon">📊</div>
                <div>
                    <h1>{config.COMPANY_NAME} Enterprise Resource & Waste Analytics Platform</h1>
                    <p>Domain Scope: {selected_sheet} | Active Window: {selected_period}</p>
                </div>
            </div>
            <div class="header-badge-row">
                <div class="header-badge">📋 {len(unique_metrics)} Metrics Loaded</div>
                <div class="header-badge live">🟢 Phase 4 Secure</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    render_executive_summary(df_long, unique_metrics, selected_period, previous_period)
    
    normalized_meta = {k.lower().strip(): v for k, v in card_meta_dictionary.items()}
    render_risk_panel(kpi_dict_payload, selected_period, previous_period, timeline_periods, normalized_meta, derivatives)

    st.markdown('<div class="section-label">Waste, Discharge & Resource Intensity Trends</div>', unsafe_allow_html=True)
    if "environment" in selected_sheet.lower():
        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown('<div class="exec-card">', unsafe_allow_html=True)
            render_waste_efficiency_hybrid_chart(df_long)
            st.markdown('</div>', unsafe_allow_html=True)
        with c_right:
            st.markdown('<div class="exec-card">', unsafe_allow_html=True)
            render_waste_stream_stacked_chart(df_long)
            st.markdown('</div>', unsafe_allow_html=True)
            
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        render_water_discharge_spline(df_long)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Visualizing generic analytical performance metric summary profiles below.")

    render_kpi_grid(df_long, unique_metrics, selected_period, previous_period)

    with st.expander("📄 View Normalized Long-Form Structural Data Table", expanded=False):
        st.dataframe(df_long, use_container_width=True, height=350)

    if schema_warnings:
        fetch_meta["warning"] = f"Validation issues: {'; '.join(schema_warnings)}"
        
    render_audit_log(fetch_meta, config.CURRENT_FISCAL_YEAR, selected_period)


if __name__ == "__main__":
    main()
