"""
Enterprise KPI Analytics Dashboard — Single-file Streamlit application.
Loads data live from a GitHub RAW Excel file. No mock data, no hardcoded columns.
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

# =============================================================================
# CONFIG
# =============================================================================
GITHUB_RAW_URL = (
    "https://raw.githubusercontent.com/AayuGo1/energy_dashboard/main/"
    "Monthly%20KPI%20Summary%20Sheet_April_GNSC.xlsx"
)
COMPANY_NAME = "GNSC"
CACHE_TTL_SECONDS = 300

PAL = {
    "bg": "#F5F7FA", "surface": "#FFFFFF", "surface-alt": "#F0F2F6",
    "border": "#E5E7EB", "text-hi": "#1F2937", "text-mid": "#4B5563",
    "text-lo": "#9CA3AF", "primary": "#0B5FFF", "primary-2": "#003E8C",
    "success": "#16A34A", "warning": "#B98900",
    "shadow": "0 1px 3px rgba(16,24,40,0.06)",
    "shadow-hover": "0 8px 20px rgba(16,24,40,0.10)",
}

st.set_page_config(page_title=f"{COMPANY_NAME} | Executive KPI Dashboard",
                    page_icon="📊", layout="wide", initial_sidebar_state="expanded")


# =============================================================================
# STYLE
# =============================================================================
def inject_css():
    p = PAL
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
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

    .skel-card {{ height:158px; border-radius:12px; border:1px solid var(--border);
        background:linear-gradient(100deg, var(--surface-alt) 30%, var(--border) 50%, var(--surface-alt) 70%);
        background-size:300% 100%; animation:shimmer 1.4s ease-in-out infinite; }}
    @keyframes shimmer {{ 0%{{background-position:200% 0;}} 100%{{background-position:-200% 0;}} }}

    @media (max-width:640px) {{
        .app-header {{ flex-direction:column; align-items:flex-start; }}
        .kpi-card {{ height:auto; }}
    }}
    </style>
    """, unsafe_allow_html=True)


inject_css()
PLOTLY_BG = "rgba(0,0,0,0)"


