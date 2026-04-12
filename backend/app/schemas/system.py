"""
System Schemas — Pydantic models for system, health, feedback, and metadata endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from uuid import UUID


# ── Feedback ─────────────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    category: str = Field(
        ...,
        pattern="^(platform|trial|patient|feature|bug|other)$",
        description="Feedback category",
    )
    message: str = Field(..., min_length=10, max_length=5000)
    rating: int = Field(..., ge=1, le=5, description="Star rating from 1 (poor) to 5 (excellent)")


class FeedbackResponse(BaseModel):
    ticket_id: UUID
    message: str = "Feedback submitted successfully"
    created_at: datetime


# ── Health ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    timestamp: datetime


# ── System Status ────────────────────────────────────────────────────────────

class SystemStatusResponse(BaseModel):
    api_version: str = "v1"
    status: str
    uptime_seconds: Optional[float] = None
    database: Dict[str, Any] = {}
    features: Dict[str, bool] = {
        "ai_assistant": True,
        "forums": True,
        "events": True,
        "surveys": True,
        "resources": True,
        "organizations": True,
        "notifications": True,
    }


# ── Metadata ─────────────────────────────────────────────────────────────────

class MetadataResponse(BaseModel):
    countries: List[str]
    disease_areas: List[str]
    languages: List[Dict[str, str]]
    trial_phases: List[str]
    trial_statuses: List[str]
    roles: List[str]
    community_types: List[str]
    event_types: List[str]
    resource_types: List[str]
    feedback_categories: List[str]

# ── Announcements ────────────────────────────────────────────────────────────
class AnnouncementRequest(BaseModel):
    title: str = Field(..., max_length=255)
    message: str = Field(..., min_length=10)
    link: Optional[str] = None
    org_id: Optional[UUID] = None
    group_id: Optional[UUID] = None
