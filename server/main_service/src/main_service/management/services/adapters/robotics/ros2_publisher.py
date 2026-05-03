"""ROS2 publisher (mock fallback) — Management FMS 시퀀서가 cur_stat 전이마다 명령 발행.

V6 canonical: Management Service → ROS2 DDS → Manufacturing/Stacking/Transport Service
(Interface Service 잔재를 Phase B 에서 이관함)

설계:
- rclpy 가 설치되어 있으면 실 ROS2 publisher 로 메시지 발행 (RA / CONV / TAT 별 토픽).
- 미설치 시 print() 로 폴백 — 데모/테스트 시각적 확인 가능.

토픽 매핑 (잠정 — 실 ROS2 노드와 통신 시 합의 필요):
  /smartcast/ra/{res_id}/cmd      std_msgs/String  (예: "MV_SRC", "GRASP", ...)
  /smartcast/conv/{res_id}/cmd    std_msgs/String  (예: "ON", "OFF")
  /smartcast/tat/{res_id}/cmd     std_msgs/String  (예: "MV_SRC", "WAIT_HANDOFF", ...)

활성화: env MGMT_ROS2_ENABLED=1 (default 0). rclpy 미설치 시 자동 OFF.
(구 FMS_ROS2 env 는 하위 호환 유지)
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("management.ros2_publisher")


# ---- 환경/가용성 검출 ----


def _ros2_requested() -> bool:
    """env MGMT_ROS2_ENABLED=1 (또는 legacy FMS_ROS2=1) 이고 rclpy 가 import 가능할 때만 활성."""
    enabled = os.environ.get("MGMT_ROS2_ENABLED", "").strip() in (
        "1",
        "true",
        "True",
    ) or os.environ.get("FMS_ROS2", "0").strip() in ("1", "true", "True")
    if not enabled:
        return False
    try:
        import rclpy  # noqa: F401  (가용성 체크용)

        return True
    except ImportError:
        logger.warning("MGMT_ROS2_ENABLED=1 이지만 rclpy 미설치 — 폴백 print 모드로 전환")
        return False


_ENABLED = _ros2_requested()


# ---- 노드/publisher 캐시 (실 ROS2 모드용) ----

_node = None  # type: ignore[assignment]
_publishers: dict[str, object] = {}  # topic_name → Publisher


def init_ros2() -> None:
    """ROS2 가 활성일 때 한 번만 호출 — context 초기화."""
    global _node
    if not _ENABLED or _node is not None:
        return
    try:
        import rclpy  # type: ignore[import-not-found]
        from rclpy.node import Node  # type: ignore[import-not-found]
    except ImportError:
        return
    rclpy.init(args=None)
    _node = Node("smartcast_fms_publisher")
    logger.info("ROS2 node 초기화 완료: smartcast_fms_publisher")


def shutdown_ros2() -> None:
    """ROS2 정리 — backend lifespan shutdown 시 호출."""
    global _node
    if not _ENABLED or _node is None:
        return
    try:
        import rclpy  # type: ignore[import-not-found]
    except ImportError:
        return
    try:
        _node.destroy_node()
    except Exception:  # noqa: BLE001
        pass
    rclpy.shutdown()
    _node = None
    _publishers.clear()


def _topic_for(res_type: str, res_id: str) -> str | None:
    """res_type 별 토픽 경로."""
    mapping = {"RA": "ra", "CONV": "conv", "TAT": "tat"}
    sub = mapping.get(res_type)
    if not sub:
        return None
    return f"/smartcast/{sub}/{res_id.lower()}/cmd"


def _get_or_create_publisher(topic: str):
    """Publisher 캐시 — 동일 토픽은 1번만 생성."""
    if topic in _publishers:
        return _publishers[topic]
    if _node is None:
        return None
    try:
        from std_msgs.msg import String  # type: ignore[import-not-found]
    except ImportError:
        return None
    pub = _node.create_publisher(String, topic, 10)
    _publishers[topic] = pub
    return pub


# ---- 외부 API: 시퀀서가 호출 ----


def publish_state(res_type: str, res_id: str, cur_stat: str, task_type: str | None = None) -> None:
    """현재 res 의 cur_stat 전이를 ROS2 토픽으로 발행 (or print 폴백).

    호출 빈도: 시퀀서 polling cycle 마다 cur_stat 변경 시 1회.
    실패는 무시 — 시퀀서 흐름을 막지 않음.
    """
    topic = _topic_for(res_type, res_id) or f"/smartcast/unknown/{res_id}/cmd"
    payload = f"{task_type or '-'}:{cur_stat}"

    if not _ENABLED or _node is None:
        # mock fallback — 로그 기반 가시성
        print(f"[ROS2-MOCK] PUB {topic}  '{payload}'", flush=True)
        return

    try:
        from std_msgs.msg import String  # type: ignore[import-not-found]
    except ImportError:
        print(f"[ROS2-MOCK] PUB {topic}  '{payload}'  (std_msgs missing)", flush=True)
        return

    pub = _get_or_create_publisher(topic)
    if pub is None:
        print(f"[ROS2-MOCK] PUB {topic}  '{payload}'  (publisher create failed)", flush=True)
        return

    msg = String()
    msg.data = payload
    try:
        pub.publish(msg)
    except Exception as exc:  # noqa: BLE001
        logger.warning("ROS2 publish 실패: %s — fallback print", exc)
        print(f"[ROS2-MOCK] PUB {topic}  '{payload}'  (publish error)", flush=True)


def is_real_ros2() -> bool:
    """현재 실 ROS2 모드인지 (테스트/디버깅용)."""
    return _ENABLED and _node is not None
