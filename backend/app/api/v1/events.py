"""
Events & Webinars API Routes.

Routes MUST NOT interact with the database directly.
They validate input, call model functions, and return schema responses.
"""

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies.connections import get_connection
from app.api.middleware.auth_middleware import auth_middleware, auth_middleware_optional
from app.models.event_model import EventModel
from app.schemas.events import (
    EventDetailResponse,
    EventListResponse,
    EventStatus,
    EventType,
    RegistrationActionResponse,
    UserEventListResponse,
)

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


# ─── 2. Get Event Details (Public, optional auth for registration_status) ───

@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event_details(
    event_id: UUID,
    conn=Depends(get_connection),
    current_user: Optional[dict] = Depends(auth_middleware_optional),
):
    """Get full details for a single event. Public endpoint with optional auth."""
    model = EventModel(conn)
    user_id = current_user["id"] if current_user else None

    event = await model.get_event_details(str(event_id), user_id=user_id)
    if not event:
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
