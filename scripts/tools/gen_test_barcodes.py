#!/usr/bin/env python3
"""테스트용 Code128 바코드 PNG 이미지 생성기.

실행 위치: **로컬 Mac 권장** (Jetson 에서 굳이 돌릴 필요 없음).
생성된 PNG 를 라벨 프린터(또는 일반 프린터 + 접착 라벨지) 로 출력해
ESP32 컨베이어의 맨홀 모형에 부착하여 Jetson 바코드 리더로 스캔 테스트.

페이로드 포맷:
    order_{ord_id}_item_{YYYYMMDD}_{seq}

이 형식은 SPEC-RFID-001 payload regex 와 동일하므로 RFID 경로와
직접 비교 가능하다 (barcode 도 rfid_scan_log 의 raw_payload 에
그대로 저장될 수 있음).

출력:
    tools/barcodes_out/order_1_item_20260417_1.png  (Code128)
    tools/barcodes_out/order_2_item_20260417_2.png
    ...

필요 패키지:
    pip install python-barcode Pillow

연관 문서:
    docs/barcode_vs_rfid_prep.md
    docs/barcode_test_plan.md
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

DEFAULT_PAYLOADS = [f"order_{i}_item_20260417_{i}" for i in range(1, 6)]


def _import_barcode() -> tuple[object, object]:
    try:
        import barcode  # type: ignore
        from barcode.writer import ImageWriter  # type: ignore
    except ImportError:
        sys.stderr.write(
            "\n[ERROR] 의존 패키지 누락. 다음으로 설치:\n\n  pip install python-barcode Pillow\n\n"
        )
        raise SystemExit(1) from None
    return barcode, ImageWriter


def _generate(payload: str, out_dir: Path, ImageWriter) -> Path:
    import barcode  # type: ignore

    # 리더 스캔 안정성 옵션:
    #   module_width 0.4mm — 일반 A4 프린터에서 바가 뭉개지지 않도록 기본 0.2 의 2배
    #   module_height 20mm — 스캔 정렬 여유
    #   quiet_zone 10mm — 바코드 좌우 여백 (리더 데모디레이션 필요)
    #   dpi 300 + font_size 14 — 인쇄 선명도 + 사람 확인용 텍스트
    writer = ImageWriter()
    code = barcode.get("code128", payload, writer=writer)
    options = {
        "module_width": 0.4,
        "module_height": 20.0,
        "quiet_zone": 10.0,
        "dpi": 300,
        "font_size": 14,
        "text_distance": 5.0,
        "write_text": True,
    }
    base = out_dir / payload  # 확장자는 writer 가 붙임
    saved = code.save(str(base), options=options)
    return Path(saved)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--payload",
        action="append",
        default=None,
        help="생성할 페이로드 (반복 지정 가능). 미지정 시 order_1_item_... ~ order_5_... 5개 기본",
    )
    parser.add_argument(
        "--out-dir",
        default="tools/barcodes_out",
        help="PNG 출력 디렉터리 (기본: tools/barcodes_out)",
    )
    args = parser.parse_args()

    barcode, ImageWriter = _import_barcode()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    payloads = args.payload if args.payload else DEFAULT_PAYLOADS

    print(f"[INFO] Code128 바코드 {len(payloads)} 개 생성 → {out_dir}/")
    for p in payloads:
        saved = _generate(p, out_dir, ImageWriter)
        size = os.path.getsize(saved)
        print(f"  ✔ {saved.name}  ({size:,} bytes)")

    print(
        f"\n[DONE] {len(payloads)} 개 PNG 생성 완료.\n"
        "인쇄 방법: 일반 프린터 → 접착 라벨지, 또는 Zebra 등 라벨 프린터.\n"
        "인쇄 후 맨홀/상자 표면에 부착하고 Jetson 바코드 리더로 스캔하여\n"
        "tools/barcode_probe.py 로 읽기 테스트 진행."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
