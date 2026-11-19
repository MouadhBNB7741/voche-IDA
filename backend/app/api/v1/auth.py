import logging
import secrets
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Security, status
from fastapi.security import OAuth2PasswordRequestForm, HTTPAuthorizationCredentials
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    GoogleSignInRequest,
    PasswordUpdateRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from app.schemas.user import UserDetailsResponse
from app.models.user_model import UserModel
from app.models.password_reset_model import PasswordResetModel
from app.models.profile_model import ProfileModel
from app.core.security import hash_password, verify_password, create_jwt, decode_jwt
from app.core.token_blacklist import revoke_token
from app.api.dependencies.connections import get_connection, get_transaction
from app.services.email import EmailService
from app.services.google_auth import verify_google_credential, sign_in_with_google
from app.api.middleware.auth_middleware import auth_middleware, account_suspended_error, security_optional

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=LoginResponse)
async def register(data: RegisterRequest, conn=Depends(get_transaction)):
    """
    Register a new user using the Model layer.
    """
    user_model = UserModel(conn)
    
    # 1. Check uniqueness
    if await user_model.check_email_exists(data.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    # 2. Hash password
    pwd_hash = hash_password(data.password)

    # 3. Create user
    # display_name defaults to "First Last"
    display_name = f"{data.first_name} {data.last_name}".strip()
    
    try:
        user = await user_model.create_user(
            email=data.email, 
            password_hash=pwd_hash, 
            user_type=data.user_type, 
            first_name=data.first_name, 
            last_name=data.last_name, 
            display_name=display_name
        )
    except Exception as e:
        logging.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

    # 4. Generate JWT
    token = create_jwt({
        "sub": str(user['id']),
        "user_type": user['user_type']
    })

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user_type=user['user_type'],
        is_new_user=True,
    )

async def _start_session(conn, user: dict, is_new_user: bool = False) -> LoginResponse:
    """Checks shared by every way of signing in (password or Google), then our login token."""
    user_model = UserModel(conn)
    user = await user_model.lift_expired_suspension(user)
    if user["status"] == 'suspended':
        raise account_suspended_error(user)

    # "onboarding": signed in with Google, role not chosen yet
    if not user["is_active"] or user["status"] not in ('active', 'onboarding'):
        raise HTTPException(status_code=403, detail="Account is inactive or suspended")

    # Check and annul account deletion schedule
    deletion_message = None
    if user.get("deletion_scheduled_at"):
        await conn.execute("UPDATE users SET deletion_scheduled_at = NULL WHERE id = $1", user["id"])
        deletion_message = "Your account deletion schedule has been annulled because you logged back in."

    # Update last login
    await user_model.update_last_login(str(user['id']))

    token = create_jwt({
        "sub": str(user["id"]),
        "user_type": user["user_type"]
    })

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user_type=user['user_type'],
        message=deletion_message,
        is_new_user=is_new_user,
    )


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, conn=Depends(get_connection)):
    """
    Login user using Model layer.
    """
    user_model = UserModel(conn)
    user = await user_model.get_by_email(data.email)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Google sign-in accounts have no password
    if not user["password_hash"] or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return await _start_session(conn, user)


@router.post("/google", response_model=LoginResponse)
async def google_sign_in(data: GoogleSignInRequest, conn=Depends(get_connection)):
    """
    Sign in with the ID token from the "Sign in with Google" button.
    Links to an existing account with the same email if Google verified it,
    otherwise creates an account that picks its role during onboarding.
    """
    claims = await verify_google_credential(data.credential)
    user, created = await sign_in_with_google(conn, claims)
    return await _start_session(conn, user, is_new_user=created)


@router.post("/logout")
async def logout(token: Optional[HTTPAuthorizationCredentials] = Security(security_optional)):
    """
    Revoke the login token, so it stops working even if someone copied it.
    """
    if token:
        try:
            payload = decode_jwt(token.credentials)
        except HTTPException:
            payload = None  # already expired or invalid: nothing to revoke
        if payload:
            try:
                await revoke_token(payload)
            except Exception as e:
                logging.error(f"Could not revoke token on logout: {e}")
                raise HTTPException(status_code=503, detail="Could not sign you out on the server. Please try again.")
    return {"message": "Signed out"}



