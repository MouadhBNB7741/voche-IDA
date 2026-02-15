from datetime import datetime
from typing import Optional, List, Dict, Union, Any, Literal
from pydantic import BaseModel, EmailStr

class NotificationTypes(BaseModel):
    trialMatches: bool = True
    communityReplies: bool = True
    events: bool = True
    system: bool = True

class NotificationPreferences(BaseModel):
    emailAlerts: bool = True
    pushNotifications: bool = True
    notificationTypes: NotificationTypes = NotificationTypes()
    frequency: Literal["instant", "daily_digest", "weekly"] = "instant"

class VerificationPayload(BaseModel):
    licenseNumber: str
    issuingRegion: str
    expirationDate: datetime

class UserProfileUpdate(BaseModel):
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

class UserDetailsResponse(BaseModel):
    """
    Public safe user details response model.
    """
    id: str
    email: EmailStr
    user_type: str
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

    class Config:
        from_attributes = True
