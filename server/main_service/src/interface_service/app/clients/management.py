"""Management Service gRPC client — Interface Service → Management 화살표 실체화.

V6 canonical 아키텍처 Phase 4 (Phase C-1): Interface Service(FastAPI, :8000) 가
Management Service(gRPC, :50051) 를 호출할 때 사용하는 싱글톤 stub.

현재 범위 (Phase C-1):
  - Health RPC proxy (canonical 화살표 1건 실체화)
  - Graceful degradation: Management 미가동 시 ManagementUnavailable 예외 → 503 응답

향후 (Phase C-2, 별도 SPEC 필요):
  - StartProduction / ListItems / WatchItems 등 write/read 경로 proxy
  - Management TaskManager 의 smartcast v2 스키마 정합 완료가 전제 조건

환경변수:
  MANAGEMENT_GRPC_HOST     기본 localhost
  MANAGEMENT_GRPC_PORT     기본 50051
  MANAGEMENT_GRPC_TIMEOUT  기본 3.0 (초)
  MGMT_GRPC_TLS_ENABLED    1 이면 mTLS (Management 서버와 동일 cert 사용)
"""

from __future__ import annotations

import logging
import os
import sys
import threading

import grpc

logger = logging.getLogger("app.clients.management")

# Management 의 proto 산출물은 backend/management/ 에 있음 — sys.path 에 등록.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
_MGMT_DIR = os.path.join(_BACKEND_DIR, "management")
if _MGMT_DIR not in sys.path:
    sys.path.insert(0, _MGMT_DIR)

try:
    import management_pb2  # type: ignore
    import management_pb2_grpc  # type: ignore

    _PROTO_AVAILABLE = True
except ImportError as exc:
    logger.warning(
        "Management proto stubs unavailable (%s) — 'make proto' in backend/management 필요", exc
    )
    management_pb2 = None  # type: ignore
    management_pb2_grpc = None  # type: ignore
    _PROTO_AVAILABLE = False


HOST = os.environ.get("MANAGEMENT_GRPC_HOST", "localhost")
PORT = int(os.environ.get("MANAGEMENT_GRPC_PORT", "50051"))
TIMEOUT = float(os.environ.get("MANAGEMENT_GRPC_TIMEOUT", "3.0"))


class ManagementUnavailable(RuntimeError):
    """Management Service 미가동 / proto stubs 없음 / 타임아웃 등."""


class ManagementClient:
    """Interface Service → Management Service gRPC 싱글톤.

    채널은 lazy 로 생성하고 프로세스 lifetime 동안 재사용.
    장애 시 ManagementUnavailable 을 던져 FastAPI route 에서 503 으로 매핑.
    """

    _instance: ManagementClient | None = None
    _lock = threading.Lock()

    def __init__(self, host: str = HOST, port: int = PORT, timeout: float = TIMEOUT) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._channel: grpc.Channel | None = None
        self._stub = None  # ManagementServiceStub lazy 생성

    @classmethod
    def get(cls) -> ManagementClient:
        """프로세스 전역 싱글톤."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @property
    def endpoint(self) -> str:
        return f"{self._host}:{self._port}"

    def _ensure_channel(self) -> None:
        if not _PROTO_AVAILABLE:
            raise ManagementUnavailable(
                "proto stubs not compiled — run 'make proto' in backend/management"
            )
        if self._channel is None:
            target = self.endpoint
            if os.environ.get("MGMT_GRPC_TLS_ENABLED", "0") in ("1", "true", "yes"):
                creds = self._load_tls_credentials()
                self._channel = grpc.secure_channel(target, creds)
                logger.info("Management gRPC 채널 생성 (TLS): %s", target)
            else:
                self._channel = grpc.insecure_channel(target)
                logger.info("Management gRPC 채널 생성 (insecure): %s", target)
            self._stub = management_pb2_grpc.ManagementServiceStub(self._channel)

    @staticmethod
    def _load_tls_credentials() -> grpc.ChannelCredentials:
        cert_dir = os.environ.get("MGMT_TLS_CERT_DIR", os.path.join(_MGMT_DIR, "certs"))
        ca_path = os.environ.get("MGMT_TLS_CA_CRT", os.path.join(cert_dir, "ca.crt"))
        client_key_path = os.environ.get(
            "MGMT_TLS_CLIENT_KEY", os.path.join(cert_dir, "client.key")
        )
        client_crt_path = os.environ.get(
            "MGMT_TLS_CLIENT_CRT", os.path.join(cert_dir, "client.crt")
        )
        with open(ca_path, "rb") as f:
            ca = f.read()
        key = crt = None
        if os.path.exists(client_key_path) and os.path.exists(client_crt_path):
            with open(client_key_path, "rb") as f:
                key = f.read()
            with open(client_crt_path, "rb") as f:
                crt = f.read()
        return grpc.ssl_channel_credentials(
            root_certificates=ca, private_key=key, certificate_chain=crt
        )

    def health(self) -> None:
        """Management Health RPC 호출. 정상=반환, 장애=ManagementUnavailable."""
        try:
            self._ensure_channel()
            assert self._stub is not None
            self._stub.Health(management_pb2.Empty(), timeout=self._timeout)
        except grpc.RpcError as exc:
            raise ManagementUnavailable(
                f"Management {self.endpoint} unreachable: {exc.code()}"
            ) from exc

    def start_production(self, ord_id: int):
        """SPEC-C2 Iteration 3: smartcast v2 단건 생산 개시 proxy.

        Returns: proto StartProductionResult (ord_id, item_id, equip_task_txn_id, message)
        Raises:
            ValueError — ord_id 무효 / 존재하지 않음 / 패턴 미등록 (gRPC INVALID_ARGUMENT)
            ManagementUnavailable — Mgmt 미가동 또는 timeout
        """
        try:
            self._ensure_channel()
            assert self._stub is not None
            resp = self._stub.StartProduction(
                management_pb2.StartProductionRequest(ord_id=int(ord_id)),
                timeout=self._timeout,
            )
        except grpc.RpcError as exc:
            code = exc.code() if hasattr(exc, "code") else None
            if code == grpc.StatusCode.INVALID_ARGUMENT:
                raise ValueError(exc.details() or "invalid argument") from exc
            raise ManagementUnavailable(
                f"StartProduction failed ({code}): {exc.details() if hasattr(exc, 'details') else exc}"
            ) from exc
        # Legacy result field may be empty while canonical ack is populated.
        result = getattr(resp, "result", None)
        if (
            result is not None
            and (
                getattr(result, "ord_id", 0)
                or getattr(result, "item_id", 0)
                or getattr(result, "equip_task_txn_id", 0)
                or getattr(result, "message", "")
            )
        ):
            return result

        ack = getattr(resp, "ack", None)
        if ack is not None and getattr(ack, "orders", None):
            first = ack.orders[0]

            class _Result:
                ord_id = first.ord_id
                item_id = first.item_id
                equip_task_txn_id = first.equip_task_txn_id
                message = first.reason or ack.message or ""

            return _Result()

        raise ManagementUnavailable("StartProduction returned no result payload")

    def close(self) -> None:
        if self._channel is not None:
            try:
                self._channel.close()
            except Exception:  # noqa: BLE001
                pass
            self._channel = None
            self._stub = None


def get_management_client() -> ManagementClient:
    """FastAPI dependency-injection 용 헬퍼 (Depends(get_management_client))."""
    return ManagementClient.get()
