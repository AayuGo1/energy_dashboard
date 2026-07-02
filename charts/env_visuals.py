# charts/env_visuals.py
"""
Plotly Enterprise Chart Customization Engine — 100% Data-Driven Architecture.
Generates responsive area, line, bar, and stacked charts directly from filtered records
utilizing dynamically mapped runtime engineering units.
"""
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from helpers.formatting import PAL, apply_enterprise_layout

def render_energy_analytics_charts(df_filtered: pd.DataFrame):
    """
    Dynamically maps out and renders Line, Bar, and Intensity trends 
    for discovered Energy indicators without hardcoding metric names.
    """
    if df_filtered.empty:
        st.info("No active energy data metrics matched the current portal filter matrix.")
        return

    # 1. Line Chart & Bar Chart - Total Period Volumetric Trends
    # Aggregate values by month and metric to prevent overlap fragmentation
    grp_df = df_filtered.groupby(["Month", "Metric", "Unit"], as_index=False)["Value"].mean()
    distinct_metrics = grp_df["Metric"].unique().tolist()

    if distinct_metrics:
        # Line Chart
        fig_line = go.Figure()
        for m in distinct_metrics:
            m_sub = grp_df[grp_df["Metric"] == m]
            unit = m_sub["Unit"].iloc[0] if not m_sub.empty else ""
            fig_line.add_trace(go.Scatter(
                x=m_sub["Month"], y=m_sub["Value"],
                name=f"{m} ({unit})", mode="lines+markers",
                line=dict(width=2.5, shape="spline"),
                marker=dict(size=5)
            ))
        fig_line.update_layout(hovermode="x unified")
        apply_enterprise_layout(fig_line, height=340, title="📈 Monthly Consumption Longitudinal Trends Profiles", legend=True)
        st.plotly_chart(fig_line, use_container_width=True, config={"displayModeBar": False})

        # Bar Chart
        fig_bar = go.Figure()
        for m in distinct_metrics:
            m_sub = grp_df[grp_df["Metric"] == m]
            unit = m_sub["Unit"].iloc[0] if not m_sub.empty else ""
            fig_bar.add_trace(go.Bar(
                x=m_sub["Month"], y=m_sub["Value"],
                name=f"{m} ({unit})"
            ))
        fig_bar.update_layout(barmode="group", hovermode="x unified")
        apply_enterprise_layout(fig_bar, height=340, title="📊 Monthly Resource Allocation Load Distributions", legend=True)
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    # 3. Intensity Trend Identification
    intensity_metrics = [m for m in distinct_metrics if "intensity" in m.lower() or "/" in m.lower() or "per" in m.lower()]
    if intensity_metrics:
        fig_int = go.Figure()
        for m in intensity_metrics:
            m_sub = grp_df[grp_df["Metric"] == m]
            unit = m_sub["Unit"].iloc[0] if not m_sub.empty else ""
            fig_int.add_trace(go.Scatter(
                x=m_sub["Month"], y=m_sub["Value"],
                name=f"{m} ({unit})", mode="lines+markers",
                fill="tozeroy", line=dict(width=2.5, shape="spline")
            ))
        fig_int.update_layout(hovermode="x unified")
        apply_enterprise_layout(fig_int, height=320, title="⚡ Operational Efficiency Intensity Curves Profile", legend=True)
        st.plotly_chart(fig_int, use_container_width=True, config={"displayModeBar": False})


