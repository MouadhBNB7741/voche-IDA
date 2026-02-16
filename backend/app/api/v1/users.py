from datetime import datetime
from typing import Optional, List, Any, Dict
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from pydantic import BaseModel, EmailStr
import os
import shutil

from app.api.middleware.auth_middleware import auth_middleware
from app.api.dependencies.connections import get_connection
from app.models.profile_model import ProfileModel
from app.models.user_model import UserModel
from app.schemas.user import UserDetailsResponse, UserProfileUpdate, NotificationPreferences

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserDetailsResponse)
async def get_my_profile(
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    """
    Fetch the complete profile of the currently logged-in user using Model.
    """
    # Prefer UserModel to fetch everything including new JSONB fields
    # But UserDetailsResponse expects profile fields too.
    # We fetch basic user data (with prefs) from UserModel
    # And profile data from ProfileModel
    
    user_model = UserModel(conn)
    profile_model = ProfileModel(conn)
    
    user = await user_model.get_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    profile = await profile_model.get_profile_by_user_id(current_user["id"])
    
    # Merge them. User fields + Profile fields.
    # UserDetailsResponse expects flat structure.
    # user dict has id, email, notification_preferences, verification, etc.
    # profile dict has bio, location, etc.
    
    response_data = {**user}
    if profile:
        response_data.update(profile)
        
    return response_data


@router.patch("/me", response_model=UserDetailsResponse)
async def update_my_profile(
    update_data: UserProfileUpdate,
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    """
    Update user profile fields using Model.
    """
    profile_model = ProfileModel(conn)
    user_model = UserModel(conn)
    user_id = current_user["id"]
    
    updates = update_data.model_dump(exclude_unset=True)
    if not updates:
        # Just return current state
        pass
    else:    
        await profile_model.update_profile(user_id, updates)
    
    # Return updated profile (need merge)
    user = await user_model.get_by_id(user_id)
    profile = await profile_model.get_profile_by_user_id(user_id)
    
    response_data = {**user}
    if profile:
        response_data.update(profile)
    
    return response_data

@router.patch("/me/notifications")
async def update_notifications(
    preferences: NotificationPreferences,
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    """
    Update notification preferences.
    """
    user_model = UserModel(conn)
    updates = preferences.model_dump(exclude_unset=True)
    
    updated_data = await user_model.update_notification_preferences(current_user['id'], updates)
    
    return {
        "success": True,
        "message": "Notification preferences updated successfully",
        "data": updated_data
    }

@router.post("/me/verification")
async def submit_verification(
    licenseNumber: str = Form(...),
    issuingRegion: str = Form(...),
    expirationDate: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    """
    Submit verification documents (HCP only).
    """
    # Role Check
    if current_user.get('user_type') != 'hcp':
        raise HTTPException(status_code=403, detail="Only HCP users can submit verification.")
        
    # File Validation
    if file.content_type not in ["application/pdf", "image/jpeg", "image/jpg", "image/webp", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: PDF, JPEG, JPG, WEBP, PNG.")
    
    # File Size Validation
    if file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds the maximum limit of 5MB.")
        
    user_model = UserModel(conn)
    
    # Save File
    upload_dir = "uploads/verification"
    os.makedirs(upload_dir, exist_ok=True)
    timestamp = int(datetime.now().timestamp())
    filename = f"{current_user['id']}_{timestamp}_{file.filename}"
    file_path = os.path.join(upload_dir, filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail="File upload failed")
        
    document_url = f"/uploads/verification/{filename}"
    
    payload = {
        "licenseNumber": licenseNumber,
        "issuingRegion": issuingRegion,
        "expirationDate": expirationDate,
        "documentUrl": document_url,
        "status": "pending_verification",
        "submittedAt": datetime.now().isoformat()
    }
    
    try:
        result = await user_model.submit_verification(current_user['id'], payload)
    except ValueError as e:
        # Clean up file if validation failed
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=str(e))
        
    return {
        "success": True,
        "message": "Verification submitted successfully",
        "data": result.get("verification")
    }

@router.delete("/me/verification")
async def delete_verification(
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    """
    Delete verification data (Withdraw submission).
    """
    if current_user.get('user_type') != 'hcp' or current_user.get('user_type') != 'admin':
        raise HTTPException(status_code=403, detail="Only HCP users can access verification.")

    user_model = UserModel(conn)
    
    # Delete from DB
    old_data = await user_model.delete_verification(current_user['id'])
    
    # Delete file if exists
    if old_data and "documentUrl" in old_data:
        doc_url = old_data["documentUrl"]
        if doc_url.startswith("/"):
            doc_url = doc_url[1:]
            
        if os.path.exists(doc_url):
            try:
                os.remove(doc_url)
            except Exception:
                pass 
                
    return {
        "success": True,
        "message": "Verification data deleted successfully"
    }

@router.patch("/me/verification")
async def update_verification(
    licenseNumber: Optional[str] = Form(None),
    issuingRegion: Optional[str] = Form(None),
    expirationDate: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    """
    Update verification data.
    """
    if current_user.get('user_type') != 'hcp' :
        raise HTTPException(status_code=403, detail="Only HCP users can access verification.")

    if current_user.get('status') != 'pending_verification':
        raise HTTPException(status_code=403, detail="You can only update verification data if your status is pending_verification.")
        
    user_model = UserModel(conn)
    
    import json
    # Fetch current data to handle old file deletion later
    user_data = await user_model.get_by_id(current_user['id'])
    old_verification = user_data.get('verification', {})
    if isinstance(old_verification, str):
        old_verification = json.loads(old_verification)
        
    updates = {}
    if licenseNumber is not None:
        updates["licenseNumber"] = licenseNumber
    if issuingRegion is not None:
        updates["issuingRegion"] = issuingRegion
    if expirationDate is not None:
        updates["expirationDate"] = expirationDate
    
    # Handle File Update
    new_file_path = None
    if file:
        if file.content_type not in ["application/pdf", "image/jpeg", "image/jpg", "image/webp", "image/png"]:
            raise HTTPException(status_code=400, detail="Invalid file type. Allowed: PDF, JPEG, JPG, WEBP, PNG.")
        if file.size > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds the maximum limit of 5MB.")
            
        upload_dir = "uploads/verification"
        os.makedirs(upload_dir, exist_ok=True)
        timestamp = int(datetime.now().timestamp())
        filename = f"{current_user['id']}_{timestamp}_{file.filename}"
        new_file_path = os.path.join(upload_dir, filename)
        
        try:
            with open(new_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception:
            raise HTTPException(status_code=500, detail="File upload failed")
            
        updates["documentUrl"] = f"/uploads/verification/{filename}"
    
    if not updates and not file:
         raise HTTPException(status_code=400, detail="No field to update")

    # Update timestamp and status
    updates["updatedAt"] = datetime.now().isoformat()
    updates["status"] = "pending_verification" # Re-trigger verification on update

    try:
        result = await user_model.update_verification(current_user['id'], updates)
    except Exception as e:
        # Cleanup new file if DB update fails
        if new_file_path and os.path.exists(new_file_path):
            os.remove(new_file_path)
        raise HTTPException(status_code=500, detail="Update failed")

    # Cleanup old file if we verified a new one was uploaded and saved
    if file and old_verification and "documentUrl" in old_verification:
        old_url = old_verification["documentUrl"]
        if old_url != updates.get("documentUrl"):
             if old_url.startswith("/"):
                 old_url = old_url[1:]
             if os.path.exists(old_url):
                 try:
                     os.remove(old_url)
                 except:
                     pass

    return {
        "success": True,
        "message": "Verification updated successfully",
        "data": result.get("verification")
    }