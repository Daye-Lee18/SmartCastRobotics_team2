"""Query: Display full order + item state snapshot.

Input  : --ord-id (required)
DB     : SELECT ord, ord_detail, ord_stat, ord_log, item_stat
Output : Human-readable summary
"""

from __future__ import annotations

import argparse
import sys

import _db


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Query order and item state")
    p.add_argument("--ord-id", type=int, required=True, help="order ID to query")
    return p.parse_args()


def main() -> int:
    _db.load_env()
    args = parse_args()

    try:
        with _db.connect() as conn:
            cur = conn.cursor()

            # Order header
            cur.execute(
                """
                SELECT
                    o.ord_id, o.created_at,
                    u.user_nm, u.co_nm,
                    od.qty, od.final_price, od.due_date, od.ship_addr,
                    p.prod_id, p.cate_cd, p.base_price,
                    os.ord_stat, os.gp_qty, os.dp_qty, os.updated_at AS stat_updated
                FROM ord o
                JOIN user_account u  ON u.user_id  = o.user_id
                JOIN ord_detail od   ON od.ord_id   = o.ord_id
                JOIN product p       ON p.prod_id   = od.prod_id
                JOIN ord_stat os     ON os.ord_id   = o.ord_id
                WHERE o.ord_id = %s
                """,
                (args.ord_id,),
            )
            hdr = cur.fetchone()
            if not hdr:
                print(f"ERROR: ord_id {args.ord_id} not found.", file=sys.stderr)
                return 1

            # PP options
            cur.execute(
                """
                SELECT pp.pp_nm, pp.extra_cost
                  FROM ord_pp_map m
                  JOIN pp_options pp ON pp.pp_id = m.pp_id
                 WHERE m.ord_id = %s
                 ORDER BY pp.pp_id
                """,
                (args.ord_id,),
            )
            pp_rows = cur.fetchall()

            # Status history
            cur.execute(
                """
                SELECT l.prev_stat, l.new_stat, u.user_nm, l.logged_at
                  FROM ord_log l
                  LEFT JOIN user_account u ON u.user_id = l.changed_by
                 WHERE l.ord_id = %s
                 ORDER BY l.log_id
                """,
                (args.ord_id,),
            )
            log_rows = cur.fetchall()

            # Item stats
            cur.execute(
                """
                SELECT item_stat_id, flow_stat, result, updated_at
                  FROM item_stat
                 WHERE ord_id = %s
                 ORDER BY item_stat_id
                """,
                (args.ord_id,),
            )
            items = cur.fetchall()

            cur.close()

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # --- print ---
    pp_str = (
        ", ".join(f"{r['pp_nm']}(+{int(r['extra_cost']):,}원)" for r in pp_rows)
        if pp_rows
        else "(없음)"
    )

    print("=" * 60)
    print(f"  주문 #{hdr['ord_id']}  [{hdr['ord_stat']}]")
    print("=" * 60)
    print(f"  고객         : {hdr['user_nm']} ({hdr['co_nm']})")
    print(f"  제품         : prod_id={hdr['prod_id']}  {hdr['cate_cd']}  기본가={int(hdr['base_price']):,}원")
    print(f"  수량         : {hdr['qty']}")
    print(f"  최종 금액    : {int(hdr['final_price']):,}원")
    print(f"  납기일       : {hdr['due_date']}")
    print(f"  배송지       : {hdr['ship_addr']}")
    print(f"  후처리       : {pp_str}")
    print(f"  주문 생성    : {hdr['created_at']}")
    print(f"  상태 갱신    : {hdr['stat_updated']}")
    print(f"  GP qty       : {hdr['gp_qty']}  /  DP qty: {hdr['dp_qty']}")

    print()
    print("--- 상태 이력 ---")
    if not log_rows:
        print("  (없음)")
    else:
        for l in log_rows:
            prev = l["prev_stat"] or "---"
            print(f"  {prev:10s}  ->  {l['new_stat']:10s}  by {l['user_nm']}  @ {l['logged_at']}")

    print()
    print(f"--- 아이템 ({len(items)}개) ---")
    if not items:
        print("  (생성 전)")
    else:
        for item in items:
            result_str = "GP" if item["result"] is True else ("DP" if item["result"] is False else "-")
            print(
                f"  item_stat_id={item['item_stat_id']:4d}  "
                f"flow={item['flow_stat']:15s}  "
                f"result={result_str}  updated={item['updated_at']}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
