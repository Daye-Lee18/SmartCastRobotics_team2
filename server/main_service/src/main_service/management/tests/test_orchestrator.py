import asyncio
from dataclasses import dataclass
from unittest.mock import AsyncMock, Mock

import pytest

from main_service.management.services.core.orchestrator import Orchestrator


@dataclass(frozen=True)
class _StartResult:
    ord_id: int
    item_id: int
    equip_task_txn_id: int
    message: str


def test_orchestrator_initialization():
    """테스트 시나리오 0: Orchestrator가 정상적으로 초기화되는가?"""
    mock_bridge = Mock()
    mock_manager = Mock()
    mock_allocator = Mock()

    orchestrator = Orchestrator(
        event_bridge=mock_bridge,
        task_manager=mock_manager,
        task_allocator=mock_allocator,
    )
    
    assert orchestrator.event_bridge == mock_bridge
    assert orchestrator.task_manager == mock_manager
    assert orchestrator.task_allocator == mock_allocator


@pytest.mark.asyncio
async def test_async_start_production_triggers_event():
    """비동기 루프 내에서 단건 큐 등록이 TaskManager 로 위임되는가?"""
    mock_bridge = Mock()
    mock_manager = Mock()
    mock_allocator = Mock()
    mock_manager.start_production_single.return_value = _StartResult(999, 10, 20, "queued")

    orchestrator = Orchestrator(
        event_bridge=mock_bridge,
        task_manager=mock_manager,
        task_allocator=mock_allocator,
    )

    ord_id = 999
    result = await orchestrator._async_start_production(ord_id)

    assert result.ord_id == 999
    mock_manager.start_production_single.assert_called_once_with(ord_id)


@pytest.mark.asyncio
async def test_async_start_production_batch_delegates_to_task_manager() -> None:
    mock_bridge = Mock()
    mock_manager = Mock()
    mock_allocator = Mock()
    mock_manager.start_production_batch.return_value = [
        _StartResult(42, 100, 200, "queued"),
        _StartResult(43, 101, 201, "queued"),
    ]

    orchestrator = Orchestrator(
        event_bridge=mock_bridge,
        task_manager=mock_manager,
        task_allocator=mock_allocator,
    )

    result = await orchestrator._async_start_production_batch(["42", "43"])

    assert [r.ord_id for r in result] == [42, 43]
    mock_manager.start_production_batch.assert_called_once_with(["42", "43"])


def test_start_production_schedules_coroutine():
    """루프가 없으면 명시적으로 실패시킨다."""
    orchestrator = Orchestrator(Mock(), Mock(), Mock())

    orchestrator._loop = None
    with pytest.raises(RuntimeError):
        orchestrator.start_production(999)
