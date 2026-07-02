# kpi_engine.py
"""
KPI Calculation Engine — Derived Analytics, Anomalies, and Interface Containers.
"""
import json
import hashlib
import streamlit as st
import config

def _stable_kpi_hash(kpis: dict) -> str:
    try:
        payload = json.dumps(kpis, sort_keys=True, default=str)
    except TypeError:
        payload = str(kpis)
    return hashlib.md5(payload.encode()).hexdigest()

def get_kpi_status_dynamic(metric_name: str, value) -> str:
    if value is None or str(value).strip() == "" or value == "N/A":
        return "na"
    norm_key = metric_name.lower().strip()
    cfg = None
    for target_key, config_vals in config.KPI_THRESHOLDS.items():
        if target_key in norm_key:
            cfg = config_vals
            break
    if not cfg:
        return "na"
    red, yellow, direction = cfg.get("red"), cfg.get("yellow"), cfg.get("direction")
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "na"

    if direction == "higher_better":
        if red is not None and v < red: return "red"
        if yellow is not None and v < yellow: return "yellow"
        return "green"
    else:
        if red is not None and v >= red: return "red"
        if yellow is not None and v >= yellow: return "yellow"
        return "green"

def detect_anomalies_dynamic(kpi_dict: dict, periods: list, target_period: str) -> list:
    if len(periods) < 2 or target_period not in periods:
        return []
    idx = periods.index(target_period)
    prev_period = periods[idx - 1]
    
    anomalies = []
    for metric_name, timeline_vals in kpi_dict.items():
        cur = timeline_vals.get(target_period)
        prev = timeline_vals.get(prev_period)
        if cur is None or prev is None:
            continue
        try:
            cur, prev = float(cur), float(prev)
        except (TypeError, ValueError):
            continue
        if abs(prev) < 1e-9:
            continue
        pct_change = ((cur - prev) / abs(prev)) * 100
        if abs(pct_change) >= config.ANOMALY_PCT_THRESHOLD:
            anomalies.append({
                "metric": metric_name,
                "pct_change": round(pct_change, 1),
                "direction": "spike" if pct_change > 0 else "drop",
                "current": cur,
                "previous": prev,
            })
    return sorted(anomalies, key=lambda a: abs(a["pct_change"]), reverse=True)

@st.cache_data(ttl=config.KPI_CACHE_TTL_SECONDS, show_spinner=False)
def compute_portal_derivatives(payload_hash: str, kpi_dict: dict, periods_tuple: tuple, target_period: str, _hse_score_fn):
    periods_list = list(periods_tuple)
    hse_score = _hse_score_fn(kpi_dict, periods_list, target_period)
    anomalies = detect_anomalies_dynamic(kpi_dict, periods_list, target_period)
    return {"hse_score": hse_score, "anomalies": anomalies}

