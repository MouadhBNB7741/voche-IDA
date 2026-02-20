from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies.connections import get_connection
from app.api.middleware.auth_middleware import auth_middleware
from app.models.community_model import CommunityModel
from app.schemas.community import (
    CommunityListResponse,
    CommunityResponse,
    CommentResponse,
    CreateCommentRequest,
    CreatePostRequest,
    EditCommentRequest,
    EditPostRequest,
    PostDetailsWithReplies,
    PostListResponse,
    ReportContentRequest,
    ReportResponse,
    ReportListResponse,
    ResolveReportRequest,
    CommunitySortOption,
    PostSortOption,
)

router = APIRouter(prefix="/community", tags=["Community"])


# Helper to check admin
def _is_admin(user: dict) -> bool:
    return user.get("user_type") == "admin"


# ======================================================================
# COMMUNITIES (public)
# ======================================================================

# ----------------------------------------------------------------------
# 1. LIST COMMUNITIES
# ----------------------------------------------------------------------
@router.get("/", response_model=CommunityListResponse)
async def list_communities(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(None, description="Filter by community type"),
    sort: CommunitySortOption = Query(
        CommunitySortOption.most_members, description="Sort communities"
    ),
    conn=Depends(get_connection),
):
    """List all active communities. Public endpoint."""
    model = CommunityModel(conn)
    result = await model.list_active_communities(
        page=page,
        limit=limit,
        community_type=type,
        sort=sort.value,
    )
    return result





# ======================================================================
# ADMIN REPORTS (global, no community scope)
# ======================================================================
# NOTE: Admin routes are defined BEFORE /{community_id}/... routes
# to prevent FastAPI from trying to match "admin" as a UUID.

# ----------------------------------------------------------------------
# 10. ADMIN: LIST REPORTS
# ----------------------------------------------------------------------
@router.get("/admin/reports", response_model=ReportListResponse)
async def list_reports(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    report_status: Optional[str] = Query(None, description="Filter: pending, reviewed, resolved"),
    community_id: Optional[UUID] = Query(None, description="Filter by community"),
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """List all reports across communities. Admin only."""
    if current_user.get("user_type") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    model = CommunityModel(conn)
    result = await model.list_reports(page=page, limit=limit, status=report_status)
    return result


# ----------------------------------------------------------------------
# 11. ADMIN: RESOLVE REPORT
# ----------------------------------------------------------------------
@router.patch("/admin/reports/{report_id}")
async def resolve_report(
    report_id: UUID,
    request: ResolveReportRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Resolve/review a report. Admin only."""
    if current_user.get("user_type") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    model = CommunityModel(conn)
    try:
        result = await model.resolve_report(
            report_id=str(report_id),
            moderator_id=current_user["id"],
            status=request.status,
            action_taken=request.action_taken,
            resolution_notes=request.resolution_notes,
        )
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {"code": "NOT_FOUND", "message": str(e)},
            },
        )


# ----------------------------------------------------------------------
# 12. ADMIN: DELETE REPORT
# ----------------------------------------------------------------------
@router.delete("/admin/reports/{report_id}")
async def delete_report(
    report_id: UUID,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Delete a report. Admin only."""
    if current_user.get("user_type") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    model = CommunityModel(conn)
    try:
        await model.delete_report(str(report_id))
        return {"success": True, "message": "Report deleted"}
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {"code": "NOT_FOUND", "message": str(e)},
            },
        )


# ======================================================================
# GLOBAL FEED
# ======================================================================

