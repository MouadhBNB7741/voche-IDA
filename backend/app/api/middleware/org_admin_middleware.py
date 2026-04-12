from typing import Dict
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from app.api.dependencies.connections import get_connection
from app.api.middleware.auth_middleware import auth_middleware

async def require_org_admin(
    org_id: UUID,
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
) -> dict:
    """
    Ensure the current user is a Platform Admin OR an Organization Admin for the specified org.
    """
    user_type = current_user.get("user_type")
    
    # 1. Platform Admin always allowed
    if user_type == "admin":
        return current_user
        
    # 2. Org Admin logic
    if user_type == "org_member":
        query = """
            SELECT role, status 
            FROM organization_members 
            WHERE org_id = $1 AND user_id = $2 AND role IN ('admin', 'moderator') AND status = 'approved'
        """
        org_member = await conn.fetchrow(query, str(org_id), current_user["id"])
        
        if org_member:
            return current_user
            
    # For patients, hcps, or unapproved org_members
    raise HTTPException(status_code=403, detail="Not authorized to act as an admin for this organization.")

async def require_working_group_admin(
    group_id: UUID,
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
) -> dict:
    """
    Ensure the current user is a Platform Admin OR an Organization Admin for the organization this group belongs to.
    """
    user_type = current_user.get("user_type")
    
    # 1. Platform Admin always allowed
    if user_type == "admin":
        return current_user
        
    # Get the org id of the current group
    org_id_query = "SELECT organization_id FROM working_groups WHERE group_id = $1"
    org_id = await conn.fetchval(org_id_query, str(group_id))
    
    if not org_id:
        raise HTTPException(status_code=404, detail="Working group not found.")
        
    # 2. Org Admin logic
    if user_type == "org_member":
        query = """
            SELECT role, status 
            FROM organization_members 
            WHERE org_id = $1 AND user_id = $2 AND role IN ('admin', 'moderator') AND status = 'approved'
        """
        org_member = await conn.fetchrow(query, org_id, current_user["id"])
        
        if org_member:
            return current_user
            
    # Inherently blocked
    raise HTTPException(status_code=403, detail="Not authorized to act as an admin for this working group.")
