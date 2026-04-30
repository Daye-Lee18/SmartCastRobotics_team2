"""Runtime configuration for the Factory Operator PyQt app."""

from __future__ import annotations

import os


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


APP_NAME = os.environ.get("APP_NAME", "SmartCast Factory Operator")
APP_VERSION = os.environ.get("APP_VERSION", "3.4.0")

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

REFRESH_INTERVAL_MS = _int_env("REFRESH_INTERVAL_MS", 3000)
AMR_POLL_INTERVAL = _float_env("AMR_POLL_INTERVAL", 10.0)