# ----------------------------------------------------------------------
# 2. GLOBAL FEED (cross-community)
# ----------------------------------------------------------------------
@router.get("/feed", response_model=PostListResponse)
async def global_feed(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, description="Community name or ID"),
    sort: PostSortOption = Query(PostSortOption.recent, description="Sort posts"),
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Global post feed across all communities. Auth required."""
    model = CommunityModel(conn)
    result = await model.list_forum_posts(
        user_id=current_user["id"],
        page=page,
        limit=limit,
        category=category,
        sort=sort.value,
    )
    return result


# ----------------------------------------------------------------------
# 1b. GET SINGLE COMMUNITY
# ----------------------------------------------------------------------
@router.get("/{community_id}", response_model=CommunityResponse)
async def get_community(
    community_id: UUID,
    conn=Depends(get_connection),
):
    """Get a single community by ID. Public endpoint."""
    model = CommunityModel(conn)
    community = await model.get_community_by_id(str(community_id))
    if not community:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Community not found",
                },
            },
        )
    return community


# ======================================================================
# COMMUNITY-SCOPED RESOURCES — /{community_id}/...
# ======================================================================

# ----------------------------------------------------------------------
# 3. LIST POSTS IN COMMUNITY
# ----------------------------------------------------------------------
@router.get("/{community_id}/posts", response_model=PostListResponse)
async def list_community_posts(
    community_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort: PostSortOption = Query(PostSortOption.recent, description="Sort posts"),
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """List posts for a specific community. Auth required."""
    model = CommunityModel(conn)
    result = await model.list_forum_posts(
        user_id=current_user["id"],
        page=page,
        limit=limit,
        category=str(community_id),
        sort=sort.value,
    )
    return result


# ----------------------------------------------------------------------
# 4. CREATE POST IN COMMUNITY
# ----------------------------------------------------------------------
@router.post("/{community_id}/posts", status_code=status.HTTP_201_CREATED)
async def create_post(
    community_id: UUID,
    request: CreatePostRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Create a new forum post in a community. Auth required."""
    model = CommunityModel(conn)
    try:
        payload = request.model_dump()
        payload["community_id"] = community_id
        post = await model.create_post(
            user_id=current_user["id"],
            payload=payload,
        )
        return {"success": True, "data": post}
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": str(e),
                },
            },
        )


# ----------------------------------------------------------------------
# 5. GET POST DETAILS
# ----------------------------------------------------------------------
@router.get("/{community_id}/posts/{post_id}", response_model=PostDetailsWithReplies)
async def get_post(
    community_id: UUID,
    post_id: UUID,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Get post details with replies. Auth required."""
    model = CommunityModel(conn)

    post = await model.get_post_details(str(post_id))
    if not post:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Post not found",
                },
            },
        )

    # Increment views
    await model.increment_post_views(str(post_id))

    comments = await model.get_post_comments(str(post_id))

    return {"post": post, "replies": comments}


# ----------------------------------------------------------------------
# 6. EDIT POST
# ----------------------------------------------------------------------
@router.patch("/{community_id}/posts/{post_id}")
async def edit_post(
    community_id: UUID,
    post_id: UUID,
    request: EditPostRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Edit a post. Only author or admin. Auth required."""
    model = CommunityModel(conn)
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "No updates provided",
                },
            },
        )
    try:
        post = await model.edit_post(
            post_id=str(post_id),
            user_id=current_user["id"],
            payload=updates,
            is_admin=_is_admin(current_user),
        )
        if not post:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": {"code": "NOT_FOUND", "message": "Post not found"},
                },
            )
        return {"success": True, "data": post}
    except PermissionError as e:
        raise HTTPException(
            status_code=403,
            detail={
                "success": False,
                "error": {"code": "FORBIDDEN", "message": str(e)},
            },
        )


