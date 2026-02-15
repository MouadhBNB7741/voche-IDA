import pytest
from httpx import AsyncClient
import secrets

@pytest.mark.asyncio
async def test_update_notification_preferences(client: AsyncClient, auth_headers):
    """
    Validates notification preferences update:
    1. Register/Login.
    2. Patch notifications.
    3. Check persistence and deep merge.
    4. Validate enum constraints.
    """
    email = f"notif_{secrets.token_hex(4)}@example.com"
    pwd = "StrongPass123!"
    
    # 1. Register
    reg_res = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": pwd,
        "first_name": "Test",
        "last_name": "User",
        "user_type": "patient"
    })
    
    # login if register doesn't return token? 
    # Usually register returns user, login returns token.
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    token = login_res.json()["access_token"]
    
    # 2. Update Prefs
    payload = {
        "emailAlerts": False,
        "frequency": "daily_digest"
    }
    
    # Need auth headers function
    headers = {"Authorization": f"Bearer {token}"}
    
    res = await client.patch("/api/v1/users/me/notifications", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()["data"]["notification_preferences"]
    
    assert data["emailAlerts"] is False
    assert data["frequency"] == "daily_digest"
    # defaults check
    assert data.get("pushNotifications") is True
    
    # 3. Invalid Frequency
    res_bad = await client.patch("/api/v1/users/me/notifications", json={"frequency": "invalid_enum"}, headers=headers)
    assert res_bad.status_code == 422

@pytest.mark.asyncio
async def test_submit_verification(client: AsyncClient, auth_headers):
    """
    Validates HCP verification submission:
    1. HCP can submit.
    2. Success status pending.
    3. Duplicate submission rejected.
    """
    email = f"hcp_{secrets.token_hex(4)}@example.com"
    pwd = "StrongPass123!"
    
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": pwd,
        "first_name": "Dr",
        "last_name": "Who",
        "user_type": "hcp"
    })
    
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Submit
    files = {"file": ("license.pdf", b"%PDF-1.4 test content", "application/pdf")}
    data = {
        "licenseNumber": "MED12345", 
        "issuingRegion": "NY, USA", 
        "expirationDate": "2030-12-31"
    }
    
    res = await client.post("/api/v1/users/me/verification", data=data, files=files, headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "pending_verification"
    
    # Duplicate
    files2 = {"file": ("license.pdf", b"%PDF-1.4 test content", "application/pdf")}
    res_dup = await client.post("/api/v1/users/me/verification", data=data, files=files2, headers=headers)
    assert res_dup.status_code == 400

@pytest.mark.asyncio
async def test_verification_permissions(client: AsyncClient, auth_headers):
    """
    Ensure non-HCP users cannot submit verification.
    """
    email = f"pat_{secrets.token_hex(4)}@example.com"
    pwd = "StrongPass123!"
    
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": pwd,
        "first_name": "Pat",
        "last_name": "Ient",
        "user_type": "patient"
    })
    
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    files = {"file": ("license.pdf", b"test", "application/pdf")}
    data = {"licenseNumber": "123", "issuingRegion": "XX", "expirationDate": "2030-01-01"}
    
    res = await client.post("/api/v1/users/me/verification", data=data, files=files, headers=headers)
    assert res.status_code == 403
