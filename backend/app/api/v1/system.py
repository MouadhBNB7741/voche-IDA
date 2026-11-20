"""
System API — /api/v1/system + /health

Endpoints:
  POST   /system/feedback    — Submit user feedback (auth required)
  GET    /system/metadata    — Platform enums/metadata (public)
  GET    /system/status      — System monitoring (internal)
  GET    /system/admin/overview — Health, review queues and platform figures (admins)
  GET    /system/audit-logs  — Admin decisions, most recent first (admins)
  GET    /health             — Health check (public, registered at root level)
"""
import logging
from typing import Literal, Optional, List
from fastapi import APIRouter, Depends, Query, Request, HTTPException

from app.api.dependencies.connections import get_connection
from app.api.middleware.admin_middleware import admin_required
from app.api.middleware.auth_middleware import auth_middleware, auth_middleware_optional
from app.services.admin_service import admin_overview, list_audit_logs
from app.services.system_service import SystemService
from app.schemas.system import FeedbackRequest
from app.db.redis import get_redis_client

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
    user_id = str(current_user["id"]) if current_user else None
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    redis = None
    try:
        redis = await get_redis_client()
    except Exception as e:
        logger.warning(f"Redis not available for feedback check: {e}")

    if redis:
        # Check by user ID first
        if user_id:
            lock_key = f"feedback_lock:{user_id}"
            if await redis.get(lock_key):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error": {
                            "code": "COOLDOWN_ACTIVE",
                            "message": "You have already submitted feedback in the last 24 hours.",
                        },
                    },
                )
        # Check by IP
        if ip_address:
            ip_key = f"feedback_lock:ip:{ip_address}"
            if await redis.get(ip_key):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "success": False,
                        "error": {
                            "code": "COOLDOWN_ACTIVE",
                            "message": "Feedback submission is temporarily locked from this IP address.",
                        },
                    },
                )

    service = SystemService(conn)
    result = await service.submit_feedback(
        user_id=user_id,
        category=data.category,
        message=data.message,
        rating=data.rating,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Set lock in Redis (24 hours = 86400 seconds)
    if redis:
        try:
            twenty_four_hours = 24 * 60 * 60
            if user_id:
                await redis.setex(f"feedback_lock:{user_id}", twenty_four_hours, "1")
            if ip_address:
                await redis.setex(f"feedback_lock:ip:{ip_address}", twenty_four_hours, "1")
        except Exception as e:
            logger.warning(f"Failed to set lock in Redis: {e}")

    return {
        "success": True,
        **result
    }


@router.get("/feedback/lock")
async def check_feedback_lock(
    request: Request,
    current_user: Optional[dict] = Depends(auth_middleware_optional),
):
    """
    Check if the feedback submission is locked for 24 hours via Redis.
    """
    user_id = str(current_user["id"]) if current_user else None
    ip_address = request.client.host if request.client else None

    redis = None
    try:
        redis = await get_redis_client()
    except Exception as e:
        return {"locked": False, "ttl": 0}

    if redis:
        if user_id:
            ttl = await redis.ttl(f"feedback_lock:{user_id}")
            if ttl > 0:
                return {"locked": True, "ttl": ttl}
        if ip_address:
            ttl = await redis.ttl(f"feedback_lock:ip:{ip_address}")
            if ttl > 0:
                return {"locked": True, "ttl": ttl}

    return {"locked": False, "ttl": 0}


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


# ── Admin portal ────────────────────────────────────────────────────────────

@router.get("/admin/overview")
async def get_admin_overview(
    conn=Depends(get_connection),
    current_user: dict = Depends(admin_required),
):
    """Platform health, what waits for review, and a few platform figures (admins only)."""
    return await admin_overview(conn)


@router.get("/audit-logs")
async def get_audit_logs(
    category: Optional[Literal["moderation", "verification", "resource", "event"]] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    conn=Depends(get_connection),
    current_user: dict = Depends(admin_required),
):
    """Admin decisions (moderation, licences, resources, events), most recent first (admins only)."""
    return await list_audit_logs(conn, category, page, limit)


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
