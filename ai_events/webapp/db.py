from __future__ import annotations

import sys
from typing import Any

import asyncpg

from ai_events.webapp.settings import database_ssl, database_url

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool | None:
    return _pool


async def init_pool() -> asyncpg.Pool | None:
    global _pool
    dsn = database_url()
    if not dsn:
        _pool = None
        return None
    ssl = database_ssl()
    try:
        _pool = await asyncpg.create_pool(dsn, ssl=ssl, min_size=1, max_size=10)
    except Exception as e:
        print(f"Postgres pool failed (API still up, empty results): {e}", file=sys.stderr)
        _pool = None
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def fetch_all(sql: str, *args: Any) -> list[asyncpg.Record]:
    pool = _pool
    if pool is None:
        return []
    async with pool.acquire() as conn:
        return await conn.fetch(sql, *args)


async def fetch_val(sql: str, *args: Any) -> Any:
    pool = _pool
    if pool is None:
        return None
    async with pool.acquire() as conn:
        return await conn.fetchval(sql, *args)
