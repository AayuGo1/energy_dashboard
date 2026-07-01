"""
Monthly KPI Dashboard — Jubilant FoodWorks style Enterprise Edition
=====================================================================
Single-file Streamlit application.

- Loads an Excel workbook directly from a GitHub RAW URL (no DB, no mock data).
- Auto-detects date columns, numeric (KPI) columns, and category-type columns.
- Dynamically builds KPI cards, trend charts, and category breakdowns based on
  whatever structure the workbook actually has — no fixed schema assumptions.
- Automatically re-reads the file so that when it's replaced on GitHub with the
  same filename, the dashboard picks up the new content (short cache TTL +
  ETag/Last-Modified based cache-busting + manual "Refresh Data" button).
- Handles missing/partial data gracefully; never crashes on missing columns.

Deployment requirements (requirements.txt alongside this file):
    streamlit
    pandas
    openpyxl
    requests
    plotly

Run:  streamlit run app.py
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
# 1. CONFIGURATION
# =============================================================================
GITHUB_RAW_URL_DEFAULT = (
    "https://raw.githubusercontent.com/AayuGo1/energy_dashboard/main/"
    "Monthly%20KPI%20Summary%20Sheet_April_GNSC.xlsx"
)
COMPANY_NAME = "GNSC"
PARENT_BRAND = "Jubilant FoodWorks"
CACHE_TTL_SECONDS = 300  # data auto-revalidates every 5 minutes

PALETTE = {
    "bg": "#F5F7FA",
    "surface": "#FFFFFF",
    "surface-alt": "#F0F2F6",
    "border": "#E5E7EB",
    "text-hi": "#1F2937",
    "text-mid": "#4B5563",
    "text-lo": "#9CA3AF",
    "primary": "#003E7E",
    "primary-2": "#0A5AA8",
    "accent": "#D71920",
    "success": "#16A34A",
    "warning": "#F59E0B",
    "danger": "#DC2626",
    "shadow": "0 1px 2px rgba(16,24,40,0.04), 0 1px 3px rgba(16,24,40,0.06)",
    "shadow-hover": "0 8px 20px rgba(16,24,40,0.10)",
}

st.set_page_config(
    page_title=f"{COMPANY_NAME} | Monthly KPI Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# 2. THEME / CSS
# =============================================================================
def inject_css():
    p = PALETTE
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {{
            --bg:{p['bg']}; --surface:{p['surface']}; --surface-alt:{p['surface-alt']};
            --border:{p['border']}; --text-hi:{p['text-hi']}; --text-mid:{p['text-mid']};
            --text-lo:{p['text-lo']}; --primary:{p['primary']}; --primary-2:{p['primary-2']};
            --accent:{p['accent']}; --success:{p['success']}; --warning:{p['warning']};
            --danger:{p['danger']}; --shadow:{p['shadow']}; --shadow-hover:{p['shadow-hover']};
        }}

        html, body, [class*="css"] {{ font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif; }}
        #MainMenu {{visibility:hidden;}}
        footer {{visibility:hidden;}}
        header[data-testid="stHeader"] {{background:transparent;}}
        .stApp {{ background:var(--bg); color:var(--text-hi); }}

        .main .block-container {{ animation: fadeIn .45s ease both; padding-top:1.1rem; }}
        @keyframes fadeIn {{ from{{opacity:0; transform:translateY(6px);}} to{{opacity:1; transform:translateY(0);}} }}

        section[data-testid="stSidebar"] {{ background:var(--surface); border-right:1px solid var(--border); }}
        section[data-testid="stSidebar"] * {{ color:var(--text-mid) !important; }}

        .sb-brand {{ display:flex; align-items:center; gap:10px; padding:6px 2px 16px 2px;
            border-bottom:1px solid var(--border); margin-bottom:14px; }}
        .sb-logo-chip {{ width:38px; height:38px; border-radius:10px; flex-shrink:0;
            background:linear-gradient(135deg, var(--primary), var(--primary-2));
            display:flex; align-items:center; justify-content:center; color:#fff !important;
            font-weight:800; font-size:14px; }}
        .sb-brand-name {{ font-size:15px; font-weight:800; color:var(--text-hi) !important; line-height:1.15; }}
        .sb-brand-sub {{ font-size:10.5px; color:var(--text-lo) !important; letter-spacing:.5px;
            text-transform:uppercase; font-weight:700; }}
        .sb-section-title {{ font-size:10.5px; text-transform:uppercase; letter-spacing:1.2px;
            color:var(--text-lo) !important; font-weight:800; margin:18px 0 8px 2px; }}
        .sb-footnote {{ font-size:11px; line-height:1.5; color:var(--text-lo) !important;
            background:var(--surface-alt); border:1px solid var(--border); border-radius:8px;
            padding:9px 11px; margin-top:4px; }}

        div.stButton > button {{ background:var(--primary); color:#fff !important; border:none;
            border-radius:8px; padding:9px 12px; font-weight:700; width:100%; box-shadow:var(--shadow);
            transition:background .15s ease, transform .15s ease; }}
        div.stButton > button:hover {{ background:var(--primary-2); transform:translateY(-1px); }}

        .app-header {{ display:flex; align-items:center; justify-content:space-between; gap:16px;
            padding:18px 24px; margin-bottom:18px; background:var(--surface); border-radius:14px;
            border:1px solid var(--border); box-shadow:var(--shadow); flex-wrap:wrap; }}
        .app-header-left {{ display:flex; align-items:center; gap:14px; }}
        .app-header-icon {{ width:46px; height:46px; border-radius:12px; display:flex; align-items:center;
            justify-content:center; background:linear-gradient(135deg, var(--primary), var(--primary-2));
            color:#fff; font-size:20px; flex-shrink:0; }}
        .app-header h1 {{ margin:0; font-size:22px; font-weight:800; color:var(--text-hi); letter-spacing:-.2px; }}
        .app-header p {{ margin:2px 0 0 0; font-size:12.5px; color:var(--text-mid); font-weight:500; }}
        .app-header-right {{ display:flex; flex-direction:column; align-items:flex-end; gap:7px; }}
        .header-badge-row {{ display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }}
        .header-badge {{ background:var(--surface-alt); border:1px solid var(--border); color:var(--text-mid);
            padding:5px 12px; border-radius:20px; font-size:11.5px; font-weight:700; white-space:nowrap; }}
        .header-badge.live {{ background:rgba(22,163,74,0.10); border-color:rgba(22,163,74,0.35); color:var(--success); }}
        .header-badge.live .dot {{ display:inline-block; width:6px; height:6px; border-radius:50%;
            background:var(--success); margin-right:6px; animation:pulseDot 1.8s infinite; }}
        @keyframes pulseDot {{ 0%{{box-shadow:0 0 0 0 rgba(22,163,74,.55);}} 70%{{box-shadow:0 0 0 6px rgba(22,163,74,0);}}
            100%{{box-shadow:0 0 0 0 rgba(22,163,74,0);}} }}
        .header-meta {{ font-size:10.5px; color:var(--text-lo); font-weight:600; }}

        .section-label {{ font-size:12px; text-transform:uppercase; letter-spacing:1.2px; color:var(--primary);
            font-weight:800; margin:22px 0 12px 2px; display:flex; align-items:center; gap:10px; }}
        .section-label::after {{ content:""; flex:1; height:1px; background:var(--border); }}

        .kpi-card {{ background:var(--surface); border:1px solid var(--border); border-radius:12px;
            padding:16px 16px 14px 16px; box-shadow:var(--shadow); height:170px;
            display:flex; flex-direction:column; justify-content:space-between;
            border-top:3px solid var(--card-accent, var(--primary));
            transition:transform .18s ease, box-shadow .18s ease; animation:fadeIn .4s ease both; }}
        .kpi-card:hover {{ transform:translateY(-3px); box-shadow:var(--shadow-hover); }}
        .kpi-top-row {{ display:flex; align-items:flex-start; justify-content:space-between; }}
        .kpi-icon-badge {{ width:34px; height:34px; border-radius:9px; display:flex; align-items:center;
            justify-content:center; font-size:16px; background:var(--surface-alt); border:1px solid var(--border); }}
        .kpi-trend-pill {{ display:flex; align-items:center; gap:4px; font-size:11px; font-weight:800;
            padding:3px 9px; border-radius:20px; white-space:nowrap; }}
        .kpi-trend-pill.good {{ background:rgba(22,163,74,0.10); color:var(--success); border:1px solid rgba(22,163,74,0.3); }}
        .kpi-trend-pill.bad  {{ background:rgba(220,38,38,0.10); color:var(--danger); border:1px solid rgba(220,38,38,0.3); }}
        .kpi-trend-pill.flat {{ background:var(--surface-alt); color:var(--text-mid); border:1px solid var(--border); }}
        .kpi-value {{ font-size:26px; font-weight:800; color:var(--text-hi); line-height:1.1; font-variant-numeric:tabular-nums; }}
        .kpi-label {{ margin-top:3px; font-size:11.5px; font-weight:700; color:var(--text-mid);
            text-transform:uppercase; letter-spacing:.3px; }}
        .kpi-compare {{ margin-top:2px; font-size:10.5px; color:var(--text-lo); font-weight:600; }}

        .exec-card {{ background:var(--surface); border:1px solid var(--border); border-radius:12px;
            padding:16px 18px; box-shadow:var(--shadow); margin-bottom:18px;
            transition:box-shadow .18s ease; animation:fadeIn .45s ease both; }}
        .exec-card:hover {{ box-shadow:var(--shadow-hover); }}

        .stat-mini {{ display:flex; align-items:center; justify-content:space-between; gap:8px;
            padding:10px 12px; border-radius:8px; background:var(--surface-alt);
            border:1px solid var(--border); margin-bottom:7px; }}
        .stat-mini .stat-label {{ font-size:11.5px; font-weight:700; color:var(--text-mid); }}
        .stat-mini .stat-value {{ font-size:15px; font-weight:800; color:var(--text-hi); font-variant-numeric:tabular-nums; }}

        .skel-card {{ height:170px; border-radius:12px; border:1px solid var(--border);
            background:linear-gradient(100deg, var(--surface-alt) 30%, var(--border) 50%, var(--surface-alt) 70%);
            background-size:300% 100%; animation:shimmer 1.5s ease-in-out infinite; }}
        @keyframes shimmer {{ 0%{{background-position:200% 0;}} 100%{{background-position:-200% 0;}} }}

        @media (max-width:640px) {{
            .app-header {{ flex-direction:column; align-items:flex-start; }}
            .app-header-right {{ align-items:flex-start; }}
            .kpi-card {{ height:auto; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_css()
PAL = PALETTE
PLOTLY_BG = "rgba(0,0,0,0)"


# =============================================================================
# 3. DATA LOADING — GitHub RAW Excel, auto-refresh on replacement
# =============================================================================
def get_remote_cache_key(url: str) -> str:
    """Builds a cache-busting key from ETag/Last-Modified so that replacing
    the file on GitHub (same filename, new content) is picked up without
    waiting for the TTL to fully expire."""
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
    """Reads every sheet in the workbook into a dict of DataFrames.
    No assumptions about sheet names or schema."""
    sheets = pd.read_excel(BytesIO(file_bytes), sheet_name=None, engine="openpyxl")
    cleaned = {}
    for name, df in sheets.items():
        if df is None or df.empty:
            continue
        df = df.copy()
        # Drop fully-empty rows/columns, normalize column names to strings.
        df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")
        df.columns = [str(c).strip() for c in df.columns]
        df = df.reset_index(drop=True)
        if not df.empty:
            cleaned[name] = df
    return cleaned


# =============================================================================
# 4. SCHEMA INFERENCE — detect date / numeric(KPI) / category columns
# =============================================================================
def try_parse_dates(series: pd.Series) -> pd.Series:
    try:
        parsed = pd.to_datetime(series, errors="coerce", infer_datetime_format=True)
        valid_ratio = parsed.notna().mean()
        if valid_ratio >= 0.6:
            return parsed
    except Exception:
        pass
    return None


def infer_columns(df: pd.DataFrame):
    """Classifies each column as date / numeric / category, ignoring columns
    that are mostly empty or unusable."""
    date_cols, numeric_cols, category_cols = [], [], []

    for col in df.columns:
        series = df[col]
        non_null = series.dropna()
        if non_null.empty:
            continue

        # Already a proper datetime dtype
        if pd.api.types.is_datetime64_any_dtype(series):
            date_cols.append(col)
            continue

        # Numeric dtype
        if pd.api.types.is_numeric_dtype(series):
            numeric_cols.append(col)
            continue

        # Try string -> date (only if the column name hints at it or values parse well)
        name_hint = bool(re.search(r"date|month|period|year", str(col), re.IGNORECASE))
        parsed_dates = try_parse_dates(non_null)
        if parsed_dates is not None and (name_hint or parsed_dates.notna().mean() >= 0.85):
            date_cols.append(col)
            continue

        # Try string -> numeric (e.g. "12.5%" wouldn't convert cleanly; plain numbers as text would)
        coerced = pd.to_numeric(non_null.astype(str).str.replace(",", "", regex=False), errors="coerce")
        if coerced.notna().mean() >= 0.85:
            numeric_cols.append(col)
            continue

        # Otherwise treat as a category column if it has a reasonable number
        # of distinct values relative to row count (avoids free-text columns).
        n_unique = non_null.nunique()
        if 1 < n_unique <= max(50, int(len(df) * 0.5)):
            category_cols.append(col)

    return date_cols, numeric_cols, category_cols


def coerce_numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return series
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def coerce_date(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    return pd.to_datetime(series, errors="coerce", infer_datetime_format=True)


# =============================================================================
# 5. FORMATTING HELPERS
# =============================================================================
def is_missing(v):
    return v is None or (isinstance(v, float) and pd.isna(v)) or pd.isna(v) if not isinstance(v, (list, dict)) else False


def fmt_number(value):
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return "N/A"
        v = float(value)
        if abs(v) >= 1_000_000:
            return f"{v/1_000_000:,.2f}M"
        if abs(v) >= 1_000:
            return f"{v:,.0f}"
        if v == int(v):
            return f"{int(v):,}"
        return f"{v:,.2f}"
    except (ValueError, TypeError):
        return "N/A"


def safe_icon_for(col_name: str) -> str:
    name = col_name.lower()
    if any(k in name for k in ["fatal", "injur", "accident", "safety", "incident"]):
        return "⚠️"
    if any(k in name for k in ["energy", "power", "kwh"]):
        return "⚡"
    if any(k in name for k in ["water"]):
        return "💧"
    if any(k in name for k in ["waste"]):
        return "🗑️"
    if any(k in name for k in ["production", "volume", "output"]):
        return "🏭"
    if any(k in name for k in ["revenue", "sales", "cost", "price", "profit"]):
        return "💰"
    if any(k in name for k in ["%", "percent", "pct", "rate"]):
        return "📊"
    return "📈"


def accent_for_index(i: int) -> str:
    palette_cycle = [PAL["primary"], PAL["accent"], PAL["success"], PAL["warning"],
                      PAL["primary-2"], "#6D28D9", "#0369A1", "#0F766E"]
    return palette_cycle[i % len(palette_cycle)]


def apply_enterprise_layout(fig, height=340, title=None, legend=True):
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
    )
    fig.update_xaxes(showgrid=False, zeroline=False, color=PAL["text-mid"], linecolor=PAL["border"])
    fig.update_yaxes(showgrid=True, gridcolor=PAL["border"], zeroline=False, color=PAL["text-mid"])
    return fig


# =============================================================================
# 6. UI SECTIONS
# =============================================================================
def render_sidebar(default_url: str):
    with st.sidebar:
        st.markdown(
            f"""
            <div class="sb-brand">
                <div class="sb-logo-chip">JFL</div>
                <div>
                    <div class="sb-brand-name">{COMPANY_NAME} Analytics</div>
                    <div class="sb-brand-sub">{PARENT_BRAND} · KPI Console</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sb-section-title">🔗 &nbsp;Data Source</div>', unsafe_allow_html=True)
        source_url = st.text_input("GitHub RAW Excel URL", value=default_url, label_visibility="collapsed")

        if st.button("🔄  Refresh Data"):
            fetch_workbook_bytes.clear()
            load_all_sheets.clear()
            st.rerun()

        st.markdown('<div class="sb-section-title">🧭 &nbsp;Filters</div>', unsafe_allow_html=True)

    return source_url.strip()