# =============================================================================
# DATA LOADING
# =============================================================================
def get_remote_cache_key(url: str) -> str:
    """Cache-busting key from ETag/Last-Modified so a same-name file replaced
    on GitHub is picked up promptly rather than waiting out the full TTL."""
    try:
        resp = requests.head(url, timeout=10, allow_redirects=True)
        tag = resp.headers.get("ETag") or resp.headers.get("Last-Modified")
        if tag:
            return tag
    except requests.RequestException:
        pass
    return str(int(time.time() // CACHE_TTL_SECONDS))


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_workbook_bytes(url: str, cache_key: str) -> bytes:
    resp = requests.get(url, timeout=25)
    resp.raise_for_status()
    return resp.content


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_all_sheets(file_bytes: bytes) -> dict:
    """Reads every sheet into a dict of DataFrames. No schema assumptions."""
    sheets = pd.read_excel(BytesIO(file_bytes), sheet_name=None, engine="openpyxl")
    cleaned = {}
    for name, df in sheets.items():
        if df is None or df.empty:
            continue
        df = df.copy()
        df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")
        df.columns = [clean_column_name(c, i) for i, c in enumerate(df.columns)]
        df = df.reset_index(drop=True)
        if not df.empty:
            cleaned[name] = df
    return cleaned


def clean_column_name(col, idx: int) -> str:
    """Removes pandas' 'Unnamed: N' placeholders and blank headers,
    replacing them with a friendly, position-based fallback name."""
    if col is None:
        return f"KPI {idx + 1}"
    text = str(col).strip()
    if not text or text.lower().startswith("unnamed") or text.lower() in ("nan", "none"):
        return f"KPI {idx + 1}"
    return re.sub(r"\s+", " ", text)


# =============================================================================
# SCHEMA INFERENCE
# =============================================================================
def try_parse_dates(series: pd.Series):
    try:
        parsed = pd.to_datetime(series, errors="coerce")
        if parsed.notna().mean() >= 0.6:
            return parsed
    except Exception:
        pass
    return None


def infer_columns(df: pd.DataFrame):
    date_cols, numeric_cols, category_cols = [], [], []
    for col in df.columns:
        series = df[col]
        non_null = series.dropna()
        if non_null.empty:
            continue

        if pd.api.types.is_datetime64_any_dtype(series):
            date_cols.append(col)
            continue

        if pd.api.types.is_numeric_dtype(series):
            numeric_cols.append(col)
            continue

        name_hint = bool(re.search(r"date|month|period|year|week", str(col), re.IGNORECASE))
        parsed_dates = try_parse_dates(non_null)
        if parsed_dates is not None and (name_hint or parsed_dates.notna().mean() >= 0.85):
            date_cols.append(col)
            continue

        try:
            coerced = pd.to_numeric(non_null.astype(str).str.replace(",", "", regex=False), errors="coerce")
        except Exception:
            coerced = pd.Series(dtype=float)
        if coerced.notna().mean() >= 0.85:
            numeric_cols.append(col)
            continue

        try:
            n_unique = non_null.nunique()
        except Exception:
            n_unique = 0
        if 1 < n_unique <= max(50, int(len(df) * 0.5)):
            category_cols.append(col)

    # Safe fallback: if nothing was classified as numeric, try harder on the
    # remaining object columns rather than leaving KPI sections empty.
    if not numeric_cols:
        for col in df.columns:
            if col in date_cols or col in category_cols:
                continue
            try:
                coerced = pd.to_numeric(df[col].astype(str).str.replace(",", "", regex=False), errors="coerce")
                if coerced.notna().sum() >= max(2, int(len(df) * 0.3)):
                    numeric_cols.append(col)
            except Exception:
                continue

    return date_cols, numeric_cols, category_cols


def coerce_numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return series
    try:
        return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")
    except Exception:
        return pd.Series([np.nan] * len(series), index=series.index)


def coerce_date(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    try:
        return pd.to_datetime(series, errors="coerce")
    except Exception:
        return pd.Series([pd.NaT] * len(series), index=series.index)


# =============================================================================
# FORMATTING HELPERS
# =============================================================================
def is_missing(v) -> bool:
    if v is None:
        return True
    try:
        return bool(pd.isna(v))
    except (TypeError, ValueError):
        return False


def fmt_number(value) -> str:
    if is_missing(value):
        return "N/A"
    try:
        v = float(value)
    except (ValueError, TypeError):
        return "N/A"
    if abs(v) >= 1_000_000:
        return f"{v/1_000_000:,.2f}M"
    if abs(v) >= 1_000:
        return f"{v:,.0f}"
    if v == int(v):
        return f"{int(v):,}"
    return f"{v:,.2f}"


def classify_change(pct_change: float) -> str:
    """Converts a raw % change into a bounded, human-readable label instead
    of showing unrealistic swings (e.g. +4500%) as a number."""
    a = abs(pct_change)
    if a < 2:
        return "Stable"
    if a < 15:
        return "Moderate Growth" if pct_change > 0 else "Moderate Decline"
    if a < 60:
        return "Strong Growth" if pct_change > 0 else "Strong Decline"
    return "High Growth" if pct_change > 0 else "Sharp Decline"


def safe_icon_for(col_name: str) -> str:
    name = col_name.lower()
    if any(k in name for k in ["fatal", "injur", "accident", "safety", "incident"]):
        return "⚠️"
    if any(k in name for k in ["energy", "power", "kwh"]):
        return "⚡"
    if "water" in name:
        return "💧"
    if "waste" in name:
        return "🗑️"
    if any(k in name for k in ["production", "volume", "output"]):
        return "🏭"
    if any(k in name for k in ["revenue", "sales", "cost", "price", "profit"]):
        return "💰"
    if any(k in name for k in ["%", "percent", "pct", "rate"]):
        return "📊"
    return "📈"


def apply_enterprise_layout(fig, height=320, title=None, legend=True):
    fig.update_layout(
        paper_bgcolor=PLOTLY_BG, plot_bgcolor=PLOTLY_BG,
        font=dict(family="Inter, sans-serif", color=PAL["text-mid"], size=12),
        title=dict(text=title, font=dict(size=13.5, color=PAL["text-hi"], family="Inter"),
                    x=0.01, xanchor="left") if title else None,
        margin=dict(l=10, r=14, t=44 if title else 16, b=10),
        height=height, showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1,
                    font=dict(size=10.5, color=PAL["text-mid"]), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=PAL["surface"], font_size=12, font_family="Inter", bordercolor=PAL["border"]),
        colorway=[PAL["primary"], PAL["primary-2"], PAL["text-lo"], PAL["text-mid"]],
    )
    fig.update_xaxes(showgrid=False, zeroline=False, color=PAL["text-mid"], linecolor=PAL["border"])
    fig.update_yaxes(showgrid=True, gridcolor=PAL["border"], zeroline=False, color=PAL["text-mid"])
    return fig


# =============================================================================
# SIDEBAR
# =============================================================================
def render_sidebar():
    with st.sidebar:
        st.markdown(f"""
            <div class="sb-brand">
                <div class="sb-logo-chip">{COMPANY_NAME[:3].upper()}</div>
                <div>
                    <div class="sb-brand-name">{COMPANY_NAME} Analytics</div>
                    <div class="sb-brand-sub">Executive KPI Console</div>
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


def render_status(placeholder, connected: bool, last_refresh: str, note: str = ""):
    with placeholder.container():
        if connected:
            st.markdown(f"""
                <div class="status-card">
                    <div class="status-row"><span class="status-dot"></span>Live · Connected</div>
                    <div class="status-sub">Last refreshed: {last_refresh}</div>
                    <div class="status-sub">Auto-syncs every {CACHE_TTL_SECONDS // 60} min</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="status-card" style="border-left:3px solid var(--warning);">
                    <div class="status-row" style="color:var(--warning) !important;">
                        <span class="status-dot" style="background:var(--warning);"></span>Connection Issue
                    </div>
                    <div class="status-sub">{note}</div>
                </div>
            """, unsafe_allow_html=True)


# =============================================================================
# KPI CARD RENDERING
# =============================================================================
def render_kpi_card(col_name, value, prev_value, icon):
    display_val = fmt_number(value)
    pill_class, arrow, delta_str = "flat", "▬", "No prior period"

    if not is_missing(value) and not is_missing(prev_value):
        try:
            v, p = float(value), float(prev_value)
            diff = v - p
            if abs(diff) < 1e-9:
                pill_class, arrow, delta_str = "flat", "▬", "No change"
            elif abs(p) > 1e-9:
                pct = (diff / abs(p)) * 100
                label = classify_change(pct)
                arrow = "▲" if diff > 0 else "▼"
                pill_class = "good" if diff > 0 else "bad"
                delta_str = label
            else:
                arrow = "▲" if diff > 0 else "▼"
                pill_class = "good" if diff > 0 else "bad"
                delta_str = "New activity"
        except (ValueError, TypeError, ZeroDivisionError):
            pass

    st.markdown(f"""
    <div class="kpi-card">
        <div>
            <div class="kpi-top-row">
                <div class="kpi-icon-badge">{icon}</div>
                <div class="kpi-trend-pill {pill_class}">{arrow} {delta_str}</div>
            </div>
            <div class="kpi-value">{display_val}</div>
            <div class="kpi-label">{col_name}</div>
        </div>
        <div class="kpi-compare">vs previous period: {fmt_number(prev_value)}</div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# DASHBOARD SECTIONS
# =============================================================================
def render_executive_summary(df, numeric_cols, date_col):
    st.markdown('<div class="section-label">Executive Summary</div>', unsafe_allow_html=True)
    if not numeric_cols:
        st.info("No numeric KPI columns were detected to summarize.")
        return

    work = df.copy()
    if date_col and date_col in work.columns:
        work = work.sort_values(date_col)

    # Hard cap: max 4 KPI cards in the Executive Summary section.
    top_cols = numeric_cols[:4]
    cols = st.columns(len(top_cols))
    for col, name in zip(cols, top_cols):
        series = coerce_numeric(work[name]).dropna()
        current_val = series.iloc[-1] if len(series) >= 1 else None
        prev_val = series.iloc[-2] if len(series) >= 2 else None
        with col:
            render_kpi_card(name, current_val, prev_val, safe_icon_for(name))


def render_kpi_grid(df, numeric_cols, date_col, columns_per_row=4):
    st.markdown('<div class="section-label">All KPI Metrics</div>', unsafe_allow_html=True)
    if not numeric_cols:
        st.info("No numeric KPI columns were detected in the selected sheet.")
        return

    work = df.copy()
    if date_col and date_col in work.columns:
        work = work.sort_values(date_col)

    for i in range(0, len(numeric_cols), columns_per_row):
        row_cols = numeric_cols[i:i + columns_per_row]
        cols = st.columns(len(row_cols))
        for col, name in zip(cols, row_cols):
            series = coerce_numeric(work[name]).dropna()
            current_val = series.iloc[-1] if len(series) >= 1 else None
            prev_val = series.iloc[-2] if len(series) >= 2 else None
            with col:
                render_kpi_card(name, current_val, prev_val, safe_icon_for(name))


def render_trend_charts(df, numeric_cols, date_col):
    st.markdown('<div class="section-label">Trends</div>', unsafe_allow_html=True)

    if not date_col:
        st.info("No date/period column was detected — trend charts require a time axis.")
        return
    if not numeric_cols:
        st.info("No numeric KPI columns were detected to plot.")
        return

    work = df[[date_col] + numeric_cols].copy()
    work[date_col] = coerce_date(work[date_col])
    work = work.dropna(subset=[date_col]).sort_values(date_col)
    if work.empty:
        st.info("Date column could not be parsed into valid dates.")
        return

    chart_cols = numeric_cols[:6]
    n_per_row = 2
    for i in range(0, len(chart_cols), n_per_row):
        row_metrics = chart_cols[i:i + n_per_row]
        cols = st.columns(len(row_metrics))
        for col, metric in zip(cols, row_metrics):
            y = coerce_numeric(work[metric])
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=work[date_col], y=y, mode="lines+markers", fill="tozeroy",
                line=dict(color=PAL["primary"], width=2.4, shape="spline"),
                fillcolor=PAL["primary"] + "1A",
                marker=dict(size=6, line=dict(width=1, color=PAL["surface"])),
                connectgaps=True, name=metric,
            ))
            apply_enterprise_layout(fig, height=280, title=metric, legend=False)
            with col:
                st.markdown('<div class="exec-card">', unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                st.markdown("</div>", unsafe_allow_html=True)


def render_breakdown_analytics(df, numeric_cols, category_cols):
    st.markdown('<div class="section-label">Breakdown Analytics</div>', unsafe_allow_html=True)

    if not category_cols or not numeric_cols:
        st.info("No categorical columns were detected for breakdown analysis.")
        return

    c1, c2 = st.columns(2)
    with c1:
        cat_col = st.selectbox("Group by", options=category_cols, key="breakdown_cat")
    with c2:
        metric_col = st.selectbox("Metric", options=numeric_cols, key="breakdown_metric")

    grouped = (
        df[[cat_col, metric_col]]
        .assign(**{metric_col: coerce_numeric(df[metric_col])})
        .dropna()
        .groupby(cat_col, as_index=False)[metric_col]
        .sum()
        .sort_values(metric_col, ascending=False)
    )
    if grouped.empty:
        st.info("No usable data to break down for this selection.")
        return

    fig = go.Figure(go.Bar(
        x=grouped[cat_col], y=grouped[metric_col],
        marker_color=PAL["primary"], marker_line_width=0,
    ))
    apply_enterprise_layout(fig, height=340, title=f"{metric_col} by {cat_col}", legend=False)
    st.markdown('<div class="exec-card">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


def render_data_table(df):
    with st.expander("📄 View Raw Data Table", expanded=False):
        st.dataframe(df, use_container_width=True, height=420)


# =============================================================================
# MAIN
# =============================================================================
def main():
    status_placeholder = render_sidebar()

    skeleton_placeholder = st.empty()
    with skeleton_placeholder.container():
        st.markdown('<div class="section-label">Executive Summary</div>', unsafe_allow_html=True)
        cols = st.columns(4)
        for c in cols:
            with c:
                st.markdown('<div class="skel-card"></div>', unsafe_allow_html=True)

    sheets, load_error = None, None
    last_refresh_str = "—"
    with st.spinner("⏳ Fetching latest KPI data..."):
        try:
            cache_key = get_remote_cache_key(GITHUB_RAW_URL)
            wb_bytes = fetch_workbook_bytes(GITHUB_RAW_URL, cache_key)
            sheets = load_all_sheets(wb_bytes)
            last_refresh_str = datetime.now().strftime("%d %b %Y, %H:%M:%S")
            if not sheets:
                load_error = "The workbook was read successfully but contains no usable data."
        except requests.RequestException as e:
            load_error = f"Could not reach the configured data source. Details: {e}"
        except Exception as e:
            load_error = f"Unexpected error while loading the workbook: {e}"

    skeleton_placeholder.empty()
    render_status(status_placeholder, connected=(load_error is None),
                   last_refresh=last_refresh_str, note=load_error or "")

    if load_error:
        st.error(f"⚠️ {load_error}")
        st.info("The dashboard could not load the latest data. Please check back shortly, "
                "or contact your administrator if the issue persists.")
        st.stop()

    # ---- Sheet selection ------------------------------------------------
    with st.sidebar:
        sheet_names = list(sheets.keys())
        selected_sheet = st.selectbox("Sheet", options=sheet_names, index=0)

    df_raw = sheets.get(selected_sheet)
    if df_raw is None or df_raw.empty:
        st.warning("The selected sheet has no data available.")
        st.stop()

    date_cols, numeric_cols, category_cols = infer_columns(df_raw)
    primary_date_col = date_cols[0] if date_cols else None
    df = df_raw.copy()

    # ---- Sidebar filters --------------------------------------------------
    with st.sidebar:
        if primary_date_col:
            parsed_dates = coerce_date(df[primary_date_col])
            valid_dates = parsed_dates.dropna()
            if not valid_dates.empty:
                min_d, max_d = valid_dates.min().date(), valid_dates.max().date()
                if min_d == max_d:
                    st.caption(f"Date: {min_d}")
                else:
                    date_range = st.date_input("Date Range", value=(min_d, max_d),
                                                min_value=min_d, max_value=max_d)
                    if isinstance(date_range, tuple) and len(date_range) == 2:
                        start_d, end_d = date_range
                        mask = parsed_dates.between(pd.Timestamp(start_d), pd.Timestamp(end_d))
                        df = df[mask.fillna(False)]

        active_category_filters = {}
        for cat_col in category_cols[:3]:
            try:
                options = sorted([v for v in df_raw[cat_col].dropna().unique().tolist()])
            except TypeError:
                options = [v for v in df_raw[cat_col].dropna().unique().tolist()]
            if options:
                selected_vals = st.multiselect(cat_col, options=options, default=options)
                active_category_filters[cat_col] = selected_vals

    for cat_col, vals in active_category_filters.items():
        if vals:
            df = df[df[cat_col].isin(vals)]

    if df.empty:
        st.warning("No rows match the current filters. Try widening your selection.")
        st.stop()

    # ---- Header -------------------------------------------------------------
    current_date_str = datetime.now().strftime("%A, %d %B %Y")
    st.markdown(f"""
        <div class="app-header">
            <div class="app-header-left">
                <div class="app-header-icon">📊</div>
                <div>
                    <h1>{COMPANY_NAME} Executive KPI Dashboard</h1>
                    <p>Performance Overview — Sheet: {selected_sheet}</p>
                </div>
            </div>
            <div class="header-badge-row">
                <div class="header-badge">📅 {current_date_str}</div>
                <div class="header-badge">{len(df)} row(s)</div>
                <div class="header-badge live">🟢 Live</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ---- Sections -------------------------------------------------------
    render_executive_summary(df, numeric_cols, primary_date_col)
    render_trend_charts(df, numeric_cols, primary_date_col)
    render_breakdown_analytics(df, numeric_cols, category_cols)

    st.markdown('<div class="section-label">Detailed KPI Metrics</div>', unsafe_allow_html=True)
    render_kpi_grid(df, numeric_cols, primary_date_col)

    render_data_table(df)

    st.caption(
        f"Sheet '{selected_sheet}' · Detected {len(date_cols)} date column(s), "
        f"{len(numeric_cols)} numeric column(s), {len(category_cols)} category column(s). "
        f"Data auto-refreshes every {CACHE_TTL_SECONDS // 60} minutes, or instantly via Refresh Data."
    )


if __name__ == "__main__":
    main()
