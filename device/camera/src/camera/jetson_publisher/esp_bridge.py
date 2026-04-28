"""ESP32 Serial Bridge — Jetson ↔ Conveyor 펌웨어(v5) 이벤트 중계.

V6 아키텍처 (2026-04-15 업데이트 · 2026-04-17 SPEC-AMR-001 추가):
    [ESP32 conveyor v1.4.0] --USB Serial 115200 ASCII-- [Jetson publisher]

본 모듈은 publisher.py 와 **같은 프로세스** 내 별도 스레드로 실행.
- RX(ESP→Jetson): STATE/STOPPED/STARTED/DONE/PONG/SENSOR* / HANDOFF_ACK
- TX(Jetson→ESP): RUN/STOP/PING/STATUS 등 명령 송신
- 핵심 이벤트:
    · "STOPPED" 수신 → (지연 INSPECTION_DELAY_MS) → "RUN\\n" 송신
        - 지연 동안 publisher 가 적어도 1 프레임을 서버로 push 완료한다는 가정
        - 2 fps 기준 기본 500 ms + 여유 → 기본 700 ms
    · "HANDOFF_ACK" 수신 (SPEC-AMR-001) → Management Service ReportHandoffAck gRPC
        - 메모리 버퍼 32 이벤트 + 지수 백오프 1s→60s 재시도
        - idempotency_key = "source_device:ts_millis" 로 중복 방지
- 재연결: Serial 끊기면 10s backoff

환경변수:
    ESP_BRIDGE_ENABLED           기본 0 (opt-in). 1 이면 스레드 기동
    ESP_BRIDGE_PORT              기본 /dev/ttyUSB0
    ESP_BRIDGE_BAUD              기본 115200
    ESP_BRIDGE_AUTO_RUN          기본 1 (STOPPED 시 자동 RUN 송신). 0 이면 로그만
    ESP_BRIDGE_INSPECTION_DELAY_MS  기본 700 (STOPPED 후 RUN 까지 대기)
    ESP_BRIDGE_DEVICE_ID         기본 ESP-CONVEYOR-01 (HandoffAck source_device)
    MANAGEMENT_GRPC_TARGET       기본 localhost:50051 (gRPC ReportHandoffAck 전송지)
    MANAGEMENT_GRPC_DISABLED     기본 0. 1 이면 gRPC 스텁 없이도 로그만

@MX:NOTE STOPPED 순간의 "정확한 한 프레임" 보장이 필요하면 publisher 와 이벤트 동기
        메커니즘(threading.Event) 을 추가하세요. 현재 MVP 는 시간 기반 지연으로 단순화.
@MX:WARN publisher 가 /dev/ttyUSB0 을 쓰지 않음 (카메라는 /dev/video0). 충돌 없음.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass

log = logging.getLogger("jetson.esp_bridge")


# SPEC-AMR-001: 버퍼링 큐 용량 / 지수 백오프 상한
HANDOFF_BUFFER_MAX = 32
HANDOFF_BACKOFF_START_S = 1.0
HANDOFF_BACKOFF_CAP_S = 60.0


@dataclass
class PendingHandoff:
    """gRPC 전송 대기 중인 HandoffAck 이벤트."""

    source_device: str
    zone: str
    occurred_at_millis: int  # ESP32 millis() (reboot 시 리셋되지만 idempotency 용도)
    idempotency_key: str


@dataclass
class PendingConveyorEvent:
    """gRPC 전송 대기 중인 ConveyorEvent (TOF1/TOF2)."""

    res_id: str
    event_type: str  # "tof1_entry" | "tof2_exit"
    occurred_at_millis: int
    idempotency_key: str


class EspBridge:
    """ESP32 serial 브리지 스레드."""

    def __init__(
        self,
        shutdown_event: threading.Event,
        port: str = "/dev/ttyUSB0",
        baud: int = 115200,
        auto_run: bool = True,
        inspection_delay_ms: int = 700,
        reconnect_sec: float = 10.0,
        device_id: str = "ESP-CONVEYOR-01",
        grpc_target: str = "localhost:50051",
        grpc_disabled: bool = False,
    ) -> None:
        self._shutdown = shutdown_event
        self._port = port
        self._baud = baud
        self._auto_run = auto_run
        self._inspection_delay = inspection_delay_ms / 1000.0
        self._reconnect = reconnect_sec
        self._device_id = device_id
        self._grpc_target = grpc_target
        self._grpc_disabled = grpc_disabled
        self._handoff_queue: deque[PendingHandoff] = deque(maxlen=HANDOFF_BUFFER_MAX)
        self._handoff_lock = threading.Lock()
        # 2026-04-26: 컨베이어 TOF 이벤트 큐 (handoff 와 동일 패턴)
        self._conveyor_queue: deque[PendingConveyorEvent] = deque(maxlen=HANDOFF_BUFFER_MAX)
        self._conveyor_lock = threading.Lock()
        # 환경변수 ESP_BRIDGE_CONVEYOR_RES_ID (default CONV-01) — STATE → res_id 매핑
        self._conveyor_res_id = os.environ.get("ESP_BRIDGE_CONVEYOR_RES_ID", "CONV-01")
        # Phase D-2 (V6 canonical): Management → Jetson → ESP32 명령 relay 큐.
        # CommandSubscriber 가 send_command(cmd) 로 enqueue 하면 _session 루프가 Serial 로 drain.
        self._tx_queue: deque[str] = deque()
        self._tx_lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, name="esp-bridge", daemon=True)
        self._handoff_thread = threading.Thread(
            target=self._handoff_drain_loop, name="esp-handoff-drain", daemon=True
        )
        self._conveyor_thread = threading.Thread(
            target=self._conveyor_drain_loop, name="esp-conveyor-drain", daemon=True
        )

    @classmethod
    def from_env(cls, shutdown_event: threading.Event) -> EspBridge:
        return cls(
            shutdown_event=shutdown_event,
            port=os.environ.get("ESP_BRIDGE_PORT", "/dev/ttyUSB0"),
            baud=int(os.environ.get("ESP_BRIDGE_BAUD", "115200")),
            auto_run=os.environ.get("ESP_BRIDGE_AUTO_RUN", "1") in ("1", "true", "yes"),
            inspection_delay_ms=int(os.environ.get("ESP_BRIDGE_INSPECTION_DELAY_MS", "700")),
            device_id=os.environ.get("ESP_BRIDGE_DEVICE_ID", "ESP-CONVEYOR-01"),
            grpc_target=os.environ.get("MANAGEMENT_GRPC_TARGET", "localhost:50051"),
            grpc_disabled=os.environ.get("MANAGEMENT_GRPC_DISABLED", "0") in ("1", "true", "yes"),
        )

    def start(self) -> None:
        if self._thread.is_alive():
            return
        log.info(
            "EspBridge 시작: port=%s baud=%d auto_run=%s delay=%.2fs device=%s grpc=%s",
            self._port,
            self._baud,
            self._auto_run,
            self._inspection_delay,
            self._device_id,
            "disabled" if self._grpc_disabled else self._grpc_target,
        )
        self._thread.start()
        self._handoff_thread.start()
        self._conveyor_thread.start()

    # ---------- internal ----------
    def _run(self) -> None:
        try:
            import serial  # lazy
        except ImportError:
            log.error("pyserial 미설치. `pip install pyserial` 필요")
            return

        while not self._shutdown.is_set():
            ser = None
            try:
                ser = serial.Serial(self._port, self._baud, timeout=0.5)
                # ESP32 DTR 토글에 의한 reset 대기 + 부팅 라인 버림
                time.sleep(1.5)
                ser.reset_input_buffer()
                log.info("EspBridge connected to %s @ %d", self._port, self._baud)
                self._session(ser)
            except Exception as e:  # noqa: BLE001
                if self._shutdown.is_set():
                    break
                log.warning("EspBridge serial 오류: %s (재연결 %.1fs)", e, self._reconnect)
                self._shutdown.wait(self._reconnect)
            finally:
                if ser is not None:
                    try:
                        ser.close()
                    except Exception:  # noqa: BLE001
                        pass
        log.info("EspBridge stopped")

    def _session(self, ser) -> None:
        """개방된 serial 세션에서 라인 단위 이벤트 처리 + outbound 큐 drain."""
        buf = bytearray()
        while not self._shutdown.is_set():
            chunk = ser.read(64)
            if chunk:
                buf += chunk
                while b"\n" in buf:
                    line_b, _, rest = buf.partition(b"\n")
                    buf = bytearray(rest)
                    line = line_b.decode(errors="replace").strip()
                    if line:
                        self._handle_line(ser, line)
            # Phase D-2: Management 에서 수신한 명령을 Serial 로 relay
            self._drain_tx(ser)

    # ---------- Outbound command relay (Phase D-2: Management → ESP32) ----------
    def send_command(self, cmd: str) -> None:
        """외부 스레드(CommandSubscriber)가 호출. Serial 접근은 _session 루프가 drain.

        cmd 끝에 newline 없으면 자동 추가. 큰 payload 는 분할 전송하지 않음 (ESP32 버퍼 한계 주의).
        """
        if not cmd:
            return
        normalized = cmd if cmd.endswith("\n") else cmd + "\n"
        with self._tx_lock:
            self._tx_queue.append(normalized)

    def _drain_tx(self, ser) -> None:
        """큐의 모든 outbound 명령을 Serial 로 flush. 스레드-안전."""
        with self._tx_lock:
            if not self._tx_queue:
                return
            pending = list(self._tx_queue)
            self._tx_queue.clear()
        for line in pending:
            try:
                ser.write(line.encode("utf-8"))
                ser.flush()
                log.info("Jetson → ESP32 cmd: %s", line.strip())
            except Exception as e:  # noqa: BLE001
                log.warning("outbound cmd 송신 실패: %s (%s)", line.strip(), e)

    def _handle_line(self, ser, line: str) -> None:
        if line == "STOPPED":
            log.info("ESP → STOPPED (inspection trigger)")
            if self._auto_run:
                # publisher 가 현재 프레임을 서버로 push 할 시간 부여
                time.sleep(self._inspection_delay)
                try:
                    ser.write(b"RUN\n")
                    ser.flush()
                    log.info("Jetson → RUN (after %.2fs delay)", self._inspection_delay)
                except Exception as e:  # noqa: BLE001
                    log.warning("RUN 송신 실패: %s", e)
            else:
                log.info("auto_run=0, STOPPED 대기만 (수동 RUN 필요)")
        elif line == "STARTED":
            log.info("ESP → STARTED (motor on)")
        elif line == "DONE":
            log.info("ESP → DONE (motor off after 4s)")
        elif line.startswith("BOOT:"):
            log.info("ESP bootup: %s", line)
        elif line.startswith("STATE:"):
            # 2026-04-26: STATE:RUNNING (TOF1 entry) / STATE:STOPPED (TOF2 exit) → ConveyorEvent
            state_name = line.split(":", 1)[1].strip()
            event_type: str | None = None
            if state_name == "RUNNING":
                event_type = "tof1_entry"
            elif state_name == "STOPPED":
                event_type = "tof2_exit"

            if event_type is not None:
                now_ms = int(time.time() * 1000)
                pending = PendingConveyorEvent(
                    res_id=self._conveyor_res_id,
                    event_type=event_type,
                    occurred_at_millis=now_ms,
                    idempotency_key=f"{self._conveyor_res_id}:{event_type}:{now_ms}",
                )
                with self._conveyor_lock:
                    if len(self._conveyor_queue) >= HANDOFF_BUFFER_MAX:
                        dropped = self._conveyor_queue.popleft()
                        log.warning(
                            "ConveyorEvent 버퍼 overflow — 가장 오래된 이벤트 폐기 (key=%s)",
                            dropped.idempotency_key,
                        )
                    self._conveyor_queue.append(pending)
                log.info(
                    "ESP → STATE:%s → %s queued (key=%s)",
                    state_name,
                    event_type,
                    pending.idempotency_key,
                )
            else:
                log.debug("ESP state: %s", line)
        elif line.startswith("PONG"):
            log.debug("ESP pong")
        elif line.startswith("ERR:"):
            log.warning("ESP error: %s", line)
        elif line == "HANDOFF_ACK":
            # SPEC-AMR-001: 후처리존 핸드오프 버튼 이벤트 수신.
            # JSON 동반 라인 (ts 포함) 은 JSON 파싱이 비효율 → millis 는 현재 시각 기반으로 대체.
            # ESP32 리부트 시 millis 리셋되지만 idempotency_key 는 source_device + wall_time 로 유일.
            now_ms = int(time.time() * 1000)
            pending = PendingHandoff(
                source_device=self._device_id,
                zone="postprocessing",
                occurred_at_millis=now_ms,
                idempotency_key=f"{self._device_id}:{now_ms}",
            )
            with self._handoff_lock:
                if len(self._handoff_queue) >= HANDOFF_BUFFER_MAX:
                    dropped = self._handoff_queue.popleft()
                    log.warning(
                        "Handoff 버퍼 overflow — 가장 오래된 이벤트 폐기 (key=%s)",
                        dropped.idempotency_key,
                    )
                self._handoff_queue.append(pending)
            log.info(
                "ESP → HANDOFF_ACK (queued key=%s, qsize=%d)",
                pending.idempotency_key,
                len(self._handoff_queue),
            )
        else:
            log.debug("ESP line: %s", line)

    # ---------- Handoff ACK drain (SPEC-AMR-001) ----------
    def _handoff_drain_loop(self) -> None:
        """큐에 쌓인 HandoffAck 이벤트를 Management gRPC 로 전송.

        지수 백오프 1s → 60s. gRPC 실패 시 큐 맨 앞 항목 유지, 성공 시 제거.
        """
        backoff = HANDOFF_BACKOFF_START_S
        stub = self._build_grpc_stub()

        while not self._shutdown.is_set():
            with self._handoff_lock:
                if not self._handoff_queue:
                    item: PendingHandoff | None = None
                else:
                    item = self._handoff_queue[0]

            if item is None:
                self._shutdown.wait(0.5)
                continue

            if self._grpc_disabled or stub is None:
                log.info(
                    "Handoff drain: gRPC disabled/unavailable — 큐 유지 (key=%s)",
                    item.idempotency_key,
                )
                self._shutdown.wait(5.0)
                # stub 재시도
                if not self._grpc_disabled:
                    stub = self._build_grpc_stub()
                continue

            try:
                self._send_handoff_ack(stub, item)
                with self._handoff_lock:
                    if self._handoff_queue and self._handoff_queue[0] is item:
                        self._handoff_queue.popleft()
                log.info("Handoff ACK 전송 성공 key=%s", item.idempotency_key)
                backoff = HANDOFF_BACKOFF_START_S  # 성공 시 리셋
            except Exception as e:  # noqa: BLE001
                log.warning(
                    "Handoff ACK 전송 실패 (backoff %.1fs): %s key=%s",
                    backoff,
                    e,
                    item.idempotency_key,
                )
                self._shutdown.wait(backoff)
                backoff = min(backoff * 2, HANDOFF_BACKOFF_CAP_S)
                # stub 재생성 (연결 복구 시도)
                stub = self._build_grpc_stub()

    def _build_grpc_stub(self):
        """Management Service gRPC stub. import/연결 실패 시 None."""
        if self._grpc_disabled:
            return None
        try:
            import grpc  # type: ignore

            # jetson_publisher/generated/ 는 PYTHONPATH 에 이미 있음 (publisher.py 에서 설정)
            from generated import management_pb2_grpc  # type: ignore

            channel = grpc.insecure_channel(self._grpc_target)
            return management_pb2_grpc.ManagementServiceStub(channel)
        except Exception as e:  # noqa: BLE001
            log.warning("gRPC stub 생성 실패: %s", e)
            return None

    def _send_handoff_ack(self, stub, item: PendingHandoff) -> None:
        """gRPC ReportHandoffAck 호출. 실패 시 예외 전파 (drain 루프가 재시도)."""
        from generated import management_pb2  # type: ignore

        req = management_pb2.HandoffAckEvent(
            source_device=item.source_device,
            zone=item.zone,
            occurred_at=management_pb2.Timestamp(
                iso8601=time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime(item.occurred_at_millis / 1000.0),
                ),
            ),
            idempotency_key=item.idempotency_key,
        )
        resp = stub.ReportHandoffAck(req, timeout=3.0)
        log.info(
            "ReportHandoffAck 응답: accepted=%s reason=%s task_id=%s amr_id=%s",
            resp.accepted,
            resp.reason,
            resp.task_id,
            resp.amr_id,
        )

    # ---------- Conveyor Event drain (TOF1/TOF2 → Mgmt gRPC) ----------
    def _conveyor_drain_loop(self) -> None:
        """큐에 쌓인 ConveyorEvent 를 Management gRPC 로 전송 (handoff 와 동일 패턴)."""
        backoff = HANDOFF_BACKOFF_START_S
        stub = self._build_grpc_stub()

        while not self._shutdown.is_set():
            with self._conveyor_lock:
                if not self._conveyor_queue:
                    item: PendingConveyorEvent | None = None
                else:
                    item = self._conveyor_queue[0]

            if item is None:
                self._shutdown.wait(0.5)
                continue

            if self._grpc_disabled or stub is None:
                log.info(
                    "Conveyor drain: gRPC disabled/unavailable — 큐 유지 (key=%s)",
                    item.idempotency_key,
                )
                self._shutdown.wait(5.0)
                if not self._grpc_disabled:
                    stub = self._build_grpc_stub()
                continue

            try:
                self._send_conveyor_event(stub, item)
                with self._conveyor_lock:
                    if self._conveyor_queue and self._conveyor_queue[0] is item:
                        self._conveyor_queue.popleft()
                log.info("ConveyorEvent 전송 성공 key=%s", item.idempotency_key)
                backoff = HANDOFF_BACKOFF_START_S
            except Exception as e:  # noqa: BLE001
                log.warning(
                    "ConveyorEvent 전송 실패 (backoff %.1fs): %s key=%s",
                    backoff,
                    e,
                    item.idempotency_key,
                )
                self._shutdown.wait(backoff)
                backoff = min(backoff * 2, HANDOFF_BACKOFF_CAP_S)
                stub = self._build_grpc_stub()

    def _send_conveyor_event(self, stub, item: PendingConveyorEvent) -> None:
        """gRPC ReportConveyorEvent 호출."""
        from generated import management_pb2  # type: ignore

        req = management_pb2.ConveyorEvent(
            res_id=item.res_id,
            event_type=item.event_type,
            occurred_at=management_pb2.Timestamp(
                iso8601=time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime(item.occurred_at_millis / 1000.0),
                ),
            ),
            idempotency_key=item.idempotency_key,
        )
        resp = stub.ReportConveyorEvent(req, timeout=3.0)
        log.info(
            "ReportConveyorEvent 응답: accepted=%s item_id=%s cur_stat=%s reason=%s",
            resp.accepted,
            resp.item_id,
            resp.item_cur_stat,
            resp.reason,
        )
