# data_pipeline.py
"""
Hardened Data Ingestion & Metadata Framework Pipeline Subsystem.
Handles zero-hardcoded auto-discovery of workbook taxonomies.
"""
import os
import re
import json
import logging
from io import BytesIO
from datetime import datetime
import requests
from openpyxl import load_workbook
import config

def get_logger() -> logging.Logger:
    logger = logging.getLogger("jfl_portal")
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))
    try:
        os.makedirs(os.path.dirname(config.LOG_FILE_PATH) or ".", exist_ok=True)
        file_handler = logging.FileHandler(config.LOG_FILE_PATH)
        file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(file_handler)
    except Exception:
        pass
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(stream_handler)
    return logger

def _save_fallback_snapshot(content: bytes, source_url: str):
    try:
        os.makedirs(os.path.dirname(config.FALLBACK_SNAPSHOT_PATH) or ".", exist_ok=True)
        with open(config.FALLBACK_SNAPSHOT_PATH, "wb") as f:
            f.write(content)
        meta = {"fetched_at": datetime.now().strftime("%d %b %Y, %H:%M:%S"), "source_url": source_url}
        with open(config.FALLBACK_META_PATH, "w") as f:
            json.dump(meta, f)
    except Exception as e:
        get_logger().warning(f"Could not persist fallback snapshot: {e}")

def _load_fallback_snapshot():
    try:
        if not (os.path.exists(config.FALLBACK_SNAPSHOT_PATH) and os.path.exists(config.FALLBACK_META_PATH)):
            return None
        with open(config.FALLBACK_SNAPSHOT_PATH, "rb") as f:
            content = f.read()
        with open(config.FALLBACK_META_PATH, "r") as f:
            meta = json.load(f)
        return content, meta
    except Exception as e:
        get_logger().warning(f"Could not load fallback snapshot: {e}")
        return None

def fetch_workbook_hardened(url: str, cache_key: str, _fetch_fn):
    logger = get_logger()
    try:
        content = _fetch_fn(url, cache_key)
        _save_fallback_snapshot(content, url)
        logger.info(f"Workbook successfully streaming live from production endpoint: {url}")
        return content, {
            "source": "live", "fetched_at": datetime.now().strftime("%d %b %Y, %H:%M:%S"),
            "source_url": url, "warning": None,
        }
    except Exception as e:
        logger.error(f"Live pipeline connection drop for endpoint {url}: {e}")
        fallback = _load_fallback_snapshot()
        if fallback is not None:
            content, meta = fallback
            meta = dict(meta)
            meta["warning"] = f"Live source unreachable ({e}). Displaying localized storage backup cache."
            meta["source"] = "fallback"
            logger.warning(meta["warning"])
            return content, meta
        logger.error("No valid local storage snapshot fallback assets located on system cluster storage.")
        raise

def validate_schema(file_bytes: bytes) -> list:
    issues = []
    try:
        wb = load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception as e:
        return [f"Could not open streaming data file buffer: {e}"]
    sheet_names = wb.sheetnames
    for required in config.REQUIRED_SHEETS:
        if required not in sheet_names:
            issues.append(f"Required base database table layer sheet missing from current workbook: '{required}'")
    wb.close()
    return issues

def resolve_latest_file_url(fallback_url: str) -> str:
    if not config.GITHUB_DATA_FOLDER:
        return fallback_url
    logger = get_logger()
    try:
        api_url = config.GITHUB_API_CONTENTS_URL.format(path=config.GITHUB_DATA_FOLDER.strip("/"))
        resp = requests.get(api_url, timeout=15)
        resp.raise_for_status()
        items = resp.json()
        files = [f for f in items if isinstance(f, dict) and f.get("name", "").lower().endswith(".xlsx")]
        latest_pattern = re.compile(config.LATEST_FILENAME_PATTERN, re.IGNORECASE)
        candidates = [f for f in files if latest_pattern.match(f["name"])]
        if not candidates:
            candidates = sorted(files, key=lambda f: f["name"])
        if not candidates:
            return fallback_url
        chosen = candidates[-1]
        return chosen.get("download_url") or fallback_url
    except Exception as e:
        logger.error(f"Auto-detect workflow failed, reverting to default override target: {e}")
        return fallback_url
