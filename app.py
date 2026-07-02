"""
Jubilant FoodWorks Limited — Modern Enterprise Analytics Portal.
100% Data-driven architecture deriving parameters directly from Excel structural taxonomy.
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
    compute_portal_derivatives,
    render_risk_panel_dynamic,
    render_audit_log_portal,
)
from helpers.formatting import (
    PAL,
    fmt_number,
    apply_enterprise_layout,
    safe_icon_for_dynamic
)
from transformers.unpivot import infer_and_melt_workbook_metadata

logger = get_logger()
CACHE_TTL_SECONDS = config.RAW_FILE_CACHE_TTL_SECONDS

# Consolidated wide canvas layout overrides initialization
st.set_page_config(
    page_title=f"{config.COMPANY_NAME} | Enterprise Analytics Portal",
    page_icon="📊", layout="wide", initial_sidebar_state="expanded"
)

def compute_hse_score_dynamic(kpi_dict: dict, periods_list: list, target_period: str) -> float:
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
        logger.error(f"Dynamic safety evaluation calculation exception: {e}")
        return 100.0

def get_remote_cache_key(url: str) -> str:
    try:
        resp = requests.head(url, timeout=10, allow_redirects=True)
        tag = resp.headers.get("ETag") or resp.headers.get("Last-Modified")
        if tag: return tag
    except requests.RequestException:
        pass
    return str(int(time.time() // CACHE_TTL_SECONDS))

@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_workbook_bytes(url: str, cache_key: str) -> bytes:
    resp = requests.get(url, timeout=25)
    resp.raise_for_status()
    return resp.content

def inject_portal_design_language():
    p = PAL
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght=400;500;600;700;800&display=swap');
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
    .main .block-container {{ max-width: 100% !important; padding: 1.5rem 3rem !important; }}

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

    div.stButton > button {{ background:var(--primary); color:var(--surface) !important; border:none;
        border-radius:8px; padding:8px 14px; font-weight:600; width:100%; transition: all 0.15s ease; box-shadow:var(--shadow); }}
    div.stButton > button:hover {{ background:var(--primary-2); color:var(--surface) !important; }}

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

def render_sidebar():
    with st.sidebar:
        st.markdown(f"""
            <div class="sb-brand">
                <div class="sb-logo-chip">{config.SIDEBAR_LOGO_TEXT}</div>
                <div>
                    <div class="sb-brand-name">{config.COMPANY_NAME}</div>
                    <div class="sb-brand-sub">{config.DASHBOARD_TITLE_SUB}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="sb-section-title">🗂 Portal Navigation</div>', unsafe_allow_html=True)
        status_placeholder = st.empty()
    return status_placeholder

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
            <div class="kpi-value">{display_val} <span style="font-size:12px; font-weight:500; color:var(--text-mid);">{unit}</span></div>
            <div class="kpi-card-label" style="font-size:12px; font-weight:500; color:var(--text-mid); margin-top:4px; text-transform:capitalize; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{metric_name}</div>
        </div>
        <div class="kpi-compare" style="margin-top:4px; font-size:11px; color:var(--text-lo); border-top:1px solid var(--surface-alt); padding-top:6px;">vs previous period: <b>{fmt_number(prev_value)}</b></div>
    </div>
    """, unsafe_allow_html=True)

def main():
    inject_portal_design_language()
    status_placeholder = render_sidebar()
    
    raw_bytes, sheets, load_error = None, None, None
    fetch_meta = {"source": "live", "fetched_at": "—", "source_url": config.GITHUB_RAW_URL_OVERRIDE, "warning": None}
    schema_warnings = []

    with st.spinner("⏳ Processing master analytical pipeline..."):
        try:
            target_endpoint = resolve_latest_file_url(config.GITHUB_RAW_URL_OVERRIDE)
            cache_sig = get_remote_cache_key(target_endpoint)
            raw_bytes = fetch_workbook_bytes(target_endpoint, cache_sig)
            schema_warnings = validate_schema(raw_bytes)
            sheets = load_all_sheets_raw(raw_bytes)
            fetch_meta = {
                "source": "live",
                "fetched_at": datetime.now().strftime("%d %b %Y, %H:%M:%S"),
                "source_url": target_endpoint,
                "warning": None
            }
        except Exception as e:
            load_error = f"Pipeline execution fault: {e}"
            logger.critical(load_error)

    if load_error or not sheets:
        st.error(f"⚠️ Critical Ingestion Failure: {load_error}")
        st.stop()

    # STEP 4 & 5: Normalize everything using metadata-driven discovery engine
    meta_bundle = infer_and_melt_workbook_metadata(raw_bytes)
    df_long = meta_bundle["long_df"]
    catalog = meta_bundle["catalog"]
    timeline_periods = meta_bundle["periods"]
    units_registry = meta_bundle["units"]

    if df_long.empty:
        st.error("⚠️ Zero entries parsed from current data layout.")
        st.stop()

    # STEP 6: Temporary Debug Dataframe Output Layer Pass
    st.markdown('<div class="section-label">⚙️ Pipeline Debug Layer (Step 6 Verification Table Matrix)</div>', unsafe_allow_html=True)
    st.dataframe(df_long, use_container_width=True, height=220)

    # STEP 7: Pure Metadata Navigation Routing Matrix Controls
    with st.sidebar:
        nav_menu_options = [
            "Executive Overview", 
            "Energy", 
            "Water", 
            "Waste"
        ]
        selected_page = st.radio("Access Console Target Area", options=nav_menu_options, label_visibility="collapsed")
        st.markdown('<div class="sb-section-title">⏱ Period Selection</div>', unsafe_allow_html=True)
        selected_period = st.selectbox("Active Period Window", options=timeline_periods, index=len(timeline_periods)-1)
        
        idx = timeline_periods.index(selected_period)
        previous_period = timeline_periods[idx - 1] if idx > 0 else None

    # STEP 7 Core Filtering Logic Rule Processing Pass
    if selected_page != "Executive Overview":
        df_page_filtered = df_long[df_long["Category"] == selected_page]
    else:
        df_page_filtered = df_long.copy()

    df_period_mask = df_page_filtered[df_page_filtered["Period"] == selected_period]
    unique_metrics = df_page_filtered["Metric"].unique().tolist()
    
    kpi_dict_payload = {}
    for m in df_long["Metric"].unique().tolist():
        m_subset = df_long[df_long["Metric"] == m]
        kpi_dict_payload[m.lower().strip()] = m_subset.set_index("Period")["Value"].to_dict()

    stable_payload_hash = _stable_kpi_hash(kpi_dict_payload)
    derivatives = compute_portal_derivatives(
        stable_payload_hash, kpi_dict_payload, tuple(timeline_periods), selected_period, compute_hse_score_dynamic
    )

    current_date_str = datetime.now().strftime("%A, %d %B %Y")
    st.markdown(f"""
        <div class="app-header">
            <div class="app-header-left">
                <div class="app-header-icon">📊</div>
                <div>
                    <h1>{config.COMPANY_NAME}</h1>
                    <p>{config.DASHBOARD_TITLE} — Context Workspace Layer: <b>{selected_page}</b></p>
                </div>
            </div>
            <div class="header-badge-row">
                <div class="header-badge">📅 {current_date_str}</div>
                <div class="header-badge">FY Target Scope: {config.CURRENT_FISCAL_YEAR}</div>
                <div class="header-badge live">🎚 Active Target: {selected_period}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- ROUTING VIEW RENDERING CHASSIS PASSES ---
    if selected_page == "Executive Overview":
        st.markdown('<div class="section-label">Enterprise High-Level Executive Status & Alert Summaries</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""<div class="kpi-card" style="border-top: 3px solid var(--primary);"><div class="kpi-top-row"><div class="kpi-icon-badge">🎯</div><div class="kpi-trend-pill flat">HSE Index</div></div><div class="kpi-value">{derivatives['hse_score']} <span style="font-size:12px; font-weight:500; color:var(--text-lo);">/ 100</span></div><div class="kpi-label">Dynamic Safety Rating Score Index</div><div class="kpi-compare">Timeline Period Focus: <b>{selected_period}</b></div></div>""", unsafe_allow_html=True)
        with c2:
            prod_val_series = df_long[(df_long["Page"] == "Production") & (df_long["Period"] == selected_period)]["Value"].dropna()
            total_prod_sum = prod_val_series.sum() if not prod_val_series.empty else 0.0
            prod_unit = units_registry.get(df_long[df_long["Page"] == "Production"]["Metric"].iloc[0], "t") if not df_long[df_long["Page"] == "Production"].empty else "t"
            st.markdown(f"""<div class="kpi-card" style="border-top: 3px solid var(--primary-2);"><div class="kpi-top-row"><div class="kpi-icon-badge">🏭</div><div class="kpi-trend-pill flat">Output Volume</div></div><div class="kpi-value">{fmt_number(total_prod_sum)} <span style="font-size:12px; font-weight:500; color:var(--text-lo);">{prod_unit}</span></div><div class="kpi-label">Aggregated Production Volume Output Summation</div><div class="kpi-compare">Current focus window consolidated total</div></div>""", unsafe_allow_html=True)
        with c3:
            total_alerts_count = len(derivatives.get("anomalies", []))
            pill_col = "var(--success)" if total_alerts_count == 0 else "var(--warning)"
            st.markdown(f"""<div class="kpi-card" style="border-top: 3px solid {pill_col};"><div class="kpi-top-row"><div class="kpi-icon-badge">🔔</div><div class="kpi-trend-pill flat">Alert Matrix</div></div><div class="kpi-value" style="color:{pill_col};">{total_alerts_count} <span style="font-size:12px; font-weight:500; color:var(--text-lo);">Active Flags</span></div><div class="kpi-label">Active Exception Anomaly Variance Notifications</div><div class="kpi-compare">Scaled relative to boundary deviations</div></div>""", unsafe_allow_html=True)

        render_risk_panel_dynamic(kpi_dict_payload, selected_period, timeline_periods, derivatives, units_registry)
        
        st.markdown('<div class="section-label">Unified Structural Domain Status Matrices</div>', unsafe_allow_html=True)
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            st.markdown('<div class="exec-card"><h6>⚡ Inferred Energy Section Status</h6>', unsafe_allow_html=True)
            for _, r in df_long[(df_long["Category"] == "Energy") & (df_long["Period"] == selected_period)].head(4).iterrows():
                st.markdown(f'<div class="stat-mini"><span class="stat-label">{r["Metric"][:35]}</span><span class="stat-value">{fmt_number(r["Value"])} {r["Unit"]}</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with cc2:
            st.markdown('<div class="exec-card"><h6>💧 Inferred Water Section Status</h6>', unsafe_allow_html=True)
            for _, r in df_long[(df_long["Category"] == "Water") & (df_long["Period"] == selected_period)].head(4).iterrows():
                st.markdown(f'<div class="stat-mini"><span class="stat-label">{r["Metric"][:35]}</span><span class="stat-value">{fmt_number(r["Value"])} {r["Unit"]}</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with cc3:
            st.markdown('<div class="exec-card"><h6>♻️ Inferred Waste Section Status</h6>', unsafe_allow_html=True)
            for _, r in df_long[(df_long["Category"] == "Waste") & (df_long["Period"] == selected_period)].head(4).iterrows():
                st.markdown(f'<div class="stat-mini"><span class="stat-label">{r["Metric"][:35]}</span><span class="stat-value">{fmt_number(r["Value"])} {r["Unit"]}</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
        render_audit_log_portal(fetch_meta, selected_period)

    else:
        # STEP 8 & 9: Generate data-driven pages from the filtered framework dataframe
        st.markdown(f'<div class="section-label">{selected_page} Management Framework Hub</div>', unsafe_allow_html=True)
        
        cols = st.columns(min(len(unique_metrics), 4))
        for i, metric in enumerate(unique_metrics[:4]):
            m_subset = df_page_filtered[df_page_filtered["Metric"] == metric]
            c_val = m_subset[m_subset["Period"] == selected_period]["Value"].iloc[0] if not m_subset[m_subset["Period"] == selected_period].empty else None
            p_val = m_subset[m_subset["Period"] == previous_period]["Value"].iloc[0] if previous_period and not m_subset[m_subset["Period"] == previous_period].empty else None
            with cols[i % 4]:
                render_kpi_card_layout(metric, c_val, p_val, units_registry.get(metric, ""))

        # STEP 8: Charts built from the workbook records
        from charts.env_visuals import (
            render_waste_efficiency_hybrid_chart,
            render_waste_stream_stacked_chart,
            render_water_discharge_spline,
            render_dynamic_hybrid_overlay,
            render_single_trajectory_area,
        )
        st.markdown('<div class="section-label">Automatic Trend Projections Matrix</div>', unsafe_allow_html=True)
        if selected_page == "Waste":
            c_left, c_right = st.columns(2)
            with c_left:
                st.markdown('<div class="exec-card">', unsafe_allow_html=True)
                render_waste_efficiency_hybrid_chart(df_long, units_registry)
                st.markdown('</div>', unsafe_allow_html=True)
            with c_right:
                st.markdown('<div class="exec-card">', unsafe_allow_html=True)
                render_waste_stream_stacked_chart(df_long, units_registry)
                st.markdown('</div>', unsafe_allow_html=True)
        elif selected_page == "Water":
            st.markdown('<div class="exec-card">', unsafe_allow_html=True)
            render_water_discharge_spline(df_long, units_registry)
            st.markdown('</div>', unsafe_allow_html=True)
        elif selected_page == "Energy":
            st.markdown('<div class="exec-card">', unsafe_allow_html=True)
            render_dynamic_hybrid_overlay(df_long, "⚡ Production Scale vs Direct Energy Consumption Footprint Profile", "Production Volume", "energy consumption", units_registry)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-label">Raw Data Table Explorer Pass</div>', unsafe_allow_html=True)
        df_table_out = df_period_mask[["Category", "Subcategory", "Metric", "Value", "Unit"]].reset_index(drop=True)
        with st.expander("📄 Query Segment Database Records Grid", expanded=False):
            st.dataframe(df_table_out, use_container_width=True, height=280)
            csv_buffer = df_table_out.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export Current Segment Frame to CSV Format", data=csv_buffer, file_name=f"{selected_page}_segment_normalized_export.csv", mime="text/csv")


if __name__ == "__main__":
    main()
