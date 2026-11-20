from typing import List, Optional
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status

from app.api.dependencies.connections import get_connection
from app.api.middleware.admin_middleware import admin_required
from app.api.middleware.auth_middleware import auth_middleware, auth_middleware_optional
from app.models.resource_model import ResourceModel, can_view_resource
from app.schemas.resources import (
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    PendingResourceListResponse,
    ResourceListResponse,
    ResourceDetailsResponse,
    ResourceSubmissionListResponse,
    ResourceSubmissionResponse,
    SubmissionAccessResponse,
    CreateRatingRequest,
    ProgressUpdateRequest,
    ProgressResponse,
    ResourceSortOption,
    ResourceType,
    ResourceRatingResponse
)
from app.services.approval_service import (
    ApprovalError,
    decide_resource,
    delete_resource_file,
    read_resource_file,
    resource_submission_access,
    store_resource_file,
    submitter_organization,
    tell_admins_resource_submitted,
)

router = APIRouter(prefix="/resources", tags=["Resources"])

_NOT_FOUND = {
    "success": False,
    "error": {"code": "NOT_FOUND", "message": "Resource not found"},
}


@router.get("/", response_model=ResourceListResponse)
async def list_resources(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[ResourceType] = Query(None, description="Filter by resource type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    language: Optional[str] = Query(None, description="Filter by language"),
    featured: Optional[bool] = Query(None, description="Filter by featured status"),
    search: Optional[str] = Query(None, description="Search resources by title, topic, or description"),
    sort: ResourceSortOption = Query(
        ResourceSortOption.newest, description="Sort resources"
    ),
    conn=Depends(get_connection),
):
    """List approved resources with optional filters. Public endpoint."""
    model = ResourceModel(conn)
    result = await model.list_resources(
        page=page,
        limit=limit,
        resource_type=type.value if type else None,
        category=category,
        language=language,
        featured=featured,
        search=search,
        sort=sort.value,
    )
    return result


# ======================================================================
# Submissions (these fixed paths come before /{resource_id})
# ======================================================================
@router.get("/can-submit", response_model=SubmissionAccessResponse)
async def can_submit(
    conn=Depends(get_connection),
    current_user: Optional[dict] = Depends(auth_middleware_optional),
):
    """Whether the current user may share resources, and if not, why."""
    allowed, reason = await resource_submission_access(conn, current_user)
    return {"can_submit": allowed, "reason": reason}


@router.post("/submit", response_model=ResourceSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_resource(
    title: str = Form(..., min_length=5, max_length=500),
    description: str = Form(..., min_length=20, max_length=5000),
    type: ResourceType = Form(...),
    category: str = Form(..., min_length=2, max_length=100),
    language: str = Form("en", min_length=2, max_length=10),
    url: Optional[str] = Form(None, max_length=500, description="A link, e.g. YouTube or Vimeo for long videos"),
    author: Optional[str] = Form(None, max_length=255),
    duration: Optional[str] = Form(None, max_length=50),
    tags: Optional[str] = Form(None, max_length=500, description="Comma-separated"),
    requires_auth: bool = Form(False),
    file: Optional[UploadFile] = File(None, description="PDF (5 MB) or MP4/WebM video (20 MB)"),
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Share an educational resource: a file, a link, or both.

    Verified HCPs and approved organization members wait for an admin's approval;
    admins' resources are published straight away.
    """
    allowed, reason = await resource_submission_access(conn, current_user)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    link = (url or "").strip() or None
    if link and not link.lower().startswith(("https://", "http://")):
        raise HTTPException(status_code=422, detail="The link must start with https://")
    has_file = file is not None and bool(file.filename)
    if not has_file and not link:
        raise HTTPException(status_code=422, detail="Add a file or a link.")

    payload = {
        "title": title.strip(),
        "description": description.strip(),
        "type": type.value,
        "category": category.strip(),
        "language": language.strip().lower(),
        "url": link,
        "author": (author or "").strip() or await conn.fetchval(
            "SELECT COALESCE(display_name, TRIM(CONCAT(first_name, ' ', last_name))) FROM users WHERE id = $1",
            current_user["id"],
        ),
        "duration": (duration or "").strip() or None,
        "tags": _parse_tags(tags),
        "requires_auth": requires_auth,
    }
    if len(payload["title"]) < 5 or len(payload["description"]) < 20:
        raise HTTPException(status_code=422, detail="Add a title (5+ characters) and a description (20+ characters).")

    file_info = await store_resource_file(file, type.value) if has_file else None
    is_admin = current_user.get("user_type") == "admin"
    try:
        resource = await ResourceModel(conn).create_submission(
            submitted_by=current_user["id"],
            payload=payload,
            approval_status="approved" if is_admin else "pending",
            organization_id=await submitter_organization(conn, current_user["id"]),
            file_info=file_info,
        )
    except Exception:
        await delete_resource_file((file_info or {}).get("file_key"))
        raise
    if resource["approval_status"] == "pending":
        await tell_admins_resource_submitted(conn, resource)
    return resource


@router.get("/mine", response_model=ResourceSubmissionListResponse)
async def my_submissions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Resources I submitted, with their approval status (and the reason if rejected)."""
    return await ResourceModel(conn).list_by_submitter(current_user["id"], page=page, limit=limit)


@router.get("/pending", response_model=PendingResourceListResponse)
async def pending_resources(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    conn=Depends(get_connection),
    admin: dict = Depends(admin_required),
):
    """Resources waiting for approval, oldest first. Admin only."""
    return await ResourceModel(conn).list_pending(page=page, limit=limit)


# ======================================================================
# A single resource
# ======================================================================
@router.get("/{resource_id}", response_model=ResourceDetailsResponse)
async def get_resource(
    resource_id: UUID,
    conn=Depends(get_connection),
    current_user: Optional[dict] = Depends(auth_middleware_optional),
):
    """A resource with ratings, reviews and related resources.

    Public for approved resources; pending or rejected ones only show to their submitter and admins.
    """
    resource = await ResourceModel(conn).get_resource_details(str(resource_id), viewer=current_user)
    if not resource:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    return resource


@router.get("/{resource_id}/download")
async def download_resource(
    resource_id: UUID,
    conn=Depends(get_connection),
    current_user: Optional[dict] = Depends(auth_middleware_optional),
):
    """Where to get the resource: its uploaded file, or its link. Counts the download."""
    model = ResourceModel(conn)
    info = await model.get_file_info(str(resource_id))
    if not info or not can_view_resource(info, current_user):
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    if info["requires_auth"] and not current_user:
        raise HTTPException(status_code=401, detail="Authentication required to download this resource")

    if info["approval_status"] == "approved":
        await model.count_download(str(resource_id))

    if info["file_key"]:
        return {
            "success": True,
            "has_file": True,
            "download_url": f"/api/v1/resources/{resource_id}/file",
            "file_name": info["file_name"],
            "file_type": info["file_type"],
        }
    return {"success": True, "has_file": False, "download_url": info["url"]}


@router.get("/{resource_id}/file")
async def get_resource_file(
    resource_id: UUID,
    conn=Depends(get_connection),
    current_user: Optional[dict] = Depends(auth_middleware_optional),
):
    """The uploaded file itself. Same rules as the resource: public once approved."""
    info = await ResourceModel(conn).get_file_info(str(resource_id))
    if not info or not info["file_key"] or not can_view_resource(info, current_user):
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    if info["requires_auth"] and not current_user:
        raise HTTPException(status_code=401, detail="Authentication required to download this resource")

    data = await read_resource_file(info["file_key"])
    if data is None:
        raise HTTPException(status_code=404, detail=_NOT_FOUND)
    name = info["file_name"] or f"resource-{resource_id}"
    ascii_name = name.encode("ascii", "ignore").decode().replace('"', "") or "resource"
    return Response(
        content=data,
        media_type=info["file_type"] or "application/octet-stream",
        headers={
            "Content-Disposition": f"inline; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name)}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=300",
        },
    )


@router.patch("/{resource_id}/approval", response_model=ApprovalDecisionResponse)
async def decide_on_resource(
    resource_id: UUID,
    request: ApprovalDecisionRequest,
    conn=Depends(get_connection),
    admin: dict = Depends(admin_required),
):
    """Approve or reject a pending resource. The submitter gets a notification and an email. Admin only."""
    try:
        result = await decide_resource(conn, str(resource_id), admin, request.decision, request.reason)
    except ApprovalError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={"success": False, "error": {"code": e.code, "message": e.message}},
        )
    return {"success": True, **result}


@router.post("/{resource_id}/rating", status_code=status.HTTP_201_CREATED)
async def create_rating(
    resource_id: UUID,
    request: CreateRatingRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Rate a resource. Auth required."""
    model = ResourceModel(conn)
    try:
        payload = request.model_dump()
        result = await model.create_or_update_rating(
            resource_id=str(resource_id),
            user_id=current_user["id"],
            payload=payload,
        )
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(
            status_code=404,  # Return 404 for resource not found, could be 400 depending on exact issue
            detail={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": str(e),
                },
            },
        )


@router.patch("/{resource_id}/progress", response_model=ProgressResponse)
async def update_progress(
    resource_id: UUID,
    request: ProgressUpdateRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware),
):
    """Update progress for a resource (e.g., video or course). Auth required."""
    model = ResourceModel(conn)
    try:
        payload = request.model_dump()
        result = await model.update_progress(
            resource_id=str(resource_id),
            user_id=current_user["id"],
            payload=payload,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": str(e),
                },
            },
        )


def _parse_tags(raw: Optional[str]) -> List[str]:
    tags = [t.strip().lstrip("#")[:50] for t in (raw or "").split(",")]
    return list(dict.fromkeys(t for t in tags if t))[:10]
