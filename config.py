"""
Centralized Enterprise Configuration System for Jubilant FoodWorks Limited.
Absolute single source of truth for variables, telemetry paths, and runtime settings.
"""
import os

# =============================================================================
# ENTERPRISE BRANDING & IDENTITY CONSTANTS
# =============================================================================
COMPANY_NAME = "Jubilant FoodWorks Limited"
COMPANY_INITIALS = "JFL"
DASHBOARD_TITLE = "Enterprise Analytics Portal"
DASHBOARD_TITLE_SUB = "Executive Sustainability Analytics Platform"
CURRENT_FISCAL_YEAR = "2026"
SIDEBAR_LOGO_TEXT = "JFL-BI"
PAGE_TITLE = f"{COMPANY_NAME} | Enterprise Portal"
DEFAULT_PERIOD = "Global"

# =============================================================================
# DATA SOURCE PIPELINE PROPERTIES
# =============================================================================
GITHUB_OWNER = os.environ.get("JFL_GITHUB_OWNER", "AayuGo1")
GITHUB_REPO = os.environ.get("JFL_GITHUB_REPO", "energy_dashboard")
GITHUB_BRANCH = os.environ.get("JFL_GITHUB_BRANCH", "main")
GITHUB_DATA_FOLDER = os.environ.get("JFL_GITHUB_DATA_FOLDER", "")
LATEST_FILENAME_PATTERN = os.environ.get("JFL_LATEST_PATTERN", r"^latest.*\.xlsx$")
ARCHIVE_FOLDER_NAME = os.environ.get("JFL_ARCHIVE_FOLDER", "archive")

GITHUB_RAW_URL_OVERRIDE = os.environ.get(
    "JFL_GITHUB_RAW_URL",
    "https://raw.githubusercontent.com/AayuGo1/energy_dashboard/main/Monthly%20KPI%20Summary%20Sheet_April_GNSC.xlsx",
)
# Alias assignment mapping to fulfill old or alternative naming targets natively
GITHUB_EXCEL_URL = GITHUB_RAW_URL_OVERRIDE

GITHUB_API_CONTENTS_URL = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{{path}}?ref={GITHUB_BRANCH}"
)

# =============================================================================
# CACHING AND TELEMETRY CONFIGURATION
# =============================================================================
RAW_FILE_CACHE_TTL_SECONDS = int(os.environ.get("JFL_RAW_CACHE_TTL", "300"))
KPI_CACHE_TTL_SECONDS = int(os.environ.get("JFL_KPI_CACHE_TTL", "300"))

FALLBACK_SNAPSHOT_PATH = os.environ.get("JFL_FALLBACK_SNAPSHOT", ".cache/last_good_workbook.bin")
FALLBACK_META_PATH = os.environ.get("JFL_FALLBACK_META", ".cache/last_good_meta.json")

LOG_FILE_PATH = os.environ.get("JFL_LOG_FILE", ".cache/ingestion.log")
LOG_LEVEL = os.environ.get("JFL_LOG_LEVEL", "INFO")

# =============================================================================
# REQUIRED CORE SCHEMA VALIDATION METADATA
# =============================================================================
REQUIRED_SHEETS = ["H&S", "Environment"]
REQUIRED_KPI_LABELS = {
    "H&S": [
        "Fatalities", "Lost Time Injury", "Total recordable accidents",
        "First Aid Accident", "Near miss", "% of UA/UC Closure",
        "Safety observation worker involvement % [%]",
    ],
    "Environment": [
        "Total energy consumption [kWh/Gross Weight (t Metric)]",
        "Total water withdrawal [m³/Gross Weight (t Metric)]",
        "Total waste per t(Metrics) [kg/Gross Weight (t Metric)]",
        "Production Volume - Gross Weight [Gross Weight (t Metric)]",
    ],
}

# =============================================================================
# RISK CONTROL PROFILE MATRIX DEFINITIONS
# =============================================================================
ANOMALY_PCT_THRESHOLD = float(os.environ.get("JFL_ANOMALY_PCT_THRESHOLD", "25"))

KPI_THRESHOLDS = {
    "fatalities":            {"direction": "lower_better",  "red": 1,    "yellow": 0.001},
    "lost time injury":      {"direction": "lower_better",  "red": 3,    "yellow": 1},
    "total recordable accidents": {"direction": "lower_better", "red": 8, "yellow": 4},
    "first aid accident":    {"direction": "lower_better",  "red": 12,   "yellow": 6},
    "near miss":             {"direction": "lower_better",  "red": None, "yellow": None},
    "% of ua/uc closure":    {"direction": "higher_better", "red": 0.70, "yellow": 0.85},
    "safety observation worker involvement % [%]": {"direction": "higher_better", "red": 0.60, "yellow": 0.80},
}
