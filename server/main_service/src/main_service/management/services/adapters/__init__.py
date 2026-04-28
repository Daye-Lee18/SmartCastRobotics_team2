"""HW 통신 어댑터 묶음 (V6 canonical 통신 행렬 준수).

V6 canonical (2026-04-20 Phase D):
- Manufacturing / Stacking / Transport (RPi5/RPi4 ROS2 노드) → ROS2 DDS            → ros2_adapter.py
- HW Control Service (ESP32 컨베이어 등)                    → Jetson 경유 Serial  → jetson_relay_adapter.py
- Image Publishing Service (Jetson)                         → gRPC streaming      → 별도 servicer

이전 (Phase D 이전):
- ESP32 는 MQTT 로 직접 통신 → Phase D 에서 제거됨. canonical 이미지의 "HW Controller ↔ Vision Controller (Serial)" 화살표 준수.

@MX:ANCHOR: robot_id prefix 가 어댑터 선택의 단일 진실. AMR/ARM → ROS2, CONV/ESP → jetson-serial.
@MX:REASON: canonical 화살표 색상(녹색 ROS2 / 주황 TCP / 파랑 Serial) 1:1 매핑 보장.
"""

from __future__ import annotations

from typing import Protocol


class HwAdapter(Protocol):
    """모든 HW 어댑터 공통 인터페이스 — duck typing."""

    name: str

    def dispatch(
        self, item_id: int, robot_id: str, command: str, payload: bytes
    ) -> tuple[bool, str]: ...

    def close(self) -> None: ...


def select_adapter(robot_id: str) -> str:
    """robot_id prefix → 어댑터 이름. 모르면 'unknown'."""
    rid = (robot_id or "").upper()
    if rid.startswith(("CONV-", "ESP-")):
        return "jetson-serial"
    if rid.startswith(("AMR-", "ARM-")):
        return "ros2"
    return "unknown"
