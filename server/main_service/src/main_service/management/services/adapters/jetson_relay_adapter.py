"""Jetson Serial relay 어댑터 — ESP32 (HW Controller) 전용 (V6 canonical Phase D).

canonical 통신 매트릭스 (2026-04-20 합의):
  Management Service --gRPC (TCP)--> Jetson (Vision Controller) --Serial 115200--> ESP32 (HW Controller)

본 어댑터는 Management 측 dispatch 만 담당: 명령을 ConveyorCommandQueue 에 enqueue.
Jetson 이 WatchConveyorCommands server streaming 으로 수신해 EspBridge 로 Serial 송신.

robot_id prefix:
  CONV-*  → 컨베이어 모터 제어
  ESP-*   → ESP32 기타 주변기기 (버튼 패널 등)

MQTT 경로는 Phase D 에서 제거됨 (`mqtt_adapter.py` 삭제).

@MX:ANCHOR: ExecuteCommand 의 ESP32 경로 단일 진입. Jetson 측 subscriber 실패 시 enqueue 자체는 성공하나 명령은 큐에 쌓임.
@MX:WARN: Management 재시작 시 queue 휘발. 중요 명령은 caller 가 ACK 확인 후 재송신.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from services.command_queue import ConveyorCmd, queue as _queue

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class JetsonRelayAdapter:
    """ESP32 명령을 Jetson 경유 Serial 로 relay (enqueue only, 동기 ACK 없음)."""

    name = "jetson-serial"

    def __init__(self) -> None:
        # 상태 없음. 큐는 프로세스 전역 싱글톤.
        pass

    def dispatch(
        self,
        item_id: int,
        robot_id: str,
        command: str,
        payload: bytes,
    ) -> tuple[bool, str]:
        if not robot_id:
            return (False, "robot_id 비어있음")
        if not command:
            return (False, "command 비어있음")

        cmd = ConveyorCmd(
            robot_id=robot_id,
            command=command,
            payload=payload or b"",
            item_id=item_id or 0,
            issued_at_iso=_now_iso(),
            issued_by="management.robot_executor",
        )
        _queue.enqueue(cmd)
        qsize = _queue.size()
        logger.info(
            "JetsonRelayAdapter enqueue %s/%s item=%s (qsize=%d)",
            robot_id,
            command,
            item_id,
            qsize,
        )
        return (
            True,
            f"jetson_relay_queued {robot_id}/{command} qsize={qsize}",
        )

    def close(self) -> None:
        # 큐는 별도 수명주기 (server.py 가 관리). 여기서는 no-op.
        pass
