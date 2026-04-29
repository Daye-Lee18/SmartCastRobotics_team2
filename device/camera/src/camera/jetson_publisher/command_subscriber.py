"""Management → Jetson ESP32 command subscriber (V6 canonical Phase D-2).

canonical 통신 매트릭스:
  Management Service --gRPC(TCP) WatchConveyorCommands--> Jetson (이 모듈)
  Jetson --Serial 115200 (EspBridge.send_command)--> ESP32 (HW Controller)

본 모듈은 Management :50051 에 server-streaming RPC 로 상시 연결해 있으며,
수신한 ConveyorCommand 를 EspBridge outbound 큐로 넘긴다.

재연결 전략:
- gRPC RpcError (서버 재시작, 네트워크 단절) 발생 시 지수 백오프 1s → 60s
- shutdown_event.is_set() 시 즉시 종료

환경변수 (env.example 과 정렬):
    MGMT_COMMAND_STREAM_ENABLED   (default 0 — ESP_BRIDGE_ENABLED=1 과 함께 켜야 의미 있음)
    MGMT_COMMAND_SUBSCRIBER_ID    (default "jetson-orin-nx-01")
    MGMT_COMMAND_ROBOT_FILTER     (default "" — 전체 CONV-*/ESP-* 수신)
    MANAGEMENT_GRPC_HOST          (publisher.py 와 공유)
    MANAGEMENT_GRPC_PORT          (기본 50051)
    MGMT_GRPC_TLS_ENABLED         (기본 0)

@MX:ANCHOR: Phase D-2 — ESP32 제어 경로 Serial 통일의 Jetson 측 진입점.
@MX:WARN: Management 재시작 시 쌓였던 command 가 휘발됨 (In-memory 큐). 중요 명령은 재발사 필요.
"""

from __future__ import annotations

import logging
import os
import threading

log = logging.getLogger("jetson.command_subscriber")


RECONNECT_START_S = 1.0
RECONNECT_CAP_S = 60.0


