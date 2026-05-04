"""Phase 2: Operator starts production.

=======================================================================
[방법 A] 스크립트로 직접 생산 시작
=======================================================================

주문 생성/승인 후, operator 가 패턴을 등록한 ord_id 에 대해
생산 시작 상태(MFG)로 바꾸고 싶을 때 사용.

실행:
    python scripts/05_operator_start_production.py --ord-id <ord_id>

예시:
    python scripts/05_operator_start_production.py --ord-id 41 --operator-id 2

흐름:
    1) ord_id 의 현재 상태가 APPR 인지 확인
    2) ord_pattern 에 패턴이 등록되어 있는지 확인
    3) 주문 수량만큼 item row 생성 (cur_stat='CREATED')
    4) ord_stat 를 APPR -> MFG 로 갱신
    5) ord_log 에 상태 이력 기록

결과 확인:
    python scripts/06_query_order_and_items.py --ord-id <ord_id>

=======================================================================
[방법 B] PyQt 앱에서 직접 실험
=======================================================================

PyQt Monitoring 앱에서 주문 상태를 직접 보면서 테스트할 때 사용.

실행:
    ./scripts/run-pyqt.sh

절차:
    1) PyQt Monitoring 앱 실행
    2) 주문 목록에서 대상 ord_id 확인
    3) operator / management 화면에서 생산 시작 동작 수행
    4) DB 확인이 필요하면 이 스크립트와 06_query_order_and_items.py 를 함께 사용

장점:
    - 버튼 클릭 이후 상태 변화를 화면에서 바로 확인 가능
    - 운영 흐름과 같은 방식으로 실험 가능

Input  : --ord-id (required), --operator-id
DB     : SELECT ord_pattern 확인 후 INSERT item x qty (cur_stat='CREATED'),
         UPDATE ord_stat APPR->MFG,
         INSERT ord_log
Output : ord_id + item_ids created
"""

from __future__ import annotations

import argparse
import sys

import _db


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Operator starts production for an approved order")
    p.add_argument("--ord-id",      type=int, required=True, help="order ID")
    p.add_argument("--operator-id", type=int, default=2,     help="operator user_id (default: 2)")
    return p.parse_args()


def main() -> int:
    _db.load_env()
    args = parse_args()

    try:
        with _db.connect() as conn:
            cur = conn.cursor()

            # Validate operator
            cur.execute(
                "SELECT user_id, user_nm, role FROM user_account WHERE user_id = %s",
                (args.operator_id,),
            )
            op = cur.fetchone()
            if not op or op["role"] != "operator":
                role = op["role"] if op else "not found"
                print(f"ERROR: user_id {args.operator_id} is not an operator (role={role}).", file=sys.stderr)
                return 1

            # Validate order state (LEFT JOIN product — prod_id may be NULL for web-created orders)
            cur.execute(
                """
                SELECT os.ord_stat, od.qty, p.cate_cd
                  FROM ord_stat os
                  JOIN ord_detail od ON od.ord_id = os.ord_id
                  LEFT JOIN product p ON p.prod_id = od.prod_id
                 WHERE os.ord_id = %s
                """,
                (args.ord_id,),
            )
            row = cur.fetchone()
            if not row:
                print(f"ERROR: ord_id {args.ord_id} not found.", file=sys.stderr)
                return 1
            if row["ord_stat"] != "APPR":
                print(
                    f"ERROR: ord_id {args.ord_id} is not in APPR state (current: {row['ord_stat']}).",
                    file=sys.stderr,
                )
                return 1

            cur.execute(
                "SELECT pattern_id, ptn_loc_id FROM ord_pattern WHERE ord_id = %s AND ptn_loc_id IS NOT NULL",
                (args.ord_id,),
            )
            pattern_row = cur.fetchone()
            if not pattern_row:
                print(
                    f"ERROR: ord_id {args.ord_id} has no registered pattern location. "
                    "Register pattern loc 1-3 first.",
                    file=sys.stderr,
                )
                return 1

            qty = row["qty"]
            cate_cd = row["cate_cd"] or "(unknown)"

            # --- writes ---
            item_ids: list[int] = []
            for _ in range(qty):
                cur.execute(
                    "INSERT INTO item (ord_id, cur_stat) VALUES (%s, 'CREATED') RETURNING item_id",
                    (args.ord_id,),
                )
                item_ids.append(cur.fetchone()["item_id"])

            cur.execute(
                """
                UPDATE ord_stat
                   SET ord_stat = 'MFG', user_id = %s, updated_at = now()
                 WHERE ord_id = %s
                """,
                (args.operator_id, args.ord_id),
            )

            cur.execute(
                """
                INSERT INTO ord_log (ord_id, prev_stat, new_stat, changed_by)
                VALUES (%s, 'APPR', 'MFG', %s)
                RETURNING logged_at
                """,
                (args.ord_id, args.operator_id),
            )
            logged_at = cur.fetchone()["logged_at"]

            cur.close()
        # auto-commit

        print("=" * 55)
        print("생산 시작 완료")
        print("=" * 55)
        print(f"  ord_id       : {args.ord_id}")
        print(f"  제품 카테고리 : {cate_cd}")
        print(f"  수량          : {qty}")
        print(f"  패턴         : pattern_id={pattern_row['pattern_id']}, ptn_loc_id={pattern_row['ptn_loc_id']}")
        print(f"  작업자        : {op['user_nm']} (operator_id={args.operator_id})")
        print(f"  상태          : APPR  ->  MFG")
        print(f"  처리 시각     : {logged_at}")
        print()
        print(f"  생성된 item ({len(item_ids)}개):")
        for i, iid in enumerate(item_ids, 1):
            print(f"    item #{i}: item_id={iid}  cur_stat=CREATED")
        print()
        print(f"  다음 단계: python scripts/06_query_order_and_items.py --ord-id {args.ord_id}")

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
