from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

ContextType = Literal["general", "trial_inquiry", "symptom_guidance", "resource_qa"]


# --- Requests ---

class CreateConversationRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    context_type: ContextType = "general"
    context_reference_id: Optional[UUID] = None


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


class FeedbackRequest(BaseModel):
    rating: Literal[-1, 1]
    comment: Optional[str] = Field(None, max_length=2000)


# --- Responses ---

class Citation(BaseModel):
    type: Literal["trial", "resource"]
    id: UUID
    title: str


class MessageResponse(BaseModel):
    id: UUID
    sender_role: Literal["user", "assistant", "system"]
    content: str
    citations: List[Citation] = []
    safety_flagged: bool = False
    created_at: datetime


class ConversationResponse(BaseModel):
    id: UUID
    title: Optional[str] = None
    context_type: ContextType
    context_reference_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse] = []


class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
