"""
Pydantic schemas for Events & Webinars API.
Covers request validation and response serialization.
"""

from datetime import date, datetime, time
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


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
