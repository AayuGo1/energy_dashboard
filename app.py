# app.py
"""
Jubilant FoodWorks Limited — Modern Enterprise Analytics Portal.
Zero-Hardcoded Data Ingestion Engine with High-Fidelity UI Customization Layouts.
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
from transformers.unpivot import infer_and_melt_workbook_metadata
from kpi_engine import (
    _stable_kpi_hash,
    compute_portal_derivatives,
    render_risk_panel_dynamic,
    render_audit_log_portal,
    get_kpi_status_dynamic,
)
from helpers.formatting import (
    PAL,
    fmt_number,
    safe_icon_for_dynamic,
    apply_enterprise_layout
)
from charts.env_visuals import (
    render_dynamic_hybrid_overlay,
    render_dynamic_category_distribution,
    render_single_trajectory_area,
)

logger = get_logger()

st.set_page_config(
    page_title=f"{config.COMPANY_NAME} | Enterprise Analytics Portal",
    page_icon="📊", layout="wide", initial_sidebar_state="expanded"
)


def compute_hse_score_dynamic(kpi_dict: dict, periods_list: list, target_period: str) -> float:
    """
    Computes a fluid, dynamic safety index by scanning metrics keys for common indicators.
    Requires no structural code rewrites when new metrics rows are modified.
    """
    try:
        total_incidents = 0.0
        incident_keywords = ["fatalit", "injury", "accident", "near miss"]
        
        for key, timeline in kpi_dict.items():
            if any(k in key for k in incident_keywords):
                val = timeline.get(target_period, 0)
                total_incidents += float(val) if val and not pd.isna(val) else 0.0
                
        closure_rate = 1.0
        for key, timeline in kpi_dict.items():
            if "closure" in key or "uauc" in key:
                rate = timeline.get(target_period, 1.0)
                closure_rate = float(rate) if rate and not pd.isna(rate) else 1.0
                break

        base_score = 100.0 - (total_incidents * 4.5)
        final_score = max(0.0, min(100.0, base_score * (0.6 + (0.4 * closure_rate))))
        return round(final_score, 1)
    except Exception as e:
        logger.error(f"Dynamic safety evaluation engine intercept anomaly: {e}")
        return 100.0


def get_remote_cache_key(url: str) -> str:
    try:
        resp = requests.head(url, timeout=10, allow_redirects=True)
        tag = resp.headers.get("ETag") or resp.headers.get("Last-Modified")
        if tag:
            return tag
    except requests.RequestException:
        pass
    return str(int(time.time() // config.RAW_FILE_CACHE_TTL_SECONDS))


@st.cache_data(ttl=config.RAW_FILE_CACHE_TTL_SECONDS, show_spinner=False)
def load_all_sheets_raw(file_bytes: bytes) -> dict:
    sheets = pd.read_excel(BytesIO(file_bytes), sheet_name=None, engine="openpyxl")
    cleaned = {}
    for name, df in sheets.items():
        if df is None or df.empty:
            continue
        cleaned[name] = df.dropna(axis=0, how="all")
    return cleaned


def inject_portal_design_language():
    p = PAL
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    :root {{
        --bg:{p['bg']}; --surface:{p['surface']}; --surface-alt:{p['surface-alt']};
        --border:{p['border']}; --text-hi:{p['text-hi']}; --text-mid:{p['text-mid']};
        --text-lo:{p['text-lo']}; --primary:{p['primary']}; --primary-2:{p['primary-2']};
        --success:{p['success']}; --warning:{p['warning']}; --danger:{p['danger']};
        --shadow:{p['shadow']}; --shadow-hover:{p['shadow-hover']};
    }}
    html, body, [class*="css"] {{ font-family:'Inter', sans-serif; }}
    #MainMenu, footer {{visibility:hidden;}}
    header[data-testid="stHeader"] {{background:transparent;}}
    .stApp {{ background:var(--bg); color:var(--text-hi); }}
    .main .block-container {{ padding: 1.5rem 3rem; }}

    section[data-testid="stSidebar"] {{ background:var(--surface); border-right:1px solid var(--border); padding-top: 1rem; }}
    section[data-testid="stSidebar"] * {{ font-size: 13.5px; color: var(--text-mid) !important; }}

    .sb-brand {{ display:flex; align-items:center; gap:12px; padding:8px 8px 22px 8px;
        border-bottom:1px solid var(--border); margin-bottom:18px; }}
    .sb-logo-chip {{ width:40px; height:40px; border-radius:10px; flex-shrink:0;
        background:linear-gradient(135deg, var(--primary), var(--primary-2));
        display:flex; align-items:center; justify-content:center; color:#fff !important;
        font-weight:800; font-size:14px; letter-spacing: -0.3px; }}
    .sb-brand-name {{ font-size:14.5px; font-weight:700; color:var(--text-hi) !important; line-height: 1.2; }}
    .sb-brand-sub {{ font-size:11px; color:var(--text-lo) !important; font-weight:500; margin-top: 1px; }}
    .sb-section-title {{ font-size:11px; text-transform:uppercase; letter-spacing:0.8px;
        color:var(--text-lo) !important; font-weight:700; margin:24px 0 8px 6px; }}

    .status-card {{ background:var(--surface-alt); border:1px solid var(--border); border-radius:12px;
        padding:12px 14px; margin-bottom:6px; box-shadow: var(--shadow); }}
    .status-row {{ display:flex; align-items:center; gap:8px; font-size:12.5px; font-weight:600;
        color:var(--text-hi) !important; }}
    .status-dot {{ height:7px; width:7px; border-radius:50%; background:var(--success);
        display:inline-block; animation:pulseDot 2s infinite; }}
    @keyframes pulseDot {{ 0%{{box-shadow:0 0 0 0 rgba(16,185,129,0.35);}} 70%{{box-shadow:0 0 0 5px rgba(16,185,129,0);}}
        100%{{box-shadow:0 0 0 0 rgba(16,185,129,0);}} }}
    .status-sub {{ font-size:11px; color:var(--text-mid) !important; margin-top:5px; font-variant-numeric: tabular-nums; }}

    div.stButton > button {{ background:var(--surface); color:var(--text-mid) !important; border:1px solid var(--border);
        border-radius:8px; padding:8px 14px; font-weight:600; width:100%; transition: all 0.15s ease; box-shadow:var(--shadow); }}
    div.stButton > button:hover {{ border-color: var(--primary); color: var(--primary) !important; background: #FAF9FA; }}

    .app-header {{ display:flex; align-items:center; justify-content:between; gap:20px;
        padding:22px 28px; margin-bottom:26px; background:var(--surface); border-radius:16px;
        border:1px solid var(--border); box-shadow:var(--shadow); flex-wrap:wrap; }}
    .app-header-left {{ display:flex; align-items:center; gap:16px; flex: 1; }}
    .app-header-icon {{ width:50px; height:50px; border-radius:12px; display:flex; align-items:center;
        justify-content:center; background:linear-gradient(135deg, var(--primary), var(--primary-2));
        color:#fff; font-size:22px; box-shadow: 0 4px 14px rgba(0,82,204,0.12); }}
    .app-header h1 {{ margin:0; font-size:22px; font-weight:700; color:var(--text-hi); letter-spacing:-0.5px; }}
    .app-header p {{ margin:3px 0 0 0; font-size:13px; color:var(--text-mid); }}
    .header-badge-row {{ display:flex; gap:10px; flex-wrap:wrap; align-items: center; }}
    .header-badge {{ background:var(--surface-alt); border:1px solid var(--border); color:var(--text-mid);
        padding:6px 14px; border-radius:30px; font-size:12px; font-weight:600; font-variant-numeric: tabular-nums; }}
    .header-badge.live {{ background:rgba(16,185,129,0.06); border-color:rgba(16,185,129,0.2); color:var(--success); }}

    .section-label {{ font-size:11.5px; text-transform:uppercase; letter-spacing:0.8px; color:var(--primary);
        font-weight:700; margin:26px 0 16px 2px; display:flex; align-items:center; gap:12px; }}
    .section-label::after {{ content:""; flex:1; height:1px; background:var(--border); }}

    .kpi-card {{ background:var(--surface); border:1px solid var(--border); border-radius:16px;
        padding:18px 20px; box-shadow:var(--shadow); height:158px;
        display:flex; flex-direction:column; justify-content:space-between;
        position: relative; overflow: hidden; transition: transform .18s cubic-bezier(0.16, 1, 0.3, 1), box-shadow .18s ease; }}
    .kpi-card:hover {{ transform:translateY(-2px); box-shadow:var(--shadow-hover); border-color: var(--text-lo); }}
    .kpi-top-row {{ display:flex; align-items:center; justify-content:space-between; width: 100%; }}
    .kpi-icon-badge {{ width:34px; height:34px; border-radius:8px; display:flex; align-items:center;
        justify-content:center; font-size:16px; background:var(--surface-alt); border:1px solid var(--border); }}
    .kpi-trend-pill {{ display:flex; align-items:center; gap:4px; font-size:11.5px; font-weight:600;
        padding:4px 10px; border-radius:30px; white-space:nowrap; font-variant-numeric: tabular-nums; }}
    .kpi-trend-pill.good {{ background:rgba(16,185,129,0.08); color:var(--success); }}
    .kpi-trend-pill.bad  {{ background:rgba(239,68,68,0.08); color:var(--danger); }}
    .kpi-trend-pill.flat {{ background:var(--surface-alt); color:var(--text-mid); }}
    .kpi-value {{ font-size:25px; font-weight:700; color:var(--text-hi); line-height:1.1; font-variant-numeric:tabular-nums; letter-spacing: -0.5px; margin-top: 12px; }}
    .kpi-label {{ margin-top:3px; font-size:12px; font-weight:500; color:var(--text-mid); text-transform:capitalize; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .kpi-compare {{ margin-top:4px; font-size:11px; color:var(--text-lo); font-weight:400; border-top: 1px solid var(--surface-alt); padding-top: 6px; }}
    .kpi-compare b {{ font-variant-numeric: tabular-nums; color: var(--text-mid); }}

    .exec-card {{ background:var(--surface); border:1px solid var(--border); border-radius:16px;
        padding:20px 24px; box-shadow:var(--shadow); margin-bottom:20px; }}

    .stat-mini {{ display:flex; align-items:center; justify-content:space-between; gap:12px;
        padding:11px 14px; border-radius:10px; background:var(--surface-alt);
        border:1px solid var(--border); margin-bottom:8px; }}
    
    div[data-testid="stExpander"] {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; box-shadow: var(--shadow); overflow: hidden; }}
    div[data-testid="stExpander"] summary {{ padding: 12px 16px; font-weight: 600; color: var(--text-hi); }}
    
    .stDataFrame div {{ font-family: 'Inter', sans-serif !important; font-size: 12.5px !important; }}
    </style>
    """, unsafe_allow_html=True)


