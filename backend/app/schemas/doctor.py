from datetime import datetime
from uuid import UUID
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

class VerificationStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class VerificationRequest(BaseModel):
    license_number: str = Field(..., min_length=1)
    institution: str = Field(..., min_length=1)
    country: str = Field(..., min_length=2)
    specialization: str = Field(..., min_length=2)

class VerificationReview(BaseModel):
    status: VerificationStatus
    rejection_reason: Optional[str] = None

class VerificationResponse(BaseModel):
    verification_id: UUID
    user_id: UUID
    license_number: str
    institution: str
    country: str
    specialization: str
    status: str
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
