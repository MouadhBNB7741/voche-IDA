"""
System API — /api/v1/system + /health

Endpoints:
  POST   /system/feedback    — Submit user feedback (auth required)
  GET    /system/metadata    — Platform enums/metadata (public)
  GET    /system/status      — System monitoring (internal)
  GET    /health             — Health check (public, registered at root level)
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, Request, HTTPException

from app.api.dependencies.connections import get_connection
from app.api.middleware.auth_middleware import auth_middleware, auth_middleware_optional
from app.services.system_service import SystemService
from app.schemas.system import FeedbackRequest

logger = logging.getLogger(__name__)

# Main system router
router = APIRouter(prefix="/system", tags=["System"])

# Separate health router (no prefix — mounted at /api/v1 level in main.py)
health_router = APIRouter(tags=["Health"])


# ── POST /system/feedback ───────────────────────────────────────────────────

@router.post("/feedback")
async def submit_feedback(
    data: FeedbackRequest,
    request: Request,
    current_user: Optional[dict] = Depends(auth_middleware_optional),
    conn=Depends(get_connection),
):
    """
    Submit platform feedback. Auth optional.
    Returns a ticket ID for reference.
    """
    service = SystemService(conn)

    # Extract client info for logging
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    user_id = str(current_user["id"]) if current_user else None

    result = await service.submit_feedback(
        user_id=user_id,
        category=data.category,
        message=data.message,
        rating=data.rating,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return {
        "success": True,
        **result
    }


from app.api.middleware.org_admin_middleware import require_org_admin, require_working_group_admin
from app.schemas.system import FeedbackRequest, AnnouncementRequest


# ── POST /system/announce ───────────────────────────────────────────────────

@router.post("/announce")
async def send_announcement(
    data: AnnouncementRequest,
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection),
):
    """
    Broadcast a system announcement across three possible scopes.
    - Global: Platform Admin only
    - Org: Org Admin or Platform Admin
    - Group: Org Admin (of parent org) or Platform Admin
    """
    service = SystemService(conn)

    # 1. Authorization Logic based on Scope
    if data.group_id:
        # Authorization check for working group
        await require_working_group_admin(data.group_id, current_user, conn)
    elif data.org_id:
        # Authorization check for organization
        await require_org_admin(data.org_id, current_user, conn)
    else:
        # Global requires Platform Admin
        if current_user.get("user_type") != "admin":
            raise HTTPException(
                status_code=403, 
                detail="Global announcements require platform administrator privileges."
            )

    # 2. Execution
    result = await service.send_announcement(
        title=data.title,
        message=data.message,
        link=data.link,
        org_id=data.org_id,
        group_id=data.group_id,
    )

    return {
        "success": True,
        **result
    }


# ── GET /system/metadata ────────────────────────────────────────────────────

# Cache the metadata since it's static
_metadata_cache = None


@router.get("/metadata")
async def get_metadata():
    """
    Return platform enums and metadata for frontend dropdowns.
    Public endpoint — no authentication required.
    Cached in-memory since data is static.
    """
    global _metadata_cache
    if _metadata_cache is None:
        _metadata_cache = SystemService.get_metadata()
    return _metadata_cache


# ── GET /system/status ──────────────────────────────────────────────────────

@router.get("/status")
async def system_status(
    conn=Depends(get_connection),
):
    """
    System monitoring endpoint.
    Returns uptime, DB status, and feature flags.
    """
    service = SystemService(conn)
    return await service.system_status()


# ── GET /health ─────────────────────────────────────────────────────────────

@health_router.get("/health", tags=["Health"])
async def health_check(
    conn=Depends(get_connection),
):
    """
    Public health check endpoint.
    Returns API status, version, and database connectivity.
    """
    service = SystemService(conn)
    return await service.health_check()
