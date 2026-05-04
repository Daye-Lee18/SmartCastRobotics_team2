"""ROS2 어댑터 — Manufacturing / Stacking / Transport Service 지령.

V6 정책 (2026-04-14):
- Server ↔ HW(RPi5/RPi4) 의 정식 채널은 ROS2 DDS
- 개발/배포 모두 Ubuntu 24.04 + ROS2 Jazzy 환경

활성화 방법:
1. `sudo apt install ros-jazzy-rclpy ros-jazzy-geometry-msgs ros-jazzy-nav2-msgs`
2. management Python venv 에 시스템 site-packages 사용 또는 source workspace
3. `MGMT_ROS2_ENABLED=1` 환경변수 설정

토픽/액션 표준:
- AMR navigate:  /{robot_id}/nav_goal  (std_msgs/String, JSON)
                 → RPi amr_executor 가 Nav2 NavigateToPose Action 으로 변환
- AMR cmd:       /{robot_id}/cmd       (std_msgs/String, JSON)
                 → pick/place/charge 등 범용 명령

Command 종류:
- navigate  → nav_goal 토픽 publish
- pick      → cmd 토픽 publish
- place     → cmd 토픽 publish
- charge    → nav_goal(HOME)

@MX:WARN: import rclpy 는 lazy. 모듈 로드 시점 충돌 회피.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any

logger = logging.getLogger(__name__)

ROS2_ENABLED = os.environ.get("MGMT_ROS2_ENABLED", "0") in ("1", "true", "yes")

# command → nav_goal 토픽 사용 여부
_NAV_COMMANDS = {"navigate", "charge"}


class Ros2Adapter:
    """ROS2 publisher/action 어댑터.

    MGMT_ROS2_ENABLED=1 설정 시 rclpy 를 init 하고 DDS 통신 활성화.
    ROS2 미활성 시에는 no-op accepted 로 테스트/시뮬레이션을 허용한다.
    """

    name = "ros2"

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._rclpy = None  # type: ignore[var-annotated]
        self._node: Any = None
        self._publishers: dict[str, Any] = {}  # topic → Publisher

        if ROS2_ENABLED:
            self._init_rclpy()
        else:
            logger.info("Ros2Adapter: MGMT_ROS2_ENABLED 미설정 — no-op dispatch 모드.")

    def _init_rclpy(self) -> None:
        try:
            import rclpy  # type: ignore[import-not-found]
            from rclpy.node import Node  # type: ignore[import-not-found]

            rclpy.init(args=None)
            self._rclpy = rclpy
            self._node = Node("casting_management_executor")
            logger.info("Ros2Adapter: rclpy 초기화 완료 (node=casting_management_executor)")
        except Exception as exc:  # noqa: BLE001
            logger.error("Ros2Adapter: rclpy 초기화 실패: %s", exc)
            self._rclpy = None

    def dispatch(
        self,
        item_id: int,
        robot_id: str,
        command: str,
        payload: bytes,
        state_machine: Any = None,
    ) -> tuple[bool, str]:
        """command 별 라우팅.

        state_machine 파라미터는 legacy compatibility 용으로만 남겨두며 사용하지 않는다.
        """

        payload_str = payload.decode("utf-8", errors="replace") if payload else ""
        try:
            payload_dict = json.loads(payload_str) if payload_str else {}
        except json.JSONDecodeError:
            payload_dict = {}

        # ROS2 publish (활성 시)
        ros2_ok, ros2_msg = self._publish_ros2(
            item_id,
            robot_id,
            command,
            payload_str,
            payload_dict,
        )

        if not ros2_ok and not ROS2_ENABLED:
            return (True, f"noop_dispatch: {command} (ROS2 비활성)")
        if not ros2_ok:
            return (False, ros2_msg)

        return (True, ros2_msg)

    def _publish_ros2(
        self,
        item_id: int,
        robot_id: str,
        command: str,
        payload_str: str,
        payload_dict: dict,
    ) -> tuple[bool, str]:
        """ROS2 토픽 publish. 미활성 시 (False, 메시지) 반환."""
        if not ROS2_ENABLED or self._rclpy is None or self._node is None:
            return (
                False,
                "ros2_not_available: MGMT_ROS2_ENABLED=1 + rclpy 환경 필요.",
            )

        # command 에 따라 토픽 선택
        if command in _NAV_COMMANDS:
            # navigate/charge → /{robot_id}/nav_goal
            robot_ns = robot_id.lower().replace("-", "")
            topic = f"/{robot_ns}/nav_goal"
            data = json.dumps(
                {
                    "command": command,
                    "target": payload_dict.get("target", "HOME"),
                    "x": payload_dict.get("x", 0.0),
                    "y": payload_dict.get("y", 0.0),
                    "item_id": item_id,
                }
            )
        else:
            # pick/place/기타 → /{robot_id}/cmd
            topic = f"/{robot_id}/cmd"
            data = payload_str or command

        try:
            from std_msgs.msg import String  # type: ignore[import-not-found]

            with self._lock:
                pub = self._publishers.get(topic)
                if pub is None:
                    pub = self._node.create_publisher(String, topic, 10)
                    self._publishers[topic] = pub
            msg = String()
            msg.data = data
            pub.publish(msg)
            logger.info("Ros2Adapter publish %s: cmd=%s item=%s", topic, command, item_id)
            return (True, f"ros2_published {topic}")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ros2Adapter dispatch 예외: %s", exc)
            return (False, f"ros2_error: {exc}")

    def close(self) -> None:
        if self._node is not None:
            try:
                self._node.destroy_node()
            except Exception:  # noqa: BLE001
                pass
        if self._rclpy is not None:
            try:
                self._rclpy.shutdown()
            except Exception:  # noqa: BLE001
                pass
        self._node = None
        self._rclpy = None
