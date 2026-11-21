"""
Notifications API — /api/v1/notifications

Endpoints:
  GET    /notifications                   — List notifications (paginated, filtered)
  PATCH  /notifications/{id}/read         — Mark single as read
  PATCH  /notifications/mark-all-read     — Mark all as read
  DELETE /notifications/{id}              — Delete notification
  GET    /notifications/preferences       — Get notification preferences
  WS     /notifications/ws                — Live notifications
"""
import asyncio
import json
import logging
import time
from uuid import UUID
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, status
from app.api.dependencies.connections import get_connection
from app.api.middleware.auth_middleware import auth_middleware, user_for_token
from app.core.security import decode_jwt
from app.db.postgres import PostgresDB
from app.services.connection_manager import manager
from app.services.notification_service import NotificationService
from app.services.system_service import SystemService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ── WS /notifications/ws ────────────────────────────────────────────────────

AUTH_TIMEOUT_SECONDS = 10
# The browser pings every 25 seconds: a socket silent for this long is gone
IDLE_TIMEOUT_SECONDS = 75
MAX_SOCKETS_PER_USER = 10

CLOSE_IDLE = 4000
CLOSE_UNAUTHORIZED = 4401
CLOSE_SUSPENDED = 4403
CLOSE_TOO_MANY = 4429


@router.websocket("/ws")
async def notifications_socket(websocket: WebSocket):
    """
    Live notifications for the logged-in user.

    After connecting, the browser sends {"type": "auth", "token": "<login token>"} as its
    first message, within 10 seconds. The token is not put in the URL, because URLs end up
    in server and proxy logs. Clients that can set headers may send
    "Authorization: Bearer <token>" instead.

    Messages from the server:
      {"type": "ready"}                                 login accepted
      {"type": "notification", "notification": {...}}   a new notification (same fields as GET /notifications)
      {"type": "pong"}                                  answer to {"type": "ping"}

    Close codes: 4401 login missing, invalid or expired (reconnect with a new token),
    4403 account suspended, 4429 too many open tabs, 4000 no ping for 75 seconds.
    """
    await websocket.accept()

    token = _bearer_token(websocket.headers.get("authorization")) or await _first_message_token(websocket)
    user = await _socket_user(token) if token else None
    if not user:
        await _close(websocket, CLOSE_UNAUTHORIZED, "Login required")
        return
    if user["status"] == "suspended":
        await _close(websocket, CLOSE_SUSPENDED, "Account suspended")
        return
    if not user["is_active"] or user["status"] != "active":
        await _close(websocket, CLOSE_UNAUTHORIZED, "Login required")
        return

    user_id = str(user["id"])
    if manager.connection_count(user_id) >= MAX_SOCKETS_PER_USER:
        await _close(websocket, CLOSE_TOO_MANY, "Too many open connections")
        return

    expires_at = _token_expiry(token)
    manager.connect(user_id, websocket)
    try:
        await manager.send(websocket, {"type": "ready"})
        while True:
            remaining = expires_at - time.time()
            if remaining <= 0:
                await _close(websocket, CLOSE_UNAUTHORIZED, "Session expired")
                break
            # Wait for the next message, but no longer than the login is valid. Which limit was
            # used decides the close reason: re-reading the clock can land a few ms early.
            waiting_for_expiry = remaining <= IDLE_TIMEOUT_SECONDS
            try:
                message = await asyncio.wait_for(websocket.receive(), timeout=min(IDLE_TIMEOUT_SECONDS, remaining))
            except asyncio.TimeoutError:
                if waiting_for_expiry:
                    await _close(websocket, CLOSE_UNAUTHORIZED, "Session expired")
                else:
                    await _close(websocket, CLOSE_IDLE, "No ping received")
                break
            if message["type"] == "websocket.disconnect":
                break
            if _message_type(message.get("text")) == "ping":
                await manager.send(websocket, {"type": "pong"})
    except Exception as e:  # noqa: BLE001
        logger.debug(f"Notifications socket for user {user_id} ended: {e}")
    finally:
        manager.disconnect(user_id, websocket)


def _bearer_token(header: Optional[str]) -> Optional[str]:
    if header and header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return None


def _message_type(text: Optional[str]) -> Optional[str]:
    try:
        data = json.loads(text or "")
    except ValueError:
        return None
    return data.get("type") if isinstance(data, dict) else None


async def _first_message_token(websocket: WebSocket) -> Optional[str]:
    try:
        message = await asyncio.wait_for(websocket.receive(), timeout=AUTH_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        return None
    if message.get("type") != "websocket.receive" or _message_type(message.get("text")) != "auth":
        return None
    token = json.loads(message["text"]).get("token")
    return token if isinstance(token, str) and token else None


async def _socket_user(token: str) -> Optional[dict]:
    # Borrow a database connection only for the login check, not for the life of the socket
    async with PostgresDB.get_pool().acquire() as conn:
        return await user_for_token(token, conn)


def _token_expiry(token: str) -> float:
    try:
        return float(decode_jwt(token).get("exp") or 0) or time.time() + 3600
    except Exception:
        return time.time()


async def _close(websocket: WebSocket, code: int, reason: str) -> None:
    try:
        await websocket.close(code=code, reason=reason)
    except Exception:
        pass  # the browser already left


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
