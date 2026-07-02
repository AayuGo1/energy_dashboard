# helpers/formatting.py
"""
UI/UX Micro-Design Token System Mapped Over Microsoft Fabric & Apple Clean Guidelines.
"""
import pandas as pd

PAL = {
    "bg": "#F4F5F7",          # Crisp slate gray context background surface
    "surface": "#FFFFFF",     # Absolute white base paper container boundaries
    "surface-alt": "#EDF0F4", # Smooth background gray accents and dividers
    "border": "#E2E8F0",      # Delicate accent card borders
    "text-hi": "#0F172A",     # Deep charcoal high-readability typographic ink
    "text-mid": "#475569",    # Corporate secondary item text description
    "text-lo": "#94A3B8",     # Muted caption text tracking and stamps
    "primary": "#0052CC",     # Premium Professional Deep Cobalt Blue
    "primary-2": "#091E42",   # Midnight corporate branding color anchor
    "success": "#10B981",     # Pure Emerald green tracking compliance indices
    "warning": "#F59E0B",     # Warning Amber indicator parameters
    "danger": "#EF4444",      # High-Contrast operations hazard red accent
    "shadow": "0 1px 3px 0 rgba(15, 23, 42, 0.03), 0 1px 2px -1px rgba(15, 23, 42, 0.02)",
    "shadow-hover": "0 12px 24px -4px rgba(15, 23, 42, 0.04), 0 4px 12px -2px rgba(15, 23, 42, 0.02)"
}

def fmt_number(value) -> str:
    if value is None or pd.isna(value): return "N/A"
    try:
        v = float(value)
    except (ValueError, TypeError):
        return "N/A"
    if abs(v) >= 1_000_000: return f"{v/1_000_000:,.2f}M"
    if abs(v) >= 1_000: return f"{v:,.1f}"
    return f"{v:,.2f}" if v != int(v) else f"{int(v):,}"

def safe_icon_for_dynamic(metric_name: str) -> str:
    n = metric_name.lower()
    if any(k in n for k in ["fatal", "injury", "accident", "safety", "incident"]): return "🦺"
    if any(k in n for k in ["diesel", "lpg", "energy", "power", "kwh", "electricity"]): return "⚡"
    if "water" in n: return "💧"
    if "waste" in n: return "♻️"
    if "emission" in n or "air" in n: return "🌫️"
    if "production" in n or "volume" in n: return "🏭"
    return "📈"

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
