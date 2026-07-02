# charts/env_visuals.py
"""
Dynamic Plotly Engine Canvas Renderers — Specialized Layout Templates.
Handles responsive structural components without hardcoded series indices.
"""
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from helpers.formatting import PAL, apply_enterprise_layout

def render_dynamic_hybrid_overlay(df_filtered: pd.DataFrame, title: str, bar_metric: str, line_metric: str):
    """
    Renders an enterprise-grade dual-axis hybrid chart tracking a volumetric metric
    (e.g., Production Volume) against an intensity metric (e.g., Energy/Waste/Water Intensity).
    """
    bar_df = df_filtered[df_filtered["Metric"].str.lower().str.contains(bar_metric.lower(), regex=False)]
    line_df = df_filtered[df_filtered["Metric"].str.lower().str.contains(line_metric.lower(), regex=False)]
    
    if bar_df.empty or line_df.empty:
        st.info("Insufficient parallel metrics dimensions located to construct correlated timeline analysis chart paths.")
        return

    # Aggregate timelines explicitly to prevent cross-filtering fragmentation anomalies
    b_grp = bar_df.groupby("Period", as_index=False)["Value"].mean()
    l_grp = line_df.groupby("Period", as_index=False)["Value"].mean()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=b_grp["Period"], y=b_grp["Value"],
        name=bar_metric, marker_color="#E2E8F0", opacity=0.85, yaxis="y1"
    ))
    fig.add_trace(go.Scatter(
        x=l_grp["Period"], y=l_grp["Value"],
        name=line_metric, mode="lines+markers",
        line=dict(color=PAL["primary"], width=3, shape="spline"),
        marker=dict(size=6, borderwidth=1, bordercolor="#FFFFFF"), yaxis="y2"
    ))
    fig.update_layout(
        yaxis=dict(title=f"<b>{bar_metric}</b>", showgrid=False, titlefont=dict(color=PAL["text-mid"])),
        yaxis2=dict(title=f"<b>{line_metric}</b>", overlaying="y", side="right", showgrid=True, gridcolor=PAL["border"], titlefont=dict(color=PAL["primary"])),
        hovermode="x unified"
    )
    fig = apply_enterprise_layout(fig, height=360, title=title, legend=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def render_dynamic_category_distribution(df_filtered: pd.DataFrame, title: str, keywords_list: list):
    """
    Dynamically tracks down metrics matching target sub-vectors and builds a clean
    stacked resource distribution display configuration.
    """
    records = []
    for row in df_filtered.to_dict(orient="records"):
        m_lower = str(row["Metric"]).lower()
        if any(k.lower() in m_lower for k in keywords_list):
            records.append(row)
            
    if not records:
        st.info("No categorical matrix subcomponents matched standard keyword registry arrays for this view.")
        return
        
    df_sub = pd.DataFrame(records)
    pivot_df = df_sub.pivot_table(index="Period", columns="Metric", values="Value", aggfunc="sum").fillna(0).reset_index()
    
    fig = go.Figure()
    for col in pivot_df.columns:
        if col == "Period":
            continue
        fig.add_trace(go.Bar(x=pivot_df["Period"], y=pivot_df[col], name=str(col)[:40]))
        
    fig.update_layout(barmode="stack", hovermode="x unified")
    fig = apply_enterprise_layout(fig, height=360, title=title, legend=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def render_single_trajectory_area(df_filtered: pd.DataFrame, target_metric_substring: str, title: str, color_hex: str):
    sub_df = df_filtered[df_filtered["Metric"].str.lower().str.contains(target_metric_substring.lower(), regex=False)]
    if sub_df.empty:
        return
    grp = sub_df.groupby("Period", as_index=False)["Value"].mean()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=grp["Period"], y=grp["Value"], mode="lines+markers", fill="tozeroy",
        line=dict(color=color_hex, width=2.5, shape="spline"),
        fillcolor=f"{color_hex}12", marker=dict(size=6, borderwidth=1, bordercolor="#FFFFFF")
    ))
    fig = apply_enterprise_layout(fig, height=300, title=title, legend=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
