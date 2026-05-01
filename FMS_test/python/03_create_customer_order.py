"""Phase 1-1: 고객 주문 생성

=======================================================================
[방법 A] 웹사이트에서 직접 주문하기 (권장)
=======================================================================

1. 백엔드 + 웹 실행
       ./scripts/run-backend.sh   # FastAPI :8000
       ./scripts/run-web.sh       # Next.js  :3001
cf) 원격접속해서 실험하는 경우, 
ssh -L 3001:localhost:3001 -L 8000:localhost:8000 addinedu@<HOST> -N
와 같은 포워드명령 사용하여, 로컬에서 http://localhost:3001 접속 가능하도록 설정

2. 브라우저에서 http://localhost:3001 접속 후 고객 계정으로 로그인

       [고객 A]
       회사명     : TechBuild Inc.
       담당자명   : 이민준
       연락처     : 010-3333-4444
       이메일     : minjun@techbuild.co
       비밀번호   : customer1234

       [고객 B]
       회사명     : BuildWorld Co.
       담당자명   : 정수연
       연락처     : 010-9999-0000
       이메일     : sooyeon@buildworld.kr
       비밀번호   : customer1234

3. 제품 선택
       카테고리:  CMH(원형) / RMH(사각) / EMH(타원형)
       예시:      R-D450 원형 맨홀뚜껑 (prod_id=1, base_price=75,000원)

4. 옵션 입력
       수량       예: 15 (10개 이상부터 가능)
       납기일     예: 2026-05-15
       배송지     예: 서울특별시 강남구 테헤란로 123
       후처리     표면 연마(+5,000) / 방청 코팅(+3,000) /
                  아연 도금(+8,000) / 로고·문구 삽입(+7,000)

5. 주문 제출 → 화면에 표시된 ord_id 메모

6. DB 반영 확인
       python python/06_query_order_and_items.py --ord-id <ord_id>

7. 다음 단계
       python python/04_admin_approve_order.py --ord-id <ord_id>

-----------------------------------------------------------------------
[방법 B] 이 스크립트로 직접 INSERT (웹 없이 빠른 테스트용)
-----------------------------------------------------------------------

실행:  python python/03_create_customer_order.py [옵션]

기본값: 이민준(user_id=4) / R-D450(prod_id=1) / 수량 3 /
        표면연마+방청코팅(pp_ids=1,2) / 납기 2026-05-15

웹과 DB 결과는 동일합니다.
=======================================================================

Input  : --user-id, --prod-id, --qty, --due-date, --ship-addr, [--pp-ids ...]
DB     : INSERT ord, ord_detail, ord_pp_map, ord_txn, ord_stat, ord_log
Output : 생성된 ord_id + 상태 요약
"""

from __future__ import annotations

import argparse
import sys

import _db


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="고객 주문 생성 (웹 UI 대체용 스크립트)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--user-id",   type=int, default=4,
                   help="customer user_id  (기본: 4 = 이민준)")
    p.add_argument("--prod-id",   type=int, default=1,
                   help="product prod_id   (기본: 1 = R-D450 / CMH)")
    p.add_argument("--qty",       type=int, default=3,
                   help="주문 수량          (기본: 3)")
    p.add_argument("--due-date",  type=str, default="2026-05-15",
                   help="납기일 YYYY-MM-DD  (기본: 2026-05-15)")
    p.add_argument("--ship-addr", type=str, default="서울특별시 강남구 테헤란로 123",
                   help="배송지")
    p.add_argument("--pp-ids",    type=int, nargs="*", default=[1, 2],
                   help="후처리 옵션 ID 목록 (기본: 1=표면연마 2=방청코팅)")
    return p.parse_args()


def main() -> int:
    _db.load_env()
    args = parse_args()

    try:
        with _db.connect() as conn:
            cur = conn.cursor()

            # 고객 계정 검증
            cur.execute(
                "SELECT user_id, user_nm, role FROM user_account WHERE user_id = %s",
                (args.user_id,),
            )
            user = cur.fetchone()
            if not user:
                print(f"ERROR: user_id {args.user_id} not found.", file=sys.stderr)
                return 1
            if user["role"] != "customer":
                print(f"ERROR: user_id {args.user_id} role={user['role']} is not a customer.", file=sys.stderr)
                return 1

            # 제품 검증
            cur.execute(
                "SELECT prod_id, cate_cd, base_price FROM product WHERE prod_id = %s",
                (args.prod_id,),
            )
            prod = cur.fetchone()
            if not prod:
                print(f"ERROR: prod_id {args.prod_id} not found.", file=sys.stderr)
                return 1

            # 후처리 옵션 검증 + 추가 비용 합산
            pp_extra = 0
            valid_pp: list[dict] = []
            for pp_id in (args.pp_ids or []):
                cur.execute(
                    "SELECT pp_id, pp_nm, extra_cost FROM pp_options WHERE pp_id = %s",
                    (pp_id,),
                )
                pp = cur.fetchone()
                if not pp:
                    print(f"ERROR: pp_id {pp_id} not found.", file=sys.stderr)
                    return 1
                pp_extra += int(pp["extra_cost"])
                valid_pp.append(pp)

            final_price = (int(prod["base_price"]) + pp_extra) * args.qty

            # --- DB INSERT ---
            cur.execute(
                "INSERT INTO ord (user_id) VALUES (%s) RETURNING ord_id, created_at",
                (args.user_id,),
            )
            ord_row = cur.fetchone()
            ord_id = ord_row["ord_id"]
            created_at = ord_row["created_at"]

            cur.execute(
                """
                INSERT INTO ord_detail (ord_id, prod_id, qty, final_price, due_date, ship_addr)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (ord_id, args.prod_id, args.qty, final_price, args.due_date, args.ship_addr),
            )

            for pp in valid_pp:
                cur.execute(
                    "INSERT INTO ord_pp_map (ord_id, pp_id) VALUES (%s, %s)",
                    (ord_id, pp["pp_id"]),
                )

            cur.execute(
                "INSERT INTO ord_txn (ord_id, txn_type) VALUES (%s, 'RCVD')",
                (ord_id,),
            )

            cur.execute(
                "INSERT INTO ord_stat (ord_id, user_id, ord_stat, gp_qty, dp_qty) VALUES (%s, %s, 'RCVD', 0, 0)",
                (args.user_id, args.user_id),
            )

            cur.execute(
                "INSERT INTO ord_log (ord_id, prev_stat, new_stat, changed_by) VALUES (%s, NULL, 'RCVD', %s)",
                (ord_id, args.user_id),
            )

            cur.close()
        # auto-commit

        pp_str = ", ".join(f"{p['pp_nm']}(+{int(p['extra_cost']):,}원)" for p in valid_pp) or "(없음)"
        print("=" * 55)
        print("주문 생성 완료")
        print("=" * 55)
        print(f"  ord_id      : {ord_id}")
        print(f"  고객         : {user['user_nm']} (user_id={args.user_id})")
        print(f"  제품         : prod_id={args.prod_id}  ({prod['cate_cd']})")
        print(f"  수량         : {args.qty}")
        print(f"  최종 금액    : {final_price:,}원")
        print(f"  납기일       : {args.due_date}")
        print(f"  배송지       : {args.ship_addr}")
        print(f"  후처리       : {pp_str}")
        print(f"  상태         : RCVD")
        print(f"  생성 시각    : {created_at}")
        print()
        print(f"  다음 단계: python 04_admin_approve_order.py --ord-id {ord_id} --admin-id 1")

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
