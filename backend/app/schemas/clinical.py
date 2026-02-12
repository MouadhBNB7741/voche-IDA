from datetime import date, datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# ----------------------------------------------------------------------
# Request / Input Schemas
# ----------------------------------------------------------------------
class TrialSearchParams(BaseModel):
    """Query parameters for GET /trials"""
    keyword: Optional[str] = None
    disease_areas: Optional[List[str]] = None
    phases: Optional[List[str]] = None
    statuses: Optional[List[str]] = None
    location: Optional[str] = None          # country or city
    sponsor: Optional[str] = None
    page: int = 1
    limit: int = 20
    sort_by: str = "relevance"             # relevance, newest, enrollment


class TrialSaveRequest(BaseModel):
    """Body for POST /trials/{trial_id}/save (currently empty)"""
    notes: Optional[str] = None


class ExpressInterestRequest(BaseModel):
    """Body for POST /trials/{trial_id}/interest"""
    message: Optional[str] = Field(None, description="Optional message to the trial coordinator")


class CreateAlertRequest(BaseModel):
    """Body for POST /alerts/trials"""
    disease_area: Optional[str] = None
    location: Optional[str] = None
    phase: Optional[str] = None
    filter_criteria: Dict[str, Any] = Field(default_factory=dict)
    alert_frequency: str = "weekly"        # instant, daily, weekly
    trial_id: Optional[UUID] = None        # if tracking a specific trial


# ----------------------------------------------------------------------
# Response Schemas
# ----------------------------------------------------------------------
class TrialSummary(BaseModel):
    """Lightweight trial info for search results"""
    id: UUID
    title: str
    phase: Optional[str]
    status: Optional[str]
    location: Optional[str]               # from trial_sites (concatenated)
    enrollment: Optional[int] = Field(None, alias="enrollment_count")
    is_saved: bool = False
    rank: Optional[float] = None

    class Config:
        allow_population_by_field_name = True
        from_attributes = True


class SponsorInfo(BaseModel):
    id: UUID
    name: str
    contact_email: Optional[str]
    website: Optional[str]


class DiseaseArea(BaseModel):
    id: UUID
    name: str


class EligibilityCriteria(BaseModel):
    inclusion: Optional[List[str]]
    exclusion: Optional[List[str]]
    min_age: Optional[int]
    max_age: Optional[int]
    gender: Optional[str]


class TrialSite(BaseModel):
    id: UUID
    site_name: str
    country: str
    city: str
    address: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    is_recruiting: bool


class TrialResource(BaseModel):
    id: UUID
    title: str
    file_url: str
    type: str
    uploaded_at: datetime


class TrialDetail(BaseModel):
    """Full trial details for GET /trials/{trial_id}"""
    id: UUID
    nct_id: Optional[str]
    title: str
    brief_description: Optional[str]
    detailed_description: Optional[str]
    objectives: Optional[Dict[str, Any]]
    phase: Optional[str]
    status: Optional[str]
    enrollment_target: Optional[int]
    enrollment_current: Optional[int]
    start_date: Optional[date]
    completion_date: Optional[date]
    location: Optional[str]               # derived from sites
    sponsor: Optional[SponsorInfo]
    disease_areas: List[DiseaseArea] = []
    eligibility: EligibilityCriteria
    sites: List[TrialSite] = []
    resources: List[TrialResource] = []
    safety_info: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class SavedTrialItem(BaseModel):
    """Trial in user's saved list, with timestamp"""
    id: UUID
    title: str
    phase: Optional[str]
    status: Optional[str]
    location: Optional[str]
    enrollment: Optional[int]
    saved_at: datetime


class PaginatedResponse(BaseModel):
    """Standard paginated response wrapper"""
    items: List[TrialSummary]
    total: int
    page: int
    limit: int
    pages: int


class AlertResponse(BaseModel):
    """Trial alert subscription"""
    alert_id: UUID
    disease_area: Optional[str]
    location: Optional[str]
    phase: Optional[str]
    filter_criteria: Dict[str, Any]
    alert_frequency: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]


class InterestResponse(BaseModel):
    """Response after expressing interest"""
    lead_id: UUID
    trial_id: UUID
    user_id: UUID
    created_at: datetime