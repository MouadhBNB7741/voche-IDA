"""
Notifications API — /api/v1/notifications

Endpoints:
  GET    /notifications                   — List notifications (paginated, filtered)
  PATCH  /notifications/{id}/read         — Mark single as read
  PATCH  /notifications/mark-all-read     — Mark all as read
  DELETE /notifications/{id}              — Delete notification
  GET    /notifications/preferences       — Get notification preferences
"""
import logging
from uuid import UUID
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.api.dependencies.connections import get_connection
from app.api.middleware.auth_middleware import auth_middleware
from app.services.notification_service import NotificationService
from app.services.system_service import SystemService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ── GET /notifications ──────────────────────────────────────────────────────

@router.get("")
async def get_notifications(
    read: Optional[bool] = Query(None, description="Filter by read status"),
    type: Optional[str] = Query(None, description="Filter by type: trial, community, event, system"),
    date_from: Optional[datetime] = Query(None, description="Filter: created after (ISO 8601)"),
    date_to: Optional[datetime] = Query(None, description="Filter: created before (ISO 8601)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection),
):
    """
    List notifications for the current user.
    Supports filtering by read/unread, type, and date range.
    Returns paginated results with unread count.
    Activity is logged automatically by the service.
    """
    service = NotificationService(conn)
    user_id = str(current_user["id"])

    result = await service.get_user_notifications(
        user_id,
        read_status=read,
        notif_type=type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        limit=limit,
    )

    return result


# ── PATCH /notifications/mark-all-read ──────────────────────────────────────
# NOTE: This route MUST be defined BEFORE /{id}/read
# to prevent FastAPI from matching "mark-all-read" as a UUID path param.

@router.patch("/mark-all-read")
async def mark_all_read(
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection),
):
    """Mark all unread notifications as read for the current user."""
    service = NotificationService(conn)
    user_id = str(current_user["id"])

    updated = await service.mark_all_read(user_id)

    return {
        "message": "All notifications marked as read",
        "updated_count": updated,
    }


# ── PATCH /notifications/{id}/read ─────────────────────────────

@router.patch("/{id}/read")
async def mark_notification_read(
    id: UUID,
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection),
):
    """
    Mark a single notification as read (ownership enforced).
    - Status 200: Success
    - Status 404: Not found or not owned by user
    - Status 401/403: Auth/RBAC errors handled by middleware
    """
    service = NotificationService(conn)
    user_id = str(current_user["id"])

    result = await service.mark_read(str(id), user_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found, already deleted, or access denied",
        )

    return result


# ── DELETE /notifications/{id} ─────────────────────────────────

@router.delete("/{id}", status_code=status.HTTP_200_OK)
async def delete_notification(
    id: UUID,
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection),
):
    """
    Delete a notification (ownership enforced).
    - Status 200: Success
    - Status 404: Not found or not owned by user
    """
    service = NotificationService(conn)
    user_id = str(current_user["id"])

    deleted = await service.delete_notification(str(id), user_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found, already deleted, or access denied",
        )

    return {
        "success": True,
        "message": "Notification deleted successfully"
    }
