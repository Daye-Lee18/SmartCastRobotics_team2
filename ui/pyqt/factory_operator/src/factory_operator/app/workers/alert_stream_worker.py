"""AlertStreamWorker — Management Service WatchAlerts gRPC stream 소비.

V6 Phase 8: WebSocket 단종 후, alerts 실시간 push 를 gRPC 로 대체.
PyQt main_window 에 토스트 알림 트리거.

@MX:NOTE: 1개 PyQt 인스턴스 = 1개 워커. main_window 에서 spawn.
@MX:WARN: 자동 재연결 포함. mgmt 서버 재시작 시 3초 backoff 후 재구독.
"""

from __future__ import annotations

import logging
import time

from PyQt5.QtCore import QObject, QThread, pyqtSignal

logger = logging.getLogger(__name__)


class AlertStreamWorker(QObject):
    """gRPC WatchAlerts stream 소비.

    signals:
        alert_event(alert_id, severity, error_code, message, equipment_id, zone, at_iso)
        connection_state(connected: bool)
    """

    alert_event = pyqtSignal(str, str, str, str, str, str, str)
    connection_state = pyqtSignal(bool)

    def __init__(self, severity_filter: str | None = None, reconnect_sec: float = 3.0) -> None:
        super().__init__()
        self._sev = severity_filter or ""
        self._reconnect = reconnect_sec
        self._stop = False
        self._client = None  # type: ignore[var-annotated]

    def request_stop(self) -> None:
        self._stop = True
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001
                pass

    def run(self) -> None:
        try:
            import grpc

            from app.management_client import ManagementClient
        except ImportError as exc:
            logger.error("AlertStreamWorker: gRPC/management_client import 실패: %s", exc)
            self.connection_state.emit(False)
            return

        while not self._stop:
            try:
                self._client = ManagementClient()
                if not self._client.health():
                    raise grpc.RpcError("health check failed")
                self.connection_state.emit(True)
                logger.info("AlertStreamWorker connected (sev=%s)", self._sev or "all")
                stream = self._client.watch_alerts(self._sev or None)
                for ev in stream:
                    if self._stop:
                        break
                    at_iso = ev.at.iso8601 if ev.HasField("at") else ""
                    self.alert_event.emit(
                        ev.id,
                        ev.severity,
                        ev.error_code,
                        ev.message,
                        ev.equipment_id,
                        ev.zone,
                        at_iso,
                    )
            except grpc.RpcError as exc:
                logger.warning(
                    "AlertStreamWorker gRPC 끊김: %s — %.1fs 후 재연결",
                    exc.code().name if hasattr(exc, "code") else exc,
                    self._reconnect,
                )
                self.connection_state.emit(False)
            except Exception as exc:  # noqa: BLE001
                logger.exception("AlertStreamWorker 예외: %s", exc)
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

        logger.info("AlertStreamWorker stopped")


class AlertStreamThread(QThread):
    def __init__(self, worker: AlertStreamWorker) -> None:
        super().__init__()
        self._worker = worker
        self._worker.moveToThread(self)
        self.started.connect(self._worker.run)

    def stop(self, timeout_ms: int = 5000) -> None:
        self._worker.request_stop()
        self.quit()
        self.wait(timeout_ms)
