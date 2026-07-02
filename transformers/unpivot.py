# transformers/unpivot.py
"""
Data Transformation & Normalized Reshaping Subsystem.
"""
import re
import numpy as np
import pandas as pd
import streamlit as st
import config

@st.cache_data(ttl=config.RAW_FILE_CACHE_TTL_SECONDS, show_spinner=False)
def melt_wide_sheet_to_long_cached(df_raw: pd.DataFrame) -> pd.DataFrame:
    timeline_cols = []
    pattern = re.compile(r"(2025|2026|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Jan|Feb|Mar)", re.IGNORECASE)
    
    for col in df_raw.columns:
        col_str = str(col)
        if pattern.search(col_str):
            if "YTD" not in col_str and "Target" not in col_str:
                timeline_cols.append(col)

    label_col = None
    for col in df_raw.columns:
        sample = df_raw[col].dropna().astype(str).tolist()
        if any(any(k in s for k in ["Volume", "Fatalities", "waste", "Usage"]) for s in sample):
            label_col = col
            break
            
    if label_col is None:
        label_col = df_raw.columns[2] if len(df_raw.columns) > 2 else df_raw.columns[0]

    records = []
    raw_records = df_raw[[label_col] + timeline_cols].to_dict(orient="records")
    for row in raw_records:
        metric_raw = str(row[label_col]).strip()
        if not metric_raw or metric_raw.lower() in ["nan", "none", "environment monthly kpi"]:
            continue

        for period in timeline_cols:
            val = row[period]
            if isinstance(val, (int, float)):
                v_num = float(val)
            else:
                try:
                    v_num = float(str(val).replace(",", "").strip())
                except (ValueError, TypeError):
                    v_num = np.nan
            
            period_str = str(period).split(" ")[0] if "-" in str(period) else str(period)
            records.append({
                "Metric": metric_raw,
                "Period": period_str,
                "Value": v_num
            })
    return pd.DataFrame(records)
