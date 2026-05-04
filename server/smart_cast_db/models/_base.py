"""SQLAlchemy 모델 공통 베이스와 공용 import."""

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
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship, synonym

from smart_cast_db.database import Base

SCHEMA = _os.environ.get("SMARTCAST_SCHEMA", "smartcast").strip() or "smartcast"


__all__ = [
    "Base",
    "SCHEMA",
    "BigInteger",
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
    "Text",
    "UniqueConstraint",
    "func",
    "relationship",
    "synonym",
]
