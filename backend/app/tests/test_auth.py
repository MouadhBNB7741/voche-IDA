import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.api.dependencies.connections import get_connection
from app.api.dependencies.jwt_auth import get_current_user

client = TestClient(app)

# Mock user data for the dependency
MOCK_USER = {
    "id": 1,
    "email": "dev@example.com",
    "role": "developer",
    "api_key": "dev_123456"
}


def override_get_current_user():
    return MOCK_USER

# Mock database connection
@pytest.fixture
def mock_conn():
    return AsyncMock()


# 2. Mock functions for Dependency Injection
def override_get_connection(mock_conn):
    async def _override():
        yield mock_conn
    return _override


@pytest.fixture(autouse=True)
def override_db(mock_conn):
    app.dependency_overrides[get_connection] = override_get_connection(mock_conn)
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.clear()


## --- REGISTER TESTS ---
def test_register_developer_success(mock_conn):
    # Setup: simulate email doesn't exist (fetchval returns None)
    mock_conn.fetchval.return_value = None
    
    payload = {
        "email": "dev@example.com",
        "password": "securePassword123",
        "role": "developer"
    }
    
    response = client.post("/api/v1/auth/register", json=payload)
    
    assert response.status_code == 200
    assert response.json()["status"] == "created"
    assert response.json()["api_key"].startswith("dev_")
    # Verify DB call
    mock_conn.execute.assert_called_once()

def test_register_invalid_role():
    payload = {
        "email": "admin@example.com",
        "password": "password",
        "role": "admin" # Admin is not allowed in your code
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid role"

def test_register_duplicate_email(mock_conn):
    # Setup: simulate email already exists (fetchval returns 1)
    mock_conn.fetchval.return_value = 1
    
    payload = {"email": "exists@test.com", "password": "pass", "role": "subscriber"}
    response = client.post("/api/v1/auth/register", json=payload)
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]

## --- LOGIN TESTS ---
def test_login_success(mock_conn):
    # Setup: Mock the DB returning a user record
    # Note: password_hash here must be a valid hash of 'password123' 
    # if your verify_password function actually runs.
    from app.core.security import hash_password
    fake_hash = hash_password("password123")
    
    mock_conn.fetchrow.return_value = {
        "id": 1,
        "password_hash": fake_hash,
        "role": "developer"
    }

    payload = {"email": "test@test.com", "password": "password123"}
    response = client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_wrong_password(mock_conn):
    from app.core.security import hash_password
    fake_hash = hash_password("password123")
    
    mock_conn.fetchrow.return_value = {
        "id": 1,
        "password_hash": fake_hash,
        "role": "subscriber"
    }

    payload = {"email": "test@test.com", "password": "wrongPassword"}
    response = client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 401
    
# --- PROFILE TESTS ---
def test_get_me_success():
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "dev@example.com"
    assert data["role"] == "developer"
    assert "api_key" in data

## --- PASSWORD UPDATE TESTS ---
def test_update_password_logic():
    # Since your endpoint code is currently comments, 
    # this test helps you verify the flow as you implement it.
    
    payload = {
        "current_password": "old_password",
        "new_password": "new_secure_password"
    }
    
    response = client.put("/api/v1/auth/update-password", json=payload)
    
    assert response.status_code == 200
    assert response.json()["message"] == "Success"
