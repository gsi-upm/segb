"""Centralized runtime settings for the backend service."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SharedContextSettings:
    namespace: str
    time_window_seconds: float
    match_threshold: float
    ambiguous_threshold: float
    close_score_margin: float


@dataclass(slots=True)
class BackendSettings:
    log_level: str
    log_file: str
    version: str
    api_info_file: str
    api_description_file: str
    max_startup_retries: int
    max_backoff_seconds: int
    runtime_ping_interval: int
    cors_origins: tuple[str, ...]
    shared_context: SharedContextSettings


def load_settings() -> BackendSettings:
    return BackendSettings(
        log_level=os.getenv("LOGGING_LEVEL", "INFO").upper(),
        log_file=os.getenv("SERVER_LOG_FILE", "segb.log"),
        version=os.getenv("VERSION") or "stable",
        api_info_file=os.getenv("DESCRIPTION_FILE_PATH", "./api_info.json"),
        api_description_file="./api_description.md",
        max_startup_retries=int(os.getenv("MAX_STARTUP_RETRIES", "6")),
        max_backoff_seconds=int(os.getenv("MAX_BACKOFF_SECONDS", "16")),
        runtime_ping_interval=int(os.getenv("RUNTIME_PING_INTERVAL", "5")),
        cors_origins=("http://localhost:5173", "http://127.0.0.1:5173"),
        shared_context=SharedContextSettings(
            namespace=os.getenv("SHARED_CONTEXT_NAMESPACE", "https://gsi.upm.es/segb/shared-context/"),
            time_window_seconds=float(os.getenv("SHARED_CONTEXT_TIME_WINDOW_SECONDS", "3.0")),
            match_threshold=float(os.getenv("SHARED_CONTEXT_MATCH_THRESHOLD", "0.85")),
            ambiguous_threshold=float(os.getenv("SHARED_CONTEXT_AMBIGUOUS_THRESHOLD", "0.70")),
            close_score_margin=float(os.getenv("SHARED_CONTEXT_CLOSE_MARGIN", "0.05")),
        ),
    )


def load_api_info(path: str) -> dict:
    default_info = {
        "title": "SEGB",
        "contact": {
            "name": "GSI-UPM",
            "url": "https://www.gsi.upm.es",
            "email": "gsi@autolistas.upm.es",
        },
        "license": {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
    }
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default_info


def load_api_description(path: str) -> str:
    fallback = "Semantic Ethical Glass Box (SEGB) API. See <https://segb.readthedocs.io/en/latest/>."
    file_path = Path(path)
    if not file_path.exists():
        return fallback
    try:
        return file_path.read_text(encoding="utf-8")
    except Exception:
        return fallback