def render_kpi_card(col_name, value, prev_value, icon, accent):
    display_val = fmt_number(value)

    pill_class, arrow, delta_str = "flat", "▬", "No prior period"
    if not is_missing(value) and not is_missing(prev_value):
        try:
            diff = float(value) - float(prev_value)
            if abs(diff) < 1e-9:
                pill_class, arrow, delta_str = "flat", "▬", "No change"
            else:
                arrow = "▲" if diff > 0 else "▼"
                pill_class = "good" if diff > 0 else "bad"
                delta_str = f"{(diff/abs(float(prev_value)))*100:+.1f}%" if abs(float(prev_value)) > 1e-9 else "N/A"
        except (ValueError, TypeError, ZeroDivisionError):
            pass

    card_html = f"""
    <div class="kpi-card" style="--card-accent:{accent};">
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
    """
    st.markdown(card_html, unsafe_allow_html=True)


def render_kpi_grid(df, numeric_cols, date_col, columns_per_row=4):
    st.markdown('<div class="section-label">Key Performance Indicators</div>', unsafe_allow_html=True)
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
                render_kpi_card(name, current_val, prev_val, safe_icon_for(name),
                                 accent_for_index(numeric_cols.index(name)))


def render_executive_summary(df, numeric_cols, date_col):
    st.markdown('<div class="section-label">Executive Summary</div>', unsafe_allow_html=True)
    if not numeric_cols:
        st.info("No numeric data available to summarize.")
        return

    work = df.copy()
    if date_col and date_col in work.columns:
        work = work.sort_values(date_col)

    top_cols = numeric_cols[:5]
    tiles = st.columns(len(top_cols)) if top_cols else []
    for i, (col, name) in enumerate(zip(tiles, top_cols)):
        series = coerce_numeric(work[name]).dropna()
        total = series.sum() if len(series) else None
        avg = series.mean() if len(series) else None
        with col:
            st.markdown(
                f"""
                <div class="exec-card" style="border-left:4px solid {accent_for_index(i)}; padding:14px 16px;">
                    <div class="kpi-label" style="margin-bottom:2px;">{name}</div>
                    <div class="kpi-value" style="font-size:22px;">{fmt_number(total)}</div>
                    <div class="kpi-compare">Average: {fmt_number(avg)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_trend_charts(df, numeric_cols, date_col):
    st.markdown('<div class="section-label">KPI Trends</div>', unsafe_allow_html=True)

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
            accent = accent_for_index(chart_cols.index(metric))
            fig.add_trace(go.Scatter(
                x=work[date_col], y=y, mode="lines+markers", fill="tozeroy",
                line=dict(color=accent, width=2.4, shape="spline"),
                fillcolor=accent + "22",
                marker=dict(size=6, line=dict(width=1, color=PAL["surface"])),
                connectgaps=True, name=metric,
            ))
            apply_enterprise_layout(fig, height=280, title=metric, legend=False)
            with col:
                st.markdown('<div class="exec-card">', unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                st.markdown("</div>", unsafe_allow_html=True)


def render_category_breakdown(df, numeric_cols, category_cols):
    if not category_cols or not numeric_cols:
        return
    st.markdown('<div class="section-label">Category / Region Breakdown</div>', unsafe_allow_html=True)

    cat_col = category_cols[0]
    metric_col = numeric_cols[0]

    grouped = (
        df[[cat_col, metric_col]]
        .assign(**{metric_col: coerce_numeric(df[metric_col])})
        .dropna()
        .groupby(cat_col, as_index=False)[metric_col]
        .sum()
        .sort_values(metric_col, ascending=False)
    )
    if grouped.empty:
        st.info("No usable category data to break down.")
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
# 7. MAIN APP FLOW
# =============================================================================
def main():
    source_url = render_sidebar(GITHUB_RAW_URL_DEFAULT)

    if not source_url:
        st.warning("Please provide a GitHub RAW Excel URL in the sidebar.")
        st.stop()

    skeleton_placeholder = st.empty()
    with skeleton_placeholder.container():
        st.markdown('<div class="section-label">Key Performance Indicators</div>', unsafe_allow_html=True)
        cols = st.columns(4)
        for c in cols:
            with c:
                st.markdown('<div class="skel-card"></div>', unsafe_allow_html=True)

    sheets, load_error = None, None
    with st.spinner("⏳ Fetching latest KPI data from GitHub..."):
        try:
            cache_key = get_remote_cache_key(source_url)
            wb_bytes = fetch_workbook_bytes(source_url, cache_key)
            sheets = load_all_sheets(wb_bytes)
            if not sheets:
                load_error = "The workbook was read successfully but contains no usable data."
        except requests.RequestException as e:
            load_error = f"Could not reach the GitHub RAW URL. Please check your network / URL. Details: {e}"
        except Exception as e:
            load_error = f"Unexpected error while loading the workbook: {e}"

    skeleton_placeholder.empty()

    if load_error:
        st.error(f"⚠️ {load_error}")
        st.info(
            "Verify the GitHub RAW URL points to a valid, publicly accessible "
            "Excel (.xlsx) file with at least one non-empty sheet."
        )
        st.stop()

    # ---- Sidebar: sheet selector + filters ---------------------------------
    with st.sidebar:
        sheet_names = list(sheets.keys())
        selected_sheet = st.selectbox("Sheet", options=sheet_names, index=0)

    df_raw = sheets[selected_sheet]
    date_cols, numeric_cols, category_cols = infer_columns(df_raw)
    primary_date_col = date_cols[0] if date_cols else None

    df = df_raw.copy()

    with st.sidebar:
        # Date range filter (only if a date column was detected)
        if primary_date_col:
            parsed_dates = coerce_date(df[primary_date_col])
            valid_dates = parsed_dates.dropna()
            if not valid_dates.empty:
                min_d, max_d = valid_dates.min().date(), valid_dates.max().date()
                date_range = st.date_input("Date Range", value=(min_d, max_d), min_value=min_d, max_value=max_d)
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    start_d, end_d = date_range
                    mask = parsed_dates.between(pd.Timestamp(start_d), pd.Timestamp(end_d))
                    df = df[mask.fillna(False)]

        # Category filters (auto-detected)
        active_category_filters = {}
        for cat_col in category_cols[:3]:
            options = sorted([v for v in df_raw[cat_col].dropna().unique().tolist()])
            if options:
                selected_vals = st.multiselect(cat_col, options=options, default=options)
                active_category_filters[cat_col] = selected_vals

        st.markdown('<div class="sb-section-title">🕒 &nbsp;Sync Status</div>', unsafe_allow_html=True)
        st.markdown(
            f"""<div class="sb-footnote"><b style="color:var(--text-hi) !important;">Last checked</b><br/>
            {datetime.now().strftime('%d %b %Y, %H:%M:%S')}<br/><br/>Auto-revalidates every
            {CACHE_TTL_SECONDS // 60} minutes, or instantly via the Refresh Data button.</div>""",
            unsafe_allow_html=True,
        )

    for cat_col, vals in active_category_filters.items():
        if vals:
            df = df[df[cat_col].isin(vals)]

    if df.empty:
        st.warning("No rows match the current filters. Try widening your selection.")
        st.stop()

    # ---- Header --------------------------------------------------------------
    current_date_str = datetime.now().strftime("%A, %d %B %Y")
    st.markdown(
        f"""
        <div class="app-header">
            <div class="app-header-left">
                <div class="app-header-icon">📊</div>
                <div>
                    <h1>{COMPANY_NAME} Monthly KPI Dashboard</h1>
                    <p>{PARENT_BRAND} · Performance Overview — Sheet: {selected_sheet}</p>
                </div>
            </div>
            <div class="app-header-right">
                <div class="header-badge-row">
                    <div class="header-badge">📅 {current_date_str}</div>
                    <div class="header-badge">{len(df)} row(s)</div>
                    <div class="header-badge live"><span class="dot"></span>Live</div>
                </div>
                <div class="header-meta">Auto-refresh every {CACHE_TTL_SECONDS // 60} min</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---- Sections -----------------------------------------------------------
    render_executive_summary(df, numeric_cols, primary_date_col)
    render_kpi_grid(df, numeric_cols, primary_date_col)
    render_trend_charts(df, numeric_cols, primary_date_col)
    render_category_breakdown(df, numeric_cols, category_cols)
    render_data_table(df)

    st.caption(
        f"Data source: GitHub RAW Excel workbook · Sheet '{selected_sheet}' · "
        f"Detected {len(date_cols)} date column(s), {len(numeric_cols)} numeric column(s), "
        f"{len(category_cols)} category column(s). Auto-refreshes every {CACHE_TTL_SECONDS // 60} "
        f"minutes, or instantly via the Refresh Data button."
    )


if __name__ == "__main__":
    main()
