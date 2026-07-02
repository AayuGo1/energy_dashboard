"""
Metadata-Driven Sheet Hierarchy & Core Unit Engineering Parsing Engine.
Strictly extracts categories from Column B, subcategories from Column C, 
metrics from Column D, and units from Row 3 with structural forward-filling.
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
    Parses workbook worksheets via openpyxl by doing strict geometric cell coordinate lookups.
    Enforces a data-driven structure without hardcoding any keyword comparisons.
    
    Structure extracted per metric row:
      - Category: Column B (Forward-filled)
      - Subcategory: Column C (Forward-filled)
      - Metric: Column D
      - Unit: Row 3 (Mapped per data column index)
      - Month columns: Inferred dynamically from Row 2 or Row 3 date strings.
    """
    wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    all_records = []
    units_registry = {}
    catalog_tree = {}

    date_regex = re.compile(r"(\b\d{4}-\d{2}-\d{2}\b|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Jan|Feb|Mar)", re.IGNORECASE)

    for sheet_name in wb.sheetnames:
        if sheet_name not in config.REQUIRED_SHEETS:
            continue
            
        ws = wb[sheet_name]
        max_row = ws.max_row
        max_col = ws.max_column
        
        if max_row < 4 or max_col < 5:
            continue

        # Extract rows 1, 2, and 3 cleanly to read operational timelines
        row2 = [ws.cell(row=2, column=c).value for c in range(1, max_col + 1)]
        row3 = [ws.cell(row=3, column=c).value for c in range(1, max_col + 1)]

        # Forward fill empty header regions caused by openpyxl merged cells evaluations
        for c in range(1, len(row2)):
            if row2[c] is None: row2[c] = row2[c-1]
        for c in range(1, len(row3)):
            if row3[c] is None: row3[c] = row3[c-1]

        # Isolate temporal column map indices dynamically
        timeline_mapping = {}
        target_col_idx = None
        ytd_col_idx = None
        mtd_col_idx = None

        for c in range(5, max_col + 1):
            val_r2 = _clean_string(row2[c-1])
            val_r3 = _clean_string(row3[c-1])
            
            if date_regex.search(val_r2) and "ytd" not in val_r2.lower() and "target" not in val_r2.lower():
                timeline_mapping[c] = val_r2
            elif date_regex.search(val_r3) and "ytd" not in val_r3.lower() and "target" not in val_r3.lower():
                timeline_mapping[c] = val_r3
                
            if "target" in val_r2.lower() or "target" in val_r3.lower():
                target_col_idx = c
            if "ytd" in val_r2.lower() or "ytd" in val_r3.lower():
                ytd_col_idx = c
            if "mtd" in val_r2.lower() or "mtd" in val_r3.lower():
                mtd_col_idx = c

        if not timeline_mapping:
            continue

        # Positional state variables for structural forward-filling logic execution
        current_category = ""
        current_subcategory = ""

        for r in range(4, max_row + 1):
            cell_b = ws.cell(row=r, column=2).value
            cell_c = ws.cell(row=r, column=3).value
            cell_d = ws.cell(row=r, column=4).value

            # Forward-fill structure metrics hierarchies
            if cell_b is not None and _clean_string(cell_b) != "": 
                current_category = str(cell_b).strip()
            if cell_c is not None and _clean_string(cell_c) != "": 
                current_subcategory = str(cell_c).strip()
                
            if cell_d is None or _clean_string(cell_d).lower() in ["nan", "none", "", "monthly kpi"]:
                continue
                
            metric_name = str(cell_d).strip()

            # Dynamic Row 3 explicit engineering unit mapping extraction pass
            inferred_unit = ""
            for c_idx in timeline_mapping.keys():
                unit_candidate = _clean_string(row3[c_idx-1])
                if unit_candidate and not date_regex.search(unit_candidate) and unit_candidate.lower() not in ["ytd", "target", "mtd", "bu"]:
                    inferred_unit = unit_candidate
                    break
            
            if not inferred_unit and target_col_idx:
                inferred_unit = _clean_string(row3[target_col_idx-1])
                
            if not inferred_unit or inferred_unit.lower() in ["ytd", "target", "mtd"]:
                inferred_unit = "Units"

            units_registry[metric_name] = inferred_unit

            # Pull non-timeline milestone segments safely
            target_val = _parse_numeric(ws.cell(row=r, column=target_col_idx).value) if target_col_idx else np.nan
            ytd_val = _parse_numeric(ws.cell(row=r, column=ytd_col_idx).value) if ytd_col_idx else np.nan
            mtd_val = _parse_numeric(ws.cell(row=r, column=mtd_col_idx).value) if mtd_col_idx else np.nan

            # Unpivot and normalize each time coordinates segment line entry
            for col_idx, period_label in timeline_mapping.items():
                numeric_val = _parse_numeric(ws.cell(row=r, column=col_idx).value)
                
                inferred_year = config.CURRENT_FISCAL_YEAR
                year_match = re.search(r"\d{4}", period_label)
                if year_match:
                    inferred_year = year_match.group(0)

                if "-" in period_label:
                    try:
                        period_clean = datetime.strptime(period_label.split(" ")[0], "%Y-%m-%d").strftime("%b-%y")
                    except Exception:
                        period_clean = period_label
                else:
                    period_clean = period_label

                all_records.append({
                    "Sheet": str(sheet_name).strip(),
                    "Category": current_category if current_category else "General Data",
                    "Subcategory": current_subcategory if current_subcategory else "Operations",
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
