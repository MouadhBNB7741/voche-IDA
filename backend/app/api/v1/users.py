from datetime import datetime
from typing import Optional, List, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from app.api.dependencies.jwt_auth import get_current_user
from app.api.dependencies.connections import get_connection
from app.models.profile_model import ProfileModel
from app.schemas.user import UserDetailsResponse, UserProfileUpdate

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserDetailsResponse)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    conn=Depends(get_connection)
):
    """
    Fetch the complete profile of the currently logged-in user using Model.
    """
    profile_model = ProfileModel(conn)
    profile = await profile_model.get_profile_by_user_id(current_user["id"])
    
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return profile


@router.patch("/me", response_model=UserDetailsResponse)
async def update_my_profile(
    update_data: UserProfileUpdate,
    current_user: dict = Depends(get_current_user),
    conn=Depends(get_connection)
):
    """
    Update user profile fields using Model.
    """
    profile_model = ProfileModel(conn)
    user_id = current_user["id"]
    
    updates = update_data.model_dump(exclude_unset=True)
    if not updates:
        profile = await profile_model.get_profile_by_user_id(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        return profile
        
    await profile_model.update_profile(user_id, updates)
    
    # Return updated profile
    updated_profile = await profile_model.get_profile_by_user_id(user_id)
    
    return updated_profile