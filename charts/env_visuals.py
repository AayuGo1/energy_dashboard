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

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=prod_df["Period"], y=prod_df["Value"],
        name="Production Gross Output (t)", marker_color="#E2E8F0", opacity=0.8, yaxis="y1"
    ))
    fig.add_trace(go.Scatter(
        x=waste_df["Period"], y=waste_df["Value"],
        name="Waste Factor Intensity (kg/t)", mode="lines+markers",
        line=dict(color=PAL["primary"], width=3, shape="spline"),
        marker=dict(size=6, borderwidth=1, bordercolor="#FFFFFF"), yaxis="y2"
    ))
    fig.update_layout(
        yaxis=dict(title="Production Volume [Metric Tons]", showgrid=False, titlefont=dict(color=PAL["text-mid"])),
        yaxis2=dict(title="Waste Generation Weight [kg/Gross t]", overlaying="y", side="right", showgrid=True, gridcolor=PAL["border"], titlefont=dict(color=PAL["primary"])),
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

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=water_df["Period"], y=water_df["Value"],
        mode="lines+markers", fill="tozeroy",
        line=dict(color=PAL["success"], width=2.5, shape="spline"),
        fillcolor="rgba(16, 185, 129, 0.05)",
        marker=dict(size=6, borderwidth=1, bordercolor="#FFFFFF")
    ))
    fig = apply_enterprise_layout(fig, height=300, title="💧 Hydraulic Intake Trajectory: Combined Intake Intensities [m³/Gross Weight t]", legend=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
