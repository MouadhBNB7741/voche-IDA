import logging
from typing import List, Optional, Any, Dict
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.api.dependencies.connections import get_connection
from app.api.middleware.admin_middleware import admin_required
from app.api.middleware.auth_middleware import auth_middleware, auth_middleware_optional
from app.api.middleware.hcp_middleware import verified_hcp_required
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
    TrialStatusUpdate,
    TrialStatusResponse,
    ScreeningRequest,
    ScreeningResponse,
    ReferralCreate,
    ReferralRespond,
    ReferralResponse,
)
from app.schemas.notification import NotificationType
from app.db.postgres import PostgresDB
from app.services import eligibility_service, trial_sync_service
from app.services.audit_service import AuditService
from app.services.email import EmailService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

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
    eligible_for_me: bool = Query(False, description="Only trials matching my profile's condition and country"),
    conn=Depends(get_connection),
    current_user: Optional[dict] = Depends(auth_middleware_optional),
):
    """
    Search and list clinical trials. Draft trials are only listed for platform admins.
    """
    model = ClinicalModel(conn)
    user_id = current_user["id"] if current_user else None

    match = {"conditions": None, "country": None}
    if eligible_for_me:
        if not current_user:
            raise HTTPException(status_code=401, detail="Sign in to see trials matching your profile")
        match = await model.get_match_profile(user_id)
        if not match["conditions"] and not match["country"]:
            raise HTTPException(status_code=400, detail="Add your condition or country to your profile to use this filter")

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
        include_drafts=bool(current_user and current_user["user_type"] == "admin"),
        match_conditions=match["conditions"],
        match_country=match["country"],
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
    is_admin = bool(current_user and current_user["user_type"] == "admin")
    trial = await model.get_trial_by_id(str(trial_id), user_id, include_drafts=is_admin)
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


# ----------------------------------------------------------------------
# LIFECYCLE (admin)
# ----------------------------------------------------------------------
@router.patch("/trials/{trial_id}/status", response_model=TrialStatusResponse)
async def change_trial_status(
    trial_id: UUID,
    request: TrialStatusUpdate,
    conn=Depends(get_connection),
    admin: dict = Depends(admin_required),
):
    """Move a trial to its next lifecycle state. Completed and Terminated are final."""
    model = ClinicalModel(conn)
    current = await model.get_trial_status(str(trial_id))
    if current is None:
        raise HTTPException(status_code=404, detail="Trial not found")
    if request.status not in model.STATUS_TRANSITIONS.get(current, set()):
        allowed = sorted(model.STATUS_TRANSITIONS.get(current, set()))
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change status from {current} to {request.status}. Allowed: {', '.join(allowed) or 'none'}",
        )
    if not await model.change_status(str(trial_id), current, request.status):
        raise HTTPException(status_code=409, detail="Trial status changed in the meantime. Please reload and try again.")

    await AuditService(conn).log_action(
        user_id=admin["id"], action="trial_status_changed", target_type="trial", target_id=str(trial_id),
        metadata={"from": current, "to": request.status},
    )
    if request.status == "Recruiting":
        await trial_sync_service.notify_matches(conn, trial_id)
    return {"trial_id": trial_id, "previous_status": current, "status": request.status}


# ----------------------------------------------------------------------
# ELIGIBILITY PRE-SCREENER
# ----------------------------------------------------------------------
@router.post("/trials/{trial_id}/screen", response_model=ScreeningResponse)
async def screen_eligibility(
    trial_id: UUID,
    request: ScreeningRequest,
    conn=Depends(get_connection),
):
    """Check a patient's answers against the trial's eligibility rules. Answers are not stored."""
    rules = await ClinicalModel(conn).get_eligibility_rules(str(trial_id))
    if rules is None:
        raise HTTPException(status_code=404, detail="Trial not found")
    return {"trial_id": trial_id, **eligibility_service.screen(rules, request.model_dump())}


# ----------------------------------------------------------------------
# HCP REFERRALS
# ----------------------------------------------------------------------
REFERRABLE_STATUSES = {"Not yet recruiting", "Recruiting"}


