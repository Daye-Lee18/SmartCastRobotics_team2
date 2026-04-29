"""AMR 배터리 상태 서비스 — ROS2 DDS 또는 SSH 폴백.

운영 모드 (MGMT_AMR_MODE 환경변수):
  "ros2"  — ROS2 sensor_msgs/BatteryState 토픽 구독 (같은 LAN, DDS multicast)
  "ssh"   — SSH 경유 pinkylib I2C 읽기 (Tailscale VPN 등 DDS 불가 환경)
  자동    — MGMT_ROS2_ENABLED=1 이면 ros2, 아니면 ssh

ROS2 모드:
  - 토픽: /{namespace}/batt_state (sensor_msgs/BatteryState)
  - AMR RPi 에서 pinky_sensor_adc 노드 실행 필요
  - percentage NaN 시 voltage 기반 계산 (pinkylib 동일 공식)

SSH 모드 (과도기):
  - MGMT_AMR_{n}_HOST / USER / PASS / PORT 환경변수
  - SSH → sudo python3 → pinkylib.Battery 호출

Management Service 내부에서 백그라운드 스레드로 실행.
GetRobotStatus RPC 가 최신 캐시 값을 반환.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Pinky Pro 배터리 전압 → 퍼센트 변환 (pinkylib.Battery 동일 공식)
_FULL_VOLTAGE = 7.6
_EMPTY_VOLTAGE = 6.8


def _voltage_to_percent(voltage: float) -> float:
    pct = (voltage - _EMPTY_VOLTAGE) / (_FULL_VOLTAGE - _EMPTY_VOLTAGE) * 100
    return round(max(0.0, min(100.0, pct)), 2)


class _MovingAverage:
    """ADC 노이즈 제거용 이동평균 필터."""

    def __init__(self, window: int = 6) -> None:
        self._window = window
        self._values: list[float] = []

    def push(self, value: float) -> float:
        self._values.append(value)
        if len(self._values) > self._window:
            self._values.pop(0)
        return sum(self._values) / len(self._values)


@dataclass
class AmrStatus:
    id: str
    host: str
    status: str = "offline"
    battery: float = 0.0
    voltage: float = 0.0
    location: str = "-"
    task_state: int = 1  # AmrTaskState enum (1=IDLE)
    task_id: str = ""
    loaded_item: str = ""


# ---------------------------------------------------------------------------
# SSH 폴링 (과도기)
# ---------------------------------------------------------------------------

BATTERY_SCRIPT = """\
from pinkylib import Battery
import json
b = Battery()
v = b.get_voltage()
p = b.battery_percentage()
b.close()
print(json.dumps({"battery": p, "voltage": round(v, 3)}))
"""


@dataclass(frozen=True)
class AmrTarget:
    id: str
    host: str
    user: str
    password: str
    port: int = 22


def _discover_targets() -> list[AmrTarget]:
    targets: list[AmrTarget] = []
    for n in range(1, 10):
        host = os.environ.get(f"MGMT_AMR_{n}_HOST", "").strip()
        if not host:
            continue
        targets.append(
            AmrTarget(
                id=os.environ.get(f"MGMT_AMR_{n}_ID", f"AMR-{n:03d}"),
                host=host,
                user=os.environ.get(f"MGMT_AMR_{n}_USER", "pinky"),
                password=os.environ.get(f"MGMT_AMR_{n}_PASS", ""),
                port=int(os.environ.get(f"MGMT_AMR_{n}_PORT", "22")),
            )
        )
    return targets


def _poll_one_ssh(target: AmrTarget) -> dict[str, Any] | None:
    try:
        import paramiko
    except ImportError:
        logger.error("paramiko 미설치 — SSH 폴링 불가")
        return None

    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        c.connect(
            hostname=target.host,
            port=target.port,
            username=target.user,
            password=target.password,
            timeout=5,
            look_for_keys=False,
            allow_agent=False,
        )
        cmd = "sudo -S python3 - <<'PY'\n" + BATTERY_SCRIPT + "PY\n"
        stdin, out, err = c.exec_command(cmd, timeout=15, get_pty=True)
        stdin.write(target.password + "\n")
        stdin.flush()

        stdout = out.read().decode().strip()
        for line in reversed(stdout.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                return json.loads(line)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("AMR %s (%s) SSH 폴링 실패: %s", target.id, target.host, exc)
        return None
    finally:
        c.close()


# ---------------------------------------------------------------------------
# ROS2 구독 모드
# ---------------------------------------------------------------------------


def _start_ros2_subscriber(
    namespaces: list[str],
    cache: dict[str, AmrStatus],
    lock: threading.Lock,
    stop_event: threading.Event,
) -> None:
    """별도 스레드에서 rclpy spin — BatteryState 토픽 구독."""
    try:
        import rclpy
        from rclpy.node import Node
        from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
        from sensor_msgs.msg import BatteryState
    except ImportError as exc:
        logger.error("rclpy/sensor_msgs 임포트 실패: %s", exc)
        return

    rclpy.init(args=None)
    node = Node("amr_battery_monitor")

    qos = QoSProfile(
        reliability=ReliabilityPolicy.BEST_EFFORT,
        durability=DurabilityPolicy.VOLATILE,
        depth=5,
    )

    # ROS2 토픽은 20Hz 퍼블리시 → 이동평균 윈도우 크게 설정
    voltage_filters: dict[str, _MovingAverage] = {}

    def _make_callback(ns: str):
        amr_id = f"AMR-{ns.replace('amr', '').lstrip('/')}"
        if amr_id == "AMR-":
            amr_id = ns
        voltage_filters[amr_id] = _MovingAverage(window=20)

        def cb(msg: BatteryState):
            raw_v = msg.voltage
            avg_v = voltage_filters[amr_id].push(raw_v)
            battery = _voltage_to_percent(avg_v)

            status = AmrStatus(
                id=amr_id,
                host="dds",
                status="online",
                battery=battery,
                voltage=round(avg_v, 3),
            )
            with lock:
                cache[amr_id] = status

        return cb

    for ns in namespaces:
        topic = f"/{ns}/batt_state"
        node.create_subscription(BatteryState, topic, _make_callback(ns), qos)
        logger.info("ROS2 구독: %s", topic)

    while not stop_event.is_set():
        rclpy.spin_once(node, timeout_sec=0.5)

    node.destroy_node()
    rclpy.shutdown()
    logger.info("ROS2 BatteryState 구독 종료")


# ---------------------------------------------------------------------------
# 통합 서비스
# ---------------------------------------------------------------------------


class AmrBatteryService:
    """AMR 배터리 상태 서비스. ROS2 또는 SSH 모드 자동 선택."""

    def __init__(self, poll_interval: float | None = None) -> None:
        self._interval = poll_interval or float(os.environ.get("MGMT_AMR_POLL_INTERVAL", "10"))
        self._cache: dict[str, AmrStatus] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        # 모드 결정
        mode = os.environ.get("MGMT_AMR_MODE", "").lower()
        ros2_enabled = os.environ.get("MGMT_ROS2_ENABLED", "0") in ("1", "true", "yes")
        if mode == "ros2" or (not mode and ros2_enabled):
            self._mode = "ros2"
        else:
            self._mode = "ssh"

        self._targets = _discover_targets()
        # ROS2 모드: 타겟 목록에서 네임스페이스 추출 (AMR-001 → amr1)
        self._ros2_namespaces = [f"amr{i + 1}" for i in range(len(self._targets))]

        logger.info(
            "AmrBatteryService: mode=%s, %d대, 간격 %.0fs",
            self._mode,
            len(self._targets),
            self._interval,
        )

    def start(self) -> None:
        if not self._targets:
            return
        if self._mode == "ros2":
            self._thread = threading.Thread(
                target=_start_ros2_subscriber,
                args=(self._ros2_namespaces, self._cache, self._lock, self._stop),
                name="amr-battery-ros2",
                daemon=True,
            )
        else:
            self._thread = threading.Thread(
                target=self._run_ssh,
                name="amr-battery-ssh",
                daemon=True,
            )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def get_all(self) -> list[AmrStatus]:
        with self._lock:
            return list(self._cache.values())

    def _run_ssh(self) -> None:
        # AMR 별 이동평균 필터 (ADC 노이즈 제거)
        voltage_ma: dict[str, _MovingAverage] = {t.id: _MovingAverage(6) for t in self._targets}

        while not self._stop.is_set():
            for t in self._targets:
                if self._stop.is_set():
                    break
                data = _poll_one_ssh(t)
                if data:
                    raw_v = data.get("voltage", 0)
                    avg_v = voltage_ma[t.id].push(raw_v)
                    avg_pct = _voltage_to_percent(avg_v)
                    status = AmrStatus(
                        id=t.id,
                        host=t.host,
                        status="online",
                        battery=avg_pct,
                        voltage=round(avg_v, 3),
                    )
                else:
                    status = AmrStatus(id=t.id, host=t.host, status="offline")
                with self._lock:
                    self._cache[t.id] = status
            self._stop.wait(timeout=self._interval)
