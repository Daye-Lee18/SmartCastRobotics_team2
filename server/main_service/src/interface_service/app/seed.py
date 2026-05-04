"""smartcast startup seed runner.

Interface startup should use the same master seed source of truth as the DB
scripts. This module therefore executes server/smart_cast_db/seed/seed_master.sql
directly instead of maintaining a partial ORM duplicate.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session


_SEED_SQL_PATH = (
    Path(__file__).resolve().parents[4] / "smart_cast_db" / "seed" / "seed_master.sql"
)


def seed_database(db: Session) -> None:
    """Execute the canonical smartcast master seed SQL."""
    sql = _load_master_seed_sql()
    engine = db.get_bind()
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cursor:
            cursor.execute("SET search_path TO smartcast")
            cursor.execute(sql)
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()


def _load_master_seed_sql() -> str:
    if not _SEED_SQL_PATH.exists():
        raise FileNotFoundError(f"master seed SQL not found: {_SEED_SQL_PATH}")
    return _SEED_SQL_PATH.read_text(encoding="utf-8")
