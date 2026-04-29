"""SPEC-C2 §12.1 — TaskManager smartcast v2 단위 테스트.

PG fixture 로 격리 실행. SQLite/in-memory 금지 (2026-04-14 policy).

DoD (Phase C-2 §13):
- conftest.py 의 PG fixture 3종 (`postgresql_*`) 사용 — SQLAlchemy create_all
  + TRUNCATE 격리 + seed.
- DATABASE_URL 환경변수가 ephemeral PG 컨테이너 가리킴 (CI service container
  또는 로컬 docker).

@MX:NOTE: 본 파일의 happy/error path 6 케이스가 모두 통과해야 SPEC-C2 §13 만족.
"""

from __future__ import annotations

import pytest
from services.core.task_manager import StartProductionResult, TaskManager, TaskManagerError


@pytest.fixture
def task_manager() -> TaskManager:
    return TaskManager()


# ---------- 실패 경로 (PG 불필요) ----------


def test_start_production_single_zero_raises(task_manager):
    with pytest.raises(TaskManagerError, match="invalid ord_id"):
        task_manager.start_production_single(0)


def test_start_production_single_negative_raises(task_manager):
    with pytest.raises(TaskManagerError, match="invalid ord_id"):
        task_manager.start_production_single(-1)


def test_start_production_batch_empty_iter(task_manager):
    assert task_manager.start_production_batch([]) == []


def test_start_production_batch_all_invalid_skipped(task_manager):
    # "abc", "" 모두 int 변환 실패 → skip → 빈 리스트
    assert task_manager.start_production_batch(["abc", ""]) == []


# ---------- 해피 경로 (PG fixture 필요) ----------


def test_start_production_single_happy(task_manager, postgresql_with_smartcast_seed):
    """정상 흐름: Ord+Pattern 등록 후 task_manager 호출 → OrdStat/Item/EquipTaskTxn 3건 INSERT."""
    ord_id = 42
    result = task_manager.start_production_single(ord_id)
    assert isinstance(result, StartProductionResult)
    assert result.ord_id == ord_id
    assert result.item_id > 0
    assert result.equip_task_txn_id > 0
    assert "RA1/MM" in result.message


def test_start_production_single_ord_not_found(task_manager, postgresql_smartcast_empty):
    with pytest.raises(TaskManagerError, match="not found"):
        task_manager.start_production_single(999999)


def test_start_production_single_pattern_missing(task_manager, postgresql_ord_without_pattern):
    with pytest.raises(TaskManagerError, match="pattern for ord_id=.* not registered"):
        task_manager.start_production_single(100)
