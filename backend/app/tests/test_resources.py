import pytest
import uuid
import json
from httpx import AsyncClient
from app.db.postgres import PostgresDB

async def create_user(client: AsyncClient, email: str = "resource_test@example.com") -> tuple[str, str]:
    """Register and login a user, return (user_id, JWT token)."""
    pwd = "StrongPassword123!"
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": pwd,
        "first_name": "Test",
        "last_name": "User",
        "user_type": "patient",
    })
    login_res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": pwd,
    })
    token = login_res.json()["access_token"]
    
    # get user_id by token
    me_res = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    user_id = me_res.json()["id"]
    return user_id, token


async def seed_resources() -> list[str]:
    """Insert test resources, return their IDs."""
    pool = PostgresDB.get_pool()
    ids = [str(uuid.uuid4()) for _ in range(5)]
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO resources (
                resource_id, title, type, category, description,
                url, language, rating, downloads, requires_auth, featured
            ) VALUES 
            ($1, 'Public Video', 'video', 'cardiology', 'A public video to watch', 'http://test.com/1', 'en', 4.5, 100, FALSE, TRUE),
            ($2, 'Auth Document', 'document', 'cardiology', 'A private doc', 'http://test.com/2', 'en', 3.0, 50, TRUE, FALSE),
            ($3, 'Spanish Toolkit', 'toolkit', 'neurology', 'A toolkit in Spanish', 'http://test.com/3', 'es', 5.0, 200, FALSE, TRUE),
            ($4, 'Course 1', 'course', 'oncology', 'A course on oncology', 'http://test.com/4', 'en', 0.0, 0, TRUE, FALSE),
            ($5, 'Course 2', 'course', 'oncology', 'Another course on oncology', 'http://test.com/5', 'en', 2.5, 10, FALSE, FALSE)
        """, *ids)
    return ids


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_resources(client: AsyncClient, setup_test_db):
    """Test listing resources with pagination and features."""
    await seed_resources()

    res = await client.get("/api/v1/resources/")
    assert res.status_code == 200
    data = res.json()
    assert len(data["data"]) >= 5
    assert data["meta"]["total"] >= 5


@pytest.mark.asyncio
async def test_list_resources_filters(client: AsyncClient, setup_test_db):
    """Test filtering and sorting listing resources."""
    await seed_resources()

    # Filter by category
    res = await client.get("/api/v1/resources/?category=cardiology")
    assert res.status_code == 200
    data = res.json()
    assert len(data["data"]) == 2

    # Filter by type and language
    res = await client.get("/api/v1/resources/?type=toolkit&language=es")
    assert res.status_code == 200
    data = res.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["type"] == "toolkit"

    # Sort by popular
    res = await client.get("/api/v1/resources/?sort=most_popular")
    assert res.status_code == 200
    data = res.json()
    assert data["data"][0]["downloads"] >= 200 # the toolkit has 200
    

@pytest.mark.asyncio
async def test_resource_details_valid(client: AsyncClient, setup_test_db):
    """Test resource details valid ID."""
    ids = await seed_resources()
    target_id = ids[0]

    res = await client.get(f"/api/v1/resources/{target_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["resource_id"] == target_id
    assert "ratings_count" in data
    assert "reviews" in data
    assert "related_resources" in data


@pytest.mark.asyncio
async def test_resource_details_invalid(client: AsyncClient, setup_test_db):
    """Test resource details invalid ID."""
    res = await client.get(f"/api/v1/resources/{uuid.uuid4()}")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_download_public(client: AsyncClient, setup_test_db):
    """Test downloading a public resource."""
    ids = await seed_resources()
    public_id = ids[0] # Public Video

    # Before download, check downloads
    res_before = await client.get(f"/api/v1/resources/{public_id}")
    downloads_before = res_before.json()["downloads"]

    res = await client.get(f"/api/v1/resources/{public_id}/download")
    assert res.status_code == 200
    data = res.json()
    assert "download_url" in data
    assert data["success"] is True

    # Check downloads incremented
    res_after = await client.get(f"/api/v1/resources/{public_id}")
    downloads_after = res_after.json()["downloads"]
    assert downloads_after == downloads_before + 1


@pytest.mark.asyncio
async def test_download_auth_required_fails(client: AsyncClient, setup_test_db):
    """Test downloading a private resource without auth fails."""
    ids = await seed_resources()
    private_id = ids[1]

    res = await client.get(f"/api/v1/resources/{private_id}/download")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_download_auth_required_success(client: AsyncClient, setup_test_db, auth_headers):
    """Test downloading a private resource with auth succeeds."""
    ids = await seed_resources()
    private_id = ids[1]
    _, token = await create_user(client)

    res = await client.get(f"/api/v1/resources/{private_id}/download", headers=auth_headers(token))
    assert res.status_code == 200
    assert res.json()["success"] is True


@pytest.mark.asyncio
async def test_create_and_update_rating(client: AsyncClient, setup_test_db, auth_headers):
    """Test creating and then updating a rating, verifying uniqueness and avg calculation."""
    ids = await seed_resources()
    resource_id = ids[3] # Course 1, Rating: 0.0
    _, token = await create_user(client, "rater@example.com")
    headers = auth_headers(token)

    # 1. Create rating
    res = await client.post(
        f"/api/v1/resources/{resource_id}/rating",
        json={"rating": 4, "review": "Good course"},
        headers=headers
    )
    assert res.status_code == 201
    assert res.json()["data"]["rating"] == 4
    assert res.json()["data"]["new_average"] == 4.0

    # 2. Add another rater to test average recalculation
    _, token2 = await create_user(client, "rater2@example.com")
    headers2 = auth_headers(token2)
    res2 = await client.post(
        f"/api/v1/resources/{resource_id}/rating",
        json={"rating": 2, "review": "Average"},
        headers=headers2
    )
    assert res2.status_code == 201
    assert res2.json()["data"]["new_average"] == 3.0 # (4 + 2) / 2 = 3.0

    # 3. Update first rating (uniqueness enforced by UPSERT)
    res_update = await client.post(
        f"/api/v1/resources/{resource_id}/rating",
        json={"rating": 5, "review": "Actually great course"},
        headers=headers
    )
    assert res_update.status_code == 201
    assert res_update.json()["data"]["rating"] == 5
    assert res_update.json()["data"]["new_average"] == 3.5 # (5 + 2) / 2 = 3.5

    # Fetch details to ensure reviews are shown
    details = await client.get(f"/api/v1/resources/{resource_id}")
    assert details.json()["ratings_count"] == 2
    assert details.json()["rating"] == 3.5


@pytest.mark.asyncio
async def test_update_progress(client: AsyncClient, setup_test_db, auth_headers):
    """Test updating progress for a resource."""
    ids = await seed_resources()
    resource_id = ids[0]
    user_id, token = await create_user(client, "progress@example.com")
    headers = auth_headers(token)

    # Initial progress
    res = await client.patch(
        f"/api/v1/resources/{resource_id}/progress",
        json={"progress": 45, "last_position": "10:23"},
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["progress"] == 45
    assert data["last_position"] == "10:23"

    # Update progress
    res2 = await client.patch(
        f"/api/v1/resources/{resource_id}/progress",
        json={"progress": 100, "last_position": "00:00"},
        headers=headers
    )
    assert res2.status_code == 200
    assert res2.json()["progress"] == 100

    # Verify table row instead of users JSONB
    pool = PostgresDB.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT progress FROM resource_progress WHERE user_id = $1 AND resource_id = $2", 
            user_id, resource_id
        )
        assert row is not None
        assert row["progress"] == 100
