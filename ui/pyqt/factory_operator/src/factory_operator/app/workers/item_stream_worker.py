"""ItemStreamWorker — Management Service WatchItems gRPC stream 을 QThread 에서 소비.

V6 아키텍처 Phase 3:
- gRPC server streaming 은 동기 호출 (반복자에서 .next() 가 블록)
- GUI 메인 스레드를 막지 않으려면 별도 QThread 에서 소비
- 받은 ItemEvent 를 pyqtSignal 로 emit → 메인 스레드 슬롯에서 UI 업데이트

@MX:NOTE: 1개 페이지에 1개 워커. 페이지 닫힐 때 stop() 호출 필수 (그렇지 않으면 좀비 스레드).
@MX:WARN: gRPC channel 은 thread-safe 하지만 stub iterator 는 그렇지 않음 → 1 worker = 1 stream.
@MX:REASON: QThread 패턴으로 PyQt GUI 와 격리 (blocking gRPC iterator 가 UI 스레드 정지 방지).
"""

from __future__ import annotations

import logging
import time

from PyQt5.QtCore import QObject, QThread, pyqtSignal

logger = logging.getLogger(__name__)


class ItemStreamWorker(QObject):
    """gRPC WatchItems stream 소비자.

    signals:
        item_event(item_id: int, stage_code: str, robot_id: str, at_iso: str)
        connection_state(connected: bool)
    """

    item_event = pyqtSignal(int, str, str, str)
    connection_state = pyqtSignal(bool)

    # gRPC stage enum int → 코드 매핑 (management_pb2.ItemStage 와 동일)
    _STAGE_CODE = {
        1: "QUE",
        2: "MM",
        3: "DM",
        4: "TR_PP",
        5: "PP",
        6: "IP",
        7: "TR_LD",
        8: "SH",
    }

    def __init__(self, order_filter: str | None = None, reconnect_sec: float = 3.0) -> None:
        super().__init__()
        self._order = order_filter
        self._reconnect = reconnect_sec
        self._stop = False
        self._client = None  # type: ignore[var-annotated]

    def request_stop(self) -> None:
        """외부에서 종료 요청. 다음 연결 시도 전에 루프 종료."""
        self._stop = True
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001
                pass

    def run(self) -> None:
        """QThread.start() 가 호출. 무한 재연결 루프."""
        # gRPC 의존 import 는 워커 시작 후 (앱 부팅 부담 경감)
        try:
            import grpc

            from app.management_client import ManagementClient
        except ImportError as exc:
            logger.error("ItemStreamWorker: gRPC/management_client import 실패: %s", exc)
            self.connection_state.emit(False)
            return

        while not self._stop:
            try:
                self._client = ManagementClient()
                if not self._client.health():
                    raise grpc.RpcError("health check failed")
                self.connection_state.emit(True)
                logger.info("ItemStreamWorker connected (order=%s)", self._order)
                stream = self._client.watch_items(self._order)
                for ev in stream:
                    if self._stop:
                        break
                    stage = self._STAGE_CODE.get(int(ev.stage), "UNSPECIFIED")
                    at_iso = ev.at.iso8601 if ev.HasField("at") else ""
                    self.item_event.emit(int(ev.item_id), stage, ev.robot_id or "", at_iso)
            except grpc.RpcError as exc:
                logger.warning(
                    "ItemStreamWorker gRPC 끊김: %s — %.1fs 후 재연결",
                    exc.code().name if hasattr(exc, "code") else exc,
                    self._reconnect,
                )
                self.connection_state.emit(False)
            except Exception as exc:  # noqa: BLE001
                logger.exception("ItemStreamWorker 예외: %s", exc)
                self.connection_state.emit(False)
            finally:
                if self._client is not None:
                    try:
                        self._client.close()
                    except Exception:  # noqa: BLE001
                        pass
                    self._client = None

            if self._stop:
                break
            time.sleep(self._reconnect)

        logger.info("ItemStreamWorker stopped")


class ItemStreamThread(QThread):
    """편의용 QThread 컨테이너."""

    def __init__(self, worker: ItemStreamWorker) -> None:
        super().__init__()
        self._worker = worker
        self._worker.moveToThread(self)
        self.started.connect(self._worker.run)

    def stop(self, timeout_ms: int = 5000) -> None:
        self._worker.request_stop()
        self.quit()
        self.wait(timeout_ms)
