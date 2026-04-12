import pytest
from httpx import AsyncClient
import secrets

# ------------------------------------------------------------------------------
# NOTE: Ensure 'auth_headers' fixture is added to conftest.py!
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    random_email = f"test_{secrets.token_hex(4)}@example.com"
    payload = {
        "email": random_email,
        "password": "StrongPassword123!", # Strong password
        "first_name": "Test",
        "last_name": "User",
        "user_type": "patient"
    }
    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user_type"] == "patient"

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    # Setup
    random_email = f"login_{secrets.token_hex(4)}@example.com"
    pwd = "StrongPassword123!" # Strong password
    
    reg_payload = {
        "email": random_email,
        "password": pwd,
        "first_name": "Login",
        "last_name": "Test",
        "user_type": "hcp"
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    # Test
    login_payload = {
        "email": random_email,
        "password": pwd
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user_type"] == "hcp"

@pytest.mark.asyncio
async def test_me_endpoint(client: AsyncClient, auth_headers):
    # Setup
    random_email = f"me_{secrets.token_hex(4)}@example.com"
    pwd = "StrongPassword123!"
    
    await client.post("/api/v1/auth/register", json={
        "email": random_email,
        "password": pwd,
        "first_name": "Me",
        "last_name": "Test",
        "user_type": "org_member"
    })
    
    login_res = await client.post("/api/v1/auth/login", json={"email": random_email, "password": pwd})
    token = login_res.json()["access_token"]
    
    # Test
    # This uses the fixture you must add to conftest.py
    response = await client.get("/api/v1/users/me", headers=auth_headers(token))
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == random_email
    assert data["user_type"] == "org_member"
    # Note: verify if your API returns 'display_name'. 
    # If not, remove this assertion or fix the API model.
    # assert data["display_name"] == "Me Test" 

@pytest.mark.asyncio
async def test_password_reset_flow(client: AsyncClient):
    # Setup
    random_email = f"reset_{secrets.token_hex(4)}@example.com"
    pwd = "StrongPassword123!"
    
    await client.post("/api/v1/auth/register", json={
        "email": random_email,
        "password": pwd,
        "first_name": "Reset",
        "last_name": "Test",
        "user_type": "patient"
    })
    
    # 1. Request Reset
    # Ensure this URL matches your actual router (e.g., /request-reset vs /request-password-reset)
    res_req = await client.post("/api/v1/auth/request-reset", json={"email": random_email})
    assert res_req.status_code == 200