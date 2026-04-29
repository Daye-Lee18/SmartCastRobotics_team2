"""AMR 실시간 상태 워커 — Management Service gRPC 경유.

V6 아키텍처: PyQt → gRPC → Management Service → SSH → AMR RPi (pinkylib)
PyQt 는 SSH 직접 호출하지 않고 ManagementClient.get_robot_status() 사용.

시그널:
    status_updated(list[dict])  — [{id, host, battery, status, location}, …]
    connection_state(bool)      — Management Service 연결 상태
"""

from __future__ import annotations

import logging
import time

from PyQt5.QtCore import QObject, QThread, pyqtSignal

logger = logging.getLogger(__name__)


class AmrStatusWorker(QObject):
    """gRPC 기반 AMR 상태 폴링 워커."""

    status_updated = pyqtSignal(list)  # list[dict]
    connection_state = pyqtSignal(bool)

    def __init__(self, poll_interval: float = 10.0) -> None:
        super().__init__()
        self._interval = poll_interval
        self._stop = False

    def request_stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        try:
            from app.management_client import ManagementClient
        except ImportError as exc:
            logger.error("ManagementClient import 실패: %s", exc)
            return

        client = ManagementClient()
        logger.info("AmrStatusWorker 시작: gRPC %s, 간격 %.0fs", client.endpoint, self._interval)
        was_connected = False

        while not self._stop:
            robots = client.get_robot_status()
            connected = bool(robots)

            if connected != was_connected:
                was_connected = connected
                self.connection_state.emit(connected)

            if robots:
                # status 매핑: online → running (AmrStatusCard fallback 호환)
                # task_state 가 있으면 AmrStatusCard 가 우선 사용
                for r in robots:
                    if r.get("status") == "online":
                        r["status"] = "running"
                    elif r.get("status") == "offline":
                        r["status"] = "error"
                logger.info(
                    "AMR 상태 수신 %d대: %s",
                    len(robots),
                    [(r["id"], r.get("battery"), r.get("task_state")) for r in robots],
                )
                self.status_updated.emit(robots)

            # interruptible sleep
            deadline = time.monotonic() + self._interval
            while not self._stop and time.monotonic() < deadline:
                time.sleep(0.5)

        client.close()
        logger.info("AmrStatusWorker 종료")


class AmrStatusThread(QThread):
    """AmrStatusWorker 를 구동하는 QThread 래퍼."""

    def __init__(self, worker: AmrStatusWorker, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._worker = worker
        self._worker.moveToThread(self)

    def run(self) -> None:
        self._worker.run()

    def shutdown(self) -> None:
        self._worker.request_stop()
        self.quit()
        self.wait(5000)
