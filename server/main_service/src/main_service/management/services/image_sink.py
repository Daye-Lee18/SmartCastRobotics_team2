"""Image Sink — Image Publisher → Management Service 수신 처리.

V6 정책 (2026-04-14):
- HW Image Publishing Service (Jetson) 가 본 endpoint 로 frame 스트림 publish
- 프로토콜: gRPC client streaming (proto: ImageFrame stream → ImageAck)

저장 정책:
- 메모리 상 latest_frame[camera_id] dict 만 유지 (최신 1장)
- Condition 기반 pub/sub — 구독자는 wait_new() 로 깨어나서 프레임 받음 (Stage B 옵션 B)
- 디스크 저장은 image_forwarder 가 담당 (IP 진입 시 스냅샷)

@MX:NOTE 동시 다중 카메라 streaming 지원 (gRPC ThreadPool 워커마다 독립 스트림).
@MX:WARN 이미지가 큰 경우 메모리 누수 주의 — latest 1장만 보관, 이전 것 GC.
@MX:ANCHOR Condition 락은 push/wait_new 가 공유 — 모든 구독자가 동일 notify 로 깨어남.
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


class ImageSink:
    """카메라별 최신 프레임을 메모리에 보관 + pub/sub."""

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._latest: dict[str, dict] = {}
        self._stats: dict[str, dict] = {}

    def push(
        self,
        camera_id: str,
        encoding: str,
        width: int,
        height: int,
        data: bytes,
        sequence: int,
        captured_at_iso: str,
    ) -> None:
        """클라이언트 streaming 한 프레임 1장 처리. 모든 구독자에게 notify."""
        with self._cond:
            self._latest[camera_id] = {
                "encoding": encoding,
                "width": width,
                "height": height,
                "size": len(data),
                "sequence": sequence,
                "captured_at": captured_at_iso,
                "received_at": datetime.now(UTC).isoformat(),
                "data": data,
            }
            stats = self._stats.setdefault(camera_id, {"count": 0, "bytes": 0})
            stats["count"] += 1
            stats["bytes"] += len(data)
            # Stage B: 구독자 깨우기
            self._cond.notify_all()

    def latest(self, camera_id: str) -> dict | None:
        with self._cond:
            return self._latest.get(camera_id)

    def wait_new(
        self,
        camera_id: str,
        after_sequence: int,
        timeout: float = 10.0,
    ) -> dict | None:
        """Stage B — 구독자 API. after_sequence 이후 프레임이 들어올 때까지 대기.

        반환:
            - 새 프레임 dict (sequence > after_sequence)
            - timeout 시 None (호출자가 재시도/keepalive 여부 판단)
        """
        with self._cond:
            # 이미 새 프레임이 있으면 즉시 반환
            current = self._latest.get(camera_id)
            if current and int(current.get("sequence", 0)) > after_sequence:
                return current
            # notify 대기
            self._cond.wait(timeout=timeout)
            current = self._latest.get(camera_id)
            if current and int(current.get("sequence", 0)) > after_sequence:
                return current
            return None

    def stats(self) -> dict[str, dict]:
        with self._cond:
            return {k: dict(v) for k, v in self._stats.items()}


# 전역 싱글톤 (모든 servicer 가 공유)
sink = ImageSink()
