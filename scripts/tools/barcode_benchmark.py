#!/usr/bin/env python3
"""바코드 리더 반복 스캔 벤치마크 — 정확도 · 레이턴시 · 중복 계측.

실행 환경: **Jetson 에서 수동 스캔 50회 반복**.
사용자가 물리 바코드 리더로 expected payloads 목록에 맞춰 순차 스캔.
스크립트가 실제 수신 vs 기대값 비교 → 정확도(%), 평균 latency(ms),
중복 탐지 수, 실패 수를 JSON 리포트로 저장.

실행 예:
    python3 tools/barcode_benchmark.py \\
        --expected order_1_item_20260417_1 \\
        --expected order_2_item_20260417_2 \\
        --expected order_3_item_20260417_3 \\
        --expected order_4_item_20260417_4 \\
        --expected order_5_item_20260417_5 \\
        --reps 10

이 예는 5개 샘플 × 10회 반복 = 50회 스캔. 각 반복 라운드마다
5개를 순서대로 스캔하면 됨. 순서가 어긋나도 시트가 자동 매칭.

중단 (Ctrl+C) 가능 — 부분 결과도 저장됨.

연관 문서: docs/barcode_test_plan.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

# barcode_probe.py 와 동일한 HID 매핑 사용 (중복 정의 회피)
from barcode_probe import (  # type: ignore
    DEFAULT_DEVICE,
    END_KEYS,
    _assemble,
    _check_permission,
    _import_evdev,
    _resolve_device,
)


def _read_one(evdev_mod, device_path: str, timeout_s: float) -> dict:
    dev = evdev_mod.InputDevice(device_path)
    ecodes = evdev_mod.ecodes

    keys: list[str] = []
    start: float | None = None
    deadline = time.monotonic() + timeout_s

    for event in dev.read_loop():
        if time.monotonic() > deadline and not keys:
            raise TimeoutError("timeout")
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


def _save_report(out_path: Path, report: dict) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def _summarize(scans: list[dict], expected: list[str]) -> dict:
    received = [s["text"] for s in scans]
    expected_set = set(expected)
    matches = sum(1 for t in received if t in expected_set)
    dup_counter = Counter(received)
    duplicates = {k: v for k, v in dup_counter.items() if v > 1}
    failures = [t for t in received if t not in expected_set]
    latencies = [s["latency_ms"] for s in scans]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    return {
        "total_scans": len(scans),
        "expected_unique": len(expected_set),
        "matches": matches,
        "failures": len(failures),
        "accuracy_pct": round((matches / len(scans)) * 100, 2) if scans else 0.0,
        "avg_latency_ms": round(avg_latency, 1),
        "min_latency_ms": min(latencies) if latencies else 0,
        "max_latency_ms": max(latencies) if latencies else 0,
        "duplicates": duplicates,
        "failure_samples": failures[:10],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--device", default=DEFAULT_DEVICE, help="evdev 장치 경로 (기본: by-id 심볼릭 링크)"
    )
    parser.add_argument(
        "--expected",
        action="append",
        required=True,
        help="기대 페이로드 (여러 번 지정). 예: --expected order_1_item_20260417_1",
    )
    parser.add_argument("--reps", type=int, default=10, help="각 페이로드 반복 횟수 (기본 10)")
    parser.add_argument(
        "--timeout", type=float, default=60.0, help="각 스캔 대기 타임아웃 초 (기본 60)"
    )
    parser.add_argument(
        "--out-dir",
        default="tools/barcode_bench_out",
        help="결과 저장 디렉터리 (기본: tools/barcode_bench_out)",
    )
    args = parser.parse_args()

    evdev_mod = _import_evdev()
    if evdev_mod is None:
        return 1

    device_path = _resolve_device(evdev_mod, args.device)
    _check_permission(device_path)

    total_expected = len(args.expected) * args.reps
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_path = Path(args.out_dir) / f"result_{ts}.json"

    scans: list[dict] = []
    report = {
        "started_at": datetime.now(UTC).isoformat(),
        "device": device_path,
        "expected": args.expected,
        "reps_per_expected": args.reps,
        "total_expected": total_expected,
        "scans": scans,
        "summary": None,
        "interrupted": False,
    }

    sys.stderr.write(
        f"[INFO] {device_path} 에서 {total_expected} 회 스캔 수집 시작.\n"
        f"[INFO] 각 라운드: {args.expected} 순서로 {args.reps} 라운드.\n"
        "Ctrl+C 로 중단 시 부분 결과 저장.\n\n"
    )

    try:
        idx = 0
        for rep in range(args.reps):
            for exp in args.expected:
                idx += 1
                sys.stderr.write(f"[{idx}/{total_expected}] rep={rep + 1} expected={exp} ... ")
                sys.stderr.flush()
                try:
                    one = _read_one(evdev_mod, device_path, args.timeout)
                except TimeoutError:
                    sys.stderr.write("TIMEOUT\n")
                    scans.append(
                        {
                            "index": idx,
                            "expected": exp,
                            "text": None,
                            "latency_ms": -1,
                            "timeout": True,
                        }
                    )
                    continue
                one["index"] = idx
                one["expected"] = exp
                one["match"] = one["text"] == exp
                scans.append(one)
                mark = "OK" if one["match"] else "MISS"
                sys.stderr.write(f"{mark} got={one['text']!r} {one['latency_ms']}ms\n")
    except KeyboardInterrupt:
        sys.stderr.write("\n[INFO] 사용자 중단 — 부분 결과 저장\n")
        report["interrupted"] = True

    report["summary"] = _summarize([s for s in scans if s.get("text") is not None], args.expected)
    report["finished_at"] = datetime.now(UTC).isoformat()
    _save_report(out_path, report)

    summary = report["summary"]
    sys.stderr.write("\n===== SUMMARY =====\n")
    sys.stderr.write(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    sys.stderr.write(f"\n리포트 저장: {out_path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
