from __future__ import annotations

import ssl
from pathlib import Path

import asyncpg

_SSL_CERT = Path(__file__).parent / "global-bundle.pem"

_DB_CONFIG: dict = {
    "host": "teamdb.ct4cesagstqf.ap-northeast-2.rds.amazonaws.com",
    "port": 5432,
    "database": "Casting",
    "user": "postgres",
    "password": "team21234",
    "min_size": 2,
    "max_size": 10,
}


async def create_pool() -> asyncpg.Pool:
    ssl_ctx = ssl.create_default_context(cafile=str(_SSL_CERT))
    return await asyncpg.create_pool(**_DB_CONFIG, ssl=ssl_ctx)
