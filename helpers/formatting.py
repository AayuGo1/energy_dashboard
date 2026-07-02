# helpers/formatting.py
"""
UI Design System Tokens & Plotly Layout Customization Helpers.
Derived directly from Modern Enterprise Specifications (Microsoft Fabric/Apple/Linear style).
"""
import pandas as pd

PAL = {
    "bg": "#F9FAFB",          # Soft neutral canvas structure background
    "surface": "#FFFFFF",     # Clean stark paper/card boundaries
    "surface-alt": "#F3F4F6", # Unfinished block accents and separators
    "border": "#E5E7EB",      # Balanced, delicate borders
    "text-hi": "#111827",     # Dark high-readability typographic ink
    "text-mid": "#4B5563",    # Secondary reading content descriptions
    "text-lo": "#9CA3AF",     # Auxiliary markers and timestamps
    "primary": "#0052CC",     # Premium Professional Blue
    "primary-2": "#072A6C",   # Midnight Blue accent focus anchor
    "success": "#10B981",     # Pure Emerald safety compliance indicator
    "warning": "#F59E0B",     # Amber operational warning parameters
    "danger": "#EF4444",      # High-contrast Alert red indicators
    "shadow": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    "shadow-hover": "0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -4px rgba(0, 0, 0, 0.05)"
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
    if any(k in name for k in ["fatal", "injur", "accident", "safety", "incident"]): return "⚠️"
    if any(k in name for k in ["energy", "power", "kwh", "diesel", "lpg"]): return "⚡"
    if "water" in name: return "💧"
    if "waste" in name: return "🗑️"
    if any(k in name for k in ["production", "volume", "output"]): return "🏭"
    return "📊"

def apply_enterprise_layout(fig, height=320, title=None, legend=True):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=PAL["text-mid"], size=12),
        title=dict(text=title, font=dict(size=14, color=PAL["text-hi"], weight=600), x=0.01, xanchor="left") if title else None,
        margin=dict(l=10, r=10, t=50 if title else 20, b=10),
        height=height,
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11, color=PAL["text-mid"]), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=PAL["surface"], font_size=12, font_family="Inter", bordercolor=PAL["border"]),
        colorway=[PAL["primary"], PAL["success"], PAL["warning"], PAL["primary-2"]],
    )
    fig.update_xaxes(showgrid=False, zeroline=False, color=PAL["text-mid"], linecolor=PAL["border"])
    fig.update_yaxes(showgrid=True, gridcolor=PAL["border"], zeroline=False, color=PAL["text-mid"])
    return fig
