"""
Notification Schemas — Pydantic models for request/response validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from enum import Enum
from uuid import UUID


# ── Enums ────────────────────────────────────────────────────────────────────

class NotificationType(str, Enum):
    """
    Strict Notification Types for Phase 1 (Patient Role).
    Aligned with real module features.
    """
    # Clinical
    TRIAL_MATCH = "trial_match"
    TRIAL_ALERT = "trial_alert"

    # Community
    COMMUNITY_REPLY = "community_reply"
    COMMUNITY_LIKE = "community_like"

    # Events
    EVENT_REMINDER = "event_reminder"
    EVENT_UPDATE = "event_update"

    # Organizations
    ORG_REQUEST_UPDATE = "org_request_update"

    # Resources
    RESOURCE_UPDATE = "resource_update"

    # Surveys
    SURVEY_AVAILABLE = "survey_available"

    # System
    SYSTEM_ANNOUNCEMENT = "system_announcement"


# ── Request Schemas ──────────────────────────────────────────────────────────

class NotificationCreateRequest(BaseModel):
    """Used internally (service layer) to create a notification."""
    user_id: UUID
    type: NotificationType
    title: str = Field(..., max_length=255)
    message: str
    link: Optional[str] = Field(None, max_length=500)
    expires_at: Optional[datetime] = None


# ── Response Schemas ─────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    notification_id: UUID
    user_id: UUID
    type: NotificationType
    title: str
    message: str
    link: Optional[str] = None
    read: bool
    expires_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginationMeta(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int


class NotificationListResponse(BaseModel):
    data: List[NotificationResponse]
    unread_count: int
    meta: PaginationMeta


class MarkAllReadResponse(BaseModel):
    message: str
    updated_count: int


class NotificationPreferences(BaseModel):
    """
    Normalized notification preferences (Patient role - Phase 1).
    Matches users.notification_preferences JSONB.
    """
    emailAlerts: bool = True
    pushNotifications: bool = True
    frequency: str = "instant"  # daily_digest, weekly, instant
    notificationTypes: Dict[NotificationType, bool] = Field(
        default_factory=lambda: {
            NotificationType.TRIAL_MATCH: True,
            NotificationType.TRIAL_ALERT: True,
            NotificationType.COMMUNITY_REPLY: True,
            NotificationType.COMMUNITY_LIKE: True,
            NotificationType.EVENT_REMINDER: True,
            NotificationType.EVENT_UPDATE: True,
            NotificationType.ORG_REQUEST_UPDATE: True,
            NotificationType.RESOURCE_UPDATE: True,
            NotificationType.SURVEY_AVAILABLE: True,
            NotificationType.SYSTEM_ANNOUNCEMENT: True,
        }
    )
