from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from app.api.dependencies.connections import get_connection
from app.api.middleware.auth_middleware import auth_middleware
from app.api.middleware.org_admin_middleware import require_org_admin, require_working_group_admin

from app.models.organization_model import OrganizationModel
from app.schemas.organization import (
    OrganizationListResponse,
    OrganizationDetailResponse,
    WorkingGroupListResponse,
    JoinOrganizationResponse,
    JoinWorkingGroupResponse,
    MembershipDecisionRequest,
    OrganizationMemberListResponse,
    WorkingGroupDetailResponse
)

router = APIRouter(prefix="/organizations", tags=["Organizations"])

# ======================================================================
# ORGANIZATIONS
# ======================================================================

@router.get("", response_model=OrganizationListResponse)
async def list_organizations(
    page: Optional[int] = Query(None, ge=1),
    limit: Optional[int] = Query(None, ge=0, le=1000), 
    type: Optional[str] = Query(None, description="Filter by organization type"),
    country: Optional[str] = Query(None, description="Filter by country"),
    conn=Depends(get_connection)
):
    """List organizations with optional 'Show All' support"""
    model = OrganizationModel(conn)
    
    result = await model.list_organizations(
        page=page or 1, 
        limit=limit, 
        org_type=type, 
        country=country
    )
    return result

@router.get("/working-groups", response_model=WorkingGroupListResponse)
async def list_working_groups(
    page: Optional[int] = Query(None, ge=1),
    limit: Optional[int] = Query(None, ge=0, le=1000), 
    organization_id: Optional[UUID] = Query(None),
    group_type: Optional[str] = Query(None, alias="type"),
    public_only: bool = Query(False),
    conn=Depends(get_connection)
):
    model = OrganizationModel(conn)
    
    result = await model.list_working_groups(
        page=page or 1, 
        limit=limit, 
        org_id=str(organization_id) if organization_id else None, 
        group_type=group_type, 
        public_only=public_only
    )
    return result

@router.get("/{org_id}", response_model=OrganizationDetailResponse)
async def get_organization(
    org_id: UUID,
    conn=Depends(get_connection)
):
    """Get organization details"""
    model = OrganizationModel(conn)
    org = await model.get_organization_details(str(org_id))
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    return org

@router.post("/{org_id}/join", response_model=JoinOrganizationResponse)
async def join_organization(
    org_id: UUID,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware)
):
    """Request to join an organization"""
    model = OrganizationModel(conn)
    try:
        result = await model.join_organization(str(org_id), current_user["id"])
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )

@router.post("/{org_id}/members/{user_id}/decide")
async def decide_org_join(
    org_id: UUID,
    user_id: UUID,
    request: MembershipDecisionRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(require_org_admin)
):
    """Accept or Refuse organization membership request"""
    model = OrganizationModel(conn)
    
    model = OrganizationModel(conn)
    from app.services.notification_service import NotificationService
    from app.schemas.notification import NotificationType
    
    try:
        result = await model.decide_organization_join(str(org_id), str(user_id), request.action)
        
        # TRIGGER NOTIFICATION: ORG_REQUEST_UPDATE
        try:
            org = await model.get_organization_details(str(org_id))
            notif_service = NotificationService(conn)
            await notif_service.notify_user(
                user_id=str(user_id),
                notif_type=NotificationType.ORG_REQUEST_UPDATE,
                data={
                    "org_name": org["name"] if org else "the organization",
                    "org_id": str(org_id),
                    "status": "approved" if request.action == "accept" else "refused"
                }
            )
        except:
            pass
            
        return result
    except ValueError as e:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{org_id}/requests", response_model=OrganizationMemberListResponse)
async def get_organization_requests(
    org_id: UUID,
    status: Optional[str] = Query(None, description="Filter by status (e.g. pending, approved)"),
    page: Optional[int] = Query(1, ge=1),
    limit: Optional[int] = Query(None, ge=1),
    conn=Depends(get_connection),
    current_user: dict = Depends(require_org_admin)
):
    """List organization membership requests (Admin/Moderator only)"""
    model = OrganizationModel(conn)
    result = await model.get_organization_requests(
        org_id=str(org_id),
        status_filter=status,
        limit=limit,
        page=page
    )
    return result

# ======================================================================
# WORKING GROUPS
# ======================================================================

@router.get("/working-groups/{group_id}", response_model=WorkingGroupDetailResponse)
async def get_working_group(
    group_id: UUID,
    conn=Depends(get_connection)
):
    """Get working group details along with its members"""
    model = OrganizationModel(conn)
    group = await model.get_working_group_details(str(group_id))
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Working group not found"
        )
    return group

@router.post("/working-groups/{group_id}/join", response_model=JoinWorkingGroupResponse)
async def join_working_group(
    group_id: UUID,
    conn=Depends(get_connection),
    current_user: dict = Depends(auth_middleware)
):
    """Request to join a working group"""
    model = OrganizationModel(conn)
    try:
        result = await model.join_working_group(str(group_id), current_user["id"])
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/working-groups/{group_id}/members/{user_id}/decide")
async def decide_group_join(
    group_id: UUID,
    user_id: UUID,
    request: MembershipDecisionRequest,
    conn=Depends(get_connection),
    current_user: dict = Depends(require_working_group_admin)
):
    """Accept or Refuse working group membership request"""
    model = OrganizationModel(conn)
    from app.services.notification_service import NotificationService
    from app.schemas.notification import NotificationType
    
    try:
        result = await model.decide_working_group_join(str(group_id), str(user_id), request.action)
        
        # TRIGGER NOTIFICATION: ORG_REQUEST_UPDATE (reusing type for groups)
        try:
             group = await model.get_working_group_details(str(group_id))
             notif_service = NotificationService(conn)
             await notif_service.notify_user(
                 user_id=str(user_id),
                 notif_type=NotificationType.ORG_REQUEST_UPDATE,
                 data={
                     "org_name": group["name"] if group else "the working group",
                     "org_id": str(group_id),
                     "status": "approved" if request.action == "accept" else "refused"
                 }
             )
        except:
             pass
             
        return result
    except ValueError as e:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/working-groups/{group_id}/requests", response_model=OrganizationMemberListResponse)
async def get_working_group_requests(
    group_id: UUID,
    status: Optional[str] = Query(None, description="Filter by status (e.g. pending, approved)"),
    page: Optional[int] = Query(1, ge=1),
    limit: Optional[int] = Query(None, ge=1),
    conn=Depends(get_connection),
    current_user: dict = Depends(require_working_group_admin)
):
    """List working group membership requests (Admin/Moderator only)"""
    model = OrganizationModel(conn)
    result = await model.get_working_group_requests(
        group_id=str(group_id),
        status_filter=status,
        limit=limit,
        page=page
    )
    return result
