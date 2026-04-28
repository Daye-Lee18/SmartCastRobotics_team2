"""StartProductionWorker — Management.StartProduction RPC 를 별도 스레드에서 호출.

V6 review Q-002 대응:
- 기존 schedule.py._do_start 가 메인 GUI 스레드에서 client.start_production() 동기 호출
- gRPC RPC 응답까지 UI 프리즈 (timeout 5초까지)
- 본 워커가 스레드에서 호출, 결과를 pyqtSignal 로 메인 스레드에 전달

@MX:NOTE: 1회용 워커 (1 클릭 = 1 워커). ItemStreamWorker(영구) 와 다른 패턴.
@MX:WARN: 사용자가 연속 클릭 시 워커 폭주 가능 → 호출자(schedule.py) 에서 버튼 비활성화 필수.
"""

from __future__ import annotations

import logging

from PyQt5.QtCore import QObject, QThread, pyqtSignal

logger = logging.getLogger(__name__)


class StartProductionWorker(QObject):
    """1회용 RPC 워커.

    signals:
        succeeded(list[WorkOrderInfo]): 성공 — DTO 리스트
        failed(str, str): 실패 — (kind, message). kind = 'grpc' | 'value' | 'other'
        finished(): 성공/실패 무관 종료 알림 (버튼 재활성용)
    """

    succeeded = pyqtSignal(list)
    failed = pyqtSignal(str, str)
    finished = pyqtSignal()

    def __init__(self, order_ids: list[str]) -> None:
        super().__init__()
        self._order_ids = list(order_ids)

    def run(self) -> None:
        client = None
        try:
            import grpc

            from app.management_client import ManagementClient
        except ImportError as exc:
            self.failed.emit("import", f"gRPC 모듈 로드 실패: {exc}")
            self.finished.emit()
            return
        try:
            client = ManagementClient()
            wos = client.start_production(self._order_ids)
            self.succeeded.emit(wos)
        except ValueError as exc:
            self.failed.emit("value", str(exc))
        except grpc.RpcError as exc:
            details = exc.details() if hasattr(exc, "details") else str(exc)
            code = exc.code().name if hasattr(exc, "code") else "UNKNOWN"
            ep = client.endpoint if client is not None else "(unknown)"
            self.failed.emit("grpc", f"endpoint={ep} code={code} detail={details}")
        except Exception as exc:  # noqa: BLE001
            logger.exception("StartProductionWorker 예외: %s", exc)
            self.failed.emit("other", str(exc))
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:  # noqa: BLE001
                    pass
            self.finished.emit()


class StartProductionThread(QThread):
    """1회용 QThread 컨테이너 — 작업 종료 시 자동 정리."""

    def __init__(self, worker: StartProductionWorker) -> None:
        super().__init__()
        self._worker = worker
        self._worker.moveToThread(self)
        self.started.connect(self._worker.run)
        # 작업 끝나면 thread quit + 자가 정리
        self._worker.finished.connect(self.quit)
        self.finished.connect(self.deleteLater)
        self._worker.finished.connect(self._worker.deleteLater)
