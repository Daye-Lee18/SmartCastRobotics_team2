"""Management Service 용 DB 세션 헬퍼.

Interface Service(backend/app/database.py) 와 동일한 PG 를 공유하지만 별도 프로세스이므로
독립 engine 을 만든다. 같은 .env.local 을 읽어 DATABASE_URL 을 가져온다.

@MX:NOTE: SQLAlchemy 세션은 thread-local. gRPC ThreadPoolExecutor 워커마다 SessionLocal()
        로 만들어 with-style 로 사용한다. 글로벌 단일 세션 공유 금지.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# backend/ 디렉터리를 sys.path 에 추가 (app.models, app.database 의 _load_env_local 재사용)
_THIS_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _THIS_DIR.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.database import _load_env_local  # noqa: E402

_load_env_local()

DATABASE_URL: str | None = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Management Service: DATABASE_URL 미설정. backend/.env.local 확인.")
if DATABASE_URL.startswith("sqlite"):
    raise RuntimeError("SQLite 미지원 (V6 정책 2026-04-14).")


def _build_engine(url: str) -> Engine:
    return create_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=False,
    )


engine: Engine = _build_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session() -> Generator[Session, None, None]:
    """Context manager 용. with get_session() as db: ..."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
