from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, Field

class SurveyStatus(str, Enum):
    draft = "draft"
    active = "active"
    closed = "closed"

class QuestionType(str, Enum):
    multiple_choice = "multiple_choice"
    scale = "scale"
    open_text = "open_text"
    yes_no = "yes_no"

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

class SurveyDetailResponse(BaseModel):
    survey_id: UUID
    title: str
    description: str
    consent_text: Optional[str] = None
    estimated_time: Optional[str] = None
    questions: List[QuestionDetail]

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
