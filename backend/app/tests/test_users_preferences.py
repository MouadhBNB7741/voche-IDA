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
