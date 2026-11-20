"""
Events & Webinars API Routes.

Routes MUST NOT interact with the database directly.
They validate input, call model functions, and return schema responses.
"""

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.dependencies.connections import get_connection
from app.api.middleware.admin_middleware import admin_required
from app.api.middleware.auth_middleware import auth_middleware, auth_middleware_optional
from app.models.event_model import EventModel, can_view_event
from app.schemas.events import (
    EventDetailResponse,
    EventListResponse,
    EventStatus,
    EventSubmissionListResponse,
    EventSubmissionResponse,
    EventSuggestionRequest,
    EventType,
    PendingEventListResponse,
    RegistrationActionResponse,
    UserEventListResponse,
)
from app.schemas.resources import ApprovalDecisionRequest, ApprovalDecisionResponse
from app.services.approval_service import ApprovalError, decide_event

router = APIRouter(prefix="/events", tags=["Events"])


# ─── 1. List Events (Public, optional auth for registration_status) ─────────

@router.get("/", response_model=EventListResponse)
async def list_events(
    page: Optional[int] = Query(None, ge=1, description="Page number"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Items per page"),
    type: Optional[EventType] = Query(None, description="Filter by event type"),
    date_from: Optional[date] = Query(None, description="Filter events from this date"),
    date_to: Optional[date] = Query(None, description="Filter events up to this date"),
    location: Optional[str] = Query(None, description="Filter by location (partial match)"),
    organizer: Optional[str] = Query(None, description="Filter by organizer (partial match)"),
    status: Optional[EventStatus] = Query(None, description="Filter by event status"),
    conn=Depends(get_connection),
    current_user: Optional[dict] = Depends(auth_middleware_optional),
):
    """List all events with optional filters. Public endpoint with optional auth."""
    model = EventModel(conn)
    user_id = current_user["id"] if current_user else None

    result = await model.list_events(
        page=page,
        limit=limit,
        event_type=type.value if type else None,
        date_from=date_from,
        date_to=date_to,
        location=location,
        organizer=organizer,
        status=status.value if status else None,
        user_id=user_id,
    )
    return result


# ─── 1b. Suggest an event (Auth required) ────────────────────────────────────

@router.post("/", response_model=EventSubmissionResponse, status_code=http_status.HTTP_201_CREATED)
async def suggest_event(
    request: EventSuggestionRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Suggest an event. Members' suggestions wait for an admin's approval; admins' events go live directly."""
    is_admin = current_user.get("user_type") == "admin"
    return await EventModel(conn).create_event(
        created_by=current_user["id"],
        payload=request.model_dump(),
        approval_status="approved" if is_admin else "pending",
    )


@router.get("/my-suggestions", response_model=EventSubmissionListResponse)
async def my_suggestions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Events I suggested, with their approval status (and the reason if rejected)."""
    return await EventModel(conn).list_by_creator(current_user["id"], page=page, limit=limit)


@router.get("/pending", response_model=PendingEventListResponse)
async def pending_events(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    conn=Depends(get_connection),
    admin: dict = Depends(admin_required),
):
    """Suggested events waiting for approval, oldest first. Admin only."""
    return await EventModel(conn).list_pending(page=page, limit=limit)


@router.patch("/{event_id}/approval", response_model=ApprovalDecisionResponse)
async def decide_on_event(
    event_id: UUID,
    request: ApprovalDecisionRequest,
    conn=Depends(get_connection),
    admin: dict = Depends(admin_required),
):
    """Approve or reject a suggested event. The person who suggested it gets a notification and an email."""
    try:
        result = await decide_event(conn, str(event_id), admin, request.decision, request.reason)
    except ApprovalError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"success": False, "error": {"code": e.code, "message": e.message}},
        )
    return {"success": True, **result}


# ─── 2. Get Event Details (Public, optional auth for registration_status) ───

@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event_details(
    event_id: UUID,
    conn=Depends(get_connection),
    current_user: Optional[dict] = Depends(auth_middleware_optional),
):
    """Get full details for a single event. Public for approved events; a pending one
    only shows to the person who suggested it and to admins."""
    model = EventModel(conn)
    user_id = current_user["id"] if current_user else None

    event = await model.get_event_details(str(event_id), user_id=user_id)
    if not event or not can_view_event(event, current_user):
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Event not found",
                },
            },
        )
    return event


# ─── 3. Register for Event (Auth required) ──────────────────────────────────

@router.post("/{event_id}/register", response_model=RegistrationActionResponse)
async def register_for_event(
    event_id: UUID,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Register the authenticated user for an event."""
    model = EventModel(conn)
    try:
        result = await model.register_for_event(
            event_id=str(event_id),
            user_id=current_user["id"],
        )
        return result
    except ValueError as e:
        error_msg = str(e)
        # Map specific errors to appropriate HTTP status codes
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        elif "already registered" in error_msg.lower():
            raise HTTPException(status_code=409, detail=error_msg)
        elif "full" in error_msg.lower():
            raise HTTPException(status_code=409, detail=error_msg)
        elif "deadline" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        elif "cancelled" in error_msg.lower() or "completed" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)


# ─── 4. Cancel Registration (Auth required) ─────────────────────────────────

@router.delete("/{event_id}/register", response_model=RegistrationActionResponse)
async def cancel_registration(
    event_id: UUID,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Cancel the authenticated user's registration for an event."""
    model = EventModel(conn)
    try:
        result = await model.cancel_registration(
            event_id=str(event_id),
            user_id=current_user["id"],
        )
        return result
    except ValueError as e:
        error_msg = str(e)
        if "no registration" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        elif "already cancelled" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)


# ─── 5. My Events (Auth required, mounted under /users) ─────────────────────

user_events_router = APIRouter(prefix="/users", tags=["Events"])


@user_events_router.get("/me/events", response_model=UserEventListResponse)
async def get_my_events(
    page: Optional[int] = Query(None, ge=1, description="Page number"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Items per page"),
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Get all events the authenticated user is registered for."""
    model = EventModel(conn)
    result = await model.get_user_events(
        user_id=current_user["id"],
        page=page,
        limit=limit,
    )
    return result
