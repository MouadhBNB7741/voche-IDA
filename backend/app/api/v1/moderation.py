"""
Moderation queue and decisions. Admins only (Phase 2 has no separate moderator role).

Users submit reports with POST /api/v1/community/{community_id}/report.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies.connections import get_connection
from app.api.middleware.auth_middleware import auth_middleware
from app.schemas.moderation import (
    DecideRequest,
    DecideResponse,
    QueueResponse,
    QueueStatus,
    ReportPriority,
)
from app.schemas.community import ReportTargetType
from app.services.moderation_service import ModerationError, ModerationService

router = APIRouter(prefix="/moderation", tags=["Moderation"])


def _require_admin(current_user: dict = Depends(auth_middleware)) -> dict:
    if current_user.get("user_type") != "admin":
        raise HTTPException(
            status_code=403,
            detail={
                "success": False,
                "error": {"code": "FORBIDDEN", "message": "Admin access required"},
            },
        )
    return current_user


@router.get("/queue", response_model=QueueResponse)
async def moderation_queue(
    status: QueueStatus = Query(QueueStatus.open, description="open (default), closed, or one report status"),
    target_type: Optional[ReportTargetType] = Query(None),
    priority: Optional[ReportPriority] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    conn=Depends(get_connection),
    current_user: dict = Depends(_require_admin),
):
    """Reports to review, most urgent first, with the reported content and its author's history."""
    return await ModerationService(conn).queue(
        status=status.value,
        target_type=target_type.value if target_type else None,
        priority=priority.value if priority else None,
        page=page,
        limit=limit,
    )


@router.post("/reports/{report_id}/decide", response_model=DecideResponse)
async def decide_report(
    report_id: UUID,
    request: DecideRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(_require_admin),
):
    """Approve, hide or delete the reported content, or warn, suspend or ban its author.

    Closes every open report on the same content, records the decision and notifies the author.
    """
    try:
        result = await ModerationService(conn).decide(
            report_id=str(report_id),
            moderator=current_user,
            action=request.action.value,
            reason=request.reason,
            duration_hours=request.duration_hours,
            remove_content=request.remove_content,
        )
    except ModerationError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"success": False, "error": {"code": e.code, "message": e.message}},
        )
    return {"success": True, "data": result}
