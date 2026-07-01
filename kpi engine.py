"""
Phase 4 — KPI Engine: caching, thresholds, anomaly detection, Risk Panel
==========================================================================
This module adds derived-computation caching and alerting ON TOP OF the
existing Phase 1-3 KPI math in app.py (compute_hse_score, compute_trend,
CARD_DEFS, etc.) — it does not reimplement or duplicate that logic.

- `compute_kpi_derivatives()` bundles HSE score + anomaly scan behind a
  SEPARATE st.cache_data layer from the raw-file cache, keyed off a stable
  hash of the parsed `kpis` dict, so re-running the app (widget clicks,
  theme toggle, etc.) does not recompute the score/anomaly scan unless the
  underlying data or selected month actually changed.
- `get_kpi_status()` classifies a KPI value into red/yellow/green using
  `config.KPI_THRESHOLDS` (metadata-driven, no per-KPI hardcoded ifs).
- `detect_anomalies()` flags KPIs with an abnormal month-over-month swing.
- `render_risk_panel()` / `render_audit_log()` are new UI sections that
  reuse the dashboard's EXISTING CSS classes (`.exec-card`, `.stat-mini`,
  `.kpi-status`, CSS variables like `var(--danger)`) so they inherit the
  current design language automatically — no new styling is introduced.
"""

import json
import hashlib

import streamlit as st

import config


# =============================================================================
# Stable cache key for the parsed KPI dict
# =============================================================================
def _stable_kpi_hash(kpis: dict) -> str:
    """Builds a stable hash from the kpis dict so downstream derived
    computations can be cached independently of the raw-file cache."""
    try:
        payload = json.dumps(kpis, sort_keys=True, default=str)
    except TypeError:
        payload = str(kpis)
    return hashlib.md5(payload.encode()).hexdigest()


# =============================================================================
# Threshold-based status classification (Phase 4 §4)
# =============================================================================
def get_kpi_status(key: str, value) -> str:
    """Returns 'red' | 'yellow' | 'green' | 'na', driven entirely by
    config.KPI_THRESHOLDS metadata (no hardcoded per-KPI logic)."""
    if value is None:
        return "na"
    cfg = config.KPI_THRESHOLDS.get(key)
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
        if red is not None and v < red:
            return "red"
        if yellow is not None and v < yellow:
            return "yellow"
        return "green"
    else:  # lower_better
        if red is not None and v >= red:
            return "red"
        if yellow is not None and v >= yellow:
            return "yellow"
        return "green"


# =============================================================================
# Anomaly detection (Phase 4 §4)
# =============================================================================
def detect_anomalies(kpis: dict, months_upto: list, selected_month: str) -> list:
    """Flags KPIs whose month-over-month % change exceeds
    config.ANOMALY_PCT_THRESHOLD -- surfaced automatically in the Risk Panel."""
    if len(months_upto) < 2:
        return []
    prev_month = months_upto[-2]
    anomalies = []
    for key, series in kpis.items():
        cur, prev = series.get(selected_month), series.get(prev_month)
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


# =============================================================================
# Cached derived-computation bundle (Phase 4 §3 — perf optimization)
# =============================================================================
@st.cache_data(ttl=config.KPI_CACHE_TTL_SECONDS, show_spinner=False)
def compute_kpi_derivatives(kpi_hash: str, _kpis: dict, _hse_score_fn, months_upto: tuple, selected_month: str):
    """
    Cached bundle of HSE score + anomaly scan. This is a SEPARATE cache
    layer from the raw-file cache (`fetch_workbook_bytes`) and from the
    parsed-workbook cache (`parse_workbook`) — it only recomputes when the
    kpi_hash (i.e. the actual parsed data) or the selected month changes,
    not on every Streamlit rerun triggered by unrelated widget interaction.

    `_hse_score_fn` is passed in as app.py's EXISTING `compute_hse_score`
    (leading underscore tells st.cache_data to skip hashing the callable)
    so the HSE scoring math is not duplicated here.
    """
    months_list = list(months_upto)
    hse_score = _hse_score_fn(_kpis, months_list, selected_month)
    anomalies = detect_anomalies(_kpis, months_list, selected_month)
    return {"hse_score": hse_score, "anomalies": anomalies}


