#!/usr/bin/env python3
"""Jetson HID 바코드 리더 → Management gRPC 실시간 적재.

워크플로우:
    1. `/dev/input/event5` (by-id 심볼릭 링크 권장) 에서 바코드 HID 이벤트 수신
    2. KEY_* 시퀀스 → 문자열 조립 (Enter/KPEnter 에서 분할)
    3. Management Service `ReportRfidScan` gRPC 호출
       - reader_id: "BARCODE-JETSON-01" (RFID 리더와 구분)
       - raw_payload: 디코딩된 바코드 텍스트
       - idempotency_key: `BARCODE-JETSON-01:<utc_ms>`
    4. DB `public.rfid_scan_log` 에 append-only 저장 (서버 측 처리)

사용 시나리오:
    Jetson 에서 데몬처럼 실행 → 사용자가 바코드 스캔하는 즉시 DB 에 row 생성.
    RFID 와 같은 regex (order_N_item_YYYYMMDD_M) 를 사용하므로 rfid_scan_log
    의 기존 스키마 그대로 활용. 추후 BARCODE-* reader_id 로 필터링 가능.

사용:
    python3 tools/barcode_live_ingest.py

    # 옵션:
    python3 tools/barcode_live_ingest.py \\
        --mgmt-host 100.77.239.25 --mgmt-port 50051 \\
        --reader-id BARCODE-JETSON-01 \\
        --zone conveyor_in \\
        --device /dev/input/by-id/usb-USB_Adapter_USB_Device-event-kbd

    # 종료: Ctrl+C

의존:
    python3 -m pip install --user evdev grpcio-tools==1.59.5
    management_pb2*.py 파일 (mgmt_grpc/ 디렉터리) 미리 생성 필요:
        python3 -m grpc_tools.protoc -I. --python_out=mgmt_grpc \\
            --grpc_python_out=mgmt_grpc management.proto

연관 문서:
    docs/barcode_jetson_ready.md
    backend/management/services/rfid_service.py (서버 측 처리 로직)
    SPEC-RFID-001 Wave 2
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# barcode_probe.py 의 KEY→char 매핑 재사용 (동일 파일 디렉터리)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from barcode_probe import (  # type: ignore
    DEFAULT_DEVICE,
    END_KEYS,
    _assemble,
    _check_permission,
    _import_evdev,
    _resolve_device,
)

# mgmt_grpc/ (로컬 Jetson 에서 protoc 로 생성) import 경로 등록
_MGMT_GRPC_DIR = Path.home() / "casting-factory" / "mgmt_grpc"
if _MGMT_GRPC_DIR.exists() and str(_MGMT_GRPC_DIR) not in sys.path:
    sys.path.insert(0, str(_MGMT_GRPC_DIR))

DEFAULT_MGMT_HOST = "100.77.239.25"  # Mac Tailscale IP (개발)
DEFAULT_MGMT_PORT = 50051
DEFAULT_READER_ID = "BARCODE-JETSON-01"
DEFAULT_ZONE = "conveyor_in"


def _import_grpc():
    try:
        import grpc  # type: ignore
        import management_pb2 as pb  # type: ignore
        import management_pb2_grpc as pbg  # type: ignore

        return grpc, pb, pbg
    except ImportError as e:
        sys.stderr.write(
            f"\n[ERROR] gRPC 의존성 누락: {e}\n"
            "Jetson 에서 실행하세요. 다음 명령으로 설정:\n"
            "  python3 -m pip install --user evdev 'grpcio-tools==1.59.5'\n"
            "  cd ~/casting-factory && mkdir -p mgmt_grpc && \\\n"
            "    python3 -m grpc_tools.protoc -I. --python_out=mgmt_grpc \\\n"
            "      --grpc_python_out=mgmt_grpc management.proto\n"
        )
        raise SystemExit(1) from None


def _now_iso_utc() -> str:
    """ISO-8601 UTC timestamp — rfid_service._parse_scanned_at 호환."""
    return datetime.now(UTC).isoformat()


def _now_ms() -> int:
    return int(time.time() * 1000)


def _read_one(evdev_mod, device_path: str) -> dict:
    """evdev read_loop 로 HID 키 이벤트 수집 → 바코드 1개 디코딩.

    Enter (END_KEYS) 까지 블록킹. timeout 없음 (데몬은 계속 대기).
    """
    dev = evdev_mod.InputDevice(device_path)
    ecodes = evdev_mod.ecodes

    keys: list[str] = []
    start: float | None = None

    for event in dev.read_loop():
        if event.type != ecodes.EV_KEY:
            continue
        ke = evdev_mod.categorize(event)
        if ke.keystate != ke.key_down:
            continue
        if start is None:
            start = time.monotonic()
        keycode = ke.keycode
        if isinstance(keycode, list):
            keycode = keycode[0]
        if keycode in END_KEYS:
            return {
                "keys": keys,
                "text": _assemble(keys),
                "latency_ms": int((time.monotonic() - start) * 1000),
            }
        keys.append(keycode)


def _report_scan(stub, pb, *, reader_id: str, zone: str, text: str) -> tuple[bool, str, str]:
    """단일 스캔을 gRPC 로 Management 에 report.

    Returns: (accepted, parse_status, reason)
    """
    ts_ms = _now_ms()
    idem = f"{reader_id}:{ts_ms}"

    # rfid_service._parse_scanned_at 가 iso 문자열을 기대하지만
    # RfidScanEvent.scanned_at 는 Timestamp proto. 서버 측에서
    # FromDatetime 또는 _parse_scanned_at(None) fallback 으로 now() 사용.
    # 간결성을 위해 scanned_at 필드는 비워두고 서버 now() 에 맡긴다.
    event = pb.RfidScanEvent(
        reader_id=reader_id,
        zone=zone,
        raw_payload=text,
        idempotency_key=idem,
    )
    ack = stub.ReportRfidScan(event, timeout=5)
    return bool(ack.accepted), ack.parse_status, ack.reason


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--device",
        default=DEFAULT_DEVICE,
        help=f"evdev 장치 (기본: {DEFAULT_DEVICE})",
    )
    parser.add_argument(
        "--mgmt-host",
        default=DEFAULT_MGMT_HOST,
        help=f"Management gRPC 호스트 (기본: {DEFAULT_MGMT_HOST})",
    )
    parser.add_argument(
        "--mgmt-port",
        type=int,
        default=DEFAULT_MGMT_PORT,
        help=f"Management gRPC 포트 (기본: {DEFAULT_MGMT_PORT})",
    )
    parser.add_argument(
        "--reader-id",
        default=DEFAULT_READER_ID,
        help=f"reader_id 값 (기본: {DEFAULT_READER_ID})",
    )
    parser.add_argument(
        "--zone",
        default=DEFAULT_ZONE,
        help=f"zone 값 (기본: {DEFAULT_ZONE})",
    )
    args = parser.parse_args()

    evdev_mod = _import_evdev()
    if evdev_mod is None:
        return 1

    grpc, pb, pbg = _import_grpc()

    device_path = _resolve_device(evdev_mod, args.device)
    _check_permission(device_path)

    target = f"{args.mgmt_host}:{args.mgmt_port}"
    channel = grpc.insecure_channel(target)
    stub = pbg.ManagementServiceStub(channel)

    # Health ping 으로 연결 사전 검증
    try:
        stub.Health(pb.Empty(), timeout=3)
    except grpc.RpcError as e:
        sys.stderr.write(
            f"\n[ERROR] Management gRPC {target} 에 연결 실패: {e.code()} {e.details()}\n"
        )
        return 2

    sys.stderr.write(
        f"[INFO] 바코드 실시간 적재 시작.\n"
        f"  device       = {device_path}\n"
        f"  management   = {target}\n"
        f"  reader_id    = {args.reader_id}\n"
        f"  zone         = {args.zone}\n"
        f"Ctrl+C 로 종료. 각 스캔마다 ReportRfidScan gRPC 호출 → rfid_scan_log INSERT.\n\n"
    )
    sys.stderr.flush()

    # SIGTERM/SIGINT 우아한 종료
    _running = {"flag": True}

    def _stop(signum, frame):
        _running["flag"] = False
        sys.stderr.write(f"\n[INFO] signal {signum} 수신 — 종료 중...\n")

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    scan_count = 0
    error_count = 0
    while _running["flag"]:
        try:
            one = _read_one(evdev_mod, device_path)
        except OSError as e:
            sys.stderr.write(f"[ERROR] evdev read: {e}. 1초 후 재시도.\n")
            time.sleep(1)
            continue
        except Exception as e:
            sys.stderr.write(f"[ERROR] read_one: {e}\n")
            error_count += 1
            if error_count > 5:
                sys.stderr.write("[FATAL] 연속 에러 5회 이상 — 종료.\n")
                return 3
            continue

        text = one["text"]
        latency = one["latency_ms"]
        scan_count += 1

        try:
            accepted, parse_status, reason = _report_scan(
                stub,
                pb,
                reader_id=args.reader_id,
                zone=args.zone,
                text=text,
            )
            status_icon = "✓" if accepted else "✗"
            sys.stderr.write(
                f"[{scan_count:04d}] {status_icon} {_now_iso_utc()} "
                f"text={text!r} hid_latency={latency}ms "
                f"parse={parse_status} accepted={accepted} reason={reason}\n"
            )
            sys.stderr.flush()
            error_count = 0
        except grpc.RpcError as e:
            sys.stderr.write(
                f"[{scan_count:04d}] ERR {_now_iso_utc()} "
                f"text={text!r} gRPC 실패: {e.code()} {e.details()}\n"
            )
            sys.stderr.flush()
            error_count += 1
            if error_count > 5:
                sys.stderr.write("[FATAL] 연속 gRPC 에러 5회 이상 — 종료.\n")
                return 4

    sys.stderr.write(f"[INFO] 총 {scan_count} 건 처리. 종료.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
