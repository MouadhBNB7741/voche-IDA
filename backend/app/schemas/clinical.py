from datetime import date, datetime
from typing import List, Optional, Dict, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ----------------------------------------------------------------------
# Request / Input Schemas
# ----------------------------------------------------------------------
class TrialSearchParams(BaseModel):
    """Query parameters for GET /trials"""
    keyword: Optional[str] = None
    disease_areas: Optional[List[str]] = Field(None, title="List of disease areas")
    phases: Optional[List[str]] = Field(None)
    statuses: Optional[List[str]] = Field(None)
    location: Optional[str] = None          # country or city
    sponsor: Optional[str] = None
    page: int = 1
    limit: int = 20
    sort_by: str = "relevance"


class TrialSite(BaseModel):
    id: UUID = Field(..., alias="site_id")
    site_name: str
    country: str
    city: str
    address: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_recruiting: bool

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TrialSummary(BaseModel):
    """Lightweight trial info for search results"""
    id: UUID = Field(..., alias="trial_id")
    title: str
    phase: Optional[str]
    status: Optional[str]
    location: Optional[str]             
    enrollment: Optional[int] = Field(None, alias="enrollment_count")
    is_saved: bool = False
    rank: Optional[float] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class TrialDetail(BaseModel):
    """Full trial details for GET /trials/{trial_id}"""
    id: UUID = Field(..., alias="trial_id")
    nct_id: Optional[str] = None
    title: str
    summary: Optional[str] = None
    disease_area: str
    phase: str
    status: str
    sponsor: str
    countries: List[str] = []
    eligibility_criteria: Optional[str] = None
    enrollment: int = Field(0, alias="enrollment_count")
    max_enrollment: Optional[int] = None
    start_date: Optional[date] = None
    completion_date: Optional[date] = Field(None, alias="estimated_completion")
    contact: Optional[str] = None
    metadata: Dict[str, Any] = {}
    sites: List[TrialSite] = []
    
    # Computed / Derived
    location: Optional[str] = None
    is_saved: bool = False  # If user is authenticated

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SavedTrialItem(BaseModel):
    """Trial in user's saved list, with timestamp"""
    id: UUID = Field(..., alias="trial_id")
    title: str
    phase: Optional[str]
    status: Optional[str]
    location: Optional[str]
    enrollment: Optional[int] = Field(None, alias="enrollment_count")
    saved_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TrialSaveRequest(BaseModel):
    """Body for POST /trials/{trial_id}/save"""
    notes: Optional[str] = None


class ExpressInterestRequest(BaseModel):
    """Body for POST /trials/{trial_id}/interest"""
    message: Optional[str] = Field(None, description="Optional message to the trial coordinator")


class CreateAlertRequest(BaseModel):
    """Body for POST /alerts/trials"""
    disease_area: Optional[str] = None
    location: Optional[str] = None
    phase: Optional[Literal['Phase 1', 'Phase 2', 'Phase 3', 'Phase 4', 'Post-Market']] = None
    filter_criteria: Dict[str, Any] = Field(default_factory=dict)
    alert_frequency: Literal['instant', 'daily', 'weekly'] = "weekly"
    trial_id: Optional[UUID] = None        # if tracking a specific trial


class UpdateAlertRequest(BaseModel):
    """Body for PATCH /alerts/trials/{id}"""
    disease_area: Optional[str] = None
    location: Optional[str] = None
    phase: Optional[Literal['Phase 1', 'Phase 2', 'Phase 3', 'Phase 4', 'Post-Market']] = None
    filter_criteria: Optional[Dict[str, Any]] = None
    alert_frequency: Optional[Literal['instant', 'daily', 'weekly']] = None
    is_active: Optional[bool] = None


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
    lead_id: Optional[UUID] = None
    trial_id: UUID
    user_id: UUID
    created_at: datetime


class TrialSaveResponse(BaseModel):
    message: str
    trial_id: UUID
