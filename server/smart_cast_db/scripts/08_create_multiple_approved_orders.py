"""Create multiple APPR orders for PyQt pattern-control testing.

Purpose:
    PyQt 의 "패턴 위치 조작 및 생산 시작" 탭에 APPR 주문이 여러 개 표시되는지
    빠르게 확인하기 위한 테스트 데이터 생성 스크립트.

Run:
    cd server/smart_cast_db
    python scripts/08_create_multiple_approved_orders.py --count 5

DB:
    INSERT ord, ord_detail, ord_pp_map, ord_pattern(pattern_id), ord_txn, ord_stat, ord_log

Output:
    생성/승인된 ord_id 목록과 PyQt 확인 방법.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from typing import Iterable

import _db


DEFAULT_SCENARIOS = [
    {"prod_id": 1, "pp_ids": [1, 2], "qty": 3},
    {"prod_id": 2, "pp_ids": [], "qty": 2},
    {"prod_id": 4, "pp_ids": [3], "qty": 4},
    {"prod_id": 7, "pp_ids": [1, 4], "qty": 1},
    {"prod_id": 9, "pp_ids": [2, 3, 4], "qty": 5},
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PyQt APPR 목록 검증용 주문 여러 건 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--count", type=int, default=5, help="생성할 주문 수 (기본: 5)")
    parser.add_argument("--user-id", type=int, default=4, help="customer user_id (기본: 4)")
    parser.add_argument("--admin-id", type=int, default=1, help="admin user_id (기본: 1)")
    parser.add_argument("--ship-addr", type=str, default="서울특별시 강남구 테헤란로 123", help="배송지")
    parser.add_argument("--due-start", type=str, default="2026-05-15", help="첫 납기일 YYYY-MM-DD")
    return parser.parse_args()


def _pp_mask(pp_ids: Iterable[int]) -> int:
    mask = 0
    for pp_id in pp_ids:
        mask |= 1 << (int(pp_id) - 1)
    return mask


def _validate_user(cur, user_id: int, role: str) -> dict:
    cur.execute(
        "SELECT user_id, user_nm, role FROM user_account WHERE user_id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    if not row or row["role"] != role:
        actual = row["role"] if row else "not found"
        raise ValueError(f"user_id {user_id} must be {role}; current={actual}")
    return row


def _load_product_context(cur, prod_id: int, pp_ids: list[int]) -> dict:
    cur.execute(
        "SELECT prod_id, cate_cd, base_price FROM product WHERE prod_id = %s",
        (prod_id,),
    )
    product = cur.fetchone()
    if not product:
        raise ValueError(f"prod_id {prod_id} not found")

    cur.execute(
        """
        SELECT prod_opt_id, diameter, thickness, material, load_class
          FROM product_option
         WHERE prod_id = %s
         ORDER BY prod_opt_id
         LIMIT 1
        """,
        (prod_id,),
    )
    option = cur.fetchone()
    if not option:
        raise ValueError(f"product_option for prod_id {prod_id} not found")

    valid_pp: list[dict] = []
    for pp_id in sorted(set(pp_ids)):
        cur.execute(
            "SELECT pp_id, pp_nm, extra_cost FROM pp_options WHERE pp_id = %s",
            (pp_id,),
        )
        pp = cur.fetchone()
        if not pp:
            raise ValueError(f"pp_id {pp_id} not found")
        valid_pp.append(pp)

    mask = _pp_mask([pp["pp_id"] for pp in valid_pp])
    cur.execute(
        """
        SELECT pattern_id, pattern_nm
          FROM product_order_pattern_master
         WHERE prod_id = %s
           AND diameter = %s
           AND thickness = %s
           AND material = %s
           AND load_class = %s
           AND pp_mask = %s
           AND is_active = TRUE
        """,
        (
            prod_id,
            option["diameter"],
            option["thickness"],
            option["material"],
            option["load_class"],
            mask,
        ),
    )
    pattern = cur.fetchone()
    if not pattern:
        raise ValueError(f"product_order_pattern_master row not found for prod_id={prod_id}, pp_mask={mask}")

    return {
        "product": product,
        "option": option,
        "pp": valid_pp,
        "pattern": pattern,
    }


def _create_approved_order(
    *,
    cur,
    user_id: int,
    admin_id: int,
    prod_id: int,
    qty: int,
    pp_ids: list[int],
    due_date: date,
    ship_addr: str,
) -> dict:
    ctx = _load_product_context(cur, prod_id, pp_ids)
    product = ctx["product"]
    option = ctx["option"]
    valid_pp = ctx["pp"]
    pattern = ctx["pattern"]
    final_price = (int(product["base_price"]) + sum(int(pp["extra_cost"]) for pp in valid_pp)) * qty

    cur.execute(
        "INSERT INTO ord (user_id) VALUES (%s) RETURNING ord_id, created_at",
        (user_id,),
    )
    ord_row = cur.fetchone()
    ord_id = ord_row["ord_id"]

    cur.execute(
        """
        INSERT INTO ord_detail
            (ord_id, prod_id, diameter, thickness, material, load_class, qty, final_price, due_date, ship_addr)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            ord_id,
            prod_id,
            option["diameter"],
            option["thickness"],
            option["material"],
            option["load_class"],
            qty,
            final_price,
            due_date.isoformat(),
            ship_addr,
        ),
    )

    for pp in valid_pp:
        cur.execute(
            "INSERT INTO ord_pp_map (ord_id, pp_id) VALUES (%s, %s)",
            (ord_id, pp["pp_id"]),
        )

    cur.execute(
        "INSERT INTO ord_pattern (ord_id, pattern_id) VALUES (%s, %s)",
        (ord_id, pattern["pattern_id"]),
    )

    cur.execute("INSERT INTO ord_txn (ord_id, txn_type) VALUES (%s, 'RCVD')", (ord_id,))
    cur.execute("INSERT INTO ord_txn (ord_id, txn_type) VALUES (%s, 'APPR')", (ord_id,))
    cur.execute(
        "INSERT INTO ord_stat (ord_id, user_id, ord_stat) VALUES (%s, %s, 'APPR')",
        (ord_id, admin_id),
    )
    cur.execute(
        "INSERT INTO ord_log (ord_id, prev_stat, new_stat, changed_by) VALUES (%s, NULL, 'RCVD', %s)",
        (ord_id, user_id),
    )
    cur.execute(
        "INSERT INTO ord_log (ord_id, prev_stat, new_stat, changed_by) VALUES (%s, 'RCVD', 'APPR', %s)",
        (ord_id, admin_id),
    )

    return {
        "ord_id": ord_id,
        "prod_id": prod_id,
        "cate_cd": product["cate_cd"],
        "qty": qty,
        "pp_ids": [pp["pp_id"] for pp in valid_pp],
        "pattern_id": pattern["pattern_id"],
        "pattern_nm": pattern["pattern_nm"],
        "due_date": due_date.isoformat(),
    }


