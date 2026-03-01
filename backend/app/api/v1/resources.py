from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies.connections import get_connection
from app.api.middleware.auth_middleware import auth_middleware, auth_middleware_optional
from app.models.resource_model import ResourceModel
from app.schemas.resources import (
    ResourceListResponse,
    ResourceDetailsResponse,
    CreateRatingRequest,
    ProgressUpdateRequest,
    ProgressResponse,
    ResourceSortOption,
    ResourceType,
    ResourceRatingResponse
)

router = APIRouter(prefix="/resources", tags=["Resources"])


@router.get("/", response_model=ResourceListResponse)
async def list_resources(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    type: Optional[ResourceType] = Query(None, description="Filter by resource type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    language: Optional[str] = Query(None, description="Filter by language"),
    featured: Optional[bool] = Query(None, description="Filter by featured status"),
    sort: ResourceSortOption = Query(
        ResourceSortOption.newest, description="Sort resources"
    ),
    conn=Depends(get_connection),
):
    """List all resources with optional filters. Public endpoint."""
    model = ResourceModel(conn)
    result = await model.list_resources(
        page=page,
        limit=limit,
        resource_type=type.value if type else None,
        category=category,
        language=language,
        featured=featured,
        sort=sort.value,
    )
    return result


@router.get("/{resource_id}", response_model=ResourceDetailsResponse)
async def get_resource(
    resource_id: UUID,
    conn=Depends(get_connection),
):
    """Get a single resource by ID with ratings, reviews, and related resources. Public endpoint."""
    model = ResourceModel(conn)
    resource = await model.get_resource_details(str(resource_id))
    if not resource:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Resource not found",
                },
            },
        )
    return resource


@router.get("/{resource_id}/download")
async def download_resource(
    resource_id: UUID,
    conn=Depends(get_connection),
    current_user: Optional[dict] = Depends(auth_middleware_optional),
):
    """Download a resource (mock secure signed URL). Auth enforced if requires_auth is true."""
    model = ResourceModel(conn)
    
    # First, fetch to check requires_auth and increment downloads
    resource = await model.fetch_for_download(str(resource_id))
    if not resource:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Resource not found",
                },
            },
        )
        
    if resource["requires_auth"] and not current_user:
        raise HTTPException(status_code=401, detail="Authentication required to download this resource")

    # Mock secure signed URL
    download_url = f"{resource.get('url', 'https://storage.voce.com')}/secure/{resource_id}?token=mock_signed_token"
    
    return {
        "success": True,
        "download_url": download_url
    }


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
