from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, EmailStr, Field

class SurveyStatus(str, Enum):
    draft = "draft"
    active = "active"
    closed = "closed"

class QuestionType(str, Enum):
    single_choice = "single_choice"
    multiple_choice = "multiple_choice"
    scale = "scale"
    open_text = "open_text"
    yes_no = "yes_no"
    number = "number"
    date = "date"

class SurveyListItem(BaseModel):
    survey_id: UUID
    title: str
    description: str
    estimated_time: Optional[str] = None
    incentive: Optional[str] = None
    status: SurveyStatus
    already_completed: bool

class SurveyListMeta(BaseModel):
    total: int
    page: int
    limit: int
    pages: int

class SurveyListResponse(BaseModel):
    data: List[SurveyListItem]
    meta: SurveyListMeta

class QuestionDetail(BaseModel):
    question_id: UUID
    text: str
    type: QuestionType
    required: bool
    options: Optional[List[str]] = None
    branching_rules: List[Dict[str, Any]] = []  # [{"condition": "equals", "value": "...", "next_question_id": "..."}]

class SurveyDetailResponse(BaseModel):
    survey_id: UUID
    title: str
    description: str
    consent_text: Optional[str] = None
    estimated_time: Optional[str] = None
    questions: List[QuestionDetail]
    draft_answers: Optional[Dict[str, Any]] = None  # the signed-in user's saved progress, if any

class MissingRequiredAnswerError(Exception):
    pass

class QuestionResponseItem(BaseModel):
    question_id: UUID
    answer: Any

class SurveySubmissionRequest(BaseModel):
    consent_given: bool
    anonymous: bool
    responses: List[QuestionResponseItem]

class SurveySubmissionResponse(BaseModel):
    message: str
    completion_id: UUID

class CompletedSurveyItem(BaseModel):
    completion_id: UUID
    survey_id: UUID
    title: str
    submitted_at: datetime

class CompletedSurveyListResponse(BaseModel):
    data: List[CompletedSurveyItem]
    meta: SurveyListMeta

class CompletedSurveyResponseItem(BaseModel):
    question_id: UUID
    question_text: str
    answer: Any

class CompletedSurveyDetailResponse(BaseModel):
    completion_id: UUID
    survey_id: UUID
    submitted_at: datetime
    responses: List[CompletedSurveyResponseItem]


# ── Phase 2: drafts, assignments, analytics ──────────────────────────────────

class SurveyDraftRequest(BaseModel):
    answers: Dict[str, Any] = Field(..., description="Answers so far, keyed by question_id")


class SurveyDraftResponse(BaseModel):
    status: str
    draft_answers: Dict[str, Any]
    updated_at: datetime


class SurveyAssignRequest(BaseModel):
    patient_emails: List[EmailStr] = Field(..., min_length=1, max_length=100)
    trial_id: Optional[UUID] = None
    due_date: Optional[datetime] = None


class SurveyAssignResponse(BaseModel):
    assigned: List[str]
    already_assigned: List[str]
    not_found: List[str]


class QuestionAnalytics(BaseModel):
    question_id: UUID
    question_text: str
    question_type: str
    answered: int
    distribution: Optional[Dict[str, int]] = None
    average: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None


class SurveyAnalyticsResponse(BaseModel):
    survey_id: UUID
    title: str
    total_responses: int
    assigned: int
    completed_assignments: int
    completion_rate: Optional[float] = None       # % of assignments completed
    avg_completion_hours: Optional[float] = None  # from assignment to submission
    questions: List[QuestionAnalytics]
