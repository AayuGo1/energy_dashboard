"""
Phase 4 — Centralized configuration for the GNSC KPI Dashboard.

All environment-specific values (GitHub source, cache TTLs, thresholds,
required schema) live here so app.py, data_pipeline.py and kpi_engine.py
never hardcode them. Every value can be overridden via environment
variables at deploy time without touching code.
"""
import os

# =============================================================================
# GitHub source configuration
# =============================================================================
GITHUB_OWNER = os.environ.get("GNSC_GITHUB_OWNER", "AayuGo1")
GITHUB_REPO = os.environ.get("GNSC_GITHUB_REPO", "energy_dashboard")
GITHUB_BRANCH = os.environ.get("GNSC_GITHUB_BRANCH", "main")

# If set, the dashboard auto-detects the "latest" workbook inside this
# GitHub folder (Phase 4 §2 multi-file support). Leave empty ("") to keep
# the current single-file behaviour (100% backward compatible default).
GITHUB_DATA_FOLDER = os.environ.get("GNSC_GITHUB_DATA_FOLDER", "")
LATEST_FILENAME_PATTERN = os.environ.get("GNSC_LATEST_PATTERN", r"^latest.*\.xlsx$")
ARCHIVE_FOLDER_NAME = os.environ.get("GNSC_ARCHIVE_FOLDER", "archive")

# Explicit single-file override (this is the existing GITHUB_RAW_URL from
# Phase 1-3, now sourced from env / config instead of being hardcoded in
# app.py). Used directly when GITHUB_DATA_FOLDER is empty, and used as the
# safety-net fallback URL if folder auto-detection fails for any reason.
GITHUB_RAW_URL_OVERRIDE = os.environ.get(
    "GNSC_GITHUB_RAW_URL",
    "https://raw.githubusercontent.com/AayuGo1/energy_dashboard/main/Monthly%20KPI%20Summary%20Sheet_April_GNSC.xlsx",
)

GITHUB_API_CONTENTS_URL = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{{path}}?ref={GITHUB_BRANCH}"
)

# =============================================================================
# Caching
# =============================================================================
RAW_FILE_CACHE_TTL_SECONDS = int(os.environ.get("GNSC_RAW_CACHE_TTL", "300"))
KPI_CACHE_TTL_SECONDS = int(os.environ.get("GNSC_KPI_CACHE_TTL", "300"))

# Local fallback snapshot: last known-good workbook, used if a live GitHub
# fetch fails (Phase 4 §1). Ephemeral on most PaaS filesystems but persists
# for the lifetime of the running container/session, which is enough to
# survive transient GitHub outages / rate limits.
FALLBACK_SNAPSHOT_PATH = os.environ.get("GNSC_FALLBACK_SNAPSHOT", ".cache/last_good_workbook.bin")
FALLBACK_META_PATH = os.environ.get("GNSC_FALLBACK_META", ".cache/last_good_meta.json")

# =============================================================================
# Application Branding
# =============================================================================
COMPANY_NAME = "Jubilant FoodWorks Limited"
DASHBOARD_TITLE = "Enterprise KPI Analytics Dashboard"
DASHBOARD_TITLE_SUB = "Executive Sustainability & EHS Analytics"
CURRENT_FISCAL_YEAR = "2026"

# =============================================================================
# Required workbook schema (Phase 4 §1 — schema validation)
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
# KPI thresholds for the Risk Panel / alerting (Phase 4 §4)
# =============================================================================
# direction: "higher_better" or "lower_better" (mirrors app.py's HIGHER_IS_BETTER)
# red / yellow: absolute trigger values. Set to None to skip threshold-based
# alerting for that KPI and rely on anomaly (% swing) detection only.
KPI_THRESHOLDS = {
    "fatalities":            {"direction": "lower_better",  "red": 1,    "yellow": 0.001},
    "lti":                   {"direction": "lower_better",  "red": 3,    "yellow": 1},
    "tra":                   {"direction": "lower_better",  "red": 8,    "yellow": 4},
    "first_aid":             {"direction": "lower_better",  "red": 12,   "yellow": 6},
    "near_miss":             {"direction": "lower_better",  "red": None, "yellow": None},
    "uauc_closure_pct":      {"direction": "higher_better", "red": 0.70, "yellow": 0.85},
    "worker_participation":  {"direction": "higher_better", "red": 0.60, "yellow": 0.80},
    "energy_intensity":      {"direction": "lower_better",  "red": None, "yellow": None},
    "water_intensity":       {"direction": "lower_better",  "red": None, "yellow": None},
    "waste_intensity":       {"direction": "lower_better",  "red": None, "yellow": None},
    "production_volume":     {"direction": "higher_better", "red": None, "yellow": None},
}

# Month-over-month % swing that counts as an "anomaly" (spike/drop) worth
# surfacing automatically in the Risk Panel.
ANOMALY_PCT_THRESHOLD = float(os.environ.get("GNSC_ANOMALY_PCT_THRESHOLD", "25"))

# =============================================================================
# Logging (Phase 4 §1 — ingestion error logging)
# =============================================================================
LOG_FILE_PATH = os.environ.get("GNSC_LOG_FILE", ".cache/ingestion.log")
LOG_LEVEL = os.environ.get("GNSC_LOG_LEVEL", "INFO")

# =============================================================================
# Role-based view (Phase 4 §6, optional)
# =============================================================================
VIEW_ROLES = ["EHS Head", "Plant Manager", "Executive"]
DEFAULT_VIEW_ROLE = os.environ.get("GNSC_DEFAULT_ROLE", "EHS Head")
