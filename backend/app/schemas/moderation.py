from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModerationActionType(str, Enum):
    approve_content = "approve_content"   # the content is fine: publish it, dismiss the reports
    hide_content = "hide_content"         # hide it (can be restored later)
    delete_content = "delete_content"     # remove it
    warn_user = "warn_user"               # notify the author
    suspend_user = "suspend_user"         # suspend the author for duration_hours
    ban_user = "ban_user"                 # suspend the author with no end date


class QueueStatus(str, Enum):
    open = "open"           # pending and under review
    closed = "closed"       # actioned and dismissed (and the old reviewed/resolved)
    pending = "pending"
    under_review = "under_review"
    actioned = "actioned"
    dismissed = "dismissed"


class ReportPriority(str, Enum):
    normal = "normal"
    high = "high"
    critical = "critical"


class DecideRequest(BaseModel):
    action: ModerationActionType
    reason: Optional[str] = Field(
        None, max_length=1000, description="Shown to the author in their notification"
    )
    duration_hours: Optional[int] = Field(
        None, ge=1, le=8760, description="Required for suspend_user (1 hour to 1 year)"
    )
    remove_content: bool = Field(
        False, description="With warn, suspend or ban: also remove the reported content"
    )

    @model_validator(mode="after")
    def check_action_details(self):
        user_actions = {
            ModerationActionType.warn_user,
            ModerationActionType.suspend_user,
            ModerationActionType.ban_user,
        }
        if self.action in user_actions and not (self.reason and self.reason.strip()):
            raise ValueError("A reason is required to warn, suspend or ban a user")
        if self.action == ModerationActionType.suspend_user and not self.duration_hours:
            raise ValueError("duration_hours is required to suspend a user")
        if self.action != ModerationActionType.suspend_user and self.duration_hours:
            raise ValueError("duration_hours is only used with suspend_user")
        if self.remove_content and self.action not in user_actions:
            raise ValueError("remove_content is only used with warn_user, suspend_user or ban_user")
        if self.reason is not None:
            self.reason = self.reason.strip() or None
        return self


class AuthorHistory(BaseModel):
    warnings: int = 0
    suspensions: int = 0
    bans: int = 0
    content_removed: int = 0
    reports_received: int = 0
    reports_upheld: int = 0
    last_action_at: Optional[datetime] = None


class QueueItem(BaseModel):
    report_id: UUID
    target_type: str
    target_id: UUID
    reason: str
    description: Optional[str] = None
    source: str = "user"
    priority: str = "normal"
    status: str
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    action_taken: Optional[str] = None
    resolution_notes: Optional[str] = None

    reporter_id: Optional[UUID] = None
    reporter_name: Optional[str] = None
    moderator_id: Optional[UUID] = None
    moderator_name: Optional[str] = None

    # The reported content, then and now
    reported_content: Optional[str] = None
    current_content: Optional[str] = None
    post_id: Optional[UUID] = None
    community_id: Optional[UUID] = None
    post_title: Optional[str] = None
    content_status: Optional[str] = None
    moderation_score: Optional[float] = None
    flagged_reason: Optional[str] = None
    content_deleted: Optional[bool] = None
    open_reports_on_target: int = 0

    # Its author and their record
    author_id: Optional[UUID] = None
    author_name: Optional[str] = None
    author_type: Optional[str] = None
    author_status: Optional[str] = None
    author_suspended_until: Optional[datetime] = None
    author_history: Optional[AuthorHistory] = None

    model_config = ConfigDict(from_attributes=True)


class QueueResponse(BaseModel):
    data: List[QueueItem]
    meta: Dict[str, Any]


class DecideResult(BaseModel):
    report_id: UUID
    action: str
    report_status: str
    reports_closed: int
    content_status: Optional[str] = None
    author_status: Optional[str] = None
    suspended_until: Optional[datetime] = None


class DecideResponse(BaseModel):
    success: bool = True
    data: DecideResult
