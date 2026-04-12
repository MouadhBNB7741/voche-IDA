from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict


# ----------------------------------------------------------------------
# Enums
# ----------------------------------------------------------------------
class PostType(str, Enum):
    question = "question"
    story = "story"
    discussion = "discussion"
    announcement = "announcement"


class ModerationStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    flagged = "flagged"
    removed = "removed"


class CommunityType(str, Enum):
    disease_specific = "disease_specific"
    general = "general"
    hcp_only = "hcp_only"


class ReportReason(str, Enum):
    misinformation = "misinformation"
    harassment = "harassment"
    spam = "spam"
    medical_advice = "medical_advice"
    other = "other"


class ReportTargetType(str, Enum):
    post = "post"
    comment = "comment"


class CommunitySortOption(str, Enum):
    most_members = "most_members"
    most_posts = "most_posts"
    newest = "newest"
    name_asc = "name_asc"


class PostSortOption(str, Enum):
    recent = "recent"
    popular = "popular"
    replies = "replies"


# ----------------------------------------------------------------------
# Response Schemas
# ----------------------------------------------------------------------
class CommunityResponse(BaseModel):
    community_id: UUID
    name: str
    description: Optional[str] = None
    type: str
    icon: Optional[str] = None
    moderation_level: Optional[str] = None
    member_count: int = 0
    post_count: int = 0
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CommunityListResponse(BaseModel):
    data: List[CommunityResponse]
    meta: Dict[str, Any]


class PostAuthor(BaseModel):
    display_name: str
    avatar: Optional[str] = None


class PostSummaryResponse(BaseModel):
    post_id: UUID
    title: str
    author_display_name: Optional[str] = None
    author_avatar: Optional[str] = None
    community_name: Optional[str] = None
    created_at: Optional[datetime] = None
    likes_count: int = 0
    replies_count: int = 0
    is_liked_by_me: bool = False

    model_config = ConfigDict(from_attributes=True)


class PostListResponse(BaseModel):
    data: List[PostSummaryResponse]
    meta: Dict[str, Any]


class CommentResponse(BaseModel):
    comment_id: UUID
    post_id: UUID
    user_id: Optional[UUID] = None
    parent_comment_id: Optional[UUID] = None
    content: str
    author_display_name: Optional[str] = None
    author_avatar: Optional[str] = None
    likes_count: int = 0
    moderation_status: str = "approved"
    is_deleted: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PostDetailsResponse(BaseModel):
    post_id: UUID
    user_id: Optional[UUID] = None
    community_id: UUID
    title: str
    content: str
    post_type: str = "discussion"
    moderation_status: str = "approved"
    views_count: int = 0
    replies_count: int = 0
    likes_count: int = 0
    is_pinned: bool = False
    is_locked: bool = False
    is_deleted: bool = False
    tags: List[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    author_display_name: Optional[str] = None
    author_avatar: Optional[str] = None
    community_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PostDetailsWithReplies(BaseModel):
    post: PostDetailsResponse
    replies: List[CommentResponse]


# ----------------------------------------------------------------------
# Request Schemas
# ----------------------------------------------------------------------
class CreatePostRequest(BaseModel):
    title: str = Field(..., min_length=5, max_length=500)
    content: str = Field(..., min_length=10)
    post_type: Optional[PostType] = PostType.discussion
    tags: Optional[List[str]] = Field(default_factory=list)


class EditPostRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=500)
    content: Optional[str] = Field(None, min_length=10)


class CreateCommentRequest(BaseModel):
    content: str = Field(..., min_length=1)
    parent_comment_id: Optional[UUID] = None


class EditCommentRequest(BaseModel):
    content: str = Field(..., min_length=1)


class ReportContentRequest(BaseModel):
    target_type: ReportTargetType
    target_id: UUID
    reason: ReportReason
    description: Optional[str] = None


class ReportResponse(BaseModel):
    report_id: UUID
    reporter_id: UUID
    target_type: str
    target_id: UUID
    reason: str
    status: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- Admin Report Management ---
class ReportDetailResponse(BaseModel):
    report_id: UUID
    reporter_id: UUID
    reporter_name: Optional[str] = None
    target_type: str
    target_id: UUID
    target_content: Optional[str] = None
    reason: str
    description: Optional[str] = None
    status: str
    moderator_id: Optional[UUID] = None
    action_taken: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ReportListResponse(BaseModel):
    reports: List[ReportDetailResponse]
    total: int
    page: int
    limit: int


class ResolveReportRequest(BaseModel):
    status: str = Field(..., description="reviewed or resolved")
    action_taken: Optional[str] = Field(None, description="approved, removed, warned, banned")
    resolution_notes: Optional[str] = None
