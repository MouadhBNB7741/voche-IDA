import pytest
from httpx import AsyncClient
from app.db.postgres import PostgresDB
from app.db.redis import get_redis_client

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """
    Test the health check endpoint.
    'client' fixture already triggers DB setup, so this works.
    """
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "online"
    assert data["database"] == "connected"
    assert data["redis"] == "connected"

@pytest.mark.asyncio
async def test_database_isolation(setup_test_db):  # <--- ADDED FIXTURE HERE
    """
    CRITICAL: Verify we are connected to the 'voce_test' database.
    """
    pool = PostgresDB.get_pool()
    async with pool.acquire() as conn:
        db_name = await conn.fetchval("SELECT current_database();")
        assert db_name == "voce_test"

@pytest.mark.asyncio
async def test_redis_operations(setup_test_db):    # <--- GOOD PRACTICE TO ADD HERE TOO
    """
    Verify Redis write/read operations work.
    """
    redis = await get_redis_client()
    assert redis is not None
    
    await redis.set("test_setup_key", "working")
    value = await redis.get("test_setup_key")
    assert value == "working"
    await redis.delete("test_setup_key")