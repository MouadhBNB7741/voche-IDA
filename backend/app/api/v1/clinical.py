from typing import List, Optional, Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies.connections import get_connection
from app.api.middleware.auth_middleware import auth_middleware, auth_middleware_optional
from app.models.clinical_model import ClinicalModel
from app.schemas.clinical import (
    TrialSearchParams,
    PaginatedResponse,
    TrialDetail,
    TrialSaveRequest,
    SavedTrialItem,
    ExpressInterestRequest,
    CreateAlertRequest,
    UpdateAlertRequest,
    AlertResponse,
    InterestResponse,
    TrialSaveResponse,
)
from app.services.email import EmailService  # hypothetical

# Assuming main.py mounts this with /api/v1 context
router = APIRouter(tags=["Clinical"])


# ----------------------------------------------------------------------
# TRIALS ENDPOINTS
# ----------------------------------------------------------------------
@router.get("/trials", response_model=PaginatedResponse)
async def search_trials(
    keyword: Optional[str] = Query(None),
    disease_areas: Optional[List[str]] = Query(None),
    phases: Optional[List[str]] = Query(None),
    statuses: Optional[List[str]] = Query(None),
    location: Optional[str] = Query(None),
    sponsor: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("relevance"),
    conn=Depends(get_connection),
    current_user: Optional[dict] = Depends(auth_middleware_optional),
):
    """
    Search and list clinical trials.
    """
    model = ClinicalModel(conn)
    user_id = current_user["id"] if current_user else None
    
    # Extract params to pass individually or as kwargs
    results = await model.search_trials(
        keyword=keyword,
        disease_areas=disease_areas,
        phases=phases,
        statuses=statuses,
        location=location,
        sponsor=sponsor,
        page=page,
        limit=limit,
        sort_by=sort_by,
        user_id=user_id,
    )
    return results


@router.get("/trials/{trial_id}", response_model=TrialDetail)
async def get_trial_by_id(
    trial_id: UUID,
    conn=Depends(get_connection),
    current_user: Optional[dict] = Depends(auth_middleware_optional),
):
    """
    Get complete details of a specific trial.
    """
    model = ClinicalModel(conn)
    user_id = current_user["id"] if current_user else None
    trial = await model.get_trial_by_id(str(trial_id), user_id)
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
        
    return trial


@router.post("/trials/{trial_id}/save", status_code=status.HTTP_201_CREATED, response_model=TrialSaveResponse)
async def save_trial(
    trial_id: UUID,
    request: TrialSaveRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """
    Save/bookmark a trial.
    """
    model = ClinicalModel(conn)
    saved = await model.save_trial(current_user["id"], str(trial_id), request.notes)
    if not saved:
        # It returns False if already saved (ON CONFLICT DO NOTHING)
        # OR if insert failed.
        # Requirement: "Duplicate save blocked (unique constraint)".
        # Return 409 Conflict if already saved.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Trial already saved",
        )
    return {"message": "Trial saved successfully", "trial_id": trial_id}


@router.delete("/trials/{trial_id}/save", status_code=status.HTTP_200_OK)
async def unsave_trial(
    trial_id: UUID,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """
    Remove a trial from saved list.
    """
    model = ClinicalModel(conn)
    deleted = await model.unsave_trial(current_user["id"], str(trial_id))
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved trial not found",
        )
    return {"message": "Trial removed from saved list", "trial_id": trial_id}


@router.post("/trials/{trial_id}/interest", response_model=InterestResponse)
async def express_interest(
    trial_id: UUID,
    request: ExpressInterestRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
    email_service: EmailService = Depends(),
):
    """
    Express interest in a trial.
    """
    model = ClinicalModel(conn)
    lead = await model.express_interest(
        user_id=current_user["id"],
        trial_id=str(trial_id),
        message=request.message,
    )
    
    # Email notifications would go here
    # await email_service.send...
    
    return lead


# ----------------------------------------------------------------------
# ALERTS ENDPOINTS
# ----------------------------------------------------------------------
@router.post("/alerts/trials", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_trial_alert(
    request: CreateAlertRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Create a new trial alert subscription."""
    model = ClinicalModel(conn)
    alert = await model.create_trial_alert(
        user_id=current_user["id"],
        disease_area=request.disease_area,
        location=request.location,
        phase=request.phase,
        filter_criteria=request.filter_criteria,
        alert_frequency=request.alert_frequency,
        trial_id=str(request.trial_id) if request.trial_id else None,
    )
    return alert


@router.get("/alerts/trials", response_model=List[AlertResponse])
async def get_my_alerts(
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """List all alert subscriptions for the current user."""
    model = ClinicalModel(conn)
    alerts = await model.get_my_alerts(current_user["id"])
    return alerts


@router.delete("/alerts/trials/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trial_alert(
    alert_id: UUID,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Delete an existing trial alert."""
    model = ClinicalModel(conn)
    deleted = await model.delete_trial_alert(str(alert_id), current_user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Alert not found or not owned by user")
    return None


@router.patch("/alerts/trials/{alert_id}", response_model=AlertResponse)
async def update_trial_alert(
    alert_id: UUID,
    request: UpdateAlertRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """
    Update an alert.
    """
    model = ClinicalModel(conn)
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
        
    alert = await model.update_trial_alert(str(alert_id), current_user["id"], updates)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    return alert


# ----------------------------------------------------------------------
# USER SUB-RESOURCES
# ----------------------------------------------------------------------
@router.get("/users/me/saved-trials", response_model=List[SavedTrialItem])
async def get_my_saved_trials(
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Get all trials saved by the current user."""
    model = ClinicalModel(conn)
    saved = await model.get_saved_trials(current_user["id"])
    return saved