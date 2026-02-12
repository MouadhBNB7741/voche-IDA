import pytest
from httpx import AsyncClient
import secrets

@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient, auth_headers):
    """
    Validates the profile update flow:
    1. Register and Login.
    2. Update bio, location, and display_name.
    3. Verify profile_completed logic triggers when 'country' is added.
    """
    # Setup
    random_email = f"profile_{secrets.token_hex(4)}@example.com"
    pwd = "StrongProfilePass123!"  # Using strong password to avoid 422
    
    await client.post("/api/v1/auth/register", json={
        "email": random_email,
        "password": pwd,
        "first_name": "Profile",
        "last_name": "Test",
        "user_type": "patient"
    })
    
    login_res = await client.post("/api/v1/auth/login", json={"email": random_email, "password": pwd})
    token = login_res.json()["access_token"]
    
    # --- 1. Test Partial Update ---
    update_payload = {
        "bio": "I am a new test bio.",
        "location": "Test City",
        "display_name": "Updated Profile"
    }
    
    res = await client.patch("/api/v1/users/me", json=update_payload, headers=auth_headers(token))
    assert res.status_code == 200
    data = res.json()
    
    assert data["bio"] == "I am a new test bio."
    assert data["location"] == "Test City"
    assert data["display_name"] == "Updated Profile"
    
    # profile_completed should be False because 'country' is still missing
    assert data["profile_completed"] is False
    
    # --- 2. Test Profile Completion ---
    # According to our model logic: first_name, last_name, and country are required for True
    res_comp = await client.patch("/api/v1/users/me", json={"country": "Wonderland"}, headers=auth_headers(token))
    assert res_comp.status_code == 200
    
    data_comp = res_comp.json()
    assert data_comp["country"] == "Wonderland"
    assert data_comp["profile_completed"] is True

@pytest.mark.asyncio
async def test_get_profile_not_found(client: AsyncClient, auth_headers):
    """
    Edge case: Verify 401 when accessing /me without valid token.
    """
    response = await client.get("/api/v1/users/me", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401