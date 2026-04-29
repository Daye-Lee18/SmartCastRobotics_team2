"""Database engine and session factory.

PostgreSQL 16 + TimescaleDB 전용. SQLite 폴백은 2026-04-14 부로 완전 제거됨.
운영/개발 모두 동일 PG (Tailscale 100.107.120.14:5432, db=smartcast_robotics, role=team2)
를 사용한다.

환경 변수:
    DATABASE_URL - 필수. 예: "postgresql+psycopg://user:pass@host:5432/dbname"
                   미설정 시 RuntimeError 로 즉시 실패한다.

@MX:ANCHOR: PG 단일 DB 정책 (V6 아키텍처 결정 2026-04-14)
@MX:REASON: SPOF 가정 단순화 + Interface/Management 두 서비스 간 데이터 일관성 보장.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_env_local() -> None:
    """backend/.env.local 파일이 있으면 단순 KEY=VALUE 를 os.environ 에 주입.

    python-dotenv 의존성 없이 stdlib 로 처리. 이미 환경변수가 설정되어 있으면 덮어쓰지 않는다.
    """
    env_path = Path(BASE_DIR) / ".env.local"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_local()

DATABASE_URL: str | None = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL 환경변수가 설정되지 않았습니다. "
        "backend/.env.local 에 PostgreSQL 연결 문자열을 설정하세요. "
        "예: DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname"
    )
if DATABASE_URL.startswith("sqlite"):
    raise RuntimeError(
        "SQLite 는 더 이상 지원되지 않습니다 (2026-04-14). "
        "PostgreSQL 연결 문자열을 사용하세요: postgresql+psycopg://..."
    )


def _build_engine(url: str) -> Engine:
    """Create SQLAlchemy engine for PostgreSQL with connection pooling."""
    return create_engine(
        url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=False,
    )


engine: Engine = _build_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: provide a database session per-request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
