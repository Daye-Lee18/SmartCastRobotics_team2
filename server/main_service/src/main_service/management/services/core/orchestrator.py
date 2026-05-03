"""Event-driven orchestrator for Management production start flows."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.core.event_bridge import EventBridge
    from services.core.task_allocator import TaskAllocator
    from services.core.task_manager import TaskManager
    from services.core.contracts.protocols import IStateManager
    from services.core.contracts.models import StartProductionBatchAckModel, StartProductionOrderAckModel

logger = logging.getLogger(__name__)


class Orchestrator:
    """Coordinates production-start entrypoints onto one async control plane."""

    def __init__(
        self,
        event_bridge: EventBridge,
        task_manager: TaskManager,
        task_allocator: TaskAllocator,
        state_manager: IStateManager,
    ) -> None:
        self.event_bridge = event_bridge
        self.task_manager = task_manager
        self.task_allocator = task_allocator
        self.state_manager = state_manager
        self._loop: asyncio.AbstractEventLoop | None = None

    def start_production(self, order_ids: list[int]) -> "StartProductionBatchAckModel":
        """Sync entrypoint for unified production starts."""
        return self._run_sync(self._async_start_production(order_ids))

    def _run_sync(self, coro):
        if self._loop is None:
            logger.error("Orchestrator loop is not running. Cannot handle request.")
            raise RuntimeError("Orchestrator 루프가 꺼져있습니다.")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=5.0)

    async def _async_start_production(self, order_ids: list[int]) -> "StartProductionBatchAckModel":
        """Create the initial production queue records for the given orders via StateManager."""
        logger.info("[Async] 통합 생산 큐 등록 시작: order_ids=%s", order_ids)
        results: list[StartProductionOrderAckModel] = []
        accepted = 0
        rejected = 0

        for ord_id in order_ids:
            try:
                result = await asyncio.to_thread(self.state_manager.start_production, ord_id)
            except Exception as exc:
                logger.warning("[Async] 생산 큐 등록 실패: ord_id=%s reason=%s", ord_id, exc)
                result = self._build_rejected_ack(ord_id, str(exc))
            if result.accepted:
                accepted += 1
            else:
                rejected += 1
            results.append(result)

        batch_result = self._build_batch_ack(order_ids, results, accepted, rejected)
        logger.info(
            "[Async] 통합 생산 큐 등록 완료: requested=%d, accepted=%d",
            batch_result.requested_count,
            batch_result.accepted_count,
        )
        return batch_result

    def _build_rejected_ack(self, ord_id: int, reason: str) -> "StartProductionOrderAckModel":
        from .contracts.models import StartProductionOrderAckModel

        return StartProductionOrderAckModel(
            ord_id=ord_id,
            accepted=False,
            reason=reason,
        )

    def _build_batch_ack(
        self,
        order_ids: list[int],
        results: list["StartProductionOrderAckModel"],
        accepted: int,
        rejected: int,
    ) -> "StartProductionBatchAckModel":
        from .contracts.models import StartProductionBatchAckModel

        return StartProductionBatchAckModel(
            requested_count=len(order_ids),
            accepted_count=accepted,
            rejected_count=rejected,
            orders=results,
            message="DB-backed start_production completed." if accepted else "No orders were accepted.",
        )

    def on_task_completed(self, event) -> None:
        """TASK_COMPLETED event handler."""
        pass

    async def run_loop(self) -> None:
        """Background async loop that owns the orchestrator event loop."""
        self._loop = asyncio.get_running_loop()
        logger.info("Orchestrator 비동기 이벤트 루프 시작됨.")
        try:
            while True:
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            logger.info("Orchestrator 루프가 종료되었습니다.")
