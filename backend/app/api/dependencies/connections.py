from typing import AsyncGenerator, Any
from app.db.postgres import PostgresDB

async def get_connection() -> AsyncGenerator[Any, None]:
    # We must not use context manager here if it closes the pool?
    # No, pool.acquire releases conn to pool, doesn't close pool.
    pool = PostgresDB.get_pool()
    async with pool.acquire() as conn:
        try:
            yield conn
        finally:
            pass

async def get_transaction() -> AsyncGenerator[Any, None]:
    pool = PostgresDB.get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            try:
                yield conn
            finally:
                pass
