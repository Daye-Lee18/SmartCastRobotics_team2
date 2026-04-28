#!/usr/bin/env python3
"""Jetson 바코드 리더 HID 진단 도구.

사용 시나리오:
  - Jetson 에 SSH 접속 후 실행
  - /dev/input/event5 (by-id 심볼릭 링크 권장) 에서 HID 키보드 이벤트 수신
  - 한 번 또는 N 회 바코드 스캔 후 JSON 으로 결과 출력

전제 조건:
  1. python-evdev 설치:  python3 -m pip install --user python-evdev
  2. jetson 사용자가 'input' 그룹에 속하거나 sudo 로 실행
     (sudo usermod -aG input jetson && sudo reboot)

연관 문서: docs/barcode_vs_rfid_prep.md §4 (준비 블로커)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

DEFAULT_DEVICE = "/dev/input/by-id/usb-USB_Adapter_USB_Device-event-kbd"

# USB HID Keyboard scan code → ASCII (evdev KEY_* -> char).
# evdev 의 ecodes.KEY_A ~ KEY_Z, KEY_0 ~ KEY_9, 기본 기호만 매핑.
KEY_MAP_NORMAL = {
    "KEY_A": "a",
    "KEY_B": "b",
    "KEY_C": "c",
    "KEY_D": "d",
    "KEY_E": "e",
    "KEY_F": "f",
    "KEY_G": "g",
    "KEY_H": "h",
    "KEY_I": "i",
    "KEY_J": "j",
    "KEY_K": "k",
    "KEY_L": "l",
    "KEY_M": "m",
    "KEY_N": "n",
    "KEY_O": "o",
    "KEY_P": "p",
    "KEY_Q": "q",
    "KEY_R": "r",
    "KEY_S": "s",
    "KEY_T": "t",
    "KEY_U": "u",
    "KEY_V": "v",
    "KEY_W": "w",
    "KEY_X": "x",
    "KEY_Y": "y",
    "KEY_Z": "z",
    "KEY_0": "0",
    "KEY_1": "1",
    "KEY_2": "2",
    "KEY_3": "3",
    "KEY_4": "4",
    "KEY_5": "5",
    "KEY_6": "6",
    "KEY_7": "7",
    "KEY_8": "8",
    "KEY_9": "9",
    "KEY_MINUS": "-",
    "KEY_EQUAL": "=",
    "KEY_LEFTBRACE": "[",
    "KEY_RIGHTBRACE": "]",
    "KEY_SEMICOLON": ";",
    "KEY_APOSTROPHE": "'",
    "KEY_GRAVE": "`",
    "KEY_BACKSLASH": "\\",
    "KEY_COMMA": ",",
    "KEY_DOT": ".",
    "KEY_SLASH": "/",
    "KEY_SPACE": " ",
    "KEY_TAB": "\t",
}
KEY_MAP_SHIFT = {
    # 숫자 → 특수문자 (대부분 바코드는 쓰지 않음. 혹시 필요 시 확장)
    "KEY_1": "!",
    "KEY_2": "@",
    "KEY_3": "#",
    "KEY_4": "$",
    "KEY_5": "%",
    "KEY_6": "^",
    "KEY_7": "&",
    "KEY_8": "*",
    "KEY_9": "(",
    "KEY_0": ")",
    "KEY_MINUS": "_",
    "KEY_EQUAL": "+",
}
END_KEYS = ("KEY_ENTER", "KEY_KPENTER", "KEY_LINEFEED")


def _import_evdev() -> object | None:
    try:
        import evdev  # type: ignore

        return evdev
    except ImportError:
        sys.stderr.write(
            "\n[ERROR] python-evdev 가 설치되어 있지 않습니다.\n"
            "Jetson 에서 다음 명령으로 설치하세요:\n\n"
            "  python3 -m pip install --user python-evdev\n\n"
            "설치 후 재실행하세요.\n"
        )
        return None


def _resolve_device(evdev_mod, path: str) -> str:
    """by-id 심볼릭 링크를 실제 /dev/input/eventN 경로로 해석."""
    if os.path.islink(path):
        return os.path.realpath(path)
    return path


def _check_permission(device_path: str) -> None:
    if not os.path.exists(device_path):
        sys.stderr.write(
            f"\n[ERROR] 장치가 없습니다: {device_path}\n"
            "Jetson 에 바코드 리더를 USB 로 연결했는지 확인하세요.\n"
            "디바이스 목록:  ls -la /dev/input/by-id/\n"
        )
        sys.exit(2)
    if not os.access(device_path, os.R_OK):
        sys.stderr.write(
            f"\n[ERROR] {device_path} 읽기 권한 없음.\n"
            "해결 (택 1):\n"
            "  A. sudo usermod -aG input $USER && sudo reboot  (권장)\n"
            "  B. sudo python3 tools/barcode_probe.py\n"
        )
        sys.exit(3)


def _assemble(keys: list[str]) -> str:
    """SHIFT 토글을 반영해 키 시퀀스를 문자열로 조립."""
    shift = False
    out = []
    for k in keys:
        if k in ("KEY_LEFTSHIFT", "KEY_RIGHTSHIFT"):
            shift = True
            continue
        if shift and k in KEY_MAP_SHIFT:
            out.append(KEY_MAP_SHIFT[k])
        elif k in KEY_MAP_NORMAL:
            ch = KEY_MAP_NORMAL[k]
            if shift and ch.isalpha():
                ch = ch.upper()
            out.append(ch)
        shift = False
    return "".join(out)


def _read_one_scan(evdev_mod, device_path: str, timeout_s: float) -> dict:
    """한 번 스캔된 내용을 읽을 때까지 block (최대 timeout_s)."""
    dev = evdev_mod.InputDevice(device_path)
    ecodes = evdev_mod.ecodes

    keys: list[str] = []
    start: float | None = None
    deadline = time.monotonic() + timeout_s

    for event in dev.read_loop():
        if time.monotonic() > deadline and not keys:
            raise TimeoutError(f"스캔 대기 {timeout_s}s 타임아웃")
        if event.type != ecodes.EV_KEY:
            continue
        key_event = evdev_mod.categorize(event)
        # key_event.keystate: 1 = down, 0 = up, 2 = hold
        if key_event.keystate != key_event.key_down:
            continue
        if start is None:
            start = time.monotonic()
        keycode = key_event.keycode
        if isinstance(keycode, list):  # evdev 이 리스트로 돌려줄 수도 있음
            keycode = keycode[0]
        if keycode in END_KEYS:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "raw": keys,
                "text": _assemble(keys),
                "latency_ms": elapsed_ms,
            }
        keys.append(keycode)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--device", default=DEFAULT_DEVICE, help="evdev 장치 경로 (기본: by-id 심볼릭 링크)"
    )
    parser.add_argument("--count", type=int, default=1, help="스캔 반복 횟수 (기본 1)")
    parser.add_argument(
        "--timeout", type=float, default=30.0, help="각 스캔 대기 타임아웃 초 (기본 30)"
    )
    args = parser.parse_args()

    evdev_mod = _import_evdev()
    if evdev_mod is None:
        return 1

    device_path = _resolve_device(evdev_mod, args.device)
    _check_permission(device_path)

    sys.stderr.write(
        f"[INFO] {device_path} 에서 {args.count} 회 스캔 대기 (타임아웃 {args.timeout}s)\n"
        "바코드를 스캔하세요...\n"
    )

    for i in range(args.count):
        try:
            result = _read_one_scan(evdev_mod, device_path, args.timeout)
        except TimeoutError as exc:
            sys.stderr.write(f"[{i + 1}/{args.count}] {exc}\n")
            return 4
        except PermissionError as exc:
            sys.stderr.write(f"[ERROR] 권한 문제: {exc}\n")
            return 3
        except KeyboardInterrupt:
            sys.stderr.write("\n[INFO] 사용자 중단\n")
            return 130
        result["index"] = i + 1
        print(json.dumps(result, ensure_ascii=False))
        sys.stdout.flush()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
