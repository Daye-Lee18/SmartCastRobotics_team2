"""Compatibility shim for the shared DB package.

실제 DB 엔트리포인트는 `server/smart_cast_db/database.py` 로 이동했다.
기존 `app.database` import 는 당분간 유지한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SERVER_DIR = str(Path(__file__).resolve().parents[4])

if _SERVER_DIR not in sys.path:
    sys.path.insert(0, _SERVER_DIR)

from smart_cast_db.database import Base, DATABASE_URL, SessionLocal, engine, get_db

__all__ = [
    "Base",
    "DATABASE_URL",
    "SessionLocal",
    "engine",
    "get_db",
]
