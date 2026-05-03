"""Phase 2: Operator starts production.

Input  : --ord-id (required), --operator-id
DB     : INSERT item x qty (cur_stat='CREATED'),
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
