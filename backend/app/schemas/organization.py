from typing import List, Optional, Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, HttpUrl

# --- Organizations ---

class OrganizationBase(BaseModel):
    org_name: str
    org_type: str
    country: str
    description: Optional[str] = None
    website: Optional[str] = None
    contact_email: str
    logo: Optional[str] = None

class OrganizationResponse(OrganizationBase):
    org_id: UUID
    membership_status: str
    member_count: int
    joined_date: Optional[datetime] = None

class OrganizationListResponse(BaseModel):
    data: List[OrganizationResponse]
    meta: dict

class OrganizationMemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    role: str
    status: str
    joined_at: datetime
    # Optionally included user details
    user_name: Optional[str] = None
    user_email: Optional[str] = None

class OrganizationMemberListResponse(BaseModel):
    data: List[OrganizationMemberResponse]
    meta: dict

# --- Working Groups ---

class WorkingGroupBase(BaseModel):
    name: str
    type: str
    privacy_level: str
    description: Optional[str] = None

class WorkingGroupResponse(WorkingGroupBase):
    group_id: UUID
    organization_id: Optional[UUID] = None
    member_count: int
    is_active: bool

class WorkingGroupListResponse(BaseModel):
    data: List[WorkingGroupResponse]
    meta: dict

# --- Organization Details ---

class OrganizationDetailResponse(OrganizationResponse):
    members: Optional[List[OrganizationMemberResponse]] = []
    working_groups: Optional[List[WorkingGroupResponse]] = []

class WorkingGroupDetailResponse(WorkingGroupResponse):
    members: Optional[List[OrganizationMemberResponse]] = []

# --- Join Responses ---

class JoinOrganizationResponse(BaseModel):
    status: str
    message: Optional[str] = None

class JoinWorkingGroupResponse(BaseModel):
    status: str
    message: Optional[str] = None

class MembershipDecisionRequest(BaseModel):
    action: Literal["accept", "refuse", "approved", "rejected"]
