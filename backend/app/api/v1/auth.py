import secrets
from datetime import datetime, timedelta, UTC
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from app.schemas.auth import RegisterRequest
from app.schemas.auth import LoginRequest, LoginResponse, PasswordUpdateSchema
from app.core.security import hash_password
from app.core.security import verify_password, create_jwt
from app.api.dependencies.jwt_auth import get_current_user
from app.api.dependencies.connections import get_connection
from app.services.email import EmailService


router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


@router.post("/register")
async def register(data: RegisterRequest, conn=Depends(get_connection)):
    if data.role not in ("subscriber", "developer"):
        raise HTTPException(400, "Invalid role")

    api_key = None
    if data.role == "developer":
        api_key = f"dev_{secrets.token_hex(16)}"

    exists = await conn.fetchval(
        "SELECT 1 FROM users WHERE email=$1", data.email
    )
    if exists:
        raise HTTPException(409, "User already exists")

    await conn.execute("""
        INSERT INTO users (email, password_hash, role, api_key, subscription_tier_id)
        VALUES ($1, $2, $3, $4, 1)
    """, data.email, hash_password(data.password), data.role, api_key)

    return {
        "status": "created",
        "api_key": api_key
    }


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, conn=Depends(get_connection)):
    user = await conn.fetchrow("""
        SELECT id, password_hash, role
        FROM users
        WHERE email=$1 AND is_active=TRUE
    """, data.email)

    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")

    token = create_jwt({
        "sub": str(user["id"]),
        "role": user["role"]
    })

    return {"access_token": token}


@router.get("/me")
async def get_me(current_user = Depends(get_current_user)):
    """
    Returns the current user's profile based on the JWT token.
    The 'get_current_user' dependency handles the token verification.
    """
    return {
        "id": str(current_user["id"]),
        "email": current_user["email"],
        "role": current_user["role"],
        "api_key": current_user.get("api_key"), # Only exists for developers
        "subscription_tier_id": current_user.get("subscription_tier_id", 1) # Default to Free
    }


@router.put("/update-password")
async def update_password(
    data: PasswordUpdateSchema, 
    user=Depends(get_current_user), 
    db=Depends(get_connection)
):
    # 1. Fetch current hashed password from DB
    # 2. Verify current_password using argon2
    # 3. Hash new_password
    # 4. Update DB
    return {"message": "Success"}


@router.post("/request-reset")
async def request_password_reset(data: PasswordResetRequest, conn=Depends(get_connection)):
    """
    Request password reset. Sends email with reset token.
    Returns same response for valid/invalid emails (security).
    """
    try:
        user = await conn.fetchrow("SELECT id, email FROM users WHERE email = $1", data.email)
        
        if user:
            reset_token = secrets.token_urlsafe(32)
            expires_at = datetime.now(UTC) + timedelta(hours=1)
            
            await conn.execute("""
                UPDATE password_reset_tokens 
                SET used = TRUE 
                WHERE user_id = $1 AND used = FALSE
            """, user["id"])
            
            await conn.execute("""
                INSERT INTO password_reset_tokens (user_id, token, expires_at)
                VALUES ($1, $2, $3)
            """, user["id"], reset_token, expires_at)
            
            await EmailService.send_password_reset(user["email"], reset_token)
    
    except Exception as e:
        print(f"Password reset error: {e}")
    
    return {"message": "If that email exists, a reset link has been sent."}


@router.get("/verify-reset-token/{token}")
async def verify_reset_token(token: str, conn=Depends(get_connection)):
    """Check if reset token is valid and not expired"""
    token_record = await conn.fetchrow("""
        SELECT id, user_id, expires_at, used
        FROM password_reset_tokens
        WHERE token = $1
    """, token)
    
    if not token_record:
        raise HTTPException(400, "Invalid reset token")
    
    if token_record["used"]:
        raise HTTPException(400, "Reset token already used")
    
    if datetime.now(UTC) > token_record["expires_at"]:
        raise HTTPException(400, "Reset token expired")
    
    return {"valid": True}


@router.post("/reset-password")
async def reset_password(data: PasswordResetConfirm, conn=Depends(get_connection)):
    """Reset password using valid token"""
    
    token_record = await conn.fetchrow("""
        SELECT id, user_id, expires_at, used
        FROM password_reset_tokens
        WHERE token = $1
    """, data.token)
    
    if not token_record:
        raise HTTPException(400, "Invalid reset token")
    
    if token_record["used"]:
        raise HTTPException(400, "Reset token already used")
    
    if datetime.now(UTC) > token_record["expires_at"]:
        raise HTTPException(400, "Reset token expired")
    
    new_hash = hash_password(data.new_password)
    await conn.execute("""
        UPDATE users 
        SET password_hash = $1 
        WHERE id = $2
    """, new_hash, token_record["user_id"])
    
    await conn.execute("""
        UPDATE password_reset_tokens 
        SET used = TRUE 
        WHERE id = $1
    """, token_record["id"])
    
    await conn.execute("""
        UPDATE password_reset_tokens 
        SET used = TRUE 
        WHERE user_id = $1 AND id != $2
    """, token_record["user_id"], token_record["id"])
    
    return {"message": "Password reset successful"}