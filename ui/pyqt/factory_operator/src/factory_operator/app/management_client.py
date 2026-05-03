"""Management Service gRPC 클라이언트 (Factory Operator PC 용).

V6 아키텍처 규정:
- PyQt 는 Interface Service(FastAPI :8000) 대신 Management Service(gRPC :50051) 직결
- Interface Service 장애/AWS 이관 시에도 공장 가동 유지
- 기존 api_client.py(HTTP) 는 WebSocket 수신과 비-Mgmt 조회용 (Phase 8 까지 점진 축소)

환경 변수:
    MANAGEMENT_GRPC_HOST   기본 localhost
    MANAGEMENT_GRPC_PORT   기본 50051
    MANAGEMENT_GRPC_TIMEOUT 기본 5.0 (초)

호출은 동기. PyQt GUI 스레드 차단을 피하려면 QThread / QThreadPool 워커에서 호출.

@MX:NOTE: Phase 4 산출물. schedule.py [▶ 생산 시작] 버튼이 본 클라이언트의 start_production 호출.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from dataclasses import dataclass

import grpc

# protoc 산출물 (monitoring/app/generated/, Makefile: monitoring/scripts/gen_proto.sh)
from app.generated import management_pb2, management_pb2_grpc

logger = logging.getLogger(__name__)

HOST = os.environ.get("MANAGEMENT_GRPC_HOST", "localhost")
PORT = int(os.environ.get("MANAGEMENT_GRPC_PORT", "50051"))
TIMEOUT = float(os.environ.get("MANAGEMENT_GRPC_TIMEOUT", "5.0"))


# ---------- 사용자 친화 DTO (proto 타입 직접 노출 회피) ----------


@dataclass
class ProductionStartOrderAck:
    """StartProduction 주문별 결과 1건."""

    ord_id: int
    accepted: bool
    reason: str
    item_id: int
    equip_task_txn_id: int


_STATUS_CODE = {1: "QUE", 2: "PROC", 3: "SUCC", 4: "FAIL"}
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


def _ack_from_proto(proto_ack) -> ProductionStartOrderAck:
    return ProductionStartOrderAck(
        ord_id=proto_ack.ord_id,
        accepted=proto_ack.accepted,
        reason=proto_ack.reason or "",
        item_id=proto_ack.item_id,
        equip_task_txn_id=proto_ack.equip_task_txn_id,
    )


def _legacy_wo_to_ack(proto_wo) -> ProductionStartOrderAck:
    return ProductionStartOrderAck(
        ord_id=int(proto_wo.order_id or 0),
        accepted=True,
        reason=_STATUS_CODE.get(proto_wo.status, "QUE"),
        item_id=proto_wo.id,
        equip_task_txn_id=0,
    )


class ManagementClient:
    """Management Service 호출 래퍼.

    사용 예:
        client = ManagementClient()
        acks = client.start_production(["2026"])
        for ack in acks:
            print(ack.ord_id, ack.accepted, ack.reason)
    """

    def __init__(self, host: str = HOST, port: int = PORT, timeout: float = TIMEOUT) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._channel = self._build_channel(host, port)
        self._stub = management_pb2_grpc.ManagementServiceStub(self._channel)

    @staticmethod
    def _build_channel(host: str, port: int):
        """V6 S-001: TLS 환경변수 활성 시 secure_channel, 아니면 insecure.

        환경변수:
            MGMT_GRPC_TLS_ENABLED  = 1 면 TLS 활성
            MGMT_TLS_CERT_DIR      = cert 디렉터리 (기본 backend/management/certs)
            MGMT_TLS_CA_CRT        = CA cert (기본 ${CERT_DIR}/ca.crt)
            MGMT_TLS_CLIENT_KEY    = 클라이언트 private key (기본 ${CERT_DIR}/client.key)
            MGMT_TLS_CLIENT_CRT    = 클라이언트 cert (기본 ${CERT_DIR}/client.crt)
            MGMT_TLS_SERVER_NAME   = TLS SNI override (기본 host 값)
        """
        target = f"{host}:{port}"
        # keep-alive ping: 서버/네트워크 끊김을 빠르게 감지 (특히 장기 streaming RPC 용)
        keepalive = [
            ("grpc.keepalive_time_ms", 30000),
            ("grpc.keepalive_timeout_ms", 10000),
            ("grpc.keepalive_permit_without_calls", 1),
            ("grpc.http2.max_pings_without_data", 0),
        ]
        if os.environ.get("MGMT_GRPC_TLS_ENABLED", "0") not in ("1", "true", "yes"):
            return grpc.insecure_channel(target, options=keepalive)

        # mTLS 활성: client cert 로딩
        # 기본 cert 디렉터리: monitoring/ 옆의 backend/management/certs/
        default_cert_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "backend", "management", "certs")
        )
        cert_dir = os.environ.get("MGMT_TLS_CERT_DIR", default_cert_dir)
        ca_path = os.environ.get("MGMT_TLS_CA_CRT", os.path.join(cert_dir, "ca.crt"))
        key_path = os.environ.get("MGMT_TLS_CLIENT_KEY", os.path.join(cert_dir, "client.key"))
        crt_path = os.environ.get("MGMT_TLS_CLIENT_CRT", os.path.join(cert_dir, "client.crt"))

        for p in (ca_path, key_path, crt_path):
            if not os.path.exists(p):
                raise FileNotFoundError(f"TLS 활성화됐으나 cert 파일 없음: {p}")

        with open(ca_path, "rb") as f:
            ca = f.read()
        with open(key_path, "rb") as f:
            client_key = f.read()
        with open(crt_path, "rb") as f:
            client_crt = f.read()

        creds = grpc.ssl_channel_credentials(
            root_certificates=ca,
            private_key=client_key,
            certificate_chain=client_crt,
        )
        options = list(keepalive)
        sni = os.environ.get("MGMT_TLS_SERVER_NAME")
        if sni:
            options.append(("grpc.ssl_target_name_override", sni))
        logger.info("ManagementClient TLS 활성: %s (sni=%s)", target, sni or host)
        return grpc.secure_channel(target, creds, options=options)

    @property
    def endpoint(self) -> str:
        return f"{self._host}:{self._port}"

    def health(self) -> bool:
        """Mgmt Service 연결 가능 여부."""
        try:
            self._stub.Health(management_pb2.Empty(), timeout=2.0)
            return True
        except grpc.RpcError as e:
            logger.warning("Management health check failed: %s", e)
            return False

    def start_production(self, order_ids: list[str]) -> list[ProductionStartOrderAck]:
        """승인 주문들을 생산 개시. 주문별 ack 리스트 반환.

        Raises:
            grpc.RpcError: 서버 에러/연결 실패 등 (호출자가 try/except 처리)
            ValueError: 빈 order_ids (서버에서 INVALID_ARGUMENT 응답)
        """
        if not order_ids:
            raise ValueError("order_ids 가 비어있습니다")
        req = management_pb2.StartProductionRequest(order_ids=order_ids)
        resp = self._stub.StartProduction(req, timeout=self._timeout)
        if resp.HasField("ack") and resp.ack.orders:
            return [_ack_from_proto(order_ack) for order_ack in resp.ack.orders]
        return [_legacy_wo_to_ack(wo) for wo in resp.work_orders]

    def list_items(self, order_id: str | None = None, limit: int = 100):
        """현재 활성 item 목록. proto Item 메시지 그대로 반환."""
        req = management_pb2.ListItemsRequest(order_id=order_id or "", limit=limit)
        resp = self._stub.ListItems(req, timeout=self._timeout)
        return list(resp.items)

    def watch_items(self, order_id: str | None = None) -> Iterator:
        """Server streaming. 무한 루프 — 별도 QThread 에서 소비."""
        req = management_pb2.WatchItemsRequest(order_id=order_id or "")
        return self._stub.WatchItems(req)

    def watch_alerts(self, severity_filter: str | None = None) -> Iterator:
        """alerts 테이블 신규 row 스트림. 별도 QThread 에서 소비."""
        req = management_pb2.WatchAlertsRequest(severity_filter=severity_filter or "")
        return self._stub.WatchAlerts(req)

    def get_robot_status(self) -> list[dict]:
        """AMR/Cobot 실시간 상태 조회. dict list 반환."""
        try:
            req = management_pb2.GetRobotStatusRequest()
            resp = self._stub.GetRobotStatus(req, timeout=self._timeout)
            return [
                {
                    "id": r.id,
                    "type": "amr" if r.type == 1 else "cobot" if r.type == 2 else "unknown",
                    "host": r.host,
                    "status": r.status,
                    "battery": round(r.battery, 1),
                    "voltage": round(r.voltage, 3),
                    "location": r.location,
                    "task_state": r.task_state,
                    "task_id": r.task_id or "",
                    "loaded_item": r.loaded_item or "",
                }
                for r in resp.robots
            ]
        except grpc.RpcError as e:
            logger.warning("GetRobotStatus 실패: %s", e)
            return []

    @staticmethod
    def stage_code_to_label(code: int) -> str:
        """proto enum 정수 → 코드 문자열 (UI 매핑용)."""
        return _STAGE_CODE.get(code, "UNSPECIFIED")

    def close(self) -> None:
        self._channel.close()
