from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, TypeVar

import asyncpg
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _log(query: str, vals: list[Any], elapsed: float) -> None:
    logger.debug(
        "[DB] %.3fms | %s | vals=%s",
        elapsed * 1000,
        " ".join(query.split()),
        vals,
    )


def _log_error(query: str, vals: list[Any], exc: Exception) -> None:
    logger.error(
        "[DB ERROR] %s | vals=%s | error=%s",
        " ".join(query.split()),
        vals,
        exc,
    )


# ─── insert_row ───────────────────────────────────────────────────────────────

async def insert_row(
    pool: asyncpg.Pool,
    table: str,
    data: BaseModel,
    return_type: type[T],
    conn: asyncpg.Connection | None = None,
) -> T:
    record_dict = data.model_dump(exclude_none=True)
    cols = list(record_dict.keys())
    vals = list(record_dict.values())
    placeholders = ", ".join(f"${i + 1}" for i in range(len(cols)))
    col_str = ", ".join(cols)
    query = (
        f"INSERT INTO {table} ({col_str}) "
        f"VALUES ({placeholders}) RETURNING *"
    )

    async def _run(c: asyncpg.Connection) -> T:
        t0 = time.perf_counter()
        try:
            row = await c.fetchrow(query, *vals)
            _log(query, vals, time.perf_counter() - t0)
            return return_type(**dict(row))
        except Exception as exc:
            _log_error(query, vals, exc)
            raise

    if conn:
        return await _run(conn)
    async with pool.acquire() as c:
        return await _run(c)


async def insert_many(
    pool: asyncpg.Pool,
    table: str,
    data_list: list[BaseModel],
    return_type: type[T],
    conn: asyncpg.Connection | None = None,
) -> list[T]:
    if not data_list:
        return []

    sample = data_list[0].model_dump(exclude_none=True)
    cols = list(sample.keys())
    col_str = ", ".join(cols)
    n = len(cols)

    rows_vals: list[Any] = []
    value_groups: list[str] = []
    for idx, item in enumerate(data_list):
        d = item.model_dump(exclude_none=True)
        value_groups.append(
            "(" + ", ".join(f"${idx * n + i + 1}" for i in range(n)) + ")"
        )
        rows_vals.extend(d[c] for c in cols)

    query = (
        f"INSERT INTO {table} ({col_str}) "
        f"VALUES {', '.join(value_groups)} RETURNING *"
    )

    async def _run(c: asyncpg.Connection) -> list[T]:
        t0 = time.perf_counter()
        try:
            rows = await c.fetch(query, *rows_vals)
            _log(query, rows_vals, time.perf_counter() - t0)
            return [return_type(**dict(r)) for r in rows]
        except Exception as exc:
            _log_error(query, rows_vals, exc)
            raise

    if conn:
        return await _run(conn)
    async with pool.acquire() as c:
        return await _run(c)


# ─── read_stat ────────────────────────────────────────────────────────────────

async def read_stat(
    pool: asyncpg.Pool,
    table: str,
    return_type: type[T],
    pk_col: str | None = None,
    pk_val: Any = None,
    filters: dict[str, Any] | None = None,
    where_in: tuple[str, list[Any]] | None = None,
    order_by: str | None = None,
    many: bool = False,
    for_update: bool = False,
    conn: asyncpg.Connection | None = None,
) -> T | list[T] | None:
    """
    - pk_col / pk_val : WHERE pk_col = pk_val
    - filters         : 추가 등치 조건  {"col": val, ...}
    - where_in        : IN 조건  ("col", [val1, val2, ...])
    - many=True       : list 반환
    - for_update=True : SELECT FOR UPDATE (Race Condition 방지)
    """
    conditions: list[str] = []
    values: list[Any] = []

    if pk_col is not None:
        conditions.append(f"{pk_col} = $1")
        values.append(pk_val)

    if filters:
        for col, val in filters.items():
            conditions.append(f"{col} = ${len(values) + 1}")
            values.append(val)

    if where_in:
        col, in_vals = where_in
        placeholders = ", ".join(
            f"${len(values) + i + 1}" for i in range(len(in_vals))
        )
        conditions.append(f"{col} IN ({placeholders})")
        values.extend(in_vals)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    order = f"ORDER BY {order_by}" if order_by else ""
    lock = "FOR UPDATE" if for_update else ""
    query = " ".join(
        part for part in
        [f"SELECT * FROM {table}", where, order, lock]
        if part
    )

    async def _fetch(c: asyncpg.Connection) -> T | list[T] | None:
        t0 = time.perf_counter()
        try:
            if many:
                rows = await c.fetch(query, *values)
                _log(query, values, time.perf_counter() - t0)
                return [return_type(**dict(r)) for r in rows]
            row = await c.fetchrow(query, *values)
            _log(query, values, time.perf_counter() - t0)
            return return_type(**dict(row)) if row else None
        except Exception as exc:
            _log_error(query, values, exc)
            raise

    if conn:
        return await _fetch(conn)
    async with pool.acquire() as c:
        return await _fetch(c)


# ─── update_stat ──────────────────────────────────────────────────────────────

async def update_stat(
    pool: asyncpg.Pool,
    table: str,
    pk_col: str,
    pk_val: Any,
    data: BaseModel,
    return_type: type[T],
    conn: asyncpg.Connection | None = None,
) -> T | None:
    update_dict = {
        k: v for k, v in
        data.model_dump(exclude_unset=True, exclude_none=False).items()
        if k in data.model_fields_set
    }

    if not update_dict:
        return await read_stat(
            pool, table, return_type,
            pk_col=pk_col, pk_val=pk_val, conn=conn,
        )

    set_clause = ", ".join(
        f"{col} = ${i + 1}" for i, col in enumerate(update_dict.keys())
    )
    pk_placeholder = f"${len(update_dict) + 1}"
    query = (
        f"UPDATE {table} SET {set_clause} "
        f"WHERE {pk_col} = {pk_placeholder} RETURNING *"
    )
    vals = [*update_dict.values(), pk_val]

    async def _run(c: asyncpg.Connection) -> T | None:
        t0 = time.perf_counter()
        try:
            row = await c.fetchrow(query, *vals)
            _log(query, vals, time.perf_counter() - t0)
            return return_type(**dict(row)) if row else None
        except Exception as exc:
            _log_error(query, vals, exc)
            raise

    if conn:
        return await _run(conn)
    async with pool.acquire() as c:
        return await _run(c)


# ─── transaction ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def transaction(
    pool: asyncpg.Pool,
) -> AsyncGenerator[asyncpg.Connection, None]:
    """
    async with transaction(pool) as conn:
        await update_stat(pool, ..., conn=conn)
        await insert_row(pool, ..., conn=conn)
    예외 발생 시 자동 ROLLBACK.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            logger.debug("[DB] transaction BEGIN")
            try:
                yield conn
                logger.debug("[DB] transaction COMMIT")
            except Exception as exc:
                logger.error("[DB] transaction ROLLBACK | reason=%s", exc)
                raise
