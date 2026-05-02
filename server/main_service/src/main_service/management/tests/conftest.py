"""pytest 공통 conftest.

- backend/management/ 모듈 import 가능하도록 sys.path 보강.
- smartcast v2 schema PG fixture 3종 (TaskManager 통합 테스트 backing) 정의.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator

import pytest

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_MGMT_DIR = os.path.dirname(_THIS_DIR)
_BACKEND_DIR = os.path.dirname(_MGMT_DIR)
_SERVER_DIR = os.path.dirname(os.path.dirname(os.path.dirname(_BACKEND_DIR)))

for p in (_MGMT_DIR, _BACKEND_DIR, _SERVER_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)


# ─────────────────────────────────────────────
# smartcast v2 PG fixture 3종 (SPEC-C2 §13 DoD)
#
# 동작:
#   1. session-scope `_smartcast_schema` 가 한 번만 SQLAlchemy create_all 로
#      smartcast schema + 33 테이블 셋업.
#   2. 각 테스트 fixture (`postgresql_*`) 는 직전 TRUNCATE 로 격리, 시드를
#      필요한 만큼만 INSERT.
#
# 전제:
#   - DATABASE_URL 환경변수가 PG 인스턴스 가리킴 (CI service container 또는
#     로컬 docker)
#   - `app.database.Base` + `app.models.*` 가 import 가능 (DATABASE_URL 만 있으면 OK)
# ─────────────────────────────────────────────


@pytest.fixture(scope="session")
def _smartcast_schema() -> Iterator[None]:
    """세션 1회: smartcast schema + 33 테이블 create_all."""
    from sqlalchemy import text

    import smart_cast_db.models  # noqa: F401  populate Base.metadata
    from smart_cast_db.database import Base, engine

    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS smartcast"))
    Base.metadata.create_all(engine)
    yield
    # session teardown 은 생략 (CI ephemeral PG 컨테이너가 통째로 사라짐).


def _truncate_all() -> None:
    """모든 metadata 테이블 TRUNCATE — fixture 격리."""
    from sqlalchemy import text

    from smart_cast_db.database import Base, engine

    with engine.begin() as conn:
        names = ", ".join(t.fullname for t in reversed(Base.metadata.sorted_tables))
        if names:
            conn.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))


def _seed_user_and_res() -> None:
    """공통 시드: customer user_id=1 + PAT res (Item.cur_res / EquipTaskTxn.res_id FK)."""
    from smart_cast_db.database import SessionLocal
    from smart_cast_db.models import Res, UserAccount

    with SessionLocal() as db:
        db.add(
            UserAccount(
                user_id=1,
                co_nm="TEST",
                user_nm="tester",
                role="customer",
                email="test@example.com",
                password="pw",
            )
        )
        db.add(Res(res_id="PAT", res_type="RA", model_nm="TEST-RA"))
        db.commit()


@pytest.fixture
def postgresql_smartcast_empty(_smartcast_schema):
    """빈 schema (ord 없음). user/res 만 시드."""
    _truncate_all()
    _seed_user_and_res()
    yield


@pytest.fixture
def postgresql_with_smartcast_seed(_smartcast_schema):
    """ord_id=42 + Pattern(42, ptn_loc=1) 시드 (happy path)."""
    from smart_cast_db.database import SessionLocal
    from smart_cast_db.models import Ord, Pattern

    _truncate_all()
    _seed_user_and_res()
    with SessionLocal() as db:
        db.add(Ord(ord_id=42, user_id=1))
        db.flush()
        db.add(Pattern(ptn_id=42, ptn_loc=1))
        db.commit()
    yield


@pytest.fixture
def postgresql_ord_without_pattern(_smartcast_schema):
    """ord_id=100 만 (Pattern 없음 → TaskManagerError 검증용)."""
    from smart_cast_db.database import SessionLocal
    from smart_cast_db.models import Ord

    _truncate_all()
    _seed_user_and_res()
    with SessionLocal() as db:
        db.add(Ord(ord_id=100, user_id=1))
        db.commit()
    yield