def render_risk_panel_dynamic(kpi_dict: dict, target_period: str, periods: list, derivatives: dict):
    st.markdown('<div class="section-label">Exception Anomalies & Live Risk Panel Indicators</div>', unsafe_allow_html=True)
    red_alerts = []
    yellow_alerts = []
    for metric_name, timeline in kpi_dict.items():
        v = timeline.get(target_period)
        status = get_kpi_status_dynamic(metric_name, v)
        if status == "red":
            red_alerts.append((metric_name, v))
        elif status == "yellow":
            yellow_alerts.append((metric_name, v))
            
    anomalies = derivatives.get("anomalies", [])

    if not red_alerts and not yellow_alerts and not anomalies:
        st.markdown(
            '<div class="exec-card" style="border-left: 4px solid var(--success);">'
            '<div class="status-row" style="color: var(--success) !important; font-size: 14px; font-weight: 600;">✓ Compliance Parameters Baseline Stable</div>'
            '<div style="font-size: 12px; color: var(--text-mid); margin-top: 4px;">Zero operations breaches recorded cross-checking target boundaries.</div></div>',
            always_allow_html=True
        )
        return

    c_red, c_yellow, c_anomaly = st.columns(3)
    with c_red:
        st.markdown('<div class="exec-card" style="border-top: 3px solid var(--danger);">', unsafe_allow_html=True)
        st.markdown('<div style="color: var(--danger); font-size: 13px; font-weight: 700; margin-bottom: 12px;">🚨 Critical Operational Breaches</div>', unsafe_allow_html=True)
        if red_alerts:
            for metric, val in red_alerts:
                st.markdown(f'<div class="stat-mini"><span class="stat-label">{metric}</span><span class="stat-value" style="color: var(--danger);">{val:,.1f}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size: 12px; color: var(--text-lo);">Zero critical items flagged</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c_yellow:
        st.markdown('<div class="exec-card" style="border-top: 3px solid var(--warning);">', unsafe_allow_html=True)
        st.markdown('<div style="color: var(--warning); font-size: 13px; font-weight: 700; margin-bottom: 12px;">⚠️ Threshold Boundaries Watchlist</div>', unsafe_allow_html=True)
        if yellow_alerts:
            for metric, val in yellow_alerts:
                st.markdown(f'<div class="stat-mini"><span class="stat-label">{metric[:40]}</span><span class="stat-value" style="color: var(--warning);">{val:,.1f}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size: 12px; color: var(--text-lo);">Zero boundary warnings triggered</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c_anomaly:
        st.markdown('<div class="exec-card" style="border-top: 3px solid var(--primary);">', unsafe_allow_html=True)
        st.markdown(f'<div style="color: var(--primary); font-size: 13px; font-weight: 700; margin-bottom: 12px;">📊 Timeline Volume Deviations (MoM ≥ {config.ANOMALY_PCT_THRESHOLD:.0f}%)</div>', unsafe_allow_html=True)
        if anomalies:
            for a in anomalies[:5]:
                arrow = "▲" if a["direction"] == "spike" else "▼"
                color = "var(--danger)" if a["direction"] == "spike" and "waste" in a["metric"].lower() else "var(--primary)"
                st.markdown(f'<div class="stat-mini"><span class="stat-label">{a["metric"][:40]}</span><span class="stat-value" style="color: {color};">{arrow} {a["pct_change"]:+.1f}%</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size: 12px; color: var(--text-lo);">Zero extreme variations observed</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def render_risk_panel(kpi_dict: dict, selected_month: str, prev_month, months_upto: list, card_meta: dict, derivatives: dict):
    render_risk_panel_dynamic(kpi_dict, selected_month, months_upto, derivatives)

def render_audit_log(fetch_meta: dict, selected_fy: str, selected_month: str):
    st.markdown('<div class="section-label">Pipeline Operational Diagnostics Log</div>', unsafe_allow_html=True)
    st.markdown('<div class="exec-card">', unsafe_allow_html=True)
    source_badge = "🟢 Live Production Feed" if fetch_meta.get("source") == "live" else "⚠️ Disconnected Snapshot Backup Layer"
    st.markdown(f'<div class="stat-mini"><span class="stat-label">System Feed Profile</span><span class="stat-value">{source_badge}</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stat-mini"><span class="stat-label">Refresh Execution Timestamp</span><span class="stat-value">{fetch_meta.get("fetched_at", "N/A")}</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stat-mini"><span class="stat-label">Active Audit Boundary Target</span><span class="stat-value">FY {selected_fy} · Period: {selected_month}</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="stat-mini"><span class="stat-label">Endpoint String URI Mapping</span><span class="stat-value" style="font-family: monospace; font-size:11px;">{fetch_meta.get("source_url", "N/A")}</span></div>', unsafe_allow_html=True)
    if fetch_meta.get("warning"):
        st.markdown(f'<div class="stat-mini" style="border-left: 3px solid var(--warning); background-color: #FFFBEB;"><span class="stat-label" style="color: var(--warning);">Diagnostic Exception Notice</span><span class="stat-value" style="color: var(--warning); font-size:11.5px;">{fetch_meta["warning"]}</span></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def render_audit_log_portal(fetch_meta: dict, current_period: str):
    render_audit_log(fetch_meta, config.CURRENT_FISCAL_YEAR, current_period)
