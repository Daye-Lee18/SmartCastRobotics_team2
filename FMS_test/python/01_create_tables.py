"""Phase 0-1: 스키마 생성 + 테이블 생성 (처음 한 번만).

DB: CREATE SCHEMA IF NOT EXISTS + 01_create_tables_v22.sql 실행
"""

from __future__ import annotations

import pathlib
import sys

import _db

_SQL = pathlib.Path(__file__).parent.parent / "sql" / "01_create_tables_v22.sql"


def main() -> int:
    _db.load_env()

    import os
    schema = os.environ.get("DB_SCHEMA", "smartcast").strip()

    try:
        import psycopg
        import os

        url = os.environ.get("DATABASE_URL")
        if not url:
            print("ERROR: DATABASE_URL is not set.", file=sys.stderr)
            return 1

        ssl_cert = os.environ.get("SSL_CERT", "").strip()
        _pem = pathlib.Path(__file__).parent.parent.parent / "global-bundle.pem"
        if not ssl_cert and _pem.exists():
            ssl_cert = str(_pem)

        connect_kwargs: dict = {"autocommit": True}
        if ssl_cert:
            connect_kwargs["sslmode"] = "verify-full"
            connect_kwargs["sslrootcert"] = ssl_cert

        with psycopg.connect(url, **connect_kwargs) as conn:
            cur = conn.cursor()
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            print(f"스키마 '{schema}' 확인/생성 완료")

            cur.execute(f"SET search_path = {schema}")
            cur.execute(_SQL.read_text())
            print(f"테이블 생성 완료  ({_SQL.name})")

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
