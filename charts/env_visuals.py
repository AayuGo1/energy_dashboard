"""
Plotly Analytics Charts — Sustainability Visual Systems Engine.
"""
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from helpers.formatting import PAL, apply_enterprise_layout

def render_waste_efficiency_hybrid_chart(df_long: pd.DataFrame, units_registry: dict):
    prod_df = df_long[df_long["Metric"].str.contains("Production Volume", case=False, na=False)]
    waste_df = df_long[df_long["Metric"].str.contains("Total waste per t", case=False, na=False)]
    if prod_df.empty or waste_df.empty:
        st.info("Insufficient volumetric tracking entries available to output metrics analysis curves.")
        return
    b_grp = prod_df.groupby("Period", as_index=False)["Value"].mean()
    l_grp = waste_df.groupby("Period", as_index=False)["Value"].mean()

    prod_unit = units_registry.get(prod_df["Metric"].iloc[0], "")
    waste_unit = units_registry.get(waste_df["Metric"].iloc[0], "")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=b_grp["Period"], y=b_grp["Value"], name=f"Production Output ({prod_unit})", marker_color="#E2E8F0", opacity=0.8, yaxis="y1"))
    fig.add_trace(go.Scatter(x=l_grp["Period"], y=l_grp["Value"], name=f"Waste Intensity ({waste_unit})", mode="lines+markers", line=dict(color=PAL["primary"], width=3, shape="spline"), yaxis="y2"))
    fig.update_layout(
        yaxis=dict(title=f"Production Volume ({prod_unit})", showgrid=False),
        yaxis2=dict(title=f"Waste Intensity ({waste_unit})", overlaying="y", side="right", showgrid=True, gridcolor=PAL["border"]),
        hovermode="x unified"
    )
    fig = apply_enterprise_layout(fig, height=360, title="🏭 Output Correlation Matrix: Volume vs Generation Intensity", legend=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def render_waste_stream_stacked_chart(df_long: pd.DataFrame, units_registry: dict):
    haz_keys = ["hazardous waste recycled [kg]", "hazardous waste reused [kg]", "hazardous waste sent to landfill [kg]"]
    non_haz_keys = ["non-hazardous waste sent to landfill [kg]", "non-hazardous waste sent for incineration  [kg]", "non-hazardous waste composting [kg]"]
    df_lower = df_long.copy()
    df_lower["norm_metric"] = df_lower["Metric"].str.lower().str.strip()
    haz_data = df_lower[df_lower["norm_metric"].isin(haz_keys)].groupby("Period", as_index=False)["Value"].sum()
    non_haz_data = df_lower[df_lower["norm_metric"].isin(non_haz_keys)].groupby("Period", as_index=False)["Value"].sum()
    merged = pd.merge(non_haz_data, haz_data, on="Period", how="outer", suffixes=("_NonHaz", "_Haz")).fillna(0)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=merged["Period"], y=merged["Value_NonHaz"], name="Non-Hazardous Component (kg)", marker_color=PAL["primary"]))
    fig.add_trace(go.Bar(x=merged["Period"], y=merged["Value_Haz"], name="Hazardous Component (kg)", marker_color=PAL["primary-2"]))
    fig.update_layout(barmode="stack", hovermode="x unified", yaxis=dict(title="Mass Allocation [kg]"))
    fig = apply_enterprise_layout(fig, height=360, title="🗑 Segregated Material Balance Composition Matrix", legend=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def render_water_discharge_spline(df_long: pd.DataFrame, units_registry: dict):
    water_df = df_long[df_long["Metric"].str.contains("water withdrawal", case=False, na=False)]
    if water_df.empty:
        return
    grp = water_df.groupby("Period", as_index=False)["Value"].mean()
    unit = units_registry.get(water_df["Metric"].iloc[0], "")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=grp["Period"], y=grp["Value"], mode="lines+markers", fill="tozeroy", line=dict(color=PAL["success"], width=2.5, shape="spline"), fillcolor="rgba(16, 185, 129, 0.05)"))
    fig.update_layout(yaxis=dict(title=f"Water Volume ({unit})"))
    fig = apply_enterprise_layout(fig, height=300, title=f"💧 Hydraulic Intake Intensity Curve ({unit})", legend=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def render_dynamic_hybrid_overlay(df_filtered: pd.DataFrame, title: str, bar_metric: str, line_metric: str, units_registry: dict):
    bar_df = df_filtered[df_filtered["Metric"].str.lower().str.contains(bar_metric.lower(), regex=False)]
    line_df = df_filtered[df_filtered["Metric"].str.lower().str.contains(line_metric.lower(), regex=False)]
    if bar_df.empty or line_df.empty:
        st.info("Insufficient metrics available to construct overlay analysis charts.")
        return
    b_grp = bar_df.groupby("Period", as_index=False)["Value"].mean()
    l_grp = line_df.groupby("Period", as_index=False)["Value"].mean()

    b_unit = units_registry.get(bar_df["Metric"].iloc[0], "")
    l_unit = units_registry.get(line_df["Metric"].iloc[0], "")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=b_grp["Period"], y=b_grp["Value"], name=f"{bar_metric} ({b_unit})", marker_color="#E2E8F0", opacity=0.85, yaxis="y1"))
    fig.add_trace(go.Scatter(x=l_grp["Period"], y=l_grp["Value"], name=f"{line_metric} ({l_unit})", mode="lines+markers", line=dict(color=PAL["primary"], width=3, shape="spline"), yaxis="y2"))
    fig.update_layout(
        yaxis=dict(title=f"{bar_metric} ({b_unit})", showgrid=False),
        yaxis2=dict(title=f"{line_metric} ({l_unit})", overlaying="y", side="right", showgrid=True, gridcolor=PAL["border"]),
        hovermode="x unified"
    )
    fig = apply_enterprise_layout(fig, height=360, title=title, legend=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def render_single_trajectory_area(df_filtered: pd.DataFrame, target_metric_substring: str, title: str, color_hex: str, units_registry: dict):
    sub_df = df_filtered[df_filtered["Metric"].str.lower().str.contains(target_metric_substring.lower(), regex=False)]
    if sub_df.empty:
        return
    grp = sub_df.groupby("Period", as_index=False)["Value"].mean()
    unit = units_registry.get(sub_df["Metric"].iloc[0], "")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=grp["Period"], y=grp["Value"], mode="lines+markers", fill="tozeroy", line=dict(color=color_hex, width=2.5, shape="spline"), fillcolor=f"{color_hex}12"))
    fig.update_layout(yaxis=dict(title=f"Value ({unit})"))
    fig = apply_enterprise_layout(fig, height=300, title=f"{title} ({unit})", legend=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
