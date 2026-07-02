# charts/env_visuals.py
"""
Plotly Analytics Charts — Sustainability Visual Systems Engine.
"""
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from helpers.formatting import PAL, apply_enterprise_layout

def render_waste_efficiency_hybrid_chart(df_long: pd.DataFrame):
    prod_df = df_long[df_long["Metric"].str.contains("Production Volume", case=False, na=False)]
    waste_df = df_long[df_long["Metric"].str.contains("Total waste per t", case=False, na=False)]
    if prod_df.empty or waste_df.empty:
        st.info("Insufficient volumetric tracking entries available to output metrics analysis curves.")
        return
    b_grp = prod_df.groupby("Period", as_index=False)["Value"].mean()
    l_grp = waste_df.groupby("Period", as_index=False)["Value"].mean()

    fig = go.Figure()
    fig.add_trace(go.Bar(x=b_grp["Period"], y=b_grp["Value"], name="Production Gross Output (t)", marker_color="#E2E8F0", opacity=0.8, yaxis="y1"))
    fig.add_trace(go.Scatter(x=l_grp["Period"], y=l_grp["Value"], name="Waste Factor Intensity (kg/t)", mode="lines+markers", line=dict(color=PAL["primary"], width=3, shape="spline"), yaxis="y2"))
    fig.update_layout(
        yaxis=dict(title="Production Volume [Metric Tons]", showgrid=False),
        yaxis2=dict(title="Waste Generation Weight [kg/Gross t]", overlaying="y", side="right", showgrid=True, gridcolor=PAL["border"]),
        hovermode="x unified"
    )
    fig = apply_enterprise_layout(fig, height=360, title="🏭 Correlation Matrix: Yield Scale vs Material Waste Factor Intensity", legend=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def render_waste_stream_stacked_chart(df_long: pd.DataFrame):
    haz_keys = ["hazardous waste recycled [kg]", "hazardous waste reused [kg]", "hazardous waste sent to landfill [kg]"]
    non_haz_keys = ["non-hazardous waste sent to landfill [kg]", "non-hazardous waste sent for incineration  [kg]", "non-hazardous waste composting [kg]"]
    df_lower = df_long.copy()
    df_lower["norm_metric"] = df_lower["Metric"].str.lower().str.strip()
    haz_data = df_lower[df_lower["norm_metric"].isin(haz_keys)].groupby("Period", as_index=False)["Value"].sum()
    non_haz_data = df_lower[df_lower["norm_metric"].isin(non_haz_keys)].groupby("Period", as_index=False)["Value"].sum()
    merged = pd.merge(non_haz_data, haz_data, on="Period", how="outer", suffixes=("_NonHaz", "_Haz")).fillna(0)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=merged["Period"], y=merged["Value_NonHaz"], name="♻️ Non-Hazardous Mass Vector", marker_color=PAL["primary"]))
    fig.add_trace(go.Bar(x=merged["Period"], y=merged["Value_Haz"], name="⚠️ Hazardous Disposal Stream", marker_color=PAL["primary-2"]))
    fig.update_layout(barmode="stack", hovermode="x unified")
    fig = apply_enterprise_layout(fig, height=360, title="🗑 Stacked Material Balance Matrix: Segregated Trash Stream Delivery Profiles", legend=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def render_water_discharge_spline(df_long: pd.DataFrame):
    water_df = df_long[df_long["Metric"].str.contains("water withdrawal", case=False, na=False)]
    if water_df.empty:
        return
    grp = water_df.groupby("Period", as_index=False)["Value"].mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=grp["Period"], y=grp["Value"], mode="lines+markers", fill="tozeroy", line=dict(color=PAL["success"], width=2.5, shape="spline"), fillcolor="rgba(16, 185, 129, 0.05)"))
    fig = apply_enterprise_layout(fig, height=300, title="💧 Hydraulic Intake Trajectory: Combined Intake Intensities [m³/Gross Weight t]", legend=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def render_dynamic_hybrid_overlay(df_filtered: pd.DataFrame, title: str, bar_metric: str, line_metric: str):
    bar_df = df_filtered[df_filtered["Metric"].str.lower().str.contains(bar_metric.lower(), regex=False)]
    line_df = df_filtered[df_filtered["Metric"].str.lower().str.contains(line_metric.lower(), regex=False)]
    if bar_df.empty or line_df.empty:
        st.info("Insufficient parallel metrics dimensions located to construct correlated timeline analysis chart paths.")
        return
    b_grp = bar_df.groupby("Period", as_index=False)["Value"].mean()
    l_grp = line_df.groupby("Period", as_index=False)["Value"].mean()

    fig = go.Figure()
    fig.add_trace(go.Bar(x=b_grp["Period"], y=b_grp["Value"], name=bar_metric, marker_color="#E2E8F0", opacity=0.85, yaxis="y1"))
    fig.add_trace(go.Scatter(x=l_grp["Period"], y=l_grp["Value"], name=line_metric, mode="lines+markers", line=dict(color=PAL["primary"], width=3, shape="spline"), yaxis="y2"))
    fig.update_layout(
        yaxis=dict(title=f"<b>{bar_metric}</b>", showgrid=False),
        yaxis2=dict(title=f"<b>{line_metric}</b>", overlaying="y", side="right", showgrid=True, gridcolor=PAL["border"]),
        hovermode="x unified"
    )
    fig = apply_enterprise_layout(fig, height=360, title=title, legend=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def render_single_trajectory_area(df_filtered: pd.DataFrame, target_metric_substring: str, title: str, color_hex: str):
    sub_df = df_filtered[df_filtered["Metric"].str.lower().str.contains(target_metric_substring.lower(), regex=False)]
    if sub_df.empty:
        return
    grp = sub_df.groupby("Period", as_index=False)["Value"].mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=grp["Period"], y=grp["Value"], mode="lines+markers", fill="tozeroy", line=dict(color=color_hex, width=2.5, shape="spline"), fillcolor=f"{color_hex}12"))
    fig = apply_enterprise_layout(fig, height=300, title=title, legend=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