# =============================================================================
# Risk Panel UI (Phase 4 §4) — reuses existing CSS classes only
# =============================================================================
def render_risk_panel(kpis: dict, selected_month: str, prev_month, months_upto: list,
                       card_meta: dict, derivatives: dict):
    """
    card_meta: dict[key] -> (label, formatter, unit), built from app.py's
    EXISTING CARD_DEFS list so labels/formatting stay perfectly in sync
    with the KPI cards (single source of truth, no duplicated metadata).
    """
    st.markdown('<div class="section-label">Risk Panel · Auto-Detected Alerts</div>', unsafe_allow_html=True)

    statuses = {key: get_kpi_status(key, kpis.get(key, {}).get(selected_month)) for key in card_meta}
    red_items = [k for k, s in statuses.items() if s == "red"]
    yellow_items = [k for k, s in statuses.items() if s == "yellow"]
    anomalies = derivatives.get("anomalies", [])

    if not red_items and not yellow_items and not anomalies:
        st.markdown(
            '<div class="exec-card" style="border-left:4px solid var(--success);">'
            '<span class="kpi-status ok">All Clear</span>&nbsp; No KPI is currently in a red/yellow '
            'threshold band and no month-over-month anomalies were detected.</div>',
            unsafe_allow_html=True,
        )
        return

    col_red, col_yellow, col_anomaly = st.columns(3)

    with col_red:
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        st.markdown('<div class="kpi-label" style="margin-bottom:8px;">🔴 Red Zone KPIs</div>', unsafe_allow_html=True)
        if red_items:
            for key in red_items:
                label, formatter, unit = card_meta[key]
                val = formatter(kpis.get(key, {}).get(selected_month))
                st.markdown(
                    f'<div class="stat-mini"><span class="stat-label">{label}</span>'
                    f'<span class="stat-value" style="color:var(--danger);">{val} {unit}</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div class="kpi-compare">None</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_yellow:
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        st.markdown('<div class="kpi-label" style="margin-bottom:8px;">🟡 Watch List KPIs</div>', unsafe_allow_html=True)
        if yellow_items:
            for key in yellow_items:
                label, formatter, unit = card_meta[key]
                val = formatter(kpis.get(key, {}).get(selected_month))
                st.markdown(
                    f'<div class="stat-mini"><span class="stat-label">{label}</span>'
                    f'<span class="stat-value" style="color:var(--warning);">{val} {unit}</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div class="kpi-compare">None</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_anomaly:
        st.markdown('<div class="exec-card">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="kpi-label" style="margin-bottom:8px;">📈 Anomalies (MoM swing ≥ {config.ANOMALY_PCT_THRESHOLD:.0f}%)</div>',
            unsafe_allow_html=True,
        )
        if anomalies:
            for a in anomalies[:6]:
                label = card_meta.get(a["key"], (a["key"], str, ""))[0]
                arrow = "▲" if a["direction"] == "spike" else "▼"
                color = "var(--danger)" if a["direction"] == "spike" else "var(--warning)"
                st.markdown(
                    f'<div class="stat-mini"><span class="stat-label">{label}</span>'
                    f'<span class="stat-value" style="color:{color};">{arrow} {a["pct_change"]:+.1f}%</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div class="kpi-compare">None</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# Audit Log UI (Phase 4 §5) — reuses existing CSS classes only
# =============================================================================
def render_audit_log(fetch_meta: dict, selected_fy: str, selected_month: str):
    st.markdown('<div class="section-label">Audit Log</div>', unsafe_allow_html=True)
    st.markdown('<div class="exec-card">', unsafe_allow_html=True)

    source_badge = "🟢 Live GitHub Fetch" if fetch_meta.get("source") == "live" else "🟠 Fallback Snapshot"
    st.markdown(
        f'<div class="stat-mini"><span class="stat-label">Data Source</span>'
        f'<span class="stat-value">{source_badge}</span></div>', unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="stat-mini"><span class="stat-label">Last Refresh</span>'
        f'<span class="stat-value">{fetch_meta.get("fetched_at", "N/A")}</span></div>', unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="stat-mini"><span class="stat-label">Reporting Period</span>'
        f'<span class="stat-value">FY {selected_fy} · {selected_month}</span></div>', unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="stat-mini"><span class="stat-label">Source File</span>'
        f'<span class="stat-value" style="font-size:11px; word-break:break-all;">{fetch_meta.get("source_url", "N/A")}</span></div>',
        unsafe_allow_html=True,
    )
    if fetch_meta.get("warning"):
        st.markdown(
            f'<div class="stat-mini" style="border-left:3px solid var(--warning);">'
            f'<span class="stat-label">Warning</span>'
            f'<span class="stat-value" style="color:var(--warning); font-size:12px;">{fetch_meta["warning"]}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
