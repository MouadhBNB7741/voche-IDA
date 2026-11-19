from datetime import datetime
from typing import Annotated, Optional, List, Dict, Union, Any, Literal
from pydantic import BaseModel, EmailStr, ConfigDict, Field, StringConstraints

# Notification preferences are now centralized in app/schemas/notification.py

class VerificationPayload(BaseModel):
    licenseNumber: str
    issuingRegion: str
    expirationDate: datetime

class UserProfileUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    country: Optional[str] = None
    language_preference: Optional[str] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None
    interests: Optional[Union[List[str], Dict[str, Any]]] = None
    location: Optional[str] = None
    profile_visibility: Optional[str] = None
    notification_enabled: Optional[bool] = None
    email_alerts: Optional[bool] = None
    push_notifications: Optional[bool] = None

class OnboardingComplete(BaseModel):
    """Only the role is required, and only when the account has none yet. The rest can be skipped."""
    user_type: Optional[Literal["patient", "caregiver", "hcp", "org_member"]] = None
    interests: Optional[List[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]]] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=255)


class UserDetailsResponse(BaseModel):
    """
    Public safe user details response model.
    """
    id: str
    email: EmailStr
    user_type: Optional[str] = None  # None until chosen during onboarding
    status: str = "active"
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    country: Optional[str] = None
    language_preference: Optional[str] = "en"
    avatar: Optional[str] = None
    bio: Optional[str] = None
    interests: Optional[Union[List[str], Dict[str, Any]]] = []
    location: Optional[str] = None
    profile_visibility: Optional[str] = "public"
    notification_enabled: bool = True
    email_alerts: bool = True
    push_notifications: bool = False
    profile_completed: bool = False
    is_verified: bool = False
    is_active: bool = True
    created_at: datetime
    notification_preferences: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None
    deletion_scheduled_at: Optional[datetime] = None
    onboarding_completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
