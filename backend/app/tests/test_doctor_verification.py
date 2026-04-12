import pytest
from httpx import AsyncClient
from app.db.postgres import PostgresDB

@pytest.mark.asyncio
async def test_doctor_verification_flow(client: AsyncClient, unique_email, auth_headers):
    # 1. Register User
    resp = await client.post("/api/v1/auth/register", json={
        "email": unique_email, "password": "password123", 
        "first_name": "Dr", "last_name": "Test", "user_type": "patient"
    })
    assert resp.status_code == 201
    
    # Login
    resp = await client.post("/api/v1/auth/login", json={"email": unique_email, "password": "password123"})
    token = resp.json()["access_token"]
    headers = auth_headers(token)
    
    # 2. Submit Verification
    payload = {
        "license_number": "MD12345",
        "institution": "General Hospital",
        "country": "US",
        "specialization": "Cardiology"
    }
    resp = await client.post("/api/v1/doctors/verification", json=payload, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"
    ver_id = resp.json()["verification_id"]
    
    # 3. Check Status
    resp = await client.get("/api/v1/doctors/verification", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"
    
    # 4. Login as Admin (create one)
    admin_email = "admin_" + unique_email
    await client.post("/api/v1/auth/register", json={
        "email": admin_email, "password": "password123", 
        "first_name": "Admin", "last_name": "User", "user_type": "admin"
    })
    
    # Promote to admin directly via DB
    pool = PostgresDB.get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET user_type = 'admin' WHERE email = $1", admin_email)
    
    # Login Admin
    resp = await client.post("/api/v1/auth/login", json={"email": admin_email, "password": "password123"})
    admin_token = resp.json()["access_token"]
    admin_headers = auth_headers(admin_token)
    
    # List Pending
    resp = await client.get("/api/v1/doctors/admin/verifications", headers=admin_headers)
    assert resp.status_code == 200
    pending_ids = [v["verification_id"] for v in resp.json()]
    assert ver_id in pending_ids
    
    # Approve
    resp = await client.patch(f"/api/v1/doctors/admin/verifications/{ver_id}", 
                              json={"status": "approved"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    
    # 5. Check User Updated (User needs to re-fetch profile or token logic)
    # The token claim users query DB so existing token might still work for routes checks if they query DB.
    # But /users/me queries DB directly.
    resp = await client.get("/api/v1/users/me", headers=headers)
    data = resp.json()
    assert data["user_type"] == "hcp"
    # Verify verification JSONB status
    assert data["user_type"] == "hcp"
    assert data.get("verification") is not None
    assert data.get("verification").get("status") == "approved"
