from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest


THIS_DIR = Path(__file__).resolve().parent
ROUTES_DIR = THIS_DIR.parent
APP_DIR = ROUTES_DIR.parent
INTERFACE_PKG_ROOT = APP_DIR.parent
SRC_ROOT = INTERFACE_PKG_ROOT.parent
MAIN_SERVICE_ROOT = SRC_ROOT.parent.parent
SERVER_ROOT = MAIN_SERVICE_ROOT.parent

for path in (
    str(INTERFACE_PKG_ROOT),
    str(SRC_ROOT),
    str(MAIN_SERVICE_ROOT),
    str(SERVER_ROOT),
):
    if path not in sys.path:
        sys.path.insert(0, path)


@pytest.fixture(scope="session")
def _smartcast_schema() -> Iterator[None]:
    from sqlalchemy import text

    import smart_cast_db.models  # noqa: F401
    from smart_cast_db.database import Base, engine

    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS smartcast"))
    Base.metadata.create_all(engine)
    yield


def _truncate_all() -> None:
    from sqlalchemy import text

    from smart_cast_db.database import Base, engine

    with engine.begin() as conn:
        names = ", ".join(t.fullname for t in reversed(Base.metadata.sorted_tables))
        if names:
            conn.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture
def postgresql_smartcast_empty(_smartcast_schema):
    _truncate_all()
    yield
