# @MX:NOTE AI Server 연동 (Phase 1: SSH/SCP 이미지 업로드)
# ------------------------------------------------------------
# V6 Architecture - AI Server (100.66.177.119, Tailscale)
#
# 용도: 검사 카메라 촬영 이미지 → AI Server 로 전송 → 모델 학습 데이터셋 구축
# 연결: Tailscale 내부망, SSH 기반 파일 전송 (paramiko)
# 인증: env 환경변수 (비밀번호) 또는 SSH 키 (권장)
#
# ⚠️ S-004: 비밀번호는 반드시 환경변수로 주입. 코드/git 커밋 금지.
#
# Phase 2 (추후): AI Server 추론 gRPC 엔드포인트 확정 시 별도 client 모듈 추가
"""AI Server SSH 업로드 클라이언트."""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import paramiko  # noqa: F401

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AIServerConfig:
    """AI Server 접속 설정 (env 기반)."""

    host: str
    user: str
    port: int = 22
    password: str | None = None
    key_path: str | None = None
    remote_base_dir: str = "/home/team2/datasets/inspection"
    enabled: bool = False

    @classmethod
    def from_env(cls) -> AIServerConfig:
        host = os.getenv("MGMT_AI_HOST", "").strip()
        user = os.getenv("MGMT_AI_USER", "").strip()
        password = os.getenv("MGMT_AI_PASS") or None
        key_path = os.getenv("MGMT_AI_SSH_KEY") or None
        port = int(os.getenv("MGMT_AI_PORT", "22"))
        remote_base = os.getenv("MGMT_AI_REMOTE_DIR", "/home/team2/datasets/inspection")
        # 활성 조건: host+user 지정 AND (password 또는 key_path 중 하나)
        enabled = bool(host and user and (password or key_path))
        return cls(
            host=host,
            user=user,
            port=port,
            password=password,
            key_path=key_path,
            remote_base_dir=remote_base,
            enabled=enabled,
        )


class AIUploader:
    """검사 이미지를 AI Server 로 업로드한다.

    사용 예:
        uploader = AIUploader(AIServerConfig.from_env())
        if uploader.enabled:
            uploader.upload_image(
                local_path="/tmp/frame_001.jpg",
                remote_subdir="CAM-01/2026-04-15",
            )

    @MX:WARN paramiko import 는 생성자에서 lazy — env 미설정 시 의존성 불필요.
    @MX:REASON 개발 환경에서 AI Server 없이도 서버 기동 가능해야 함.
    """

    def __init__(self, config: AIServerConfig):
        self.config = config
        self._ssh = None  # type: ignore[var-annotated]

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    @contextmanager
    def _client(self) -> Iterator[paramiko.SSHClient]:
        if not self.enabled:
            raise RuntimeError("AIUploader 비활성화 (MGMT_AI_HOST/USER + PASS or SSH_KEY 필요)")
        try:
            import paramiko  # lazy
        except ImportError as e:
            raise RuntimeError("paramiko 미설치. `pip install paramiko` 필요") from e

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs = {
            "hostname": self.config.host,
            "port": self.config.port,
            "username": self.config.user,
            "timeout": 10,
            "banner_timeout": 10,
            "auth_timeout": 10,
        }
        if self.config.key_path:
            connect_kwargs["key_filename"] = self.config.key_path
        else:
            connect_kwargs["password"] = self.config.password
            connect_kwargs["look_for_keys"] = False
            connect_kwargs["allow_agent"] = False

        client.connect(**connect_kwargs)
        try:
            yield client
        finally:
            client.close()

    def upload_image(
        self,
        local_path: str | Path,
        remote_subdir: str = "",
        remote_filename: str | None = None,
    ) -> str:
        """단일 이미지 업로드. 반환값: 원격 절대 경로."""
        local_path = Path(local_path)
        if not local_path.is_file():
            raise FileNotFoundError(local_path)

        remote_filename = remote_filename or local_path.name
        remote_dir = f"{self.config.remote_base_dir.rstrip('/')}"
        if remote_subdir:
            remote_dir = f"{remote_dir}/{remote_subdir.strip('/')}"
        remote_full = f"{remote_dir}/{remote_filename}"

        with self._client() as ssh:  # type: ignore[var-annotated]
            ssh.exec_command(f"mkdir -p {remote_dir}")
            sftp = ssh.open_sftp()
            try:
                sftp.put(str(local_path), remote_full)
                logger.info(
                    "AI upload ok: %s → %s@%s:%s",
                    local_path,
                    self.config.user,
                    self.config.host,
                    remote_full,
                )
            finally:
                sftp.close()
        return remote_full

    def health_check(self) -> bool:
        """SSH 연결 확인용 (진단 RPC 에서 사용 예정)."""
        if not self.enabled:
            return False
        try:
            with self._client() as ssh:  # type: ignore[var-annotated]
                _stdin, stdout, _stderr = ssh.exec_command("echo ok", timeout=5)
                return stdout.read().decode().strip() == "ok"
        except Exception as e:  # noqa: BLE001
            logger.warning("AI Server health_check 실패: %s", e)
            return False
