from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies.connections import get_connection
from app.api.middleware.auth_middleware import auth_middleware, auth_middleware_optional
from app.models.survey_model import SurveyModel
from app.schemas.surveys import (
    SurveyListResponse,
    SurveyDetailResponse,
    SurveySubmissionRequest,
    SurveySubmissionResponse,
    SurveyStatus,
    CompletedSurveyListResponse,
    CompletedSurveyDetailResponse,
    SurveyDraftRequest,
    SurveyDraftResponse,
    SurveyAssignRequest,
    SurveyAssignResponse,
    SurveyAnalyticsResponse,
)
from app.schemas.notification import NotificationType
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/surveys", tags=["Surveys"])

@router.get("/", response_model=SurveyListResponse)
async def list_surveys(
    status: Optional[SurveyStatus] = Query(None, description="Filter by status (default is active)"),
    page: Optional[int] = Query(None, ge=1, description="Page number"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Items per page"),
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """
    List available surveys the authenticated user is eligible to complete.
    """
    model = SurveyModel(conn)
    result = await model.list_surveys(
        user_id=current_user["id"],
        status_filter=status.value if status else None,
        page=page,
        limit=limit,
    )
    return result

@router.get("/completed", response_model=CompletedSurveyListResponse)
async def list_completed_surveys(
    page: Optional[int] = Query(None, ge=1, description="Page number"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Items per page"),
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """
    List surveys completed by the authenticated user.
    """
    model = SurveyModel(conn)
    result = await model.get_user_completed_surveys(
        user_id=current_user["id"],
        page=page,
        limit=limit,
    )
    return result

@router.get("/completed/{completion_id}", response_model=CompletedSurveyDetailResponse)
async def get_completed_survey_details(
    completion_id: UUID,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """
    Get full details and answers of a specific completed survey.
    """
    model = SurveyModel(conn)
    details = await model.get_completion_details(str(completion_id), current_user["id"])
    
    if not details:
        raise HTTPException(status_code=404, detail="Completed survey not found or is anonymous")
        
    return details

@router.get("/{survey_id}", response_model=SurveyDetailResponse)
async def get_survey_questions(
    survey_id: UUID,
    conn=Depends(get_connection),
    current_user: Optional[dict] = Depends(auth_middleware_optional),
):
    """
    Get full survey details including questions.
    """
    model = SurveyModel(conn)
    survey = await model.get_survey_questions(str(survey_id), current_user["id"] if current_user else None)
    
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
        
    return survey

@router.post("/{survey_id}/responses", response_model=SurveySubmissionResponse)
async def submit_survey_response(
    survey_id: UUID,
    payload: SurveySubmissionRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """
    Submit a response to a survey.
    """
    if not payload.consent_given:
        raise HTTPException(status_code=400, detail="Consent is required to submit the survey")
        
    model = SurveyModel(conn)
    try:
        # Convert responses to dict for internal methods
        responses_dict = [r.model_dump() for r in payload.responses]
        
        result = await model.submit_survey_response(
            survey_id=str(survey_id),
            user_id=current_user["id"],
            responses=responses_dict,
            anonymous=payload.anonymous,
        )
        return result
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)


# ── Phase 2 ──────────────────────────────────────────────────────────────────

async def survey_manager_required(
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection),
) -> dict:
    """Admins, organization members and verified HCPs can assign surveys and see analytics."""
    user_type = current_user.get("user_type")
    if user_type in ("admin", "org_member"):
        return current_user
    if user_type == "hcp" and await conn.fetchval("SELECT is_verified FROM users WHERE id = $1", current_user["id"]):
        return current_user
    raise HTTPException(status_code=403, detail="Only admins, organizations and verified HCPs can manage surveys")


@router.patch("/{survey_id}/draft", response_model=SurveyDraftResponse)
async def save_survey_draft(
    survey_id: UUID,
    payload: SurveyDraftRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Save answers so far and resume later. GET /surveys/{id} returns them as draft_answers."""
    try:
        return await SurveyModel(conn).save_draft(str(survey_id), current_user["id"], payload.answers)
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e).lower() else 400, detail=str(e))


@router.post("/{survey_id}/assign", response_model=SurveyAssignResponse)
async def assign_survey(
    survey_id: UUID,
    payload: SurveyAssignRequest,
    conn=Depends(get_connection),
    manager: dict = Depends(survey_manager_required),
):
    """Assign a survey to patients by email. Each newly assigned patient gets an in-app notification."""
    if payload.due_date and payload.due_date.replace(tzinfo=payload.due_date.tzinfo or timezone.utc) <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Due date must be in the future")
    try:
        result = await SurveyModel(conn).assign(
            str(survey_id), payload.patient_emails, manager["id"],
            str(payload.trial_id) if payload.trial_id else None, payload.due_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e).lower() else 400, detail=str(e))

    notifications = NotificationService(conn)
    data = {"survey_id": str(survey_id), "survey_title": result["survey"]["title"]}
    for a in result["assigned"]:
        await notifications.notify_user(str(a["user_id"]), NotificationType.SURVEY_AVAILABLE, data)
    return {
        "assigned": [a["email"] for a in result["assigned"]],
        "already_assigned": result["already_assigned"],
        "not_found": result["not_found"],
    }


@router.get("/{survey_id}/analytics", response_model=SurveyAnalyticsResponse)
async def survey_analytics(
    survey_id: UUID,
    conn=Depends(get_connection),
    manager: dict = Depends(survey_manager_required),
):
    """Completion rate, average time to complete and answer distribution per question."""
    result = await SurveyModel(conn).analytics(str(survey_id))
    if not result:
        raise HTTPException(status_code=404, detail="Survey not found")
    return result
