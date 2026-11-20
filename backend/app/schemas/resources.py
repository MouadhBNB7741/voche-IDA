from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResourceType(str, Enum):
    video = "video"
    document = "document"
    toolkit = "toolkit"
    course = "course"


class ResourceSortOption(str, Enum):
    newest = "newest"
    most_popular = "most_popular"
    highest_rated = "highest_rated"


class ResourceSummaryResponse(BaseModel):
    resource_id: UUID
    title: str
    type: str
    category: str
    description: str
    url: Optional[str] = None
    language: str = "en"
    duration: Optional[str] = None
    author: Optional[str] = None
    tags: List[str] = []
    published_date: Optional[datetime] = None
    downloads: int = 0
    rating: float = 0.0
    featured: bool = False
    requires_auth: bool = False
    approval_status: str = "approved"
    has_file: bool = False
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ResourceListResponse(BaseModel):
    data: List[ResourceSummaryResponse]
    meta: Dict[str, Any]


class ResourceRatingResponse(BaseModel):
    rating_id: UUID
    user_id: UUID
    resource_id: UUID
    rating: int
    review: Optional[str] = None
    created_at: Optional[datetime] = None
    user_display_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ResourceDetailsResponse(ResourceSummaryResponse):
    ratings_count: int = 0
    reviews: List[ResourceRatingResponse] = []
    related_resources: List[ResourceSummaryResponse] = []


class CreateRatingRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    review: Optional[str] = None


class ProgressUpdateRequest(BaseModel):
    progress: int = Field(..., ge=0, le=100)
    last_position: Optional[str] = None


class ProgressResponse(BaseModel):
    success: bool
    resource_id: UUID
    progress: int
    last_position: Optional[str] = None


# ----------------------------------------------------------------------
# Submissions and approval
# ----------------------------------------------------------------------
class SubmissionAccessResponse(BaseModel):
    can_submit: bool
    reason: Optional[str] = None  # why not, in words the user can act on


class ResourceSubmissionResponse(ResourceSummaryResponse):
    submitted_by: Optional[UUID] = None
    rejection_reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class ResourceSubmissionListResponse(BaseModel):
    data: List[ResourceSubmissionResponse]
    meta: Dict[str, Any]


class PendingResourceResponse(ResourceSubmissionResponse):
    submitter_name: Optional[str] = None
    submitter_email: Optional[str] = None
    submitter_type: Optional[str] = None


class PendingResourceListResponse(BaseModel):
    data: List[PendingResourceResponse]
    meta: Dict[str, Any]


class ApprovalDecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    reason: Optional[str] = Field(None, max_length=1000, description="Required to reject; sent to the submitter")

    @model_validator(mode="after")
    def reason_for_rejection(self):
        self.reason = (self.reason or "").strip() or None
        if self.decision == "reject" and not self.reason:
            raise ValueError("A reason is required to reject a submission")
        return self


class ApprovalDecisionResponse(BaseModel):
    success: bool = True
    id: UUID
    approval_status: str
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
