"""AMR telemetry/handoff cache.

정교한 운송 상태 전이 엔진 대신 최소 런타임 캐시 역할만 유지한다.
- AMR별 상태/작업 메타데이터 캐시
- handoff ACK 수신 시 best-effort release
- legacy 호출부 호환용 transition()/force_reset()
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import IntEnum

logger = logging.getLogger(__name__)


class TaskState(IntEnum):
    """Proto AmrTaskState enum 과 1:1 매핑."""

    UNSPECIFIED = 0
    IDLE = 1
    MOVE_TO_SOURCE = 2
    AT_SOURCE = 3
    LOADING = 4
    LOAD_COMPLETED = 5
    MOVE_TO_DEST = 6
    AT_DESTINATION = 7
    UNLOADING = 8
    UNLOAD_COMPLETED = 9
    FAILED = 10


# display label (한국어)
TASK_STATE_LABELS: dict[TaskState, str] = {
    TaskState.UNSPECIFIED: "-",
    TaskState.IDLE: "대기",
    TaskState.MOVE_TO_SOURCE: "출발지 이동",
    TaskState.AT_SOURCE: "출발지 도착",
    TaskState.LOADING: "상차",
    TaskState.LOAD_COMPLETED: "상차 완료",
    TaskState.MOVE_TO_DEST: "도착지 이동",
    TaskState.AT_DESTINATION: "도착지 도착",
    TaskState.UNLOADING: "하차중",
    TaskState.UNLOAD_COMPLETED: "하차 완료",
    TaskState.FAILED: "실패",
}


@dataclass
class AmrContext:
    """AMR 한 대의 운송 상태 컨텍스트."""

    state: TaskState = TaskState.IDLE
    task_id: str = ""
    loaded_item: str = ""
    updated_at: float = field(default_factory=time.monotonic)


class AmrStateMachine:
    """AMR fleet 최소 캐시. Thread-safe."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._robots: dict[str, AmrContext] = {}

    def register(self, robot_id: str) -> None:
        """AMR 등록. 이미 등록된 경우 무시."""
        with self._lock:
            if robot_id not in self._robots:
                self._robots[robot_id] = AmrContext()
                logger.info("AmrStateMachine: %s 등록 (IDLE)", robot_id)

    def get(self, robot_id: str) -> AmrContext:
        """현재 상태 조회. 미등록 시 기본 IDLE 반환."""
        with self._lock:
            return self._robots.get(robot_id, AmrContext())

    def get_all(self) -> dict[str, AmrContext]:
        """전체 AMR 상태 스냅샷."""
        with self._lock:
            return dict(self._robots)

    def transition(
        self,
        robot_id: str,
        new_state: TaskState,
        task_id: str | None = None,
        loaded_item: str | None = None,
    ) -> bool:
        """Legacy compatibility: validation 없이 cache 를 갱신한다."""
        with self._lock:
            ctx = self._robots.get(robot_id)
            if ctx is None:
                ctx = AmrContext()
                self._robots[robot_id] = ctx

            old = ctx.state.name
            ctx.state = new_state
            ctx.updated_at = time.monotonic()

            if task_id is not None:
                ctx.task_id = task_id
            if loaded_item is not None:
                ctx.loaded_item = loaded_item

            if new_state in (TaskState.IDLE, TaskState.UNLOAD_COMPLETED):
                ctx.task_id = ""
                ctx.loaded_item = ""

            logger.info(
                "AmrStateMachine(cache): %s %s → %s (task=%s, item=%s)",
                robot_id,
                old,
                new_state.name,
                ctx.task_id,
                ctx.loaded_item,
            )
            return True

    def confirm_handoff(self, robot_id: str) -> tuple[bool, str]:
        """후처리존 handoff ACK 수신 시 best-effort release."""
        with self._lock:
            ctx = self._robots.get(robot_id)
            if ctx is None:
                ctx = AmrContext()
                self._robots[robot_id] = ctx

            old = ctx.state.name
            ctx.state = TaskState.IDLE
            ctx.task_id = ""
            ctx.loaded_item = ""
            ctx.updated_at = time.monotonic()
            logger.info("confirm_handoff: %s %s → IDLE", robot_id, old)
            return True, "released"

    def find_waiting_amr_at_zone(self, zone: str) -> str | None:
        """주어진 zone 에서 대기 중인 AMR 탐색용 legacy helper."""
        with self._lock:
            candidates = [
                (rid, ctx.updated_at)
                for rid, ctx in self._robots.items()
                if ctx.state not in (TaskState.IDLE, TaskState.UNSPECIFIED)
            ]
            if not candidates:
                return None
            candidates.sort(key=lambda x: x[1])
            return candidates[0][0]

    def force_reset(self, robot_id: str) -> None:
        """강제 IDLE 리셋."""
        with self._lock:
            ctx = self._robots.get(robot_id)
            if ctx is not None:
                old = ctx.state.name
                ctx.state = TaskState.IDLE
                ctx.task_id = ""
                ctx.loaded_item = ""
                ctx.updated_at = time.monotonic()
                logger.warning("AmrStateMachine: %s 리셋 %s → IDLE", robot_id, old)
