"""Logging utilities for backend bootstrap."""

from __future__ import annotations

import logging
import os
from pathlib import Path


def configure_server_logger(*, name: str, level: str, log_file: str) -> logging.Logger:
    """Creates one file+stream logger and avoids duplicate handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    logs_dir = Path("/logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s -> %(message)s", "%Y-%m-%d %H:%M:%S")

    file_handler = logging.FileHandler(logs_dir / log_file, mode="a", encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger
