#!/usr/bin/env python3
"""테스트용 Code 39 바코드 PNG 생성기 — Code 128 미지원 리더 대체용.

사용 시점:
    gen_test_barcodes.py (Code 128) 인쇄물을 저가 1D 레이저 리더가
    beep 없이 거부할 때 사용. Code 39 는 거의 모든 리더에서
    기본 활성화되어 있으므로 호환성 리스크가 낮다.

Code 39 제약:
    - 허용 문자: 0-9, A-Z (대문자만), space, 그리고 - . $ / + % *
    - 소문자·언더스코어(_) 미지원
    - '*' 는 start/stop 문자 (python-barcode 가 자동 추가)

페이로드 변환 규칙 (Code 128 → Code 39):
    order_1_item_20260417_1  →  ORDER-1-ITEM-20260417-1
        1) 전부 대문자화
        2) 언더스코어(_) → 하이픈(-)

이렇게 변환한 페이로드는 rfid_scan_log 의 raw_payload 에
그대로 기록 가능하며, SPEC-RFID-001 regex 와의 호환은
추후 서버 레이어에서 정규화 (예: upper+hyphen→lower+underscore).

출력:
    tools/barcodes_out_code39/ORDER-1-ITEM-20260417-1.png
    tools/barcodes_out_code39/ORDER-2-ITEM-20260417-2.png
    ...

필요 패키지:
    pip install python-barcode Pillow

사용:
    python3 tools/gen_test_barcodes_code39.py

    # 커스텀 페이로드:
    python3 tools/gen_test_barcodes_code39.py \\
        --payload HELLO-WORLD-001 --payload TEST-42

벤치마크 스캔 시:
    python3 tools/barcode_benchmark.py \\
        --expected ORDER-1-ITEM-20260417-1 \\
        --expected ORDER-2-ITEM-20260417-2 \\
        --expected ORDER-3-ITEM-20260417-3 \\
        --expected ORDER-4-ITEM-20260417-4 \\
        --expected ORDER-5-ITEM-20260417-5 \\
        --reps 10

연관 문서:
    docs/barcode_vs_rfid_prep.md
    docs/barcode_test_plan.md
    docs/barcode_jetson_ready.md
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

DEFAULT_PAYLOADS = [f"ORDER-{i}-ITEM-20260417-{i}" for i in range(1, 6)]

# Code 39 허용 문자 검증 정규식 (start/stop '*' 제외)
CODE39_PATTERN = re.compile(r"^[0-9A-Z\-\.\$\/\+\%\s]+$")


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


def _validate_payload(payload: str) -> None:
    if not CODE39_PATTERN.match(payload):
        sys.stderr.write(
            f"\n[ERROR] Code 39 허용 범위 벗어남: {payload!r}\n"
            "  허용 문자: 0-9, A-Z, space, - . $ / + %\n"
            "  소문자와 언더스코어(_) 는 사용 불가. 대문자·하이픈으로 변환하세요.\n"
        )
        raise SystemExit(2)


def _generate(payload: str, out_dir: Path, ImageWriter) -> Path:
    import barcode  # type: ignore

    # gen_test_barcodes.py (Code 128) 와 동일 스펙의 writer 옵션:
    #   module_width 0.4mm — 일반 A4 프린터 인쇄 시 바 유지
    #   module_height 20mm — 스캔 정렬 여유
    #   quiet_zone 10mm — 리더 디모디레이션 여백
    #   dpi 300 + font_size 14 — 인쇄 선명도 + human-readable 텍스트
    writer = ImageWriter()
    # Code 39 는 기본 add_checksum=False. 체크섬 필요 시 add_checksum=True.
    # barcode.get() 은 kwargs 전달 못 하므로 클래스 직접 사용.
    Code39 = barcode.get_barcode_class("code39")
    code = Code39(payload, writer=writer, add_checksum=False)
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
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--payload",
        action="append",
        default=None,
        help="생성할 페이로드 (반복 지정 가능). 미지정 시 ORDER-1-ITEM-... ~ ORDER-5-... 5개 기본",
    )
    parser.add_argument(
        "--out-dir",
        default="tools/barcodes_out_code39",
        help="PNG 출력 디렉터리 (기본: tools/barcodes_out_code39)",
    )
    args = parser.parse_args()

    barcode, ImageWriter = _import_barcode()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    payloads = args.payload if args.payload else DEFAULT_PAYLOADS

    # 검증 먼저 (부분 생성 방지)
    for p in payloads:
        _validate_payload(p)

    print(f"[INFO] Code 39 바코드 {len(payloads)} 개 생성 → {out_dir}/")
    for p in payloads:
        saved = _generate(p, out_dir, ImageWriter)
        size = os.path.getsize(saved)
        print(f"  ✔ {saved.name}  ({size:,} bytes)")

    print(
        f"\n[DONE] {len(payloads)} 개 PNG 생성 완료 (Code 39).\n"
        "인쇄 시 주의: 실제 크기 100% (프린터 'Fit to page' 해제).\n"
        "바코드 너비 5cm 이상 유지. 레이저 프린터 권장.\n\n"
        "벤치마크 실행 시 --expected 인자는 대문자·하이픈 형식으로:\n"
        + "\n".join(f"  --expected {p}" for p in payloads)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
