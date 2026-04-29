"""adapters.select_adapter() prefix 라우터 단위 테스트.

V6 통신 행렬 준수 검증 (Phase D-1/D-2 이후, 2026-04-20):
- AMR-* / ARM-* → ros2 어댑터
- CONV-* / ESP-* → jetson-serial 어댑터 (구 MQTT 경로는 V6 canonical 에서 제거)
- 그 외 → unknown
"""

import pytest
from services.adapters import select_adapter


@pytest.mark.parametrize(
    "robot_id, expected",
    [
        # ROS2 (AMR/Cobot)
        ("AMR-001", "ros2"),
        ("AMR-002", "ros2"),
        ("amr-001", "ros2"),  # case insensitive
        ("ARM-001", "ros2"),
        ("ARM-LEFT", "ros2"),
        # Jetson Serial (ESP32) — V6 canonical
        ("CONV-001", "jetson-serial"),
        ("CONV-CONVEYOR-MAIN", "jetson-serial"),
        ("ESP-001", "jetson-serial"),
        ("esp-002", "jetson-serial"),
        # Unknown
        ("ROBOT-001", "unknown"),
        ("UNKNOWN-X", "unknown"),
        ("CAMERA-01", "unknown"),
        ("", "unknown"),
    ],
)
def test_select_adapter_routing(robot_id, expected):
    assert select_adapter(robot_id) == expected


def test_v6_communication_matrix_no_overlap():
    """ROS2 와 Jetson Serial 채널이 동일 robot_id 로 겹치지 않음 검증."""
    samples = ["AMR-001", "ARM-001", "CONV-001", "ESP-001"]
    routes = {select_adapter(r) for r in samples}
    # 정확히 2개 채널만 사용
    assert routes == {"ros2", "jetson-serial"}
