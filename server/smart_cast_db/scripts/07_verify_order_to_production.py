"""End-to-end DB verification: create order -> approve -> start production.

목적:
    smartcast v23 스키마 기준으로 주문 1건을 생성하고, 관리자 승인 후
    생산 시작까지 진행했을 때 주요 테이블에 record 가 정상 반영되는지 확인한다.

검증 대상:
    ord, ord_detail, ord_pattern, ord_pp_map, ord_txn, ord_stat, ord_log, item

주의:
    이 스크립트는 검증용 주문/아이템 데이터를 실제 DB에 INSERT 한다.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

import _db


@dataclass
class Scenario:
    ord_id: int
    qty: int
    user_id: int
    admin_id: int
    operator_id: int
    prod_id: int
    ptn_id: int
    pp_ids: list[int]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="주문 생성부터 생산 시작까지 DB 적재를 검증합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--user-id", type=int, default=4, help="customer user_id (기본: 4)")
    p.add_argument("--admin-id", type=int, default=1, help="admin user_id (기본: 1)")
    p.add_argument("--operator-id", type=int, default=2, help="operator user_id (기본: 2)")
    p.add_argument("--prod-id", type=int, default=1, help="product prod_id (기본: 1)")
    p.add_argument("--qty", type=int, default=3, help="주문 수량 (기본: 3)")
    p.add_argument("--due-date", type=str, default="2026-05-31", help="납기일 YYYY-MM-DD")
    p.add_argument("--ship-addr", type=str, default="서울특별시 강남구 테헤란로 123", help="배송지")
    p.add_argument("--pp-ids", type=int, nargs="*", default=[1, 2, 3, 4], help="후처리 옵션 ID 목록")
    p.add_argument("--ptn-id", type=int, default=1, help="패턴 ID (기본: 1)")
    return p.parse_args()


def main() -> int:
    _db.load_env()
    args = parse_args()

    try:
        with _db.connect() as conn:
            cur = conn.cursor()

            _validate_actor(cur, args.user_id, "customer")
            _validate_actor(cur, args.admin_id, "admin")
            _validate_actor(cur, args.operator_id, "operator")
            product = _validate_product(cur, args.prod_id)
            _validate_pattern(cur, args.ptn_id)
            valid_pp = _validate_pp_options(cur, args.pp_ids)

            final_price = (int(product["base_price"]) + sum(int(pp["extra_cost"]) for pp in valid_pp)) * args.qty

            ord_id = _create_order(
                cur=cur,
                user_id=args.user_id,
                prod_id=args.prod_id,
                qty=args.qty,
                due_date=args.due_date,
                ship_addr=args.ship_addr,
                final_price=final_price,
                ptn_id=args.ptn_id,
                pp_ids=[pp["pp_id"] for pp in valid_pp],
            )
            _approve_order(cur=cur, ord_id=ord_id, admin_id=args.admin_id)
            _start_production(cur=cur, ord_id=ord_id, operator_id=args.operator_id, qty=args.qty)

            scenario = Scenario(
                ord_id=ord_id,
                qty=args.qty,
                user_id=args.user_id,
                admin_id=args.admin_id,
                operator_id=args.operator_id,
                prod_id=args.prod_id,
                ptn_id=args.ptn_id,
                pp_ids=[pp["pp_id"] for pp in valid_pp],
            )
            rows = _verify_records(cur, scenario)
            cur.close()

        _print_report(scenario, rows)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


def _validate_actor(cur, user_id: int, expected_role: str) -> None:
    cur.execute(
        "SELECT user_id, user_nm, role FROM user_account WHERE user_id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"user_id {user_id} not found")
    if row["role"] != expected_role:
        raise ValueError(
            f"user_id {user_id} role mismatch: expected {expected_role}, got {row['role']}"
        )


def _validate_product(cur, prod_id: int) -> dict:
    cur.execute(
        "SELECT prod_id, cate_cd, base_price FROM product WHERE prod_id = %s",
        (prod_id,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"prod_id {prod_id} not found")
    return row


def _validate_pattern(cur, ptn_id: int) -> None:
    cur.execute(
        "SELECT ptn_id FROM pattern_master WHERE ptn_id = %s AND is_active = TRUE",
        (ptn_id,),
    )
    if not cur.fetchone():
        raise ValueError(f"ptn_id {ptn_id} not found or inactive")


def _validate_pp_options(cur, pp_ids: list[int]) -> list[dict]:
    rows: list[dict] = []
    for pp_id in pp_ids:
        cur.execute(
            "SELECT pp_id, pp_nm, extra_cost FROM pp_options WHERE pp_id = %s",
            (pp_id,),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"pp_id {pp_id} not found")
        rows.append(row)
    return rows


def _create_order(
    *,
    cur,
    user_id: int,
    prod_id: int,
    qty: int,
    due_date: str,
    ship_addr: str,
    final_price: int,
    ptn_id: int,
    pp_ids: list[int],
) -> int:
    cur.execute(
        "INSERT INTO ord (user_id) VALUES (%s) RETURNING ord_id",
        (user_id,),
    )
    ord_id = cur.fetchone()["ord_id"]

    cur.execute(
        "INSERT INTO ord_pattern (ord_id, ptn_id) VALUES (%s, %s)",
        (ord_id, ptn_id),
    )
    cur.execute(
        """
        INSERT INTO ord_detail (ord_id, prod_id, qty, final_price, due_date, ship_addr)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (ord_id, prod_id, qty, final_price, due_date, ship_addr),
    )
    for pp_id in pp_ids:
        cur.execute(
            "INSERT INTO ord_pp_map (ord_id, pp_id) VALUES (%s, %s)",
            (ord_id, pp_id),
        )
    cur.execute("INSERT INTO ord_txn (ord_id, txn_type) VALUES (%s, 'RCVD')", (ord_id,))
    cur.execute(
        "INSERT INTO ord_stat (ord_id, user_id, ord_stat) VALUES (%s, %s, 'RCVD')",
        (ord_id, user_id),
    )
    cur.execute(
        "INSERT INTO ord_log (ord_id, prev_stat, new_stat, changed_by) VALUES (%s, NULL, 'RCVD', %s)",
        (ord_id, user_id),
    )
    return ord_id


def _approve_order(*, cur, ord_id: int, admin_id: int) -> None:
    cur.execute("INSERT INTO ord_txn (ord_id, txn_type) VALUES (%s, 'APPR')", (ord_id,))
    cur.execute(
        """
        UPDATE ord_stat
           SET ord_stat = 'APPR', user_id = %s, updated_at = now()
         WHERE ord_id = %s
        """,
        (admin_id, ord_id),
    )
    cur.execute(
        """
        INSERT INTO ord_log (ord_id, prev_stat, new_stat, changed_by)
        VALUES (%s, 'RCVD', 'APPR', %s)
        """,
        (ord_id, admin_id),
    )


def _start_production(*, cur, ord_id: int, operator_id: int, qty: int) -> None:
    for _ in range(qty):
        cur.execute(
            "INSERT INTO item (ord_id, cur_stat, cur_res) VALUES (%s, 'CREATED', 'PAT')",
            (ord_id,),
        )
    cur.execute(
        """
        UPDATE ord_stat
           SET ord_stat = 'MFG', user_id = %s, updated_at = now()
         WHERE ord_id = %s
        """,
        (operator_id, ord_id),
    )
    cur.execute(
        """
        INSERT INTO ord_log (ord_id, prev_stat, new_stat, changed_by)
        VALUES (%s, 'APPR', 'MFG', %s)
        """,
        (ord_id, operator_id),
    )


def _verify_records(cur, scenario: Scenario) -> dict[str, object]:
    rows: dict[str, object] = {}

    cur.execute("SELECT user_id FROM ord WHERE ord_id = %s", (scenario.ord_id,))
    rows["ord"] = cur.fetchone()

    cur.execute(
        "SELECT prod_id, qty FROM ord_detail WHERE ord_id = %s",
        (scenario.ord_id,),
    )
    rows["ord_detail"] = cur.fetchone()

    cur.execute(
        "SELECT ptn_id FROM ord_pattern WHERE ord_id = %s",
        (scenario.ord_id,),
    )
    rows["ord_pattern"] = cur.fetchone()

    cur.execute(
        "SELECT pp_id FROM ord_pp_map WHERE ord_id = %s ORDER BY pp_id",
        (scenario.ord_id,),
    )
    rows["ord_pp_map"] = cur.fetchall()

    cur.execute(
        "SELECT txn_type FROM ord_txn WHERE ord_id = %s ORDER BY txn_id",
        (scenario.ord_id,),
    )
    rows["ord_txn"] = cur.fetchall()

    cur.execute(
        "SELECT ord_stat, user_id FROM ord_stat WHERE ord_id = %s",
        (scenario.ord_id,),
    )
    rows["ord_stat"] = cur.fetchone()

    cur.execute(
        "SELECT prev_stat, new_stat, changed_by FROM ord_log WHERE ord_id = %s ORDER BY log_id",
        (scenario.ord_id,),
    )
    rows["ord_log"] = cur.fetchall()

    cur.execute(
        """
        SELECT item_id, cur_stat, cur_res, is_defective
          FROM item
         WHERE ord_id = %s
         ORDER BY item_id
        """,
        (scenario.ord_id,),
    )
    rows["item"] = cur.fetchall()

    return rows


def _print_report(scenario: Scenario, rows: dict[str, object]) -> None:
    ord_row = rows["ord"]
    detail_row = rows["ord_detail"]
    pattern_row = rows["ord_pattern"]
    pp_rows = rows["ord_pp_map"]
    txn_rows = rows["ord_txn"]
    stat_row = rows["ord_stat"]
    log_rows = rows["ord_log"]
    item_rows = rows["item"]

    checks: list[tuple[str, bool, str]] = [
        (
            "ord",
            ord_row is not None and ord_row["user_id"] == scenario.user_id,
            f"user_id={ord_row['user_id'] if ord_row else None}",
        ),
        (
            "ord_detail",
            detail_row is not None and detail_row["prod_id"] == scenario.prod_id and detail_row["qty"] == scenario.qty,
            f"prod_id={detail_row['prod_id'] if detail_row else None}, qty={detail_row['qty'] if detail_row else None}",
        ),
        (
            "ord_pattern",
            pattern_row is not None and pattern_row["ptn_id"] == scenario.ptn_id,
            f"ptn_id={pattern_row['ptn_id'] if pattern_row else None}",
        ),
        (
            "ord_pp_map",
            [r["pp_id"] for r in pp_rows] == scenario.pp_ids,
            f"pp_ids={[r['pp_id'] for r in pp_rows]}",
        ),
        (
            "ord_txn",
            [r["txn_type"] for r in txn_rows] == ["RCVD", "APPR"],
            f"txn_types={[r['txn_type'] for r in txn_rows]}",
        ),
        (
            "ord_stat",
            stat_row is not None and stat_row["ord_stat"] == "MFG" and stat_row["user_id"] == scenario.operator_id,
            f"ord_stat={stat_row['ord_stat'] if stat_row else None}, user_id={stat_row['user_id'] if stat_row else None}",
        ),
        (
            "ord_log",
            [(r["prev_stat"], r["new_stat"]) for r in log_rows] == [
                (None, "RCVD"),
                ("RCVD", "APPR"),
                ("APPR", "MFG"),
            ],
            f"log_pairs={[(r['prev_stat'], r['new_stat']) for r in log_rows]}",
        ),
        (
            "item",
            len(item_rows) == scenario.qty
            and all(r["cur_stat"] == "CREATED" for r in item_rows)
            and all(r["cur_res"] == "PAT" for r in item_rows),
            f"count={len(item_rows)}, states={[(r['cur_stat'], r['cur_res']) for r in item_rows]}",
        ),
    ]

    print("=" * 64)
    print("주문 생성 -> 승인 -> 생산 시작 DB 검증 결과")
    print("=" * 64)
    print(f"ord_id={scenario.ord_id}  qty={scenario.qty}  prod_id={scenario.prod_id}")
    print()
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name:12s}  {detail}")

    passed = sum(1 for _, ok, _ in checks if ok)
    print()
    print(f"summary: {passed}/{len(checks)} checks passed")
    print()
    print("생성된 item:")
    for row in item_rows:
        print(
            f"  item_id={row['item_id']} cur_stat={row['cur_stat']} cur_res={row['cur_res']} is_defective={row['is_defective']}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