class CommandSubscriber:
    """Management WatchConveyorCommands 구독 → ESP32 Serial relay."""

    def __init__(
        self,
        bridge,  # EspBridge (순환 import 회피 위해 타입 힌트 생략)
        shutdown_event: threading.Event,
        grpc_host: str = "localhost",
        grpc_port: int = 50051,
        subscriber_id: str = "jetson-orin-nx-01",
        robot_id_filter: str = "",
        tls_enabled: bool = False,
    ) -> None:
        self._bridge = bridge
        self._shutdown = shutdown_event
        self._grpc_host = grpc_host
        self._grpc_port = grpc_port
        self._subscriber_id = subscriber_id
        self._robot_id_filter = robot_id_filter
        self._tls_enabled = tls_enabled
        self._thread = threading.Thread(target=self._run, name="mgmt-cmd-subscriber", daemon=True)

    @classmethod
    def from_env(cls, bridge, shutdown_event: threading.Event) -> CommandSubscriber:
        return cls(
            bridge=bridge,
            shutdown_event=shutdown_event,
            grpc_host=os.environ.get("MANAGEMENT_GRPC_HOST", "localhost"),
            grpc_port=int(os.environ.get("MANAGEMENT_GRPC_PORT", "50051")),
            subscriber_id=os.environ.get("MGMT_COMMAND_SUBSCRIBER_ID", "jetson-orin-nx-01"),
            robot_id_filter=os.environ.get("MGMT_COMMAND_ROBOT_FILTER", ""),
            tls_enabled=os.environ.get("MGMT_GRPC_TLS_ENABLED", "0") in ("1", "true", "yes"),
        )

    def start(self) -> None:
        if self._thread.is_alive():
            return
        log.info(
            "CommandSubscriber 시작: target=%s:%d subscriber=%s filter=%s tls=%s",
            self._grpc_host,
            self._grpc_port,
            self._subscriber_id,
            self._robot_id_filter or "<all>",
            self._tls_enabled,
        )
        self._thread.start()

    # ---------- internal ----------
    def _run(self) -> None:
        backoff = RECONNECT_START_S
        while not self._shutdown.is_set():
            stub = self._build_stub()
            if stub is None:
                self._shutdown.wait(backoff)
                backoff = min(backoff * 2, RECONNECT_CAP_S)
                continue

            try:
                count = self._consume(stub)
                log.info("CommandSubscriber stream ended (received=%d)", count)
                backoff = RECONNECT_START_S  # 정상 종료 시 리셋
            except Exception as e:  # noqa: BLE001
                if self._shutdown.is_set():
                    break
                log.warning(
                    "CommandSubscriber stream 오류: %s (재연결 %.1fs)",
                    e,
                    backoff,
                )
                self._shutdown.wait(backoff)
                backoff = min(backoff * 2, RECONNECT_CAP_S)

        log.info("CommandSubscriber stopped")

    def _build_stub(self):
        """gRPC stub 생성. 실패 시 None."""
        try:
            import grpc  # type: ignore
            from generated import management_pb2_grpc  # type: ignore
        except ImportError as e:
            log.error("gRPC/proto import 실패: %s", e)
            return None
        target = f"{self._grpc_host}:{self._grpc_port}"
        try:
            if self._tls_enabled:
                creds = self._load_tls_credentials()
                channel = grpc.secure_channel(target, creds)
            else:
                channel = grpc.insecure_channel(target)
            return management_pb2_grpc.ManagementServiceStub(channel)
        except Exception as e:  # noqa: BLE001
            log.warning("gRPC channel 생성 실패 target=%s: %s", target, e)
            return None

    @staticmethod
    def _load_tls_credentials():
        import grpc  # type: ignore

        ca_path = os.environ.get("MGMT_TLS_CA_CRT")
        client_crt = os.environ.get("MGMT_TLS_CLIENT_CRT")
        client_key = os.environ.get("MGMT_TLS_CLIENT_KEY")
        ca = key = crt = None
        if ca_path and os.path.exists(ca_path):
            with open(ca_path, "rb") as f:
                ca = f.read()
        if client_crt and os.path.exists(client_crt):
            with open(client_crt, "rb") as f:
                crt = f.read()
        if client_key and os.path.exists(client_key):
            with open(client_key, "rb") as f:
                key = f.read()
        return grpc.ssl_channel_credentials(
            root_certificates=ca, private_key=key, certificate_chain=crt
        )

    def _consume(self, stub) -> int:
        """단일 스트림 수명주기. 연결 끊기면 예외 전파 → _run 이 재연결."""
        from generated import management_pb2  # type: ignore

        req = management_pb2.WatchConveyorCommandsRequest(
            subscriber_id=self._subscriber_id,
            robot_id_filter=self._robot_id_filter or "",
        )
        log.info("WatchConveyorCommands stream 개시")
        count = 0
        for cmd in stub.WatchConveyorCommands(req):
            if self._shutdown.is_set():
                break
            count += 1
            self._forward(cmd)
        return count

    def _forward(self, cmd) -> None:
        """수신한 ConveyorCommand → ESP32 Serial.

        현재 포맷: 명령 문자열만 그대로 전달 ("RUN", "STOP", "PING").
        ESP32 펌웨어가 JSON 지원 시 cmd.payload 를 함께 전송하도록 확장 가능.
        """
        robot_id = cmd.robot_id or "?"
        command = cmd.command or ""
        item_id = cmd.item_id or 0
        if not command:
            log.warning("empty command 수신 robot=%s — skip", robot_id)
            return
        log.info(
            "gRPC → Jetson cmd: robot=%s command=%s item=%d issued_by=%s",
            robot_id,
            command,
            item_id,
            cmd.issued_by or "-",
        )
        try:
            self._bridge.send_command(command)
        except Exception as e:  # noqa: BLE001
            log.exception("EspBridge.send_command 예외 %s: %s", command, e)
