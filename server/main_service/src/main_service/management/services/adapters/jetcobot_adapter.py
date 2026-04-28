"""JetCobot 어댑터 — pymycobot SSH 리모트 호출 (ROS2 드라이버 미설치 과도기 버전).

Elephant Robotics MyCobot 280 (JetCobot 에디션) 을 Mgmt Server 에서 조작하기 위한
임시 어댑터. ROS2 드라이버(mycobot_ros2) 가 설치·기동되면 ros2_adapter 로 이전 예정.

사용 패턴 (멀티 인스턴스):
    from services.adapters.jetcobot_adapter import JetCobotAdapter
    jc1 = JetCobotAdapter.from_env("1")   # MGMT_JETCOBOT_1_HOST …
    jc2 = JetCobotAdapter.from_env("2")   # MGMT_JETCOBOT_2_HOST …

    # 하위 호환: 인덱스 없이 호출하면 MGMT_JETCOBOT_HOST 참조
    jc = JetCobotAdapter.from_env()

환경변수 (접두어 MGMT_JETCOBOT_{idx}_):
    MGMT_JETCOBOT_{idx}_HOST          Tailscale IP
    MGMT_JETCOBOT_{idx}_USER          기본 jetcobot
    MGMT_JETCOBOT_{idx}_PASS          (또는 MGMT_JETCOBOT_{idx}_SSH_KEY)
    MGMT_JETCOBOT_{idx}_PORT          기본 22
    MGMT_JETCOBOT_{idx}_SERIAL        로봇측 시리얼 경로 (기본 /dev/ttyJETCOBOT)
    MGMT_JETCOBOT_{idx}_BAUD          기본 1000000
    MGMT_JETCOBOT_{idx}_VENV_PY       기본 ~/venv/mycobot/bin/python

@MX:NOTE: SSH 왕복 ~130ms (Tailscale 기준). 실시간 제어는 지연이 중요하면 부족 —
        ROS2 마이그레이션 시 DDS 로 교체 예정.
@MX:WARN: paramiko SSH 채널은 호출마다 open/close — 고빈도 루프에서는 커넥션 풀 필요.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JetCobotConfig:
    host: str
    user: str
    port: int = 22
    password: str | None = None
    key_path: str | None = None
    serial: str = "/dev/ttyJETCOBOT"
    baud: int = 1_000_000
    venv_py: str = "~/venv/mycobot/bin/python"
    enabled: bool = False

    @classmethod
    def from_env(cls, idx: str = "") -> JetCobotConfig:
        """환경변수로부터 설정 로드. idx="1" → MGMT_JETCOBOT_1_HOST 등."""
        prefix = f"MGMT_JETCOBOT_{idx}_" if idx else "MGMT_JETCOBOT_"
        host = os.environ.get(f"{prefix}HOST", "").strip()
        user = os.environ.get(f"{prefix}USER", "jetcobot").strip()
        password = os.environ.get(f"{prefix}PASS") or None
        key_path = os.environ.get(f"{prefix}SSH_KEY") or None
        enabled = bool(host and user and (password or key_path))
        return cls(
            host=host,
            user=user,
            port=int(os.environ.get(f"{prefix}PORT", "22")),
            password=password,
            key_path=key_path,
            serial=os.environ.get(f"{prefix}SERIAL", "/dev/ttyJETCOBOT"),
            baud=int(os.environ.get(f"{prefix}BAUD", "1000000")),
            venv_py=os.environ.get(f"{prefix}VENV_PY", "~/venv/mycobot/bin/python"),
            enabled=enabled,
        )


class JetCobotError(RuntimeError):
    """JetCobot 원격 호출 실패 (SSH/파이썬/시리얼)."""


class JetCobotAdapter:
    """SSH + pymycobot 으로 원격 MyCobot 280 제어."""

    def __init__(self, config: JetCobotConfig):
        self.cfg = config

    @classmethod
    def from_env(cls, idx: str = "") -> JetCobotAdapter:
        return cls(JetCobotConfig.from_env(idx))

    @property
    def enabled(self) -> bool:
        return self.cfg.enabled

    # ---------- public API ----------
    def get_angles(self) -> list[float]:
        """6-axis 조인트 각도 (deg)."""
        return self._call("mc.get_angles()")

    def get_coords(self) -> list[float]:
        """엔드 이펙터 좌표 [x,y,z,rx,ry,rz] (mm, deg)."""
        return self._call("mc.get_coords()")

    def is_power_on(self) -> bool:
        """로봇 전원 상태."""
        return bool(self._call("mc.is_power_on()"))

    def send_angles(self, angles: list[float], speed: int = 30) -> None:
        """6-axis 각도로 이동 (deg). speed 0~100."""
        assert len(angles) == 6, "angles 는 6원소 필요"
        self._call(f"mc.send_angles({list(angles)}, {int(speed)}); None")

    def send_coords(self, coords: list[float], speed: int = 30, mode: int = 0) -> None:
        """좌표 [x,y,z,rx,ry,rz] 로 이동. mode=0 angular, 1 linear."""
        assert len(coords) == 6, "coords 는 6원소 필요"
        self._call(f"mc.send_coords({list(coords)}, {int(speed)}, {int(mode)}); None")

    def power_on(self) -> None:
        self._call("mc.power_on(); None")

    def power_off(self) -> None:
        self._call("mc.power_off(); None")

    def health_check(self) -> bool:
        try:
            return self.is_power_on()
        except Exception as e:  # noqa: BLE001
            logger.warning("JetCobot health_check 실패: %s", e)
            return False

    # ---------- internal ----------
    def _call(self, expr: str):
        """원격 pymycobot 표현식 실행 후 JSON 파싱 결과 반환."""
        if not self.enabled:
            raise JetCobotError("JetCobotAdapter 비활성 (MGMT_JETCOBOT_* 환경변수 미설정)")
        try:
            import paramiko  # lazy
        except ImportError as exc:
            raise JetCobotError("paramiko 미설치") from exc

        # 원격 스크립트: MyCobot280 커넥션 + 식(expr) 평가 → JSON
        # thread_lock=True 로 pymycobot 내부 락 사용 (동시 호출 안전)
        payload = f"""
from pymycobot.mycobot280 import MyCobot280
import json, time, sys
try:
    mc = MyCobot280({self.cfg.serial!r}, {self.cfg.baud})
    mc.thread_lock = True
    time.sleep(0.1)
    result = {expr}
    print(json.dumps(result, ensure_ascii=False))
except Exception as e:
    print(json.dumps({{'__error__': type(e).__name__, 'msg': str(e)}}), file=sys.stderr)
    sys.exit(1)
"""
        cmd = f"{self.cfg.venv_py} - <<'PY'\n{payload}\nPY\n"

        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kw = {
            "hostname": self.cfg.host,
            "port": self.cfg.port,
            "username": self.cfg.user,
            "timeout": 10,
        }
        if self.cfg.key_path:
            kw["key_filename"] = self.cfg.key_path
        else:
            kw["password"] = self.cfg.password
            kw["look_for_keys"] = False
            kw["allow_agent"] = False
        c.connect(**kw)
        try:
            _, out, err = c.exec_command(cmd, timeout=15)
            stdout = out.read().decode().strip()
            stderr = err.read().decode().strip()
            rc = out.channel.recv_exit_status()
            if rc != 0:
                raise JetCobotError(stderr or f"remote rc={rc}")
            if not stdout:
                return None
            return json.loads(stdout)
        finally:
            c.close()
