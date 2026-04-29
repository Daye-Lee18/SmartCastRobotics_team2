"""EspBridge 이벤트 처리 단위 테스트 (mock serial).

실제 ESP32 없이 bridge 의 라인 파싱 + auto-RUN 로직만 검증.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

# jetson_publisher 경로 삽입
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from esp_bridge import EspBridge  # noqa: E402


class FakeSerial:
    """_handle_line 테스트용 최소 mock."""

    def __init__(self) -> None:
        self.writes: list[bytes] = []

    def write(self, data: bytes) -> int:
        self.writes.append(data)
        return len(data)

    def flush(self) -> None:
        pass


def _make_bridge(auto_run: bool = True, delay_ms: int = 0) -> EspBridge:
    return EspBridge(
        shutdown_event=threading.Event(),
        port="/dev/null",
        baud=115200,
        auto_run=auto_run,
        inspection_delay_ms=delay_ms,
    )


def test_stopped_with_auto_run_sends_run() -> None:
    br = _make_bridge(auto_run=True, delay_ms=0)
    ser = FakeSerial()
    br._handle_line(ser, "STOPPED")
    assert ser.writes == [b"RUN\n"]


def test_stopped_with_auto_run_off_does_not_send() -> None:
    br = _make_bridge(auto_run=False, delay_ms=0)
    ser = FakeSerial()
    br._handle_line(ser, "STOPPED")
    assert ser.writes == []


def test_inspection_delay_respected() -> None:
    br = _make_bridge(auto_run=True, delay_ms=200)
    ser = FakeSerial()
    t0 = time.monotonic()
    br._handle_line(ser, "STOPPED")
    elapsed = time.monotonic() - t0
    assert 0.18 <= elapsed <= 0.4
    assert ser.writes == [b"RUN\n"]


def test_non_trigger_lines_do_not_send() -> None:
    br = _make_bridge(auto_run=True, delay_ms=0)
    ser = FakeSerial()
    for line in (
        "STATE:IDLE",
        "BOOT:conveyor_v5_serial 1.0.0",
        "STARTED",
        "DONE",
        "PONG",
        "",
        "ERR:unknown_cmd:xxx",
        "UNKNOWN_GARBAGE",
    ):
        br._handle_line(ser, line)
    assert ser.writes == []


def test_from_env_defaults(monkeypatch) -> None:
    for k in (
        "ESP_BRIDGE_PORT",
        "ESP_BRIDGE_BAUD",
        "ESP_BRIDGE_AUTO_RUN",
        "ESP_BRIDGE_INSPECTION_DELAY_MS",
    ):
        monkeypatch.delenv(k, raising=False)
    br = EspBridge.from_env(threading.Event())
    assert br._port == "/dev/ttyUSB0"
    assert br._baud == 115200
    assert br._auto_run is True
    assert br._inspection_delay == 0.7


def test_from_env_custom(monkeypatch) -> None:
    monkeypatch.setenv("ESP_BRIDGE_PORT", "/dev/ttyUSB1")
    monkeypatch.setenv("ESP_BRIDGE_BAUD", "9600")
    monkeypatch.setenv("ESP_BRIDGE_AUTO_RUN", "0")
    monkeypatch.setenv("ESP_BRIDGE_INSPECTION_DELAY_MS", "250")
    br = EspBridge.from_env(threading.Event())
    assert br._port == "/dev/ttyUSB1"
    assert br._baud == 9600
    assert br._auto_run is False
    assert br._inspection_delay == 0.25