# ----------------------------------------------------------------------
# 7. DELETE POST
# ----------------------------------------------------------------------
@router.delete("/{community_id}/posts/{post_id}", status_code=status.HTTP_200_OK)
async def delete_post(
    community_id: UUID,
    post_id: UUID,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Soft delete a post. Only author or admin. Auth required."""
    model = CommunityModel(conn)
    try:
        deleted = await model.soft_delete_post(
            post_id=str(post_id),
            user_id=current_user["id"],
            is_admin=_is_admin(current_user),
        )
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": {"code": "NOT_FOUND", "message": "Post not found"},
                },
            )
        return {"success": True, "message": "Post deleted"}
    except PermissionError as e:
        raise HTTPException(
            status_code=403,
            detail={
                "success": False,
                "error": {"code": "FORBIDDEN", "message": str(e)},
            },
        )


# ----------------------------------------------------------------------
# 8a. REPLY TO POST
# ----------------------------------------------------------------------
@router.post(
    "/{community_id}/posts/{post_id}/replies",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def reply_to_post(
    community_id: UUID,
    post_id: UUID,
    request: CreateCommentRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Reply to a post. Auth required."""
    model = CommunityModel(conn)
    try:
        comment = await model.create_comment(
            post_id=str(post_id),
            user_id=current_user["id"],
            content=request.content,
            parent_comment_id=str(request.parent_comment_id)
            if request.parent_comment_id
            else None,
        )
        return comment
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {"code": "INVALID_REQUEST", "message": str(e)},
            },
        )


# ----------------------------------------------------------------------
# 8b. EDIT REPLY
# ----------------------------------------------------------------------
@router.patch("/{community_id}/replies/{comment_id}", response_model=CommentResponse)
async def edit_reply(
    community_id: UUID,
    comment_id: UUID,
    request: EditCommentRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Edit a reply/comment. Only author or admin. Auth required."""
    model = CommunityModel(conn)
    try:
        comment = await model.edit_comment(
            comment_id=str(comment_id),
            user_id=current_user["id"],
            content=request.content,
            is_admin=_is_admin(current_user),
        )
        if not comment:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": {"code": "NOT_FOUND", "message": "Comment not found"},
                },
            )
        return comment
    except PermissionError as e:
        raise HTTPException(
            status_code=403,
            detail={
                "success": False,
                "error": {"code": "FORBIDDEN", "message": str(e)},
            },
        )


# ----------------------------------------------------------------------
# 8c. DELETE REPLY
# ----------------------------------------------------------------------
@router.delete("/{community_id}/replies/{comment_id}", status_code=status.HTTP_200_OK)
async def delete_reply(
    community_id: UUID,
    comment_id: UUID,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Soft delete a reply/comment. Only author or admin. Auth required."""
    model = CommunityModel(conn)
    try:
        deleted = await model.soft_delete_comment(
            comment_id=str(comment_id),
            user_id=current_user["id"],
            is_admin=_is_admin(current_user),
        )
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": {"code": "NOT_FOUND", "message": "Comment not found"},
                },
            )
        return {"success": True, "message": "Comment deleted"}
    except PermissionError as e:
        raise HTTPException(
            status_code=403,
            detail={
                "success": False,
                "error": {"code": "FORBIDDEN", "message": str(e)},
            },
        )


# ----------------------------------------------------------------------
# 9a. LIKE POST
# ----------------------------------------------------------------------
@router.post("/{community_id}/posts/{post_id}/like")
async def like_post(
    community_id: UUID,
    post_id: UUID,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Like a post. Auth required."""
    model = CommunityModel(conn)
    try:
        result = await model.like_post(str(post_id), current_user["id"])
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {"code": "NOT_FOUND", "message": str(e)},
            },
        )


# ----------------------------------------------------------------------
# 9b. LIKE REPLY
# ----------------------------------------------------------------------
@router.post("/{community_id}/replies/{comment_id}/like")
async def like_reply(
    community_id: UUID,
    comment_id: UUID,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Like a reply/comment. Auth required."""
    model = CommunityModel(conn)
    try:
        result = await model.like_comment(str(comment_id), current_user["id"])
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {"code": "NOT_FOUND", "message": str(e)},
            },
        )


# ----------------------------------------------------------------------
# 9c. REPORT CONTENT
# ----------------------------------------------------------------------
@router.post(
    "/{community_id}/report",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def report_content(
    community_id: UUID,
    request: ReportContentRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Report content within a community. Auth required."""
    model = CommunityModel(conn)
    try:
        report = await model.create_content_report(
            reporter_id=current_user["id"],
            payload=request.model_dump(),
        )
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "success": False,
                "error": {"code": "CONFLICT", "message": str(e)},
            },
        )
