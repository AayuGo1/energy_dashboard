"""
UI Design System Tokens & Plotly Layout Customization Helpers.
"""
import pandas as pd

PAL = {
    "bg": "#F4F5F7",
    "surface": "#FFFFFF",
    "surface-alt": "#EDF0F4",
    "border": "#E2E8F0",
    "text-hi": "#0F172A",
    "text-mid": "#475569",
    "text-lo": "#94A3B8",
    "primary": "#0052CC",
    "primary-2": "#091E42",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "shadow": "0 1px 3px 0 rgba(15, 23, 42, 0.03)",
    "shadow-hover": "0 12px 24px -4px rgba(15, 23, 42, 0.04)"
}

def is_missing(v) -> bool:
    if v is None: return True
    try:
        return bool(pd.isna(v))
    except (TypeError, ValueError):
        return False

def fmt_number(value) -> str:
    if value is None or pd.isna(value): return "N/A"
    try:
        v = float(value)
    except (ValueError, TypeError):
        return "N/A"
    if abs(v) >= 1_000_000: return f"{v/1_000_000:,.2f}M"
    if abs(v) >= 1_000: return f"{v:,.1f}"
    return f"{v:,.2f}" if v != int(v) else f"{int(v):,}"

def safe_icon_for(col_name: str) -> str:
    name = col_name.lower()
    if any(k in name for k in ["fatal", "injur", "accident", "safety", "incident"]): return "🦺"
    if any(k in name for k in ["energy", "power", "kwh", "diesel", "lpg", "electricity"]): return "⚡"
    if "water" in name: return "💧"
    if "waste" in name: return "♻️"
    if any(k in name for k in ["production", "volume", "output"]): return "🏭"
    return "📊"

def safe_icon_for_dynamic(metric_name: str) -> str:
    return safe_icon_for(metric_name)

def apply_enterprise_layout(fig, height=340, title=None, legend=True):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=PAL["text-mid"], size=12),
        title=dict(text=title, font=dict(size=14, color=PAL["text-hi"], weight=600), x=0.01, xanchor="left") if title else None,
        margin=dict(l=10, r=10, t=50 if title else 20, b=10),
        height=height, showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11, color=PAL["text-mid"]), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=PAL["surface"], font_size=12, font_family="Inter", bordercolor=PAL["border"]),
        colorway=[PAL["primary"], PAL["success"], PAL["warning"], PAL["primary-2"]],
    )
    fig.update_xaxes(showgrid=False, zeroline=False, color=PAL["text-mid"], linecolor=PAL["border"])
    fig.update_yaxes(showgrid=True, gridcolor=PAL["border"], zeroline=False, color=PAL["text-mid"])
    return fig
