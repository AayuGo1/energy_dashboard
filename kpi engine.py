# kpi_engine.py
"""
KPI Calculation Engine — Derived Analytics and Risk Panels.
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

def get_kpi_status(key: str, value) -> str:
    if value is None:
        return "na"
    cfg = config.KPI_THRESHOLDS.get(key.lower().strip())
    if not cfg:
        return "na"
    red, yellow, direction = cfg.get("red"), cfg.get("yellow"), cfg.get("direction")
    if red is None and yellow is None:
        return "na"
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

def detect_anomalies(kpis: dict, months_upto: list, selected_month: str) -> list:
    if len(months_upto) < 2:
        return []
    prev_month = months_upto[-2]
    anomalies = []
    for key, series in kpis.items():
        cur = series.get(selected_month)
        prev = series.get(prev_month)
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
                "key": key,
                "pct_change": round(pct_change, 1),
                "direction": "spike" if pct_change > 0 else "drop",
                "current": cur,
                "previous": prev,
            })
    return sorted(anomalies, key=lambda a: abs(a["pct_change"]), reverse=True)

@st.cache_data(ttl=config.KPI_CACHE_TTL_SECONDS, show_spinner=False)
def compute_kpi_derivatives(kpi_hash: str, _kpis: dict, _hse_score_fn, months_upto: tuple, selected_month: str):
    months_list = list(months_upto)
    hse_score = _hse_score_fn(_kpis, months_list, selected_month)
    anomalies = detect_anomalies(_kpis, months_list, selected_month)
    return {"hse_score": hse_score, "anomalies": anomalies}

def render_risk_panel(kpis: dict, selected_month: str, prev_month, months_upto: list, card_meta: dict, derivatives: dict):
    st.markdown('<div class="section-label">Risk Dashboard · Exceptional Variances</div>', unsafe_allow_html=True)
    statuses = {key: get_kpi_status(key, kpis.get(key.lower().strip(), {}).get(selected_month)) for key in card_meta}
    red_items = [k for k, s in statuses.items() if s == "red"]
    yellow_items = [k for k, s in statuses.items() if s == "yellow"]
    anomalies = derivatives.get("anomalies", [])

    if not red_items and not yellow_items and not anomalies:
        st.markdown(
            '<div class="exec-card" style="border-left:4px solid var(--success);">'
            '<div class="status-row" style="color:var(--success) !important; font-size:13px;">✓ Operations Clean & Compliant</div>'
            '<div style="font-size:12px; color:var(--text-mid); margin-top:4px;">No active compliance alert parameters are breaking boundary thresholds.</div></div>',
            unsafe_allow_html=True
        )
        return

    col_red, col_yellow, col_anomaly = st.columns(3)
    with col_red:
        st.markdown('<div class="exec-card" style="border-top: 3px solid var(--danger);">', unsafe_allow_html=True)
        st.markdown('<div class="kpi-label" style="color:var(--danger); font-weight:700; margin-bottom:12px;">🚨 Critical Violations</div>', unsafe_allow_html=True)
        if red_items:
            for key in red_items:
                label, formatter, unit = card_meta[key]
                val = formatter(kpis.get(key.lower().strip(), {}).get(selected_month))
                st.markdown(f'<div class="stat-mini"><span class="stat-label">{label}</span><span class="stat-value" style="color:var(--danger);">{val} {unit}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:12px; color:var(--text-lo);">Zero items in breach state</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_yellow:
        st.markdown('<div class="exec-card" style="border-top: 3px solid var(--warning);">', unsafe_allow_html=True)
        st.markdown('<div class="kpi-label" style="color:var(--warning); font-weight:700; margin-bottom:12px;">⚠️ Attention Required</div>', unsafe_allow_html=True)
        if yellow_items:
            for key in yellow_items:
                label, formatter, unit = card_meta[key]
                val = formatter(kpis.get(key.lower().strip(), {}).get(selected_month))
                st.markdown(f'<div class="stat-mini"><span class="stat-label">{label}</span><span class="stat-value" style="color:var(--warning);">{val} {unit}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:12px; color:var(--text-lo);">Zero tracking flags warning bounds</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_anomaly:
        st.markdown('<div class="exec-card" style="border-top: 3px solid var(--primary);">', unsafe_allow_html=True)
        st.markdown('<div class="kpi-label" style="color:var(--primary); font-weight:700; margin-bottom:12px;">📊 Structural Fluctuations</div>', unsafe_allow_html=True)
        if anomalies:
            for a in anomalies[:5]:
                raw_key = a["key"]
                label = card_meta.get(raw_key, (raw_key, str, ""))[0]
                arrow = "▲" if a["direction"] == "spike" else "▼"
                color = "var(--danger)" if a["direction"] == "spike" and "waste" in raw_key else "var(--primary)"
                st.markdown(f'<div class="stat-mini"><span class="stat-label">{label}</span><span class="stat-value" style="color:{color}; font-weight:700;">{arrow} {a["pct_change"]:+.1f}%</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:12px; color:var(--text-lo);">No extreme period swings detected</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

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
