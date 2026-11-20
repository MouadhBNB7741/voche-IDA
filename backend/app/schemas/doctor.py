from datetime import date, datetime
from uuid import UUID
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, model_validator

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
    rejection_reason: Optional[str] = Field(None, max_length=1000)

    @model_validator(mode="after")
    def _check_decision(self):
        if self.status == VerificationStatus.pending:
            raise ValueError("A review must approve or reject the licence.")
        self.rejection_reason = (self.rejection_reason or "").strip() or None
        if self.status == VerificationStatus.rejected and not self.rejection_reason:
            raise ValueError("Give the doctor a reason when rejecting a licence.")
        return self

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
    issuing_region: Optional[str] = None
    expiration_date: Optional[date] = None
    has_document: bool = False  # The file itself is only served by /doctors/verification/{id}/document

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _set_has_document(cls, data):
        if isinstance(data, dict):
            return {**data, "has_document": bool(data.get("document_url"))}
        return data


class PendingVerificationResponse(VerificationResponse):
    """A licence in the admin queue, with the doctor who sent it."""
    display_name: Optional[str] = None
    email: Optional[str] = None
