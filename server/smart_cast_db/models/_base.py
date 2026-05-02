"""SQLAlchemy 모델 공통 베이스 — SCHEMA 상수 + 공통 import.

다른 모델 파일이 `from ._base import Base, SCHEMA, ...` 로 import.

2026-04-27: backend/app/models/models.py (553 LOC) 분할 산출. 모든 ORM
클래스가 같은 metadata 를 공유하도록 단일 Base 사용.
"""

from __future__ import annotations

import os as _os

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from smart_cast_db.database import Base

# 모든 신규 테이블이 사용할 schema.
# 기본은 로컬 smartcast_robotics 의 'smartcast' 스키마.
# 환경변수 SMARTCAST_SCHEMA 로 'public' 등 다른 스키마 (예: AWS RDS Casting) 사용 가능.
SCHEMA = _os.environ.get("SMARTCAST_SCHEMA", "smartcast").strip() or "smartcast"


__all__ = [
    "Base",
    "SCHEMA",
    "Boolean",
    "CheckConstraint",
    "Column",
    "Date",
    "DateTime",
    "ForeignKey",
    "Index",
    "Integer",
    "Numeric",
    "String",
    "UniqueConstraint",
    "func",
    "relationship",
    "BigInteger",
]