def render_kpi_card_layout(metric_name, value, prev_value, unit):
    display_val = fmt_number(value)
    pill_class, arrow, delta_str = "flat", "▬", "Stable"
    
    if value is not None and prev_value is not None:
        try:
            v, p = float(value), float(prev_value)
            diff = v - p
            if abs(diff) < 1e-9:
                pill_class, arrow, delta_str = "flat", "▬", "No variance"
            elif abs(p) > 1e-9:
                pct = (diff / abs(p)) * 100
                arrow = "▲" if diff > 0 else "▼"
                is_bad_metric = any(k in metric_name.lower() for k in ["waste", "accident", "injury", "fatality", "diesel"])
                pill_class = "good" if (diff <= 0 if is_bad_metric else diff > 0) else "bad"
                delta_str = f"{arrow} {abs(pct):.1f}%"
        except (ValueError, TypeError):
            pass

    st.markdown(f"""
    <div class="kpi-card">
        <div>
            <div class="kpi-top-row">
                <div class="kpi-icon-badge">{safe_icon_for_dynamic(metric_name)}</div>
                <div class="kpi-trend-pill {pill_class}">{delta_str}</div>
            </div>
            <div class="kpi-value">{display_val} <span style="font-size:13px; font-weight:500; color:var(--text-mid);">{unit}</span></div>
            <div class="kpi-label">{metric_name}</div>
        </div>
        <div class="kpi-compare">vs previous period: <b>{fmt_number(prev_value)}</b></div>
    </div>
    """, unsafe_allow_html=True)


