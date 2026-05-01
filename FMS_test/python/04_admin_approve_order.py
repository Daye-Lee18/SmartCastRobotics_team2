"""Phase 1-2: 관리자 주문 승인 (RCVD → APPR)

=======================================================================
[방법 A] 웹사이트에서 승인하기 (권장)
=======================================================================

1. 백엔드 + 웹 실행 (아직 안 띄운 경우)
       ./scripts/run-backend.sh   # FastAPI :8000
       ./scripts/run-web.sh       # Next.js  :3001
cf) 원격접속의 경우:
       ssh -L 3001:localhost:3001 -L 8000:localhost:8000 addinedu@<HOST> -N

2. 브라우저에서 http://localhost:3001 접속 → 메인 화면에서 [관리자] 클릭

3. 관리자 로그인 (/admin/login)
       비밀번호 : admin1234  (기본값)

4. 관리자 포털 → [주문 관리] 클릭 → /orders 이동

5. 좌측 주문 목록에서 승인할 주문 클릭 (상태: 접수대기/RCVD)

6. 우측 상세 패널에서 [승인] 버튼 클릭 → RCVD → APPR 전환

7. DB 반영 확인
       python python/06_query_order_and_items.py --ord-id <ord_id>

8. 다음 단계
       python python/05_operator_start_production.py --ord-id <ord_id>

-----------------------------------------------------------------------
[방법 B] 이 스크립트로 직접 UPDATE (웹 없이 빠른 테스트용)
-----------------------------------------------------------------------

실행:  python python/04_admin_approve_order.py --ord-id <ord_id>

기본값: admin_id=1 (관리자)

=======================================================================

Input  : --ord-id (required), --admin-id
DB     : INSERT ord_txn(APPR), UPDATE ord_stat RCVD->APPR, INSERT ord_log
Output : ord_id + new status summary
"""

from __future__ import annotations

import argparse
import sys

import _db


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Admin approves an order")
    p.add_argument("--ord-id",   type=int, required=True, help="order ID to approve")
    p.add_argument("--admin-id", type=int, default=1,     help="admin user_id (default: 1)")
    return p.parse_args()


def main() -> int:
    _db.load_env()
    args = parse_args()

    try:
        with _db.connect() as conn:
            cur = conn.cursor()

            # Validate admin
            cur.execute(
                "SELECT user_id, user_nm, role FROM user_account WHERE user_id = %s",
                (args.admin_id,),
            )
            admin = cur.fetchone()
            if not admin or admin["role"] != "admin":
                role = admin["role"] if admin else "not found"
                print(f"ERROR: user_id {args.admin_id} is not an admin (role={role}).", file=sys.stderr)
                return 1

            # Validate order state
            cur.execute(
                """
                SELECT os.ord_stat, od.qty, u.user_nm AS customer_nm
                  FROM ord_stat os
                  JOIN ord o  ON o.ord_id  = os.ord_id
                  JOIN ord_detail od ON od.ord_id = os.ord_id
                  JOIN user_account u ON u.user_id = o.user_id
                 WHERE os.ord_id = %s
                """,
                (args.ord_id,),
            )
            stat = cur.fetchone()
            if not stat:
                print(f"ERROR: ord_id {args.ord_id} not found.", file=sys.stderr)
                return 1
            if stat["ord_stat"] != "RCVD":
                print(
                    f"ERROR: ord_id {args.ord_id} is not in RCVD state (current: {stat['ord_stat']}).",
                    file=sys.stderr,
                )
                return 1

            # --- writes ---
            cur.execute(
                "INSERT INTO ord_txn (ord_id, txn_type) VALUES (%s, 'APPR')",
                (args.ord_id,),
            )

            cur.execute(
                """
                UPDATE ord_stat
                   SET ord_stat = 'APPR', user_id = %s, updated_at = now()
                 WHERE ord_id = %s
                """,
                (args.admin_id, args.ord_id),
            )

            cur.execute(
                """
                INSERT INTO ord_log (ord_id, prev_stat, new_stat, changed_by)
                VALUES (%s, 'RCVD', 'APPR', %s)
                RETURNING logged_at
                """,
                (args.ord_id, args.admin_id),
            )
            logged_at = cur.fetchone()["logged_at"]

            cur.close()
        # auto-commit

        print("=" * 55)
        print("주문 승인 완료")
        print("=" * 55)
        print(f"  ord_id   : {args.ord_id}")
        print(f"  고객     : {stat['customer_nm']}")
        print(f"  수량     : {stat['qty']}")
        print(f"  승인자   : {admin['user_nm']} (admin_id={args.admin_id})")
        print(f"  상태     : RCVD  ->  APPR")
        print(f"  처리 시각: {logged_at}")
        print()
        print(f"  다음 단계: python 05_operator_start_production.py --ord-id {args.ord_id} --operator-id 2")

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
