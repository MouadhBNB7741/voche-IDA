from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies.connections import get_connection
from app.api.dependencies.jwt_auth import get_current_user
from app.models.clinical_model import ClinicalModel
from app.schemas.clinical import (
    TrialSearchParams,
    PaginatedResponse,
    TrialDetail,
    TrialSaveRequest,
    SavedTrialItem,
    ExpressInterestRequest,
    CreateAlertRequest,
    AlertResponse,
    InterestResponse,
)
from app.services.email import EmailService  # hypothetical

router = APIRouter(prefix="/api/v1/clinical", tags=["Clinical"])


@router.get("/trials", response_model=PaginatedResponse)
async def search_trials(
    params: TrialSearchParams = Depends(),
    conn=Depends(get_connection),
    current_user: Optional[dict] = Depends(get_current_user),
):
    """
    Search and list clinical trials with full‑text search, filters, pagination.
    For authenticated users, each trial includes a `is_saved` flag.
    """
    model = ClinicalModel(conn)
    user_id = current_user["id"] if current_user else None
    results = await model.search_trials(
        keyword=params.keyword,
        disease_areas=params.disease_areas,
        phases=params.phases,
        statuses=params.statuses,
        location=params.location,
        sponsor=params.sponsor,
        page=params.page,
        limit=params.limit,
        sort_by=params.sort_by,
        user_id=user_id,
    )
    return results


@router.get("/trials/{trial_id}", response_model=TrialDetail)
async def get_trial_by_id(
    trial_id: UUID,
    conn=Depends(get_connection),
    current_user: Optional[dict] = Depends(get_current_user),  # not used, but could be for saved flag
):
    """Get complete details of a specific trial."""
    model = ClinicalModel(conn)
    trial = await model.get_trial_by_id(str(trial_id))
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    return trial


@router.post("/trials/{trial_id}/save", status_code=status.HTTP_201_CREATED)
async def save_trial(
    trial_id: UUID,
    request: TrialSaveRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(get_current_user),
):
    """Save/bookmark a trial for the authenticated user."""
    model = ClinicalModel(conn)
    saved = await model.save_trial(current_user["id"], str(trial_id), request.notes)
    if not saved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Trial already saved",
        )
    return {"message": "Trial saved successfully", "trial_id": trial_id}


@router.delete("/trials/{trial_id}/save", status_code=status.HTTP_200_OK)
async def unsave_trial(
    trial_id: UUID,
    conn=Depends(get_connection),
    current_user: dict = Depends(get_current_user),
):
    """Remove a trial from the user's saved list."""
    model = ClinicalModel(conn)
    deleted = await model.unsave_trial(current_user["id"], str(trial_id))
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved trial not found",
        )
    return {"message": "Trial removed from saved list", "trial_id": trial_id}


@router.get("/users/me/saved-trials", response_model=List[SavedTrialItem])
async def get_my_saved_trials(
    conn=Depends(get_connection),
    current_user: dict = Depends(get_current_user),
):
    """Get all trials saved by the current user."""
    model = ClinicalModel(conn)
    saved = await model.get_saved_trials(current_user["id"])
    return saved


@router.post("/trials/{trial_id}/interest", response_model=InterestResponse)
async def express_interest(
    trial_id: UUID,
    request: ExpressInterestRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(get_current_user),
    email_service: EmailService = Depends(),  # injected service
):
    """
    Express interest in a trial.
    - Logs the interest in the database.
    - Sends notification email to trial coordinator.
    - Sends confirmation email to the user.
    """
    model = ClinicalModel(conn)
    lead = await model.express_interest(
        user_id=current_user["id"],
        trial_id=str(trial_id),
        message=request.message,
    )

    # --- Email notifications (service layer) ---
    # Fetch trial and user details for email content
    trial = await model.get_trial_by_id(str(trial_id))
    # Get user profile (using another model)
    from app.models.user_model import UserModel
    user_model = UserModel(conn)
    user = await user_model.get_by_id(current_user["id"])

    # Send to trial coordinator (emails from trial_sites)
    if trial and trial.get("sites"):
        for site in trial["sites"]:
            if site.get("contact_email"):
                await email_service.send_trial_interest_notification(
                    sponsor_email=site["contact_email"],
                    user=user,
                    trial=trial,
                    message=request.message,
                )

    # Send confirmation to user
    await email_service.send_interest_confirmation(user["email"], trial)

    return lead


@router.post("/alerts/trials", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_trial_alert(
    request: CreateAlertRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(get_current_user),
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


@router.delete("/alerts/trials/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trial_alert(
    alert_id: UUID,
    conn=Depends(get_connection),
    current_user: dict = Depends(get_current_user),
):
    """Delete an existing trial alert."""
    model = ClinicalModel(conn)
    deleted = await model.delete_trial_alert(str(alert_id), current_user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Alert not found or not owned by user")
    return None


@router.get("/users/me/alerts", response_model=List[AlertResponse])
async def get_my_alerts(
    conn=Depends(get_connection),
    current_user: dict = Depends(get_current_user),
):
    """List all alert subscriptions for the current user."""
    model = ClinicalModel(conn)
    alerts = await model.get_my_alerts(current_user["id"])
    return alerts