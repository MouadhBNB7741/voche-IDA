import asyncpg
from app.core.config import settings


class PostgresDB:
    __pool: asyncpg.Pool | None = None

    @classmethod
    def get_pool(cls) -> asyncpg.Pool:
        if cls.__pool is None:
            raise RuntimeError("There is no Database Connection found")
        return cls.__pool

    @classmethod
    async def connect(cls):
        cls.__pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=5,
            max_size=20,
            command_timeout=60,
        )

    @classmethod
    async def disconnect(cls):
        if cls.__pool:
            try:
                await cls.__pool.close()
            except Exception:
                pass
            finally:
                cls.__pool = None

    @classmethod
    async def execute(cls, query: str, *args):
        """Use for INSERT, UPDATE, DELETE"""
        pool = cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)

    @classmethod
    async def fetch_one(cls, query: str, *args):
        """Use for SELECTing a single row"""
        pool = cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    @classmethod
    async def fetch_all(cls, query: str, *args):
        """Use for SELECTing multiple rows"""
        pool = cls.get_pool()
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)
