"""Phase 0-2: 마스터 데이터 시드 (테이블 생성 후 한 번만).

DB: seed/seed_master.sql 실행
    - user_account, product, product_option, pp_options, product_order_pattern_master
    - pattern_master, zone, res, equip, chg_location_stat, strg_location_stat, ship_location_stat
    - trans, trans_task_bat_threshold, tat_nav_pose_master, ra_motion_step, ai_model 등
"""

from __future__ import annotations

import pathlib
import sys

import _db

_SQL = pathlib.Path(__file__).parent.parent / "seed" / "seed_master.sql"


def main() -> int:
    _db.load_env()

    try:
        with _db.connect(autocommit=True) as conn:
            cur = conn.cursor()
            cur.execute(_SQL.read_text())
            print(f"마스터 데이터 시드 완료  ({_SQL.name})")

            tables = [
                "user_account", "category", "product", "product_option",
                "pp_options", "product_order_pattern_master", "pattern_master", "zone", "res", "equip",
                "equip_load_spec", "chg_location_stat",
                "strg_location_stat", "ship_location_stat", "trans",
                "trans_task_bat_threshold", "tat_nav_pose_master",
                "ra_motion_step", "ai_model",
            ]
            print()
            print("--- 시드 결과 ---")
            for t in tables:
                cur.execute(f"SELECT COUNT(*) AS n FROM {t}")
                print(f"  {t}: {cur.fetchone()['n']}")

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
