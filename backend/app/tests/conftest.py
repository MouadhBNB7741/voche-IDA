import pytest
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport

# --- 1. ENV LOADING ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env.test"
load_dotenv(ENV_PATH, override=True)

from app.main import app
from app.db.postgres import PostgresDB
from app.db.redis import connect_redis, disconnect_redis, get_redis_client
from app.core.config import settings

# --- 2. EVENT LOOP ---
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

# --- 3. DB SETUP FIXTURE ---
@pytest.fixture(scope="function")
async def setup_test_db():
    # Verify we are indeed on the test database
    if "voce_test" not in settings.database_url:
        raise RuntimeError(f"⚠️ SAFETY TRIGGER: settings.database_url is pointing to: {settings.database_url}")

    # Reset Singleton
    PostgresDB._PostgresDB__pool = None 
    
    # Connect
    await PostgresDB.connect()
    
    try:
        pool = PostgresDB.get_pool()
        async with pool.acquire() as conn:
            # Apply Schema
            schema_path = BASE_DIR / "app" / "db" / "schema.sql"
            if schema_path.exists():
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
                    await conn.execute(schema_path.read_text(encoding="utf-8"))
            
            # Truncate
            await conn.execute("TRUNCATE users, organizations, clinical_trials RESTART IDENTITY CASCADE;")
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