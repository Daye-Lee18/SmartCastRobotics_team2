"""Shared DB connection helper for smart_cast_db scripts."""
from __future__ import annotations

import os
import pathlib
import sys

import psycopg
from psycopg.rows import dict_row

_DB_ROOT = pathlib.Path(__file__).parent.parent
_DEFAULT_PEM = _DB_ROOT.parent.parent / "global-bundle.pem"


def load_env() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore[import-untyped]

        load_dotenv(_DB_ROOT / ".env")
    except ImportError:
        pass


def connect(**extra_params) -> psycopg.Connection:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL is not set.", file=sys.stderr)
        print("  Copy server/smart_cast_db/.env.example to server/smart_cast_db/.env and fill in the values.", file=sys.stderr)
        sys.exit(1)

    params: dict = {"row_factory": dict_row}

    ssl_cert = os.environ.get("SSL_CERT", "").strip()
    if not ssl_cert and _DEFAULT_PEM.exists():
        ssl_cert = str(_DEFAULT_PEM)

    if ssl_cert:
        params["sslmode"] = "verify-full"
        params["sslrootcert"] = ssl_cert

    schema = os.environ.get("DB_SCHEMA", "smartcast").strip()
    if schema:
        params["options"] = f"-c search_path={schema} -c timezone=Asia/Seoul"

    params.update(extra_params)
    return psycopg.connect(url, **params)
