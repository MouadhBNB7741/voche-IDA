from typing import AsyncGenerator, Any
from app.db.postgres import PostgresDB


# use it when u need to use single queries
async def get_connection() -> AsyncGenerator[Any, None]:
    pool = PostgresDB.get_pool()
    async with pool.acquire() as conn:
        yield conn


# use it when u need to use multiple concurrent queries
async def get_transaction() -> AsyncGenerator[Any, None]:
    pool = PostgresDB.get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            yield conn
