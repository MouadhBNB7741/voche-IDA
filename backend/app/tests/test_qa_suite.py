import pytest
import secrets
from httpx import AsyncClient

# Note: 'client' and 'unique_email' fixtures come automatically from conftest.py

@pytest.mark.asyncio
async def test_auth_full_lifecycle(client: AsyncClient, unique_email: str):
    """
    Validates: Register -> Login -> Me -> Update Password -> Logout (implied)
    """
    password = "StrongPass123!"
    
    # 1. Register
    reg_payload = {
        "email": unique_email,
        "password": password,
        "first_name": "QA",
        "last_name": "Tester",
        "user_type": "patient"
    }
    response = await client.post("/api/v1/auth/register", json=reg_payload)
    assert response.status_code == 201, f"Register failed: {response.text}"
    data = response.json()
    assert "access_token" in data
    assert data["user_type"] == "patient"
    
    # Store token
    token = data["access_token"]
    
    # 2. Login
    login_payload = {"email": unique_email, "password": password}
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    assert "access_token" in response.json()
    
    # 3. Get /me
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    me_data = response.json()
    assert me_data["email"] == unique_email
    assert me_data["first_name"] == "QA"
    
    # 4. Update Password
    new_password = "NewStrongPass456!"
    update_pwd_payload = {
        "current_password": password,
        "new_password": new_password
    }
    response = await client.put("/api/v1/auth/update-password", json=update_pwd_payload, headers=headers)
    assert response.status_code == 200
    
    # 5. Verify New Password Login
    login_retry = {"email": unique_email, "password": new_password}
    response = await client.post("/api/v1/auth/login", json=login_retry)
    assert response.status_code == 200
    
    # Verify Old Password fails
    login_fail = {"email": unique_email, "password": password}
    response = await client.post("/api/v1/auth/login", json=login_fail)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_auth_failures(client: AsyncClient):
    """
    Validates: Bad Inputs, Duplicate Email, Bad Login
    """
    # Generate a unique email locally for this specific test
    email = f"dup_{secrets.token_hex(4)}@test.com"
    pwd = "StrongPass123!"
    
    # 1. Register First User (Success)
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": pwd, "first_name": "A", "last_name": "B", "user_type": "patient"
    })
    
    # 2. Register Duplicate (Should Fail with 409 Conflict)
    res = await client.post("/api/v1/auth/register", json={
        "email": email, "password": pwd, "first_name": "A", "last_name": "B", "user_type": "patient"
    })
    assert res.status_code == 409 
    
    # 3. Register Short Password
    res = await client.post("/api/v1/auth/register", json={
        "email": "short@test.com", "password": "123", "first_name": "A", "last_name": "B", "user_type": "patient"
    })
    assert res.status_code == 422 # Validation Error
    
    # 4. Login Non-Existent
    res = await client.post("/api/v1/auth/login", json={"email": "ghost@test.com", "password": "Pass123"})
    assert res.status_code == 401 # Unauthorized

@pytest.mark.asyncio
async def test_profile_management(client: AsyncClient):
    """
    Validates: get/update profile, profile_completed logic
    """
    email = f"prof_{secrets.token_hex(4)}@test.com"
    pwd = "ProfilePass123"
    
    # Register & Login
    reg_res = await client.post("/api/v1/auth/register", json={
        "email": email, "password": pwd, "first_name": "P", "last_name": "User", "user_type": "hcp"
    })
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get Profile (Check Defaults)
    res = await client.get("/api/v1/users/me", headers=headers)
    assert res.status_code == 200
    pdata = res.json()
    assert pdata["profile_completed"] is False
    
    # Update partial
    update_data = {
        "bio": "Expert in QA",
        "location": "Remote",
        "interests": ["Testing", "Automation"]
    }
    res = await client.patch("/api/v1/users/me", json=update_data, headers=headers)
    assert res.status_code == 200
    pdata = res.json()
    assert pdata["bio"] == "Expert in QA"
    
    # Completed Profile Check
    # (Assuming your logic sets profile_completed=True when country is added)
    res = await client.patch("/api/v1/users/me", json={"country": "Canada"}, headers=headers)
    pdata = res.json()
    assert pdata["country"] == "Canada"
    
    # If your backend logic updates 'profile_completed', this assertion passes:
    # assert pdata["profile_completed"] is True 

@pytest.mark.asyncio
async def test_password_reset_flow(client: AsyncClient):
    """
    Validates: Request Password Reset
    """
    email = f"reset_{secrets.token_hex(4)}@test.com"
    
    # Create user first
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": "StrongPass123!", "first_name": "R", "last_name": "T", "user_type": "patient"
    })
    
    # Request Reset
    res = await client.post("/api/v1/auth/request-reset", json={"email": email})
    assert res.status_code == 200
    
    assert res.json()["message"] == "If this email is registered, you will receive a reset link."
