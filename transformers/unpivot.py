# transformers/unpivot.py
"""
Metadata-Driven Taxonomy Extraction & Workbook Ingestion Pipeline Subsystem.
Scans and infers workbook metrics, structural categories, sections and periods dynamically.
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

@st.cache_data(ttl=config.RAW_FILE_CACHE_TTL_SECONDS, show_spinner=False)
def infer_and_melt_workbook_metadata(sheets_dict: dict) -> dict:
    unified_records = []
    units_registry = {}
    metric_catalog = {}
    
    date_pattern = re.compile(r"(2025|2026|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Jan|Feb|Mar)", re.IGNORECASE)
    
    for sheet_name, df_raw in sheets_dict.items():
        if df_raw.empty:
            continue
        df = df_raw.dropna(how="all").reset_index(drop=True)
        timeline_cols = []
        for col in df.columns:
            col_str = str(col)
            if date_pattern.search(col_str) and "YTD" not in col_str and "Target" not in col_str:
                timeline_cols.append(col)
        text_cols = [col for col in df.columns if col not in timeline_cols]
        if not text_cols:
            continue
            
        records_list = df.to_dict(orient="records")
        for row in records_list:
            text_values = [str(row[c]).strip() for c in text_cols if row[c] is not None and str(row[c]).strip().lower() not in ["nan", "none", ""]]
            if len(text_values) < 1:
                continue
            metric_name = text_values[-1]
            if "monthly kpi" in metric_name.lower():
                continue
            unit_match = re.search(r"\[(.*?)\]", metric_name)
            unit_str = unit_match.group(1) if unit_match else ""
            units_registry[metric_name] = unit_str
            
            primary_cat = text_values[0] if len(text_values) > 1 else sheet_name
            sub_cat = text_values[1] if len(text_values) > 2 else "General Operations"
            
            inferred_page = "Executive Overview"
            m_lower = metric_name.lower()
            s_lower = sheet_name.lower()
            
            if "health" in s_lower or "safety" in s_lower or "h&s" in s_lower or "injury" in m_lower or "fatal" in m_lower:
                inferred_page = "Health & Safety"
            elif "energy" in m_lower or "diesel" in m_lower or "lpg" in m_lower or "electricity" in m_lower:
                inferred_page = "Energy"
            elif "water" in m_lower or "withdrawal" in m_lower or "discharge" in m_lower:
                inferred_page = "Water"
            elif "waste" in m_lower or "landfill" in m_lower or "compost" in m_lower or "recycle" in m_lower:
                inferred_page = "Waste"
            elif "production" in m_lower or "production" in primary_cat.lower() or "volume" in m_lower:
                inferred_page = "Production"
                
            if inferred_page not in metric_catalog:
                metric_catalog[inferred_page] = set()
            metric_catalog[inferred_page].add(metric_name)
            
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
                unified_records.append({
                    "Page": inferred_page, 
                    "Category": primary_cat, 
                    "Subcategory": sub_cat,
                    "Metric": metric_name, 
                    "Period": period_str, 
                    "Value": v_num, 
                    "Unit": unit_str
                })
                
    df_long = pd.DataFrame(unified_records)
    all_periods = sorted(df_long["Period"].unique().tolist(), key=lambda x: ("2026" in x, x))
    structured_catalog = {k: sorted(list(v)) for k, v in metric_catalog.items()}
    
    return {
        "long_df": df_long, 
        "catalog": structured_catalog, 
        "periods": all_periods, 
        "units": units_registry
    }