@router.get("/me", response_model=UserDetailsResponse)
async def get_me(
    current_user: dict = Depends(auth_middleware), 
    conn=Depends(get_connection)
):
    """
    Get current user details using ProfileModel (joins data).
    """
    profile_model = ProfileModel(conn)
    # The middleware now returns the user dict directly
    user_details = await profile_model.get_profile_by_user_id(current_user["id"])
    
    if not user_details:
        raise HTTPException(status_code=404, detail="User not found")
        
    return user_details

@router.put("/update-password")
async def update_password(
    data: PasswordUpdateRequest, 
    current_user: dict = Depends(auth_middleware), 
    conn=Depends(get_connection)
):
    """
    Update password using Model layer.
    """
    user_model = UserModel(conn)
    user_id = current_user["id"]
    
    # Verify old password
    current_hash = await user_model.get_password_hash(user_id)
    if not current_hash:
        # Signed up with Google. Setting a first password goes through the emailed
        # reset link, so someone using a stolen session cannot add one.
        raise HTTPException(
            status_code=400,
            detail="Your account signs in with Google and has no password yet. "
                   "Use \"Forgot password?\" on the login page to set one.",
        )

    if not verify_password(data.current_password, current_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")
        
    # Update logic
    new_hash = hash_password(data.new_password)
    await user_model.update_password(user_id, new_hash)
    
    return {"message": "Password updated successfully"}

@router.post("/request-reset")
async def request_password_reset(
    data: PasswordResetRequest, 
    conn=Depends(get_connection)
):
    """
    Request password reset using Model layer.
    """
    user_model = UserModel(conn)
    pwd_model = PasswordResetModel(conn)
    
    # Check if user exists (to get ID)
    user = await user_model.get_by_email(data.email)
    
    # Always return success
    generic_msg = {"message": "If this email is registered, you will receive a reset link."}
    
    if not user:
        return generic_msg
        
    # Generate token
    token = await pwd_model.create_token(str(user['id']))
    
    # Send password reset email
    logging.info(f"📤 Preparing to send password reset email to {data.email}")
    try:
        await EmailService.send_password_reset(data.email, token)
        logging.info(f"✅ Reset email sent. TOKEN for {data.email}: {token}")
    except Exception as e:
        logging.error(f"❌ Failed to send reset email to {data.email}: {str(e)}")
    
    return generic_msg

@router.get("/verify-reset-token/{token}")
async def verify_reset_token(token: str, conn=Depends(get_connection)):
    """
    Verify token validity.
    """
    pwd_model = PasswordResetModel(conn)
    result = await pwd_model.validate_token(token)
    
    if not result:
        raise HTTPException(status_code=400, detail="Invalid token")
    
    if not result["valid"]:
        detail = "Token expired" if result["reason"] == "expired" else "Token already used"
        raise HTTPException(status_code=400, detail=detail)
        
    return {"message": "Token is valid", "valid": True}

@router.post("/reset-password")
async def reset_password(
    data: PasswordResetConfirm, 
    conn=Depends(get_connection)
):
    """
    Reset password using Model layer.
    """
    pwd_model = PasswordResetModel(conn)
    user_model = UserModel(conn)
    
    # Validate
    result = await pwd_model.validate_token(data.token)
    
    if not result:
        raise HTTPException(status_code=400, detail="Invalid token")
        
    if not result["valid"]:
        detail = "Token expired" if result["reason"] == "expired" else "Token already used"
        raise HTTPException(status_code=400, detail=detail)
    
    # Update password
    new_hash = hash_password(data.new_password)
    await user_model.update_password(str(result["user_id"]), new_hash)
    
    # Mark token used
    await pwd_model.mark_token_used(str(result["token_id"]))
    
    return {"message": "Password has been reset successfully"}