def main():
    inject_portal_design_language()
    status_placeholder = render_sidebar()
    
    # Core system state initializations
    raw_bytes, sheets, load_error = None, None, None
    fetch_meta = {"source": "live", "fetched_at": "—", "source_url": config.GITHUB_RAW_URL_OVERRIDE, "warning": None}
    schema_warnings = []

    with st.spinner("⏳ Authorizing and establishing live pipeline synchronization..."):
        try:
            target_endpoint = resolve_latest_file_url(config.GITHUB_RAW_URL_OVERRIDE)
            cache_sig = get_remote_cache_key(target_endpoint)
            raw_bytes, fetch_meta = fetch_workbook_hardened(target_endpoint, cache_sig, fetch_workbook_bytes)
            schema_warnings = validate_schema(raw_bytes)
            sheets = load_all_sheets_raw(raw_bytes)
        except Exception as e:
            load_error = f"Pipeline execution termination sequence: {e}"
            logger.critical(load_error)

    if load_error or not sheets:
        st.error(f"⚠️ High-Priority Pipeline Failure Intercepted: {load_error}")
        st.stop()

    render_status(
        status_placeholder, connected=(load_error is None),
        last_refresh=fetch_meta.get("fetched_at", "—"),
        is_fallback=(fetch_meta.get("source") == "fallback"),
        note=str(fetch_meta.get("warning") or "")
    )

    # Execute zero-hardcoded dynamic taxonomy metadata inference unpivoting block
    meta_bundle = infer_and_melt_workbook_metadata(sheets)
    df_long = meta_bundle["long_df"]
    taxonomies = meta_bundle["taxonomies"]
    timeline_periods = meta_bundle["periods"]
    units_registry = meta_bundle["units"]

    if df_long.empty:
        st.error("⚠️ Zero tracking entries could be parsed from current spreadsheet source.")
        st.stop()

    # Determine reporting period boundaries dynamically
    selected_period = timeline_periods[-1] if timeline_periods else "Global"
    previous_period = timeline_periods[-2] if len(timeline_periods) >= 2 else None

    # Assemble dynamic key dictionary layout structures to support computation analytics
    unique_metrics = df_long["Metric"].unique().tolist()
    kpi_dict_payload = {}
    for m in unique_metrics:
        m_subset = df_long[df_long["Metric"] == m]
        kpi_dict_payload[m.lower().strip()] = m_subset.set_index("Period")["Value"].to_dict()

    stable_payload_hash = _stable_kpi_hash(kpi_dict_payload)
    derivatives = compute_portal_derivatives(
        stable_payload_hash, kpi_dict_payload, tuple(timeline_periods), selected_period, compute_hse_score_dynamic
    )

    # =============================================================================
    # ENTERPRISE PORTAL SIDEBAR NAVIGATION
    # =============================================================================
    with st.sidebar:
        st.markdown('<div class="sb-section-title">🗂 Portal Navigation</div>', unsafe_allow_html=True)
        
        # Setup modern page selection tree indexing
        nav_options = ["🏠 Executive Overview", "🦺 Health & Safety", "⚡ Energy Metrics", "💧 Water Management", "♻️ Waste & Sustainability", "🏭 Production Yields", "📈 Macro Trends", "📋 Diagnostics"]
        selected_page = st.radio("Access Console Target Area", options=nav_options, label_visibility="collapsed")
        
        st.markdown('<div class="sb-section-title">⏱ Reporting Window Filter</div>', unsafe_allow_html=True)
        selected_period = st.selectbox("Active Period Focus", options=timeline_periods, index=len(timeline_periods)-1)
        idx = timeline_periods.index(selected_period)
        previous_period = timeline_periods[idx - 1] if idx > 0 else None

    # Filter baseline dataframes inside hot data paths to avoid repetitive copying overheads
    df_period_mask = df_long[df_long["Period"] == selected_period]

    # =============================================================================
    # PAGE LAYOUT ENGINES
    # =============================================================================
    
    # --- PAGE 1: EXECUTIVE SUMMARY OVERVIEW ---
    if "executive" in selected_page.lower():
        st.markdown('<div class="section-label">Enterprise Executive Summary Console</div>', unsafe_allow_html=True)
        
        # Draw high-level aggregate scoring matrix cards
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""<div class="kpi-card" style="border-top: 3px solid var(--primary);"><div class="kpi-top-row"><div class="kpi-icon-badge">🎯</div><div class="kpi-trend-pill flat">Score Index</div></div><div class="kpi-value">{derivatives['hse_score']} <span style="font-size:12px; font-weight:500; color:var(--text-lo);">/ 100</span></div><div class="kpi-label">Dynamic EHS Operational Index</div><div class="kpi-compare">Timeline Period Focus: <b>{selected_period}</b></div></div>""", unsafe_allow_html=True)
        with c2:
            prod_val_series = df_period_mask[df_period_mask["Page"] == "Production"]["Value"].dropna()
            total_prod_sum = prod_val_series.sum() if not prod_val_series.empty else 0.0
            st.markdown(f"""<div class="kpi-card" style="border-top: 3px solid var(--primary-2);"><div class="kpi-top-row"><div class="kpi-icon-badge">🏭</div><div class="kpi-trend-pill flat">Gross Vol</div></div><div class="kpi-value">{fmt_number(total_prod_sum)} <span style="font-size:12px; font-weight:500; color:var(--text-lo);">Metrics</span></div><div class="kpi-label">Aggregated Industrial Production Output</div><div class="kpi-compare">Consolidated current period summation</div></div>""", unsafe_allow_html=True)
        with c3:
            total_alerts_count = len(derivatives.get("anomalies", []))
            pill_col = "var(--success)" if total_alerts_count == 0 else "var(--warning)"
            st.markdown(f"""<div class="kpi-card" style="border-top: 3px solid {pill_col};"><div class="kpi-top-row"><div class="kpi-icon-badge">🔔</div><div class="kpi-trend-pill flat">Alert System</div></div><div class="kpi-value" style="color:{pill_col};">{total_alerts_count} <span style="font-size:12px; font-weight:500; color:var(--text-lo);">Flags</span></div><div class="kpi-label">Active Exception Anomaly Violations</div><div class="kpi-compare">Triggers scaled MoM change bounds</div></div>""", unsafe_allow_html=True)

        render_risk_panel_dynamic(kpi_dict_payload, selected_period, timeline_periods, derivatives)
        
        # Secondary segmented summary cross checks
        st.markdown('<div class="section-label">Cross-Divisional Inferred Categorical Benchmarks</div>', unsafe_allow_html=True)
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            st.markdown('<div class="exec-card"><h6>⚡ Energy System Subcategories</h6>', unsafe_allow_html=True)
            df_eg = df_period_mask[df_period_mask["Metric"].str.lower().str.contains("energy|diesel|lpg|electricity", regex=True)]
            for _, r in df_eg.head(4).iterrows():
                st.markdown(f'<div class="stat-mini"><span class="stat-label">{r["Metric"][:35]}</span><span class="stat-value">{fmt_number(r["Value"])} {r["Unit"]}</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with cc2:
            st.markdown('<div class="exec-card"><h6>💧 Water Network Balances</h6>', unsafe_allow_html=True)
            df_wt = df_period_mask[df_period_mask["Metric"].str.lower().str.contains("water|withdrawal|discharge", regex=True)]
            for _, r in df_wt.head(4).iterrows():
                st.markdown(f'<div class="stat-mini"><span class="stat-label">{r["Metric"][:35]}</span><span class="stat-value">{fmt_number(r["Value"])} {r["Unit"]}</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with cc3:
            st.markdown('<div class="exec-card"><h6>♻️ Waste Management Aggregations</h6>', unsafe_allow_html=True)
            df_ws = df_period_mask[df_period_mask["Metric"].str.lower().str.contains("waste|landfill|compost", regex=True)]
            for _, r in df_ws.head(4).iterrows():
                st.markdown(f'<div class="stat-mini"><span class="stat-label">{r["Metric"][:35]}</span><span class="stat-value">{fmt_number(r["Value"])} {r["Unit"]}</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # --- PAGE 2: HEALTH & SAFETY ---
    elif "safety" in selected_page.lower():
        st.markdown('<div class="section-label">Health & Safety Automated Dashboard Console</div>', unsafe_allow_html=True)
        df_hs = df_long[df_long["Page"] == "Health & Safety"]
        hs_metrics = df_hs["Metric"].unique().tolist()
        
        cols = st.columns(min(len(hs_metrics), 4))
        for i, metric in enumerate(hs_metrics[:4]):
            m_df = df_hs[df_hs["Metric"] == metric]
            c_val = m_df[m_df["Period"] == selected_period]["Value"].iloc[0] if not m_df[m_df["Period"] == selected_period].empty else None
            p_val = m_df[m_df["Period"] == previous_period]["Value"].iloc[0] if previous_period and not m_df[m_df["Period"] == previous_period].empty else None
            with cols[i % 4]:
                render_kpi_card_layout(metric, c_val, p_val, units_registry.get(metric, ""))
                
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        render_single_trajectory_area(df_hs, "near miss", "🚨 Near Miss Performance Log Frequency Curve", PAL["warning"])
        st.markdown('</div>', unsafe_allow_html=True)

    # --- PAGE 3: ENERGY METRICS ---
    elif "energy" in selected_page.lower():
        st.markdown('<div class="section-label">Energy System Resource Subdivision Management Console</div>', unsafe_allow_html=True)
        df_en = df_long[df_long["Metric"].str.lower().str.contains("energy|diesel|lpg|electricity", regex=True)]
        en_metrics = df_en["Metric"].unique().tolist()
        
        cols = st.columns(min(len(en_metrics), 4))
        for i, metric in enumerate(en_metrics[:4]):
            m_df = df_en[df_en["Metric"] == metric]
            c_val = m_df[m_df["Period"] == selected_period]["Value"].iloc[0] if not m_df[m_df["Period"] == selected_period].empty else None
            p_val = m_df[m_df["Period"] == previous_period]["Value"].iloc[0] if previous_period and not m_df[m_df["Period"] == previous_period].empty else None
            with cols[i % 4]:
                render_kpi_card_layout(metric, c_val, p_val, units_registry.get(metric, ""))
                
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        render_dynamic_hybrid_overlay(df_long, "⚡ Production Vol vs Direct Energy Consumption Intensity Mapping", "Production Volume", "energy consumption")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- PAGE 4: WATER MANAGEMENT ---
    elif "water" in selected_page.lower():
        st.markdown('<div class="section-label">Hydraulic Infrastructure Intake & Discharge Monitors</div>', unsafe_allow_html=True)
        df_wt = df_long[df_long["Metric"].str.lower().str.contains("water", regex=False)]
        wt_metrics = df_wt["Metric"].unique().tolist()
        
        cols = st.columns(min(len(wt_metrics), 4))
        for i, metric in enumerate(wt_metrics[:4]):
            m_df = df_wt[df_wt["Metric"] == metric]
            c_val = m_df[m_df["Period"] == selected_period]["Value"].iloc[0] if not m_df[m_df["Period"] == selected_period].empty else None
            p_val = m_df[m_df["Period"] == previous_period]["Value"].iloc[0] if previous_period and not m_df[m_df["Period"] == previous_period].empty else None
            with cols[i % 4]:
                render_kpi_card_layout(metric, c_val, p_val, units_registry.get(metric, ""))
                
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        render_water_discharge_spline(df_long)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- PAGE 5: WASTE & SUSTAINABILITY ---
    elif "waste" in selected_page.lower():
        st.markdown('<div class="section-label">Waste Vector Minimization & Material Stewardship Matrix</div>', unsafe_allow_html=True)
        df_wst = df_long[df_long["Metric"].str.lower().str.contains("waste", regex=False)]
        wst_metrics = df_wst["Metric"].unique().tolist()
        
        cols = st.columns(min(len(wst_metrics), 4))
        for i, metric in enumerate(wst_metrics[:4]):
            m_df = df_wst[df_wst["Metric"] == metric]
            c_val = m_df[m_df["Period"] == selected_period]["Value"].iloc[0] if not m_df[m_df["Period"] == selected_period].empty else None
            p_val = m_df[m_df["Period"] == previous_period]["Value"].iloc[0] if previous_period and not m_df[m_df["Period"] == previous_period].empty else None
            with cols[i % 4]:
                render_kpi_card_layout(metric, c_val, p_val, units_registry.get(metric, ""))
                
        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown('<div class="exec-card">', unsafe_allow_html=True)
            render_waste_efficiency_hybrid_chart(df_long)
            st.markdown('</div>', unsafe_allow_html=True)
        with c_right:
            st.markdown('<div class="exec-card">', unsafe_allow_html=True)
            render_waste_stream_stacked_chart(df_long)
            st.markdown('</div>', unsafe_allow_html=True)

    # --- PAGE 6: PRODUCTION YIELDS ---
    elif "production" in selected_page.lower():
        st.markdown('<div class="section-label">Industrial Production Yield Volumes & Outputs</div>', unsafe_allow_html=True)
        df_pr = df_long[df_long["Page"] == "Production"]
        pr_metrics = df_pr["Metric"].unique().tolist()
        
        for metric in pr_metrics:
            m_df = df_pr[df_pr["Metric"] == metric]
            c_val = m_df[m_df["Period"] == selected_period]["Value"].iloc[0] if not m_df[m_df["Period"] == selected_period].empty else None
            p_val = m_df[m_df["Period"] == previous_period]["Value"].iloc[0] if previous_period and not m_df[m_df["Period"] == previous_period].empty else None
            render_kpi_card_layout(metric, c_val, p_val, units_registry.get(metric, ""))
            
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        render_single_trajectory_area(df_pr, "production volume", "🏭 Consolidated Manufacturing Physical Production Volume Trend [Metric Tons]", PAL["primary"])
        st.markdown('</div>', unsafe_allow_html=True)

    # --- PAGE 7: TRENDS GENERAL GRID OVERVIEW ---
    elif "trends" in selected_page.lower():
        st.markdown('<div class="section-label">Consolidated Historical Micro-Trends Matrix Dashboard</div>', unsafe_allow_html=True)
        metric_selection = st.selectbox("Select Target Variable Series to Project", options=unique_metrics)
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        render_single_trajectory_area(df_long, metric_selection, f"📈 Historical Longitudinal Evaluation Timeline Profile: {metric_selection}", PAL["primary"])
        st.markdown('</div>', unsafe_allow_html=True)

    # --- PAGE 8: SYSTEM LOG DIAGNOSTICS Expanded View ---
    elif "diagnostics" in selected_page.lower():
        st.info("System operational configurations and telemetry logs summary detailed below.")

    # =============================================================================
    # PERSISTENT SYSTEM BASE LAYOUTS (Tables and Audit Traces)
    # =============================================================================
    st.markdown('<div class="section-label">Context Inferred Tabular Spreadsheet Source Grid View</div>', unsafe_allow_html=True)
    df_grid_display = df_long[df_long["Period"] == selected_period][["Category", "Subcategory", "Metric", "Value", "Unit"]].reset_index(drop=True)
    
    with st.expander("📄 Access Active Workspace Row Balance Data Array Matrix", expanded=False):
        c1, c2 = st.columns([3, 1])
        with c1:
            search_query = st.text_input("⚡ Local String Parameter Search Engine Filter", placeholder="Type keywords to filter row dimensions dynamically...")
        if search_query:
            df_grid_display = df_grid_display[df_grid_display["Metric"].str.lower().str.contains(search_query.lower()) | df_grid_display["Category"].str.lower().str.contains(search_query.lower())]
        st.dataframe(df_grid_display, use_container_width=True, height=350)
        
        csv_buffer = df_grid_display.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Current Table Pass to CSV Text Format", data=csv_buffer, file_name=f"{selected_sheet}_normalized_export.csv", mime="text/csv")

    render_audit_log_portal(fetch_meta, selected_period)
    
    st.caption(
        f"Authenticated Portal State · Auto-Discovered {len(unique_metrics)} unique variables. "
        f"Pipeline auto-sync key expires in {config.RAW_FILE_CACHE_TTL_SECONDS // 60} minutes."
    )


if __name__ == "__main__":
    main()
