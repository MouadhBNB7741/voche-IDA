from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies.connections import get_connection
from app.api.middleware.auth_middleware import auth_middleware
from app.models.survey_model import SurveyModel
from app.schemas.surveys import (
    SurveyListResponse,
    SurveyDetailResponse,
    SurveySubmissionRequest,
    SurveySubmissionResponse,
    SurveyStatus,
    CompletedSurveyListResponse,
    CompletedSurveyDetailResponse,
)

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
    current_user: dict = Depends(auth_middleware),
):
    """
    Get full survey details including questions.
    """
    model = SurveyModel(conn)
    survey = await model.get_survey_questions(str(survey_id))
    
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


