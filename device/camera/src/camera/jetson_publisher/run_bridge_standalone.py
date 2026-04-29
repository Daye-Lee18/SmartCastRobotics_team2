#!/usr/bin/env python3
"""ESP Bridge 단독 실행 러너 (publisher.py 없이, handoff 테스트용).

사용 (Jetson):
    export ESP_BRIDGE_ENABLED=1
    export ESP_BRIDGE_PORT=/dev/ttyUSB0
    export MANAGEMENT_GRPC_TARGET=100.77.239.25:50051
    export ESP_BRIDGE_DEVICE_ID=ESP-CONVEYOR-01
    python3 jetson_publisher/run_bridge_standalone.py

- STOPPED → RUN 자동 복귀는 `ESP_BRIDGE_AUTO_RUN=0` 으로 끌 수 있음 (handoff 테스트에는 무관).
- Ctrl+C 로 종료.
- ESP32 `/dev/ttyUSB0` 이 연결되어 있어야 함. 연결 끊기면 10s 간격으로 재연결 시도.

출력:
    [INFO] EspBridge connected to /dev/ttyUSB0 @ 115200
    [INFO] ESP → HANDOFF_ACK (queued key=ESP-CONVEYOR-01:1776..., qsize=1)
    [INFO] ReportHandoffAck 응답: accepted=True reason=released/orphan_no_waiting_task

연관: backend/management/server.py ReportHandoffAck, backend/app/models/models_mgmt.py HandoffAck
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time
from pathlib import Path

# 스크립트 디렉터리 + generated/ 를 sys.path 등록 (esp_bridge.py 가 `from generated import ...` 사용)
_HERE = Path(__file__).resolve().parent
for p in (_HERE, _HERE / "generated"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from esp_bridge import EspBridge  # noqa: E402


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    shutdown = threading.Event()
    bridge = EspBridge.from_env(shutdown)
    bridge.start()

    def _stop(signum, frame):
        print(f"\n[INFO] signal {signum} 수신 — 종료 중...", flush=True)
        shutdown.set()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    try:
        while not shutdown.is_set():
            time.sleep(0.5)
    finally:
        shutdown.set()
        time.sleep(2)  # 스레드 정리 여유
    print("[INFO] bridge stopped", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
