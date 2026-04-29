"""Management → Jetson conveyor command queue (V6 canonical Phase D).

robot_executor 가 ESP32 (CONV-* / ESP-*) 명령을 발사하면 본 큐에 enqueue 되고,
Jetson(Vision Controller) 이 gRPC WatchConveyorCommands 스트림으로 수신해 Serial 로 relay.

설계 원칙:
- In-memory. Management 프로세스 재시작 시 모든 pending 명령은 휘발.
  (운영에서 중요 명령은 ExecuteCommand RPC 응답을 caller 가 확인 후 재송신.)
- 구독자(=Jetson) 다중 연결 지원하지만 **1 command → 1 consumer** (round-robin) 으로 단일 전달.
- robot_id_filter 로 특정 컨베이어만 구독 가능 (현재는 단일 Jetson 가정 → 전역 구독이 일반적).
- threading.Condition 기반 blocking wait — gRPC ThreadPoolExecutor 에 친화적.

@MX:ANCHOR: V6 Phase D 의 핵심 중계 자료구조. 다중 Jetson / 다중 라인 확장 시 본 모듈만 교체.
@MX:WARN: 메모리 누수 방지 위해 MAX_QUEUE 초과 시 oldest drop + warning 로그.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 큐 최대 크기. 초과 시 oldest 부터 drop.
MAX_QUEUE = 1024


@dataclass
class ConveyorCmd:
    """Management → Jetson 으로 relay 될 단일 명령."""

    robot_id: str
    command: str
    payload: bytes = b""
    item_id: int = 0
    issued_at_iso: str = ""
    issued_by: str = "management.robot_executor"
    enqueued_at_mono: float = field(default_factory=time.monotonic)


class ConveyorCommandQueue:
    """Thread-safe FIFO + Condition 기반 blocking drain."""

    def __init__(self) -> None:
        self._queue: deque[ConveyorCmd] = deque()
        self._cond = threading.Condition()
        self._closed = False

    def enqueue(self, cmd: ConveyorCmd) -> None:
        """명령 추가. MAX_QUEUE 초과 시 oldest 1건 drop."""
        with self._cond:
            if self._closed:
                logger.warning(
                    "ConveyorCommandQueue closed — drop %s/%s", cmd.robot_id, cmd.command
                )
                return
            if len(self._queue) >= MAX_QUEUE:
                dropped = self._queue.popleft()
                logger.warning(
                    "ConveyorCommandQueue overflow — drop oldest %s/%s",
                    dropped.robot_id,
                    dropped.command,
                )
            self._queue.append(cmd)
            self._cond.notify()  # 1 consumer wakeup

    def wait_next(self, robot_id_filter: str | None, timeout: float = 10.0) -> ConveyorCmd | None:
        """필터와 매칭되는 다음 명령 반환. 없으면 timeout 초 대기 후 None.

        filter 가 비어있으면 모든 robot_id 수신.
        다른 filter 와 매칭되는 명령이 있으면 건너뛴다 (다른 구독자 용).
        """
        deadline = time.monotonic() + timeout
        with self._cond:
            while not self._closed:
                # 매칭되는 첫 명령 pop (없으면 건너뛸 뿐, 큐에서 제거 X)
                idx = self._find_match_idx(robot_id_filter)
                if idx is not None:
                    return self._pop_at(idx)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._cond.wait(remaining)
        return None

    def _find_match_idx(self, robot_id_filter: str | None) -> int | None:
        if not robot_id_filter:
            return 0 if self._queue else None
        f = robot_id_filter.upper()
        for i, cmd in enumerate(self._queue):
            if cmd.robot_id.upper() == f:
                return i
        return None

    def _pop_at(self, idx: int) -> ConveyorCmd:
        if idx == 0:
            return self._queue.popleft()
        cmd = self._queue[idx]
        del self._queue[idx]
        return cmd

    def close(self) -> None:
        """모든 구독자 깨우고 신규 enqueue 차단."""
        with self._cond:
            self._closed = True
            self._cond.notify_all()

    def size(self) -> int:
        with self._cond:
            return len(self._queue)


# 프로세스 전역 큐 (server.py 부팅 시 1회 생성되어 공유)
queue: ConveyorCommandQueue = ConveyorCommandQueue()
