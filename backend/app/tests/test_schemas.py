from datetime import datetime
from typing import Optional, List
from httpx import AsyncClient
import pytest
from app.schemas.auth import RegisterRequest, LoginRequest
from app.schemas.user import UserDetailsResponse, UserProfileUpdate
from pydantic import ValidationError

def test_register_schema_validation():
    # Valid
    valid_data = {
        "email": "test@example.com",
        "password": "password123",
        "first_name": "John",
        "last_name": "Doe",
        "user_type": "patient"
    }
    schema = RegisterRequest(**valid_data)
    assert schema.email == "test@example.com"
    
    # Invalid email
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="not-an-email",
            password="password123",
            first_name="John",
            last_name="Doe",
            user_type="patient"
        )

    # Short password
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="test@example.com",
            password="short",
            first_name="John",
            last_name="Doe",
            user_type="patient"
        )
        
    # Invalid user_type
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="test@example.com",
            password="password123",
            first_name="John",
            last_name="Doe",
            user_type="alien"
        )


def test_user_details_response_defaults():
    # Minimal data
    data = {
        "id": "123",
        "email": "test@example.com",
        "user_type": "patient",
        "created_at": datetime.now()
    }
    schema = UserDetailsResponse(**data)
    assert schema.language_preference == "en"
    assert schema.profile_visibility == "public"
    assert schema.notification_enabled is True
    assert schema.email_alerts is True
    assert schema.interests == []
