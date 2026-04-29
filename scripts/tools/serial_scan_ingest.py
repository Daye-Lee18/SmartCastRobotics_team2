#!/usr/bin/env python3
"""Serial JSON → RFID 태그 파싱 → item 공정 단계 업데이트.

시리얼 포트에서 JSON 수신 → access_key 인증 → 태그 파싱(ord_id, item_id)
→ smartcast.item 의 cur_stage 를 다음 공정으로 갱신 → 결과 출력.

rfid_scan_log 에 저장하지 않고, 파싱된 ord_id / item_id 를
비즈니스 테이블(item)에 직접 반영한다.

태그 형식: order_{ord_id}_item_{YYYYMMDD}_{seq}
    → ord_id = 주문 번호
    → seq   = item_id (아이템 PK)

공정 단계 순서: QUE → MM → DM → TR_PP → PP → IP → TR_LD → SH

사용:
    python3 tools/serial_scan_ingest.py                    # 연속 모드
    python3 tools/serial_scan_ingest.py --exit-on-first    # 단건 모드
    python3 tools/serial_scan_ingest.py --stage PP         # 특정 단계 지정

필수 환경변수 (backend/.env.local):
    DATABASE_URL  - "postgresql://user:pass@host:5432/dbname"
    SHARED_KEY    - 시리얼 JSON access_key 인증 키

의존:
    pip install pyserial psycopg2-binary
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import sys
from pathlib import Path
from urllib.parse import urlparse

# --- 상수 ---
DEFAULT_SERIAL_PORT = "/tmp/ttyV1"
DEFAULT_BAUDRATE = 9600

# RfidService 와 동일 regex
RFID_PAYLOAD_RE = re.compile(r"^order_(?P<ord>\d+)_item_(?P<date>\d{8})_(?P<seq>\d+)$")

# 공정 단계 순서 (models_legacy.py Item.cur_stage 참조)
STAGE_ORDER = ["QUE", "MM", "DM", "TR_PP", "PP", "IP", "TR_LD", "SH"]

# .env.local 로드
for _p in [
    Path(__file__).resolve().parent.parent / "backend" / ".env.local",
    Path(__file__).resolve().parent.parent / ".env.local",
]:
    if _p.exists():
        for _raw in _p.read_text(encoding="utf-8").splitlines():
            _line = _raw.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _key, _, _val = _line.partition("=")
            _key = _key.strip()
            _val = _val.strip().strip('"').strip("'")
            if _key and _key not in os.environ:
                os.environ[_key] = _val


def _import_deps():
    """런타임 의존성 지연 import."""
    try:
        import psycopg2  # type: ignore
    except ImportError:
        sys.stderr.write("[ERROR] psycopg2 미설치. pip install psycopg2-binary\n")
        raise SystemExit(1) from None

    try:
        import serial as pyserial  # type: ignore
    except ImportError:
        sys.stderr.write("[ERROR] pyserial 미설치. pip install pyserial\n")
        raise SystemExit(1) from None

    return psycopg2, pyserial


def _parse_db_url() -> dict:
    """DATABASE_URL → psycopg2 연결 파라미터."""
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        sys.stderr.write(
            "[ERROR] DATABASE_URL 환경변수 미설정.\nbackend/.env.local 에 설정하세요.\n"
        )
        raise SystemExit(1) from None

    # SQLAlchemy dialect 제거: postgresql+psycopg:// → postgresql://
    if "+" in url.split("://")[0]:
        dialect, rest = url.split("://", 1)
        driver = dialect.split("+", 1)[0]
        url = f"{driver}://{rest}"

    parsed = urlparse(url)
    return {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "dbname": parsed.lstrip("/").split("?")[0],
        "user": parsed.username,
        "password": parsed.password,
    }


def _get_db(psycopg2):
    """PostgreSQL 연결 (search_path = smartcast, public)."""
    params = _parse_db_url()
    conn = psycopg2.connect(**params)
    with conn.cursor() as cur:
        cur.execute("SET search_path TO smartcast, public")
    conn.commit()
    return conn


def _next_stage(current: str) -> str | None:
    """현재 단계의 다음 단계 반환. 마지막 단계면 None."""
    idx = STAGE_ORDER.index(current) if current in STAGE_ORDER else -1
    if idx < 0 or idx >= len(STAGE_ORDER) - 1:
        return None
    return STAGE_ORDER[idx + 1]


def _lookup_item(conn, item_id: int) -> dict | None:
    """item + order + user_account 조인 조회 (기존 스크립트와 동일)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT i.item_id, i.cur_stat, u.user_nm, u.co_nm
            FROM item i
            JOIN ord o ON i.ord_id = o.ord_id
            JOIN user_account u ON o.user_id = u.user_id
            WHERE i.item_id = %s
            """,
            (item_id,),
        )
        row = cur.fetchone()
        if row:
            return {
                "item_id": row[0],
                "cur_stat": row[1],
                "user_nm": row[2],
                "co_nm": row[3],
            }
    return None


def _advance_stage(conn, item_id: int, target_stage: str | None = None) -> dict | None:
    """item 의 cur_stat 를 다음 단계(또는 지정 단계)로 UPDATE.

    Returns: {"item_id", "prev_stat", "new_stat"} or None
    """
    with conn.cursor() as cur:
        # 현재 상태 조회
        cur.execute(
            "SELECT item_id, cur_stat FROM item WHERE item_id = %s",
            (item_id,),
        )
        row = cur.fetchone()
        if not row:
            return None

        _, current_stat = row[0], row[1]

        # 대상 단계 결정
        new_stat = target_stage or _next_stage(current_stat or "")
        if not new_stat:
            return {"item_id": item_id, "prev_stat": current_stat, "new_stat": None}

        # 업데이트
        cur.execute(
            "UPDATE item SET cur_stat = %s WHERE item_id = %s",
            (new_stat, item_id),
        )
        conn.commit()

        return {"item_id": item_id, "prev_stat": current_stat, "new_stat": new_stat}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="시리얼 RFID 태그 → item 공정 단계 업데이트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--serial-port",
        default=DEFAULT_SERIAL_PORT,
        help=f"시리얼 포트 (기본: {DEFAULT_SERIAL_PORT})",
    )
    p.add_argument(
        "--baudrate",
        type=int,
        default=DEFAULT_BAUDRATE,
        help=f"보드레이트 (기본: {DEFAULT_BAUDRATE})",
    )
    p.add_argument("--stage", help="직접 지정할 공정 단계 (예: MM, DM, PP). 미지정 시 자동 진행")
    p.add_argument("--dry-run", action="store_true", help="DB 업데이트 없이 조회만")
    p.add_argument("--exit-on-first", action="store_true", help="첫 처리 성공 후 종료")
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    shared_key = os.getenv("SHARED_KEY")
    if not shared_key:
        sys.stderr.write("[ERROR] SHARED_KEY 환경변수 미설정.\n")
        return 1

    psycopg2, pyserial = _import_deps()

    # DB 연결
    try:
        db = _get_db(psycopg2)
    except Exception as e:
        sys.stderr.write(f"[ERROR] DB 연결 실패: {e}\n")
        return 2

    # 시리얼 포트 열기
    try:
        ser = pyserial.Serial(args.serial_port, args.baudrate, timeout=1)
    except pyserial.SerialException as e:
        sys.stderr.write(f"[ERROR] 시리얼 포트 열기 실패: {e}\n")
        db.close()
        return 3

    stage_hint = f"고정={args.stage}" if args.stage else "자동진행"
    sys.stderr.write(
        f"[INFO] 시리얼 RFID → item 업데이트 시작\n"
        f"  port       = {args.serial_port}\n"
        f"  baudrate   = {args.baudrate}\n"
        f"  stage      = {stage_hint}\n"
        f"  dry_run    = {args.dry_run}\n"
        f"  mode       = {'단건' if args.exit_on_first else '연속'}\n"
        f"Ctrl+C 로 종료.\n\n"
    )
    sys.stderr.flush()

    # 우아한 종료
    _running = {"flag": True}

    def _stop(signum, _frame):
        _running["flag"] = False
        sys.stderr.write(f"\n[INFO] signal {signum} 수신 — 종료 중...\n")

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    scan_count = 0
    try:
        while _running["flag"]:
            if not ser.readable():
                continue

            line = ser.readline().decode("utf-8").strip()
            if not line:
                continue

            # JSON 파싱
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            # access_key 인증
            if data.get("access_key") != shared_key:
                continue

            full_id = data.get("item_id", "")
            if not full_id:
                continue

            # 태그 파싱: order_{ord_id}_item_{YYYYMMDD}_{item_id}
            match = RFID_PAYLOAD_RE.fullmatch(full_id.strip())
            if not match:
                sys.stderr.write(f"[WARN] 태그 형식 불일치: {full_id!r}\n")
                continue

            ord_id = int(match.group("ord"))
            item_id = int(match.group("seq"))
            scan_count += 1

            sys.stderr.write(
                f"[{scan_count:04d}] 태그 수신: {full_id} → ord_id={ord_id} item_id={item_id}\n"
            )

            # --- 1. 현재 아이템 조회 ---
            try:
                info = _lookup_item(db, item_id)
            except Exception as e:
                db.rollback()
                sys.stderr.write(f"[{scan_count:04d}] 조회 에러: {e}\n")
                continue

            if not info:
                print(f"  [조회 실패] item_id={item_id} — DB에 없음")
                sys.stdout.flush()
                continue

            print("-" * 40)
            print(f"  아이템: {info['item_id']}")
            print(f"  담당자: {info['user_nm']} ({info['co_nm']})")
            print(f"  현재 공정: {info['cur_stat']}")

            # --- 2. 공정 단계 업데이트 ---
            if args.dry_run:
                target = args.stage or _next_stage(info["cur_stat"] or "")
                print(f"  [DRY-RUN] → {target or '(마지막 단계)'}")
            else:
                try:
                    result = _advance_stage(db, item_id, target_stage=args.stage)
                except Exception as e:
                    db.rollback()
                    print(f"  [업데이트 실패] {e}")
                    continue

                if result and result["new_stat"]:
                    print(f"  공정 변경: {result['prev_stat']} → {result['new_stat']}")
                elif result and result["new_stat"] is None:
                    print(f"  [완료] '{result['prev_stat']}' 이 마지막 단계입니다")
                else:
                    print(f"  [실패] item_id={item_id} 업데이트 대상 없음")

            print("-" * 40)
            sys.stdout.flush()

            if args.exit_on_first:
                print("처리 완료 — 프로그램을 종료합니다.")
                break
    finally:
        ser.close()
        db.close()

    sys.stderr.write(f"[INFO] 총 {scan_count} 건 처리. 종료.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
