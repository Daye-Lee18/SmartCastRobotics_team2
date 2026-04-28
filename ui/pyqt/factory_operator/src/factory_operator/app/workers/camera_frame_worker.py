"""CameraFrameWorker — Management Service WatchCameraFrames gRPC stream 소비.

Stage B (옵션 B): image_sink condvar 기반 서버 push 스트림을 QThread 에서 수신.
기존 QTimer 폴링(Stage A) 을 대체한다. 첫 프레임 지연 ~RTT, 이후 Jetson push 즉시 전달.

사용:
    worker = CameraFrameWorker(camera_id="CAM-INSP-01")
    thread = QThread()
    worker.moveToThread(thread)
    worker.frame_received.connect(on_frame)           # 메인 스레드 슬롯
    thread.started.connect(worker.run)
    thread.start()

@MX:NOTE: 다중 카메라 지원 필요 시 각 카메라당 Worker 1개 (서버도 ThreadPool 에서 각 스트림 1 워커).
@MX:WARN: 자동 재연결 포함 — 서버 재시작/네트워크 끊김 시 3초 backoff 후 재구독.
"""

from __future__ import annotations

import logging
import time

from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class CameraFrameWorker(QObject):
    """gRPC WatchCameraFrames stream 소비. JPEG 바이트를 signal 로 메인 스레드에 전달."""

    # data, encoding, sequence, received_at
    frame_received = pyqtSignal(bytes, str, int, str)
    connection_state = pyqtSignal(bool)

    def __init__(self, camera_id: str, reconnect_sec: float = 3.0) -> None:
        super().__init__()
        self._camera_id = camera_id
        self._reconnect = reconnect_sec
        self._stop = False
        self._last_sequence: int = 0
        self._client = None  # type: ignore[var-annotated]
        self._current_stream = None  # type: ignore[var-annotated]

    def request_stop(self) -> None:
        self._stop = True
        if self._current_stream is not None:
            try:
                self._current_stream.cancel()
            except Exception:  # noqa: BLE001
                pass
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001
                pass

    def run(self) -> None:
        try:
            import grpc

            from app.generated import management_pb2
            from app.management_client import ManagementClient
        except ImportError as exc:
            logger.error("CameraFrameWorker import 실패: %s", exc)
            self.connection_state.emit(False)
            return

        while not self._stop:
            try:
                self._client = ManagementClient()
                if not self._client.health():
                    raise grpc.RpcError("health check failed")
                self.connection_state.emit(True)

                req = management_pb2.WatchFramesRequest(
                    camera_id=self._camera_id,
                    after_sequence=self._last_sequence,
                )
                # 직접 stub 호출 — ManagementClient 에 편의 메서드 없음
                self._current_stream = self._client._stub.WatchCameraFrames(req)  # noqa: SLF001
                logger.info(
                    "CameraFrameWorker subscribed camera=%s after_seq=%d",
                    self._camera_id,
                    self._last_sequence,
                )

                for resp in self._current_stream:
                    if self._stop:
                        break
                    if not resp.available:
                        continue
                    self._last_sequence = int(resp.sequence)
                    self.frame_received.emit(
                        bytes(resp.data),
                        resp.encoding or "jpeg",
                        self._last_sequence,
                        resp.received_at.iso8601 if resp.HasField("received_at") else "",
                    )
            except Exception as exc:  # noqa: BLE001
                if self._stop:
                    break
                logger.warning(
                    "CameraFrameWorker stream 오류: %s (재연결 %.1fs)", exc, self._reconnect
                )
                self.connection_state.emit(False)
                time.sleep(self._reconnect)
            finally:
                self._current_stream = None
                if self._client is not None:
                    try:
                        self._client.close()
                    except Exception:  # noqa: BLE001
                        pass
                    self._client = None
        logger.info("CameraFrameWorker stopped camera=%s", self._camera_id)
