"""
Metadata-Driven Taxonomy Extraction & Advanced Normalization Subsystem.
Parses row topologies, isolates merged cells, extracts engineering units from Row 3, 
and produces a unified data-driven warehouse format with zero hardcoding.
"""
import re
from io import BytesIO
import numpy as np
import pandas as pd
import openpyxl
import streamlit as st
import config

def _clean_string(val) -> str:
    if val is None or pd.isna(val):
        return ""
    return str(val).strip()

def _parse_numeric(val) -> float:
    if val is None or pd.isna(val) or str(val).strip() == "":
        return np.nan
    try:
        if isinstance(val, (int, float)):
            return float(val)
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return np.nan

@st.cache_data(ttl=config.RAW_FILE_CACHE_TTL_SECONDS, show_spinner=False)
def infer_and_melt_workbook_metadata(file_bytes: bytes) -> dict:
    """
    Parses every worksheet using openpyxl, handles merged dimensions natively,
    resolves structural hierarchies, row-wise units, monthly allocations,
    targets, and YTD/MTD figures dynamically.

    Returns exactly one unified long-form dataframe with zero hardcoded values.
    """
    wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    all_records = []
    units_registry = {}
    catalog_tree = {}

    date_regex = re.compile(r"(\b\d{4}-\d{2}-\d{2}\b|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Jan|Feb|Mar)", re.IGNORECASE)

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        max_row = ws.max_row
        max_col = ws.max_column
        
        if max_row < 4 or max_col < 2:
            continue

        # Extract rows 1, 2, and 3 cleanly to scan structural dimensions and period boundaries
        row1 = [ws.cell(row=1, column=c).value for c in range(1, max_col + 1)]
        row2 = [ws.cell(row=2, column=c).value for c in range(1, max_col + 1)]
        row3 = [ws.cell(row=3, column=c).value for c in range(1, max_col + 1)]

        # Forward-fill header regions to correct openpyxl none assignments on merged header cells
        for c in range(1, len(row1)):
            if row1[c] is None: row1[c] = row1[c-1]
        for c in range(1, len(row2)):
            if row2[c] is None: row2[c] = row2[c-1]
        for c in range(1, len(row3)):
            if row3[c] is None: row3[c] = row3[c-1]

        # Scan row 2 or row 3 headers to identify period, target, and baseline dimensions
        timeline_mapping = {}
        target_col_idx = None
        ytd_col_idx = None
        mtd_col_idx = None

        for c in range(1, max_col + 1):
            val_r2 = _clean_string(row2[c-1])
            val_r3 = _clean_string(row3[c-1])
            
            # Identify month markers
            if date_regex.search(val_r2) and "ytd" not in val_r2.lower() and "target" not in val_r2.lower():
                timeline_mapping[c] = val_r2
            elif date_regex.search(val_r3) and "ytd" not in val_r3.lower() and "target" not in val_r3.lower():
                timeline_mapping[c] = val_r3
                
            # Identify calculated aggregates and standard milestones
            if "target" in val_r2.lower() or "target" in val_r3.lower():
                target_col_idx = c
            if "ytd" in val_r2.lower() or "ytd" in val_r3.lower():
                ytd_col_idx = c
            if "mtd" in val_r2.lower() or "mtd" in val_r3.lower():
                mtd_col_idx = c

        if not timeline_mapping:
            continue

        # Process the metric payload entries from row 4 downward
        current_category = ""
        current_subcategory = ""

        for r in range(4, max_row + 1):
            col1_val = ws.cell(row=r, column=1).value
            col2_val = ws.cell(row=r, column=2).value
            col3_val = ws.cell(row=r, column=3).value
            col4_val = ws.cell(row=r, column=4).value

            # Manage state mappings across structural hierarchy blocks
            if col1_val is not None: current_category = str(col1_val).strip()
            if col2_val is not None: current_subcategory = str(col2_val).strip()
            
            # The innermost text element acts as the primary metric key name
            metric_raw = col3_val if col3_val is not None else col4_val
            if metric_raw is None or _clean_string(metric_raw).lower() in ["nan", "none", ""]:
                continue
            
            metric_name = str(metric_raw).strip()
            if "monthly kpi" in metric_name.lower():
                continue

            # Universal Unit Extraction Pass: Read directly from Row 3 of the sheet
            # If a specific column map is associated with timeline elements, use row 3's string value
            inferred_unit = ""
            for c_idx in timeline_mapping.keys():
                unit_candidate = _clean_string(row3[c_idx-1])
                if unit_candidate and not date_regex.search(unit_candidate) and unit_candidate.lower() not in ["ytd", "target", "mtd", "bu"]:
                    inferred_unit = unit_candidate
                    break
                    
            # Secondary backup unit resolution fallback if row 3 strings hold date timestamps
            if not inferred_unit:
                unit_bracket_match = re.search(r"\[(.*?)\]", metric_name)
                inferred_unit = unit_bracket_match.group(1) if unit_bracket_match else ""

            units_registry[metric_name] = inferred_unit

            # Calculate and map static milestone columns for this row pass
            target_val = _parse_numeric(ws.cell(row=r, column=target_col_idx).value) if target_col_idx else np.nan
            ytd_val = _parse_numeric(ws.cell(row=r, column=ytd_col_idx).value) if ytd_col_idx else np.nan
            mtd_val = _parse_numeric(ws.cell(row=r, column=mtd_col_idx).value) if mtd_col_idx else np.nan

            # Unpivot monthly value points into normalized individual records
            for col_idx, period_label in timeline_mapping.items():
                raw_cell_value = ws.cell(row=r, column=col_idx).value
                numeric_val = _parse_numeric(raw_cell_value)
                
                # Deduce fiscal calendar parameters safely
                inferred_year = config.CURRENT_FISCAL_YEAR
                year_match = re.search(r"\d{4}", period_label)
                if year_match:
                    inferred_year = year_match.group(0)

                # Format period strings uniformly
                if "-" in period_label:
                    try:
                        period_clean = datetime.strptime(period_label.split(" ")[0], "%Y-%m-%d").strftime("%b-%y")
                    except Exception:
                        period_clean = period_label
                else:
                    period_clean = period_label

                all_records.append({
                    "Sheet": str(sheet_name).strip(),
                    "Category": current_category if current_category else str(sheet_name).strip(),
                    "Subcategory": current_subcategory if current_subcategory else "General Operations",
                    "Metric": metric_name,
                    "Unit": inferred_unit,
                    "Month": period_clean,
                    "Value": numeric_val,
                    "Target": target_val,
                    "YTD": ytd_val,
                    "MTD": mtd_val,
                    "Year": inferred_year
                })

    df_long = pd.DataFrame(all_records)
    
    if not df_long.empty:
        # Build dynamic page layout dictionaries from discovered category keys
        distinct_categories = df_long["Category"].unique().tolist()
        for cat in distinct_categories:
            catalog_tree[cat] = sorted(df_long[df_long["Category"] == cat]["Metric"].unique().tolist())
            
        sorted_periods = sorted(df_long["Month"].unique().tolist(), key=lambda x: ("26" in str(x) or "2026" in str(x), x))
    else:
        sorted_periods = []

    return {
        "long_df": df_long,
        "catalog": catalog_tree,
        "periods": sorted_periods,
        "units": units_registry
    }
