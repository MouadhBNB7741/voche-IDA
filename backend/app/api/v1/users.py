from datetime import date, datetime
from typing import Optional, List, Any, Dict
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from pydantic import BaseModel, EmailStr
import os
import shutil

from app.api.middleware.auth_middleware import auth_middleware, auth_middleware_onboarding
from app.api.dependencies.connections import get_connection, get_transaction
from app.models.doctor_model import DoctorModel
from app.models.profile_model import ProfileModel
from app.models.user_model import UserModel
from app.schemas.user import OnboardingComplete, UserDetailsResponse, UserProfileUpdate
from app.services.verification_service import (
    check_expiration_date, delete_licence, store_licence, submit_licence,
)
from app.schemas.notification import NotificationPreferences

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserDetailsResponse)
async def get_my_profile(
    current_user: dict = Depends(auth_middleware_onboarding),
    conn=Depends(get_connection)
):
    """
    Fetch the complete profile of the currently logged-in user using Model.
    """
    profile_model = ProfileModel(conn)
    profile = await profile_model.get_profile_by_user_id(current_user["id"])
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
        
    return profile


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
    user_id = current_user["id"]
    
    updates = update_data.model_dump(exclude_unset=True)
    if updates:
        if "email" in updates and updates["email"]:
            new_email = updates["email"].strip().lower()
            query = "SELECT id FROM users WHERE LOWER(email) = $1 AND id != $2"
            existing_id = await conn.fetchval(query, new_email, user_id)
            if existing_id:
                raise HTTPException(status_code=400, detail="This email is already in use by another account.")
            updates["email"] = new_email # Save normalized email

        await profile_model.update_profile(user_id, updates)
    
    profile = await profile_model.get_profile_by_user_id(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
        
    return profile


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    """
    Upload user avatar. Max 2MB, allowed formats: PNG, JPEG, JPG, WEBP.
    """
    allowed_content_types = ["image/png", "image/jpeg", "image/jpg", "image/webp"]
    allowed_extensions = [".png", ".jpeg", ".jpg", ".webp"]
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file extension. Allowed extensions: {', '.join(allowed_extensions)}"
        )
        
    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=400, 
            detail="Invalid content type. Allowed formats: PNG, JPEG, JPG, WEBP."
        )

    # Check size
    try:
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
    except Exception:
        file_size = 0
        
    if file_size > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds the maximum limit of 2MB.")

    # Save File
    upload_dir = "uploads/avatars"
    os.makedirs(upload_dir, exist_ok=True)
    timestamp = int(datetime.now().timestamp())
    filename = f"{current_user['id']}_{timestamp}{ext}"
    file_path = os.path.join(upload_dir, filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail="File upload failed")
        
    avatar_url = f"/static/avatars/{filename}"
    
    profile_model = ProfileModel(conn)
    await profile_model.update_profile(current_user['id'], {"avatar": avatar_url})
    
    return {
        "success": True,
        "message": "Avatar uploaded successfully",
        "avatar": avatar_url
    }


