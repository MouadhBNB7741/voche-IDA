import pytest
import asyncio
import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport
import asyncpg

# --- 1. ENV LOADING ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env.test"
load_dotenv(ENV_PATH, override=True)

# Tests use their own Redis database (db 1), so flushdb() between tests
# never wipes the data of the app running locally (db 0).
_redis_url = urlparse(os.environ.get("REDIS_URL", ""))
if _redis_url.scheme and _redis_url.path in ("", "/", "/0"):
    os.environ["REDIS_URL"] = urlunparse(_redis_url._replace(path="/1"))

from app.main import app
from app.db.postgres import PostgresDB
from app.db.redis import connect_redis, disconnect_redis, get_redis_client
from app.core.config import settings

DB_DIR = BASE_DIR / "app" / "db"
MIGRATION_FILES = sorted((DB_DIR / "migrations").glob("*.sql"))

# --- 2. EVENT LOOP ---
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

# --- 3. DB SETUP FIXTURE ---
_schema_built = False


async def _build_schema(conn):
    """Recreate every table once per test run, the same way app/db/init_db.py does:
    schema.sql, then indexes.sql, then every migration in order."""
    async with conn.transaction():
        await conn.execute("""
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END $$;
        """)
        await conn.execute((DB_DIR / "schema.sql").read_text(encoding="utf-8"))
        await conn.execute((DB_DIR / "indexes.sql").read_text(encoding="utf-8"))
        for migration in MIGRATION_FILES:
            await conn.execute(migration.read_text(encoding="utf-8"))


async def _empty_all_tables(conn):
    """Delete every row so each test starts from an empty database.
    Much faster than rebuilding the tables for every test."""
    tables = [r["name"] for r in await conn.fetch(
        "SELECT quote_ident(tablename) AS name FROM pg_tables WHERE schemaname = 'public'"
    )]
    try:
        async with conn.transaction():
            # Skip foreign key checks while deleting, so the order of the tables does not matter
            await conn.execute("SET LOCAL session_replication_role = replica")
            for table in tables:
                await conn.execute(f"DELETE FROM {table}")
    except asyncpg.InsufficientPrivilegeError:
        # The database user is not allowed to skip foreign key checks: use the slower TRUNCATE
        await conn.execute(f"TRUNCATE {', '.join(tables)} CASCADE")

    for seq in await conn.fetch(
        "SELECT quote_ident(sequencename) AS name FROM pg_sequences WHERE schemaname = 'public'"
    ):
        await conn.execute(f"ALTER SEQUENCE {seq['name']} RESTART")

    # Migrations run on every app startup, so they are idempotent. Running them again
    # puts back any reference rows a migration inserts.
    for migration in MIGRATION_FILES:
        await conn.execute(migration.read_text(encoding="utf-8"))


@pytest.fixture(scope="function")
async def setup_test_db():
    global _schema_built

    # Verify we are indeed on the test database
    if "voche_test" not in settings.database_url and "voce_test" not in settings.database_url:
        raise RuntimeError(f"⚠️ SAFETY TRIGGER: settings.database_url is pointing to: {settings.database_url}")

    # Reset Singleton
    PostgresDB._PostgresDB__pool = None

    # Connect
    await PostgresDB.connect()

    try:
        pool = PostgresDB.get_pool()
        async with pool.acquire() as conn:
            if not _schema_built:
                await _build_schema(conn)
                _schema_built = True
            else:
                await _empty_all_tables(conn)
    except Exception as e:
        print(f"❌ DB Setup Error: {e}")
        raise e

    # Redis
    try:
        await connect_redis()
        redis = await get_redis_client()
        if redis:
            await redis.flushdb()
    except Exception:
        pass

    yield

    # Teardown
    await PostgresDB.disconnect()
    await disconnect_redis()
    PostgresDB._PostgresDB__pool = None

@pytest.fixture(scope="function")
async def client(setup_test_db) -> AsyncClient:
    app.router.lifespan_context = lambda app: (yield)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def unique_email():
    import secrets
    return f"test_{secrets.token_hex(4)}@example.com"

@pytest.fixture
def auth_headers():
    return lambda token: {"Authorization": f"Bearer {token}"}