def render_water_analytics_charts(df_filtered: pd.DataFrame):
    """
    Dynamically groups and isolates Withdrawal, Consumption, and Discharge
    sub-trends dynamically without hardcoding explicit row index labels.
    """
    if df_filtered.empty:
        st.info("No active water data metrics matched the current portal filter matrix.")
        return

    grp_df = df_filtered.groupby(["Month", "Metric", "Unit"], as_index=False)["Value"].mean()
    distinct_metrics = grp_df["Metric"].unique().tolist()

    # Dynamic Slicing mapping to separate sub-trend layouts based on workbook keywords
    withdrawal_kpis = [m for m in distinct_metrics if "withdrawal" in m.lower() or "intake" in m.lower() or "ground" in m.lower()]
    consumption_kpis = [m for m in distinct_metrics if "consumption" in m.lower() or "usage" in m.lower()]
    discharge_kpis = [m for m in distinct_metrics if "discharge" in m.lower() or "outflow" in m.lower()]

    if withdrawal_kpis:
        fig_w = go.Figure()
        for m in withdrawal_kpis:
            m_sub = grp_df[grp_df["Metric"] == m]
            unit = m_sub["Unit"].iloc[0] if not m_sub.empty else ""
            fig_w.add_trace(go.Scatter(x=m_sub["Month"], y=m_sub["Value"], name=f"{m} ({unit})", mode="lines+markers", line=dict(shape="spline")))
        apply_enterprise_layout(fig_w, height=300, title="💧 Hydraulic Intake & Withdrawal Long-Term Trajectories", legend=True)
        st.plotly_chart(fig_w, use_container_width=True, config={"displayModeBar": False})

    if consumption_kpis:
        fig_c = go.Figure()
        for m in consumption_kpis:
            m_sub = grp_df[grp_df["Metric"] == m]
            unit = m_sub["Unit"].iloc[0] if not m_sub.empty else ""
            fig_c.add_trace(go.Bar(x=m_sub["Month"], y=m_sub["Value"], name=f"{m} ({unit})"))
        apply_enterprise_layout(fig_c, height=300, title="📉 Consolidated Local Water Consumption Loading Profiles", legend=True)
        st.plotly_chart(fig_c, use_container_width=True, config={"displayModeBar": False})

    if discharge_kpis:
        fig_d = go.Figure()
        for m in discharge_kpis:
            m_sub = grp_df[grp_df["Metric"] == m]
            unit = m_sub["Unit"].iloc[0] if not m_sub.empty else ""
            fig_d.add_trace(go.Scatter(x=m_sub["Month"], y=m_sub["Value"], name=f"{m} ({unit})", mode="lines+markers", fill="tozeroy"))
        apply_enterprise_layout(fig_d, height=300, title="🌊 Hydraulic Discharge & Outflow Efficiency Trends", legend=True)
        st.plotly_chart(fig_d, use_container_width=True, config={"displayModeBar": False})


def render_waste_analytics_charts(df_filtered: pd.DataFrame):
    """
    Renders completely dynamic data-driven generation trends, stacked compositions,
    and donut allocation charts from active waste streams.
    """
    if df_filtered.empty:
        st.info("No active waste data metrics matched the current portal filter matrix.")
        return

    grp_df = df_filtered.groupby(["Month", "Metric", "Unit"], as_index=False)["Value"].mean()
    distinct_metrics = grp_df["Metric"].unique().tolist()

    # 1. Total Generation Mass Trend
    fig_gen = go.Figure()
    for m in distinct_metrics:
        if "intensity" not in m.lower() and "/" not in m.lower():
            m_sub = grp_df[grp_df["Metric"] == m]
            unit = m_sub["Unit"].iloc[0] if not m_sub.empty else ""
            fig_gen.add_trace(go.Scatter(x=m_sub["Month"], y=m_sub["Value"], name=f"{m} ({unit})", mode="lines+markers", line=dict(shape="spline")))
    apply_enterprise_layout(fig_gen, height=320, title="♻️ Consolidated Material Waste Footprint Trajectories", legend=True)
    st.plotly_chart(fig_gen, use_container_width=True, config={"displayModeBar": False})

    # 2. Stacked Bar Composition (Hazardous vs Non-Hazardous Distribution Layers)
    pivot_df = grp_df.pivot_table(index="Month", columns="Metric", values="Value", aggfunc="sum").fillna(0).reset_index()
    if not pivot_df.empty and len(pivot_df.columns) > 1:
        fig_stack = go.Figure()
        for col in pivot_df.columns:
            if col == "Month": continue
            # Find the unit token for this column pass
            u_subset = grp_df[grp_df["Metric"] == col]["Unit"]
            unit = u_subset.iloc[0] if not u_subset.empty else ""
            fig_stack.add_trace(go.Bar(x=pivot_df["Month"], y=pivot_df[col], name=f"{col} ({unit})"))
        fig_stack.update_layout(barmode="stack", hovermode="x unified")
        apply_enterprise_layout(fig_stack, height=340, title="🗑 Stacked Mass Disposals & Processing Allocation Grid Matrix", legend=True)
        st.plotly_chart(fig_stack, use_container_width=True, config={"displayModeBar": False})

    # 3. Donut Metric Breakdown Profile
    latest_month = grp_df["Month"].iloc[-1] if not grp_df.empty else None
    if latest_month:
        df_latest = grp_df[(grp_df["Month"] == latest_month) & (~grp_df["Metric"].str.lower().str.contains("intensity|/", regex=True))]
        if not df_latest.empty and df_latest["Value"].sum() > 0:
            fig_donut = go.Figure(data=[go.Pie(
                labels=df_latest["Metric"], values=df_latest["Value"],
                hole=0.45, textinfo="percent+label",
                hovertemplate="<b>%{label}</b><br>Value: %{value}<br>Distribution: %{percent}<extra></extra>"
            )])
            apply_enterprise_layout(fig_donut, height=340, title=f"🍩 Structural Material Composition Profile (Period Window: {latest_month})", legend=True)
            st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})