@router.delete("/me/avatar")
async def delete_avatar(
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    """
    Delete user avatar.
    """
    profile_model = ProfileModel(conn)
    profile = await profile_model.get_profile_by_user_id(current_user['id'])
    
    if not profile or not profile.avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")
        
    if profile.avatar.startswith("/static/"):
        relative_path = profile.avatar.replace("/static/", "uploads/")
        if os.path.exists(relative_path):
            try:
                os.remove(relative_path)
            except Exception:
                pass
                
    await profile_model.update_profile(current_user['id'], {"avatar": None})
    
    return {
        "success": True,
        "message": "Avatar deleted successfully"
    }

@router.get("/me/preferences/notifications")
async def get_notification_preferences(
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    """
    Get current user's notification preferences.
    """
    user_model = UserModel(conn)
    user = await user_model.get_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return user.get("notification_preferences") or {}


@router.patch("/me/preferences/notifications")
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

def _verification_summary(row: dict) -> dict:
    return {
        "verificationId": str(row["verification_id"]),
        "status": row["status"],
        "licenseNumber": row["license_number"],
        "issuingRegion": row.get("issuing_region"),
        "expirationDate": row["expiration_date"].isoformat() if row.get("expiration_date") else None,
        "hasDocument": bool(row.get("document_url")),
    }


@router.post("/me/verification")
async def submit_verification(
    licenseNumber: str = Form(..., min_length=1, max_length=100),
    issuingRegion: str = Form(..., max_length=100),
    expirationDate: date = Form(...),
    institution: Optional[str] = Form(None, max_length=255),
    country: Optional[str] = Form(None, max_length=100),
    specialization: Optional[str] = Form(None, max_length=100),
    file: UploadFile = File(...),
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    """
    Submit verification documents (HCP only). Saved in doctor_verifications,
    so the request reaches the admin queue. Same as POST /doctors/verification/upload.
    """
    if current_user.get('user_type') != 'hcp':
        raise HTTPException(status_code=403, detail="Only HCP users can submit verification.")

    profile = await ProfileModel(conn).get_profile_by_user_id(current_user['id'])
    specialization = specialization or await conn.fetchval(
        "SELECT specialization FROM user_profiles WHERE user_id = $1", current_user['id']
    )
    row = await submit_licence(conn, current_user['id'], {
        "license_number": licenseNumber,
        "institution": institution or "Not provided",
        "country": country or (profile.country if profile else None) or "Not provided",
        "specialization": specialization or "Not provided",
        "issuing_region": issuingRegion,
        "expiration_date": expirationDate,
    }, file)
    return {
        "success": True,
        "message": "Verification submitted successfully",
        "data": _verification_summary(row)
    }

@router.delete("/me/verification")
async def delete_verification(
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    """
    Withdraw a pending verification request and delete its document.
    """
    if current_user.get('user_type') not in ('hcp', 'admin'):
        raise HTTPException(status_code=403, detail="Only HCP users can access verification.")

    row = await DoctorModel(conn).withdraw_pending_verification(current_user['id'])
    if not row:
        raise HTTPException(status_code=404, detail="No pending verification to withdraw")

    await delete_licence(row.get("document_url"))
    return {
        "success": True,
        "message": "Verification data deleted successfully"
    }

@router.patch("/me/verification")
async def update_verification(
    licenseNumber: Optional[str] = Form(None, min_length=1, max_length=100),
    issuingRegion: Optional[str] = Form(None, max_length=100),
    expirationDate: Optional[date] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    """
    Update a pending verification request, optionally replacing its document.
    """
    if current_user.get('user_type') != 'hcp':
        raise HTTPException(status_code=403, detail="Only HCP users can access verification.")

    model = DoctorModel(conn)
    current = await model.get_verification_by_user(current_user['id'])
    if not current or current["status"] != "pending":
        raise HTTPException(status_code=403, detail="You can only update a pending verification.")

    check_expiration_date(expirationDate)
    updates = {
        name: value for name, value in {
            "license_number": licenseNumber,
            "issuing_region": issuingRegion,
            "expiration_date": expirationDate,
        }.items() if value is not None
    }
    if file:
        updates["document_url"] = await store_licence(current_user['id'], file)
    if not updates:
        raise HTTPException(status_code=400, detail="No field to update")

    try:
        row = await model.update_pending_verification(current_user['id'], updates)
    except Exception:
        await delete_licence(updates.get("document_url"))
        raise HTTPException(status_code=500, detail="Update failed")

    if file:
        await delete_licence(current.get("document_url"))

    return {
        "success": True,
        "message": "Verification updated successfully",
        "data": _verification_summary(row)
    }


@router.post("/onboarding/complete", response_model=UserDetailsResponse)
async def complete_onboarding(
    data: OnboardingComplete,
    current_user: dict = Depends(auth_middleware_onboarding),
    conn=Depends(get_transaction)
):
    """
    Finish the onboarding wizard. The role is required only if the account has none yet;
    interests and location can be skipped and completed later from the dashboard.
    """
    current_role = current_user.get('user_type')
    if not current_role and not data.user_type:
        raise HTTPException(status_code=400, detail="Please choose your role to continue.")
    if current_role and data.user_type and data.user_type != current_role:
        raise HTTPException(status_code=400, detail="Your role has already been set.")

    profile_model = ProfileModel(conn)
    profile_updates = data.model_dump(include={"interests", "location"}, exclude_none=True)
    if profile_updates:
        await profile_model.update_profile(current_user['id'], profile_updates)
    await UserModel(conn).complete_onboarding(current_user['id'], data.user_type)

    return await profile_model.get_profile_by_user_id(current_user['id'])


@router.delete("/me", status_code=200)
async def schedule_delete_my_account(
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    """
    Schedule the account for deletion in 7 days.
    """
    user_id = current_user['id']
    query = """
        UPDATE users 
        SET deletion_scheduled_at = NOW() + INTERVAL '7 days' 
        WHERE id = $1
    """
    await conn.execute(query, user_id)
    return {
        "success": True,
        "message": "Your account has been scheduled for deletion in 7 days. Log in anytime before then to cancel."
    }


@router.post("/me/cancel-deletion", status_code=200)
async def cancel_my_account_deletion(
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection)
):
    """
    Cancel a scheduled account deletion (logging in also cancels it).
    """
    cancelled = await UserModel(conn).cancel_deletion(current_user['id'])
    return {
        "success": True,
        "message": "Your account deletion has been cancelled." if cancelled
                   else "Your account is not scheduled for deletion."
    }