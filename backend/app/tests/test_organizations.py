import pytest
import uuid
from httpx import AsyncClient
from app.db.postgres import PostgresDB

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
async def create_user(client: AsyncClient, email: str = "org_test@example.com", is_verified: bool = True) -> dict:
    pwd = "StrongPassword123!"
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": pwd,
        "first_name": "Test",
        "last_name": "User",
        "user_type": "patient",
    })
    
    # We need to manually set is_verified in DB to bypass verification process
    pool = PostgresDB.get_pool()
    async with pool.acquire() as conn:
        user_id = await conn.fetchval("SELECT id FROM users WHERE email = $1", email)
        if is_verified:
            await conn.execute("UPDATE users SET is_verified = TRUE WHERE id = $1", user_id)
            
    login_res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": pwd,
    })
    return {
        "token": login_res.json()["access_token"],
        "id": str(user_id)
    }

async def create_admin_user(client: AsyncClient, email: str = "sysadmin@example.com") -> dict:
    pwd = "StrongPassword123!"
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": pwd,
        "first_name": "Sys",
        "last_name": "Admin",
        "user_type": "admin",
    })
    pool = PostgresDB.get_pool()
    async with pool.acquire() as conn:
        user_id = await conn.fetchval("SELECT id FROM users WHERE email = $1", email)
        await conn.execute("UPDATE users SET is_verified = TRUE WHERE id = $1", user_id)
            
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    return {"token": login_res.json()["access_token"], "id": str(user_id)}

async def create_org_admin(client: AsyncClient, org_id: str, email: str = "orgadmin@example.com") -> dict:
    pwd = "StrongPassword123!"
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": pwd,
        "first_name": "Org",
        "last_name": "Admin",
        "user_type": "org_member",
    })
    pool = PostgresDB.get_pool()
    async with pool.acquire() as conn:
        user_id = await conn.fetchval("SELECT id FROM users WHERE email = $1", email)
        await conn.execute("UPDATE users SET is_verified = TRUE WHERE id = $1", user_id)
        await conn.execute("""
            INSERT INTO organization_members (id, org_id, user_id, role, status)
            VALUES (gen_random_uuid(), $1, $2, 'admin', 'approved')
        """, org_id, user_id)
            
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    return {"token": login_res.json()["access_token"], "id": str(user_id)}


async def seed_organization(org_name="Test Org", org_type="research_institution", country="USA") -> str:
    pool = PostgresDB.get_pool()
    org_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO organizations (
                org_id, org_name, org_type, country, contact_email, member_count
            ) VALUES (
                $1, $2, $3, $4, 'contact@test.com', 0
            )
        """, org_id, org_name, org_type, country)
    return org_id

async def seed_working_group(org_id: str, name="Test Group", privacy_level="public") -> str:
    pool = PostgresDB.get_pool()
    group_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO working_groups (
                group_id, name, organization_id, type, privacy_level, member_count, is_active
            ) VALUES (
                $1, $2, $3, 'research', $4, 0, TRUE
            )
        """, group_id, name, org_id, privacy_level)
    return group_id

# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_organizations(client: AsyncClient, setup_test_db):
    org_id = await seed_organization()
    res = await client.get("/api/v1/organizations")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) >= 1
    org_ids = [org["org_id"] for org in data]
    assert org_id in org_ids

@pytest.mark.asyncio
async def test_list_organizations_filter_by_type(client: AsyncClient, setup_test_db):
    org_id1 = await seed_organization(org_name="Hosp1", org_type="hospital")
    org_id2 = await seed_organization(org_name="Hosp2", org_type="research_institution")
    
    res = await client.get("/api/v1/organizations?type=hospital")
    assert res.status_code == 200
    data = res.json()["data"]
    types = set([org["org_type"] for org in data])
    assert types == {"hospital"}

@pytest.mark.asyncio
async def test_list_organizations_filter_by_country(client: AsyncClient, setup_test_db):
    await seed_organization(org_name="Org ZA", country="South Africa")
    await seed_organization(org_name="Org US", country="USA")
    
    res = await client.get("/api/v1/organizations?country=South Africa")
    assert res.status_code == 200
    data = res.json()["data"]
    countries = set([org["country"] for org in data])
    assert countries == {"South Africa"}

@pytest.mark.asyncio
async def test_get_organization_details(client: AsyncClient, setup_test_db):
    org_id = await seed_organization(org_name="Detail Org")
    res = await client.get(f"/api/v1/organizations/{org_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["org_id"] == org_id
    assert data["org_name"] == "Detail Org"
    assert "members" in data
    assert "working_groups" in data

@pytest.mark.asyncio
async def test_join_organization_success(client: AsyncClient, setup_test_db, auth_headers):
    org_id = await seed_organization()
    user = await create_user(client, "join1@example.com")
    headers = auth_headers(user["token"])
    
    res = await client.post(f"/api/v1/organizations/{org_id}/join", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "pending_approval"

@pytest.mark.asyncio
async def test_join_organization_duplicate(client: AsyncClient, setup_test_db, auth_headers):
    org_id = await seed_organization()
    user = await create_user(client, "join2@example.com")
    headers = auth_headers(user["token"])
    
    # First join
    await client.post(f"/api/v1/organizations/{org_id}/join", headers=headers)
    
    # Second join
    res2 = await client.post(f"/api/v1/organizations/{org_id}/join", headers=headers)
    assert res2.status_code == 400
    assert "exists" in res2.json()["detail"]

@pytest.mark.asyncio
async def test_join_organization_unverified(client: AsyncClient, setup_test_db, auth_headers):
    org_id = await seed_organization()
    user = await create_user(client, "join3@example.com", is_verified=False)
    headers = auth_headers(user["token"])
    
    res = await client.post(f"/api/v1/organizations/{org_id}/join", headers=headers)
    assert res.status_code == 403
    assert "not verified" in res.json()["detail"]

@pytest.mark.asyncio
async def test_decide_organization_join(client: AsyncClient, setup_test_db, auth_headers):
    org_id = await seed_organization()
    user = await create_user(client, "join4@example.com")
    admin = await create_org_admin(client, org_id, "admin_join4@example.com")
    
    # Request to join
    await client.post(f"/api/v1/organizations/{org_id}/join", headers=auth_headers(user["token"]))
    
    # Decide join -> approve Using Admin!
    res = await client.post(
        f"/api/v1/organizations/{org_id}/members/{user['id']}/decide",
        json={"action": "accept"},
        headers=auth_headers(admin["token"])
    )
    assert res.status_code == 200
    assert res.json()["status"] == "approved"

    # Check that member_count increased
    pool = PostgresDB.get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT member_count FROM organizations WHERE org_id = $1", org_id)
        assert count == 1

@pytest.mark.asyncio
async def test_decide_organization_join_unauthorized(client: AsyncClient, setup_test_db, auth_headers):
    org_id = await seed_organization()
    user = await create_user(client, "join5@example.com")
    hacker = await create_user(client, "hacker@example.com")
    await client.post(f"/api/v1/organizations/{org_id}/join", headers=auth_headers(user["token"]))
    
    # Decide join -> approve Using unauthorized!
    res = await client.post(
        f"/api/v1/organizations/{org_id}/members/{user['id']}/decide",
        json={"action": "accept"},
        headers=auth_headers(hacker["token"])
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_list_working_groups(client: AsyncClient, setup_test_db):
    org_id = await seed_organization()
    group_id = await seed_working_group(org_id)
    
    res = await client.get(f"/api/v1/organizations/working-groups?organization_id={org_id}")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) >= 1
    assert data[0]["group_id"] == group_id

@pytest.mark.asyncio
async def test_join_working_group_public(client: AsyncClient, setup_test_db, auth_headers):
    org_id = await seed_organization()
    group_id = await seed_working_group(org_id, privacy_level="public")
    user = await create_user(client, "wg1@example.com")
    headers = auth_headers(user["token"])
    
    res = await client.post(f"/api/v1/organizations/working-groups/{group_id}/join", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "approved" # Public auto-approves

@pytest.mark.asyncio
async def test_join_working_group_private(client: AsyncClient, setup_test_db, auth_headers):
    org_id = await seed_organization()
    group_id = await seed_working_group(org_id, privacy_level="private")
    user = await create_user(client, "wg2@example.com")
    headers = auth_headers(user["token"])
    
    res = await client.post(f"/api/v1/organizations/working-groups/{group_id}/join", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "pending"

@pytest.mark.asyncio
async def test_decide_working_group_join(client: AsyncClient, setup_test_db, auth_headers):
    org_id = await seed_organization()
    group_id = await seed_working_group(org_id, privacy_level="private")
    user = await create_user(client, "wg3@example.com")
    admin = await create_admin_user(client, "sysadmin_wg@example.com")
    
    # Request to join
    await client.post(f"/api/v1/organizations/working-groups/{group_id}/join", headers=auth_headers(user["token"]))
    
    # Decide join -> approve Using Platform Admin!
    res = await client.post(
        f"/api/v1/organizations/working-groups/{group_id}/members/{user['id']}/decide",
        json={"action": "accept"},
        headers=auth_headers(admin["token"])
    )
    assert res.status_code == 200
    assert res.json()["status"] == "approved"
    
    # Check that member_count increased
    pool = PostgresDB.get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT member_count FROM working_groups WHERE group_id = $1", group_id)
        assert count == 1
        
@pytest.mark.asyncio
async def test_decide_working_group_join_unauthorized(client: AsyncClient, setup_test_db, auth_headers):
    org_id = await seed_organization()
    group_id = await seed_working_group(org_id, privacy_level="private")
    user = await create_user(client, "wg4@example.com")
    hacker = await create_user(client, "wghacker@example.com")
    await client.post(f"/api/v1/organizations/working-groups/{group_id}/join", headers=auth_headers(user["token"]))
    
    res = await client.post(
        f"/api/v1/organizations/working-groups/{group_id}/members/{user['id']}/decide",
        json={"action": "accept"},
        headers=auth_headers(hacker["token"])
    )
    assert res.status_code == 403