@router.post("/trials/{trial_id}/refer", response_model=ReferralResponse, status_code=status.HTTP_201_CREATED)
async def refer_patient(
    trial_id: UUID,
    request: ReferralCreate,
    conn=Depends(get_connection),
    hcp: dict = Depends(verified_hcp_required),
):
    """A verified HCP refers a patient (by email) to a trial. Notifies the patient in-app and by email."""
    model = ClinicalModel(conn)
    trial = await model.get_trial_by_id(str(trial_id))
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    if trial["status"] not in REFERRABLE_STATUSES:
        raise HTTPException(status_code=409, detail=f"This trial is {trial['status']} and is not accepting referrals")

    email = request.patient_email.lower()
    if email == hcp["email"].lower():
        raise HTTPException(status_code=400, detail="You cannot refer yourself")
    patient = await conn.fetchrow("SELECT id FROM users WHERE lower(email) = $1 AND is_active = TRUE", email)
    patient_id = patient["id"] if patient else None

    referral = await model.create_referral(str(trial_id), hcp["id"], patient_id, email, request.clinical_notes)

    if patient_id:
        notifications = NotificationService(conn)
        if await notifications._should_notify(str(patient_id), NotificationType.TRIAL_MATCH):
            await notifications.create_notification(
                user_id=str(patient_id),
                notif_type=NotificationType.TRIAL_MATCH.value,
                title="Your doctor referred you to a trial",
                message=f"{referral['hcp_name']} referred you to: {trial['title']}",
                link=f"/trials/{trial_id}",
            )
    try:
        await EmailService.send_trial_referral(email, referral["hcp_name"], trial["title"], str(trial_id), bool(patient_id))
    except Exception as e:
        # The referral is saved and visible in-app; a mail outage must not undo it.
        logger.warning(f"Referral {referral['id']} saved but email failed: {e}")
    return referral


@router.get("/referrals/sent", response_model=List[ReferralResponse])
async def list_sent_referrals(
    conn=Depends(get_connection),
    hcp: dict = Depends(verified_hcp_required),
):
    """Referrals this HCP has sent, newest first, with their current status."""
    return await ClinicalModel(conn).list_sent_referrals(hcp["id"])


@router.get("/referrals/received", response_model=List[ReferralResponse])
async def list_received_referrals(
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Trials the current user's doctors referred them to. Opening the list marks new referrals as viewed."""
    return await ClinicalModel(conn).list_received_referrals(current_user["id"], current_user["email"])


@router.patch("/referrals/{referral_id}/respond", response_model=ReferralResponse)
async def respond_to_referral(
    referral_id: UUID,
    request: ReferralRespond,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """
    The referred patient accepts or declines. Accepting moves the referral to consent_pending:
    the patient still has to give informed consent before enrolment.
    """
    model = ClinicalModel(conn)
    new_status = "consent_pending" if request.action == "accept" else "declined"
    referral = await model.respond_to_referral(referral_id, current_user["id"], current_user["email"], new_status)
    if referral:
        return referral
    if await model.referral_exists_for_patient(referral_id, current_user["id"], current_user["email"]):
        raise HTTPException(status_code=409, detail="This referral has already been answered")
    raise HTTPException(status_code=404, detail="Referral not found")


# ----------------------------------------------------------------------
# CLINICALTRIALS.GOV SYNC (admin)
# ----------------------------------------------------------------------
async def _run_sync_in_background(log_id):
    async with PostgresDB.get_pool().acquire() as conn:
        if not await conn.fetchval("SELECT pg_try_advisory_lock($1)", trial_sync_service.SYNC_LOCK_ID):
            await conn.execute(
                "UPDATE trial_sync_logs SET status = 'failed', sync_completed_at = NOW(), "
                "error_details = 'Another sync was already running' WHERE id = $1",
                log_id,
            )
            return
        try:
            await trial_sync_service.run_sync(conn, log_id=log_id)
        finally:
            await conn.execute("SELECT pg_advisory_unlock($1)", trial_sync_service.SYNC_LOCK_ID)


@router.post("/trials/sync", status_code=status.HTTP_202_ACCEPTED)
async def trigger_trial_sync(
    background_tasks: BackgroundTasks,
    conn=Depends(get_connection),
    admin: dict = Depends(admin_required),
):
    """Start a ClinicalTrials.gov sync now. It runs in the background; check GET /trials/sync/logs for the result."""
    log_id = await conn.fetchval("INSERT INTO trial_sync_logs DEFAULT VALUES RETURNING id")
    await AuditService(conn).log_action(
        user_id=admin["id"], action="trial_sync_triggered", target_type="trial_sync", target_id=str(log_id),
    )
    background_tasks.add_task(_run_sync_in_background, log_id)
    return {"sync_id": log_id, "status": "running"}


@router.get("/trials/sync/logs")
async def list_trial_sync_logs(
    conn=Depends(get_connection),
    admin: dict = Depends(admin_required),
):
    """The 20 most recent sync runs, newest first."""
    rows = await conn.fetch("SELECT * FROM trial_sync_logs ORDER BY sync_started_at DESC LIMIT 20")
    return [dict(r) for r in rows]