def main() -> int:
    _db.load_env()
    args = parse_args()

    if args.count <= 0:
        print("ERROR: --count must be greater than 0.", file=sys.stderr)
        return 1

    try:
        due_start = date.fromisoformat(args.due_start[:10])
    except ValueError:
        print(f"ERROR: invalid --due-start: {args.due_start}", file=sys.stderr)
        return 1

    try:
        with _db.connect() as conn:
            cur = conn.cursor()
            user = _validate_user(cur, args.user_id, "customer")
            admin = _validate_user(cur, args.admin_id, "admin")

            created: list[dict] = []
            for idx in range(args.count):
                scenario = DEFAULT_SCENARIOS[idx % len(DEFAULT_SCENARIOS)]
                created.append(
                    _create_approved_order(
                        cur=cur,
                        user_id=args.user_id,
                        admin_id=args.admin_id,
                        prod_id=int(scenario["prod_id"]),
                        qty=int(scenario["qty"]),
                        pp_ids=list(scenario["pp_ids"]),
                        due_date=due_start + timedelta(days=idx),
                        ship_addr=args.ship_addr,
                    )
                )
            cur.close()

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("=" * 72)
    print("PyQt 패턴 위치 탭 검증용 APPR 주문 생성 완료")
    print("=" * 72)
    print(f"  customer : {user['user_nm']} (user_id={args.user_id})")
    print(f"  admin    : {admin['user_nm']} (admin_id={args.admin_id})")
    print()
    for row in created:
        pp_label = ",".join(str(pp_id) for pp_id in row["pp_ids"]) or "없음"
        print(
            f"  ord_id={row['ord_id']:<4} APPR  prod_id={row['prod_id']}({row['cate_cd']}) "
            f"qty={row['qty']} pp={pp_label} pattern_id={row['pattern_id']} due={row['due_date']}"
        )
    print()
    print("확인:")
    print("  1. ./scripts/run-backend.sh")
    print("  2. ./scripts/run-pyqt.sh")
    print("  3. 첫 탭 '패턴 위치 조작 및 생산 시작'에서 위 ord_id들이 보이는지 확인")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
