"""Phase 0: DB connection check.

Input  : DATABASE_URL (env or .env file)
DB     : Reads master table row counts.
Output : Prints row counts for key master tables.
"""

from __future__ import annotations

import sys

import _db

MASTER_TABLES = [
    "user_account",
    "category",
    "product",
    "product_option",
    "pp_options",
    "zone",
    "res",
    "equip",
    "strg_loc_stat",
    "ship_loc_stat",
    "trans",
]


def main() -> int:
    _db.load_env()

    try:
        with _db.connect() as conn:
            cur = conn.cursor()
            print("FMS_test DB connection OK")
            for table_name in MASTER_TABLES:
                cur.execute(f"SELECT COUNT(*) AS row_count FROM {table_name}")
                row = cur.fetchone()
                print(f"  {table_name}: {row['row_count']}")
            cur.close()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
