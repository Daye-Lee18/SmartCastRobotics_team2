"""Robot Executor — robot_id prefix 기반 어댑터 라우터.

V6 canonical 통신 행렬 (2026-04-20 Phase D):
- AMR-* / ARM-*  → ros2_adapter          (Manufacturing/Stacking/Transport ROS2 노드)
- CONV-* / ESP-* → jetson_relay_adapter  (Jetson 경유 Serial 로 ESP32 HW Control 에 relay)
- 그 외          → unknown (NotImplemented 반환)

본 모듈은 비즈니스 로직 없이 어댑터 dispatch 만 수행. 실제 wire 는 adapters/ 참고.
MQTT 경로는 Phase D 에서 제거됨.

@MX:ANCHOR: ExecuteCommand RPC 의 단일 진입점. 어댑터 추가 시 본 파일만 수정.
"""

from __future__ import annotations

import logging
from typing import Any

from .adapters import select_adapter
from .adapters.jetson_relay_adapter import JetsonRelayAdapter
from .adapters.ros2_adapter import Ros2Adapter

logger = logging.getLogger(__name__)


class RobotExecutor:
    """robot_id 별 어댑터 라우팅. 어댑터는 1회 초기화 후 재사용."""

    def __init__(self, state_machine: Any = None) -> None:
        self._ros2 = Ros2Adapter()
        self._jetson = JetsonRelayAdapter()
        self._state_machine = state_machine

    def dispatch(
        self,
        item_id: int,
        robot_id: str,
        command: str,
        payload: bytes,
    ) -> tuple[bool, str]:
        adapter_name = select_adapter(robot_id)
        if adapter_name == "ros2":
            return self._ros2.dispatch(
                item_id,
                robot_id,
                command,
                payload,
                state_machine=self._state_machine,
            )
        if adapter_name == "jetson-serial":
            return self._jetson.dispatch(item_id, robot_id, command, payload)
        return (
            False,
            f"unknown_robot_prefix: '{robot_id}' — V6 canonical 채널 매핑 없음. "
            "AMR-/ARM- (ROS2) 또는 CONV-/ESP- (Jetson Serial) 사용.",
        )

    def close(self) -> None:
        try:
            self._ros2.close()
        finally:
            self._jetson.close()
