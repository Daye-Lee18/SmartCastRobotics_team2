"""Image Forwarder — image_sink 의 latest 프레임을 AI Server 로 배치 업로드.

플로우:
    IP 단계 진입 이벤트 → snapshot(item_id, stage, camera_id)
        → image_sink.latest(camera_id) 복사
        → 로컬 스풀 디렉터리(JPEG) + 메타(JSON) 저장
    백그라운드 타이머 → flush()
        → AI Server 로 SSH 업로드 (ai_client.AIUploader)
        → 성공 시 스풀 파일 삭제

설계 결정 (2026-04-15):
- Q2 전량 전송: 모든 IP 진입 1건당 1장 업로드
- Q3 배치: 타이머 기반 flush (MGMT_IMAGE_BATCH_SEC 기본 30초)
- Q1 이벤트 트리거: execution_monitor 가 stage 전이 감지 시 snapshot() 호출

@MX:ANCHOR 공정 이벤트 → 학습 데이터셋 브리지. fan_in >= execution_monitor + 수동 RPC
@MX:REASON Jetson 은 dumb producer. 이벤트 판단/선별/업로드는 전부 Server 책임.
@MX:WARN AI Server 장애 시 스풀 무한 증가 방지 — MGMT_IMAGE_SPOOL_MAX_FILES 초과 시 최오래된 것 drop
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ForwarderConfig:
    spool_dir: Path
    batch_interval_sec: float
    batch_max_files: int
    spool_max_files: int

    @classmethod
    def from_env(cls) -> ForwarderConfig:
        return cls(
            spool_dir=Path(os.environ.get("MGMT_IMAGE_SPOOL_DIR", "/tmp/casting-image-spool")),
            batch_interval_sec=float(os.environ.get("MGMT_IMAGE_BATCH_SEC", "30")),
            batch_max_files=int(os.environ.get("MGMT_IMAGE_BATCH_MAX", "50")),
            spool_max_files=int(os.environ.get("MGMT_IMAGE_SPOOL_MAX_FILES", "5000")),
        )


class ImageForwarder:
    """image_sink latest → spool → AI Server 업로드."""

    def __init__(
        self,
        config: ForwarderConfig,
        sink_latest: Callable[[str], dict | None],
        uploader,  # AIUploader-compatible: .enabled + .upload_image(local_path, remote_subdir, remote_filename)
    ) -> None:
        self.cfg = config
        self._sink_latest = sink_latest
        self._uploader = uploader
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._stats = {"snapshot": 0, "uploaded": 0, "failed": 0, "dropped": 0}
        self.cfg.spool_dir.mkdir(parents=True, exist_ok=True)

    # ---------- public API ----------
    def snapshot(self, item_id: int, stage: str, camera_id: str) -> Path | None:
        """latest frame 을 스풀로 복사. 성공 시 JPEG 경로, 없으면 None."""
        frame = self._sink_latest(camera_id)
        if not frame:
            logger.info("snapshot skipped: camera=%s 최신 프레임 없음", camera_id)
            return None
        if frame.get("encoding") != "jpeg":
            logger.warning(
                "snapshot: 지원하지 않는 encoding=%s camera=%s",
                frame.get("encoding"),
                camera_id,
            )
            return None

        ts = frame.get("captured_at", "").replace(":", "").replace("-", "")
        stem = f"{camera_id}_{stage}_item{item_id}_{ts}_seq{frame.get('sequence', 0)}"
        jpg = self.cfg.spool_dir / f"{stem}.jpg"
        meta = self.cfg.spool_dir / f"{stem}.json"

        with self._lock:
            self._enforce_spool_limit()
            jpg.write_bytes(frame["data"])
            meta.write_text(
                json.dumps(
                    {
                        "item_id": item_id,
                        "stage": stage,
                        "camera_id": camera_id,
                        "captured_at": frame.get("captured_at"),
                        "received_at": frame.get("received_at"),
                        "encoding": "jpeg",
                        "width": frame.get("width"),
                        "height": frame.get("height"),
                        "sequence": frame.get("sequence"),
                        "bytes": frame.get("size"),
                    },
                    ensure_ascii=False,
                )
            )
            self._stats["snapshot"] += 1
        logger.info("snapshot ok: %s (%d bytes)", jpg.name, frame.get("size", 0))
        return jpg

    def flush(self) -> int:
        """스풀에 쌓인 파일을 AI Server 로 업로드. 반환: 업로드 건수."""
        if not getattr(self._uploader, "enabled", False):
            logger.debug("flush skipped: uploader 비활성")
            return 0
        files = sorted(self.cfg.spool_dir.glob("*.jpg"))[: self.cfg.batch_max_files]
        uploaded = 0
        for jpg in files:
            meta_path = jpg.with_suffix(".json")
            meta = {}
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                except json.JSONDecodeError:
                    pass
            date_str = (meta.get("captured_at", "") or "")[:10] or time.strftime("%Y-%m-%d")
            subdir = f"{meta.get('camera_id', 'unknown')}/{date_str}"
            try:
                self._uploader.upload_image(
                    local_path=jpg,
                    remote_subdir=subdir,
                    remote_filename=jpg.name,
                )
                jpg.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
                uploaded += 1
                with self._lock:
                    self._stats["uploaded"] += 1
            except Exception as e:  # noqa: BLE001
                logger.warning("upload failed %s: %s", jpg.name, e)
                with self._lock:
                    self._stats["failed"] += 1
                # 실패 파일은 스풀에 남김 (다음 배치에서 재시도)
                break  # 첫 실패 시 중단 — 연쇄 실패 방지
        if uploaded:
            logger.info("flush ok: %d uploaded", uploaded)
        return uploaded

    # ---------- background loop ----------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="image-forwarder",
            daemon=True,
        )
        self._thread.start()
        logger.info("image_forwarder started interval=%.1fs", self.cfg.batch_interval_sec)

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.flush()
            except Exception:  # noqa: BLE001
                logger.exception("forwarder loop error")
            self._stop.wait(self.cfg.batch_interval_sec)

    # ---------- helpers ----------
    def _enforce_spool_limit(self) -> None:
        """스풀 한도 초과 시 가장 오래된 파일 drop. 새 파일 1장 들어올 자리 확보."""
        files = sorted(self.cfg.spool_dir.glob("*.jpg"), key=lambda p: p.stat().st_mtime)
        # 새로 쓸 1장 포함해서 한도 유지
        excess = (len(files) + 1) - self.cfg.spool_max_files
        for jpg in files[: max(0, excess)]:
            jpg.unlink(missing_ok=True)
            jpg.with_suffix(".json").unlink(missing_ok=True)
            self._stats["dropped"] += 1

    def stats(self) -> dict:
        with self._lock:
            return dict(self._stats)
