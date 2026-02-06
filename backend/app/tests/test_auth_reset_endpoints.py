import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, UTC
from app.main import app
from app.api.dependencies.connections import get_connection

client = TestClient(app)

# Mock connection class to simulate asyncpg behavior


class MockConn:
    def __init__(self):
        self.fetchrow = AsyncMock()
        self.execute = AsyncMock()


@pytest.fixture
def mock_conn():
    conn = MockConn()
    # Override the dependency to use our mock
    app.dependency_overrides[get_connection] = lambda: conn
    yield conn
    app.dependency_overrides.clear()

# --- Tests ---
@patch("app.services.email.EmailService.send_password_reset", new_callable=AsyncMock)
def test_request_reset_user_exists(mock_email, mock_conn):
    # Setup: User exists in DB
    mock_conn.fetchrow.return_value = {"id": 1, "email": "dev@example.com"}

    response = client.post("/api/v1/auth/request-reset",
                           json={"email": "dev@example.com"})

    assert response.status_code == 200
    assert "reset link has been sent" in response.json()["message"]
    # Verify DB interactions
    assert mock_conn.execute.called  # Ensure it deleted/inserted tokens
    mock_email.assert_called_once()  # Ensure email was "sent"


def test_request_reset_user_not_found(mock_conn):
    # Setup: User does NOT exist
    mock_conn.fetchrow.return_value = None

    response = client.post("/api/v1/auth/request-reset",
                           json={"email": "ghost@example.com"})

    # Security check: even if user doesn't exist, return 200
    assert response.status_code == 200
    assert "reset link has been sent" in response.json()["message"]
    assert not mock_conn.execute.called  # Should not try to insert tokens


def test_verify_token_expired(mock_conn):
    # Setup: Token is expired
    mock_conn.fetchrow.return_value = {
        "id": 10,
        "user_id": 1,
        "expires_at": datetime.now(UTC) - timedelta(hours=1),  # Past time
        "used": False
    }

    response = client.get("/api/v1/auth/verify-reset-token/some_token")

    assert response.status_code == 400
    assert response.json()["detail"] == "Reset token expired"


def test_verify_token_success(mock_conn):
    # Setup: Valid token
    mock_conn.fetchrow.return_value = {
        "id": 10,
        "user_id": 1,
        "expires_at": datetime.now(UTC) + timedelta(hours=1),  # Future time
        "used": False
    }

    response = client.get("/api/v1/auth/verify-reset-token/valid_token")
    assert response.status_code == 200
    assert response.json() == {"valid": True}

@patch("app.api.v1.auth.hash_password") # Mock hashing to speed up/control test
def test_reset_password_final_step(mock_hash, mock_conn):
    mock_hash.return_value = "new_hashed_password_123"
    
    # 1. Mock the token lookup
    mock_conn.fetchrow.return_value = {
        "id": 10,
        "user_id": 1,
        "expires_at": datetime.now(UTC) + timedelta(hours=1),
        "used": False
    }
    
    payload = {"token": "valid_token", "new_password": "securePassword123"}
    response = client.post("/api/v1/auth/reset-password", json=payload)
    
    assert response.status_code == 200
    assert response.json()["message"] == "Password reset successful"
    
    # Verify the UPDATE query was called for the password
    # In a real test, you'd check the exact SQL string if necessary
    assert mock_conn.execute.call_count >= 2
    