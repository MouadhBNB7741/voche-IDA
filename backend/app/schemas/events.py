"""
Pydantic schemas for Events & Webinars API.
Covers request validation and response serialization.
"""

from datetime import date, datetime, time
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ─── Enums ────────────────────────────────────────────────────────────────────

class EventType(str, Enum):
    webinar = "webinar"
    conference = "conference"
    training = "training"
    roundtable = "roundtable"


class EventStatus(str, Enum):
    upcoming = "upcoming"
    ongoing = "ongoing"
    completed = "completed"
    cancelled = "cancelled"


class RegistrationStatus(str, Enum):
    registered = "registered"
    attended = "attended"
    no_show = "no_show"
    cancelled = "cancelled"


# ─── Response: Event Summary (for list endpoints) ────────────────────────────

class EventSummaryResponse(BaseModel):
    event_id: UUID
    title: str
    event_date: date
    event_time: time
    type: str
    organizer: str
    location: Optional[str] = None
    participants: int = 0
    status: Optional[str] = None
    registration_status: Optional[str] = None  
    registration_deadline: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EventListResponse(BaseModel):
    data: List[EventSummaryResponse]
    meta: Dict[str, Any]


# ─── Response: Event Details ─────────────────────────────────────────────────

class EventDetailResponse(BaseModel):
    event_id: UUID
    title: str
    description: str
    event_date: date
    event_time: time
    timezone: str = "UTC"
    type: str
    organizer: str
    location: Optional[str] = None
    virtual_link: Optional[str] = None
    participants: int = 0
    max_participants: Optional[int] = None
    registration_deadline: Optional[datetime] = None
    status: Optional[str] = None
    tags: List[str] = []
    banner_image: Optional[str] = None
    registration_status: Optional[str] = None
    approval_status: str = "approved"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ─── Suggesting an event, and the admin's decision ──────────────────────────

class EventSuggestionRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=500)
    description: str = Field(..., min_length=20, max_length=5000)
    type: EventType
    organizer: str = Field(..., min_length=2, max_length=255)
    event_date: date
    event_time: time
    timezone: str = Field("UTC", min_length=1, max_length=50)
    location: Optional[str] = Field(None, max_length=255)
    virtual_link: Optional[str] = Field(None, max_length=500)
    max_participants: Optional[int] = Field(None, ge=1, le=100000)
    registration_deadline: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list, max_length=10)

    @field_validator("title", "description", "organizer", "location", "virtual_link", "timezone", mode="before")
    @classmethod
    def strip_text(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if isinstance(value, str) else value

    @field_validator("location")
    @classmethod
    def empty_location(cls, value: Optional[str]) -> Optional[str]:
        return value or None

    @field_validator("virtual_link")
    @classmethod
    def check_link(cls, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        if not value.lower().startswith(("https://", "http://")):
            raise ValueError("The online link must start with https://")
        return value

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, tags: List[str]) -> List[str]:
        cleaned = [t.strip()[:50] for t in tags if t and t.strip()]
        return list(dict.fromkeys(cleaned))

    @model_validator(mode="after")
    def check_event(self):
        if self.event_date < date.today():
            raise ValueError("The event date can't be in the past")
        if not self.location and not self.virtual_link:
            raise ValueError("Add a location or an online link")
        if self.registration_deadline and self.registration_deadline.date() > self.event_date:
            raise ValueError("The registration deadline must be on or before the event date")
        return self


class EventSubmissionResponse(EventDetailResponse):
    created_by: Optional[UUID] = None
    rejection_reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class EventSubmissionListResponse(BaseModel):
    data: List[EventSubmissionResponse]
    meta: Dict[str, Any]


class PendingEventResponse(EventSubmissionResponse):
    suggester_name: Optional[str] = None
    suggester_email: Optional[str] = None
    suggester_type: Optional[str] = None


class PendingEventListResponse(BaseModel):
    data: List[PendingEventResponse]
    meta: Dict[str, Any]


# ─── Response: Registration Action ───────────────────────────────────────────

class RegistrationActionResponse(BaseModel):
    status: str
    message: str


# ─── Response: User Event (My Events) ───────────────────────────────────────

class UserEventResponse(BaseModel):
    event_id: UUID
    title: str
    event_date: date
    event_time: Optional[time] = None
    type: Optional[str] = None
    organizer: Optional[str] = None
    location: Optional[str] = None
    virtual_link: Optional[str] = None
    participants: int = 0
    status: str = "upcoming"  # event status
    registration_status: str  # user's registration status

    model_config = ConfigDict(from_attributes=True)


class UserEventListResponse(BaseModel):
    data: List[UserEventResponse]
    meta: Dict[str, Any]
