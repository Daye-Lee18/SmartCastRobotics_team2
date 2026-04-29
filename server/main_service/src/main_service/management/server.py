"""Management Service gRPC 서버 (port 50051).

공장 가동 SPOF 제거 목적으로 FastAPI(Interface Service)와 독립 프로세스로 실행된다.
Factory Operator PC(PyQt)가 직접 gRPC 로 호출하며, Interface Service 장애/이관 시에도
공장 운영이 중단되지 않는다.

실행:
    cd backend/management
    python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/management.proto
    python server.py

환경 변수:
    MANAGEMENT_GRPC_HOST  기본 0.0.0.0
    MANAGEMENT_GRPC_PORT  기본 50051
    MANAGEMENT_DB_URL     SQLAlchemy URL (Interface Service 와 동일 DB 공유)

@MX:ANCHOR: V6 Phase 1~8 의 단일 진입점. ManagementServicer + ImagePublisherServicer 등록.
        모든 PyQt gRPC 호출이 본 서버를 통과 — 변경 시 호환성 영향 큼.
@MX:REASON: 5개 service 모듈 + 2개 servicer 의 wiring 책임. RPC 추가 시 servicer 메서드 + proto 동시 갱신 필요.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
from concurrent import futures

import grpc

# `python server.py` 로 직접 실행 가능하도록 sys.path 보장
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_THIS_DIR)  # backend/ — app.models 접근용
for p in (_THIS_DIR, _BACKEND_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

import management_pb2  # type: ignore  # noqa: E402
import management_pb2_grpc  # type: ignore  # noqa: E402
from rpc.field_event_rpc import FieldEventRpcMixin  # noqa: E402
from rpc.hardware_rpc import HardwareRpcMixin, ImagePublisherServicer  # noqa: E402
from rpc.monitor_rpc import MonitorRpcMixin  # noqa: E402
from rpc.production_rpc import ProductionRpcMixin  # noqa: E402
from rpc.robot_rpc import RobotRpcMixin  # noqa: E402
from rpc.task_rpc import TaskRpcMixin  # noqa: E402
from rpc.traffic_rpc import TrafficRpcMixin  # noqa: E402
from services.ai_client import AIServerConfig, AIUploader  # noqa: E402
from services.amr_battery import AmrBatteryService  # noqa: E402
from services.amr_state_machine import AmrStateMachine  # noqa: E402
from services.execution_monitor import ExecutionMonitor  # noqa: E402

# Phase B: Interface 로부터 이관된 FMS 자동 진행 시퀀서 + ROS2 publisher
from services.fms_sequencer import (
    is_enabled as fms_is_enabled,  # noqa: E402
    run_sequencer as run_fms_sequencer,  # noqa: E402
)
from services.image_forwarder import ForwarderConfig, ImageForwarder  # noqa: E402
from services.image_sink import sink as image_sink  # noqa: E402
from services.rfid_service import RfidService  # noqa: E402
from services.robot_executor import RobotExecutor  # noqa: E402
from services.ros2_publisher import init_ros2, is_real_ros2, shutdown_ros2  # noqa: E402
from services.task_allocator import TaskAllocator  # noqa: E402
from services.task_manager import TaskManager  # noqa: E402
from services.traffic_manager import TrafficManager  # noqa: E402

logger = logging.getLogger(__name__)

HOST = os.environ.get("MANAGEMENT_GRPC_HOST", "0.0.0.0")
PORT = int(os.environ.get("MANAGEMENT_GRPC_PORT", "50051"))


class ManagementServicer(
    ProductionRpcMixin,
    TaskRpcMixin,
    TrafficRpcMixin,
    MonitorRpcMixin,
    RobotRpcMixin,
    FieldEventRpcMixin,
    HardwareRpcMixin,
    management_pb2_grpc.ManagementServiceServicer,
):
    """gRPC servicer wiring for Management RPC mixins."""

    def __init__(self) -> None:
        self.task_manager = TaskManager()
        self.rfid_service = RfidService()
        self.task_allocator = TaskAllocator()
        self.traffic_manager = TrafficManager()
        # V6 AI 학습 데이터 브리지: Jetson -> image_sink -> forwarder -> AI Server SSH 업로드
        self.image_forwarder = _build_image_forwarder()
        self.execution_monitor = ExecutionMonitor(
            image_forwarder=self.image_forwarder,
        )
        # AMR 배터리 폴링 (SSH -> pinkylib)
        self.amr_battery = AmrBatteryService()
        self.amr_battery.start()
        # AMR 운송 상태 머신
        self.amr_state_machine = AmrStateMachine()
        for s in self.amr_battery.get_all():
            self.amr_state_machine.register(s.id)
        # RobotExecutor 에 state_machine 주입
        self.robot_executor = RobotExecutor(state_machine=self.amr_state_machine)

    def Health(self, request, context):
        return management_pb2.Empty()


def _build_image_forwarder():
    """ImageForwarder 를 구성. AI Server 설정이 없으면 None 반환 → 훅 비활성."""
    ai_cfg = AIServerConfig.from_env()
    if not ai_cfg.enabled:
        logger.info("image_forwarder 비활성: AI Server 환경변수 미설정")
        return None
    fwd = ImageForwarder(
        config=ForwarderConfig.from_env(),
        sink_latest=image_sink.latest,
        uploader=AIUploader(ai_cfg),
    )
    fwd.start()
    logger.info(
        "image_forwarder 활성: spool=%s batch=%.1fs", fwd.cfg.spool_dir, fwd.cfg.batch_interval_sec
    )
    return fwd


def _load_tls_credentials():
    """V6 S-001: mTLS 환경변수 활성 시 ssl_server_credentials 반환, 아니면 None.

    환경변수:
        MGMT_GRPC_TLS_ENABLED  = 1 면 활성
        MGMT_TLS_CERT_DIR      = cert 디렉터리 (기본 ./certs/)
        MGMT_TLS_SERVER_KEY    = 서버 private key 경로 (기본 ${CERT_DIR}/server.key)
        MGMT_TLS_SERVER_CRT    = 서버 cert 경로 (기본 ${CERT_DIR}/server.crt)
        MGMT_TLS_CA_CRT        = CA cert (클라이언트 검증용, 기본 ${CERT_DIR}/ca.crt)
        MGMT_TLS_REQUIRE_CLIENT_CERT = 1 면 mTLS, 0 이면 server-only TLS (기본 1)
    """
    if os.environ.get("MGMT_GRPC_TLS_ENABLED", "0") not in ("1", "true", "yes"):
        return None
    cert_dir = os.environ.get(
        "MGMT_TLS_CERT_DIR",
        os.path.join(_THIS_DIR, "certs"),
    )
    key_path = os.environ.get("MGMT_TLS_SERVER_KEY", os.path.join(cert_dir, "server.key"))
    crt_path = os.environ.get("MGMT_TLS_SERVER_CRT", os.path.join(cert_dir, "server.crt"))
    ca_path = os.environ.get("MGMT_TLS_CA_CRT", os.path.join(cert_dir, "ca.crt"))

    for p in (key_path, crt_path, ca_path):
        if not os.path.exists(p):
            raise FileNotFoundError(
                f"mTLS 활성화됐으나 cert 파일 없음: {p}\nscripts/gen_certs.sh 를 먼저 실행하세요."
            )

    with open(key_path, "rb") as f:
        server_key = f.read()
    with open(crt_path, "rb") as f:
        server_crt = f.read()
    with open(ca_path, "rb") as f:
        ca_crt = f.read()

    require_client = os.environ.get("MGMT_TLS_REQUIRE_CLIENT_CERT", "1") in ("1", "true", "yes")
    creds = grpc.ssl_server_credentials(
        [(server_key, server_crt)],
        root_certificates=ca_crt,
        require_client_auth=require_client,
    )
    logger.info(
        "mTLS 활성: cert_dir=%s require_client_auth=%s",
        cert_dir,
        require_client,
    )
    return creds


def _start_fms_sequencer_thread():
    """FMS 자동 진행 시퀀서를 daemon thread + asyncio loop 로 기동.

    V6 canonical (Phase B): Interface Service 로부터 이관됨.
    FMS_AUTOPLAY=1 일 때만 가동. 실기 연동 시 OFF.
    ROS2 publisher 는 MGMT_ROS2_ENABLED=1 + rclpy 설치 시 실 publish, 아니면 print 폴백.
    gRPC 서버는 ThreadPoolExecutor 기반이라 별도 이벤트 루프 스레드 필요.
    """
    import asyncio
    import threading

    if not fms_is_enabled():
        logger.info("FMS_AUTOPLAY 비활성 — 시퀀서 미가동 (실기 연동 모드)")
        print("[FMS] FMS_AUTOPLAY 비활성 — sequencer 미가동", flush=True)
        return None

    init_ros2()
    ros2_mode = "real" if is_real_ros2() else "mock-print"
    print(f"[FMS] FMS_AUTOPLAY=1 — sequencer 백그라운드 시작 (ROS2={ros2_mode})", flush=True)
    logger.info("FMS sequencer 백그라운드 시작 (ROS2 %s)", ros2_mode)

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_fms_sequencer())
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.exception("FMS sequencer 스레드 오류: %s", exc)
        finally:
            try:
                shutdown_ros2()
            except Exception:  # noqa: BLE001
                pass
            loop.close()

    t = threading.Thread(target=_run, daemon=True, name="fms-sequencer")
    t.start()
    return t


def serve() -> None:
    # WatchItems + WatchAlerts + WatchCameraFrames 등 스트리밍이 워커 점유.
    # 다중 PyQt 클라이언트 + 내부 모니터링 대비 여유있게 32로 확장.
    # keepalive: 죽은 클라이언트(단절된 TCP) 를 빠르게 정리. 구독자 수 가볍게 유지.
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=32),
        options=[
            ("grpc.keepalive_time_ms", 30000),
            ("grpc.keepalive_timeout_ms", 10000),
            ("grpc.keepalive_permit_without_calls", 1),
            ("grpc.http2.min_ping_interval_without_data_ms", 20000),
            ("grpc.http2.max_pings_without_data", 0),
        ],
    )
    management_pb2_grpc.add_ManagementServiceServicer_to_server(ManagementServicer(), server)
    management_pb2_grpc.add_ImagePublisherServiceServicer_to_server(
        ImagePublisherServicer(), server
    )
    bind_addr = f"{HOST}:{PORT}"

    creds = _load_tls_credentials()
    if creds is not None:
        server.add_secure_port(bind_addr, creds)
        scheme = "TLS"
    else:
        server.add_insecure_port(bind_addr)
        scheme = "INSECURE (V6 S-001: MGMT_GRPC_TLS_ENABLED=1 권장)"

    server.start()
    logger.info("Management Service listening on %s [%s]", bind_addr, scheme)

    # Phase B: FMS 자동 진행 시퀀서 (Interface 로부터 이관)
    _start_fms_sequencer_thread()

    # Graceful shutdown
    def _stop(_signum, _frame):
        logger.info("Shutting down...")
        server.stop(grace=5)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    serve()
