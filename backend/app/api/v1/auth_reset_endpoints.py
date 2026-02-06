import secrets
from datetime import datetime, timedelta, UTC
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from app.core.security import hash_password
from app.api.dependencies.connections import get_connection
from app.services.email import EmailService


router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


@router.post("/request-reset")
async def request_password_reset(data: PasswordResetRequest, conn=Depends(get_connection)):
    """
    Request password reset. Sends email with reset token.
    Returns same response for valid/invalid emails (security).
    """
    # Always return success to prevent email enumeration
    try:
        # Check if user exists
        user = await conn.fetchrow("SELECT id, email FROM users WHERE email = $1", data.email)

        if user:
            # Generate secure random token
            reset_token = secrets.token_urlsafe(32)
            expires_at = datetime.now(UTC) + timedelta(hours=1)

            # Invalidate any existing unused tokens for this user
            await conn.execute("""
                DELETE FROM password_reset_tokens 
                WHERE user_id = $1
            """, user["id"])

            # Create new reset token
            await conn.execute("""
                INSERT INTO password_reset_tokens (user_id, token, expires_at)
                VALUES ($1, $2, $3)
            """, user["id"], reset_token, expires_at)

            # Send email (async in background would be better, but keeping simple)
            await EmailService.send_password_reset(user["email"], reset_token)

    except Exception as e:
        # Log error but don't expose to user
        print(f"Password reset error: {e}")

    # Always return success (security best practice)
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

    # Validate token
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

    # Update password
    new_hash = hash_password(data.new_password)
    await conn.execute("""
        UPDATE users 
        SET password_hash = $1 
        WHERE id = $2
    """, new_hash, token_record["user_id"])

    # Mark token as used
    await conn.execute("""
        UPDATE password_reset_tokens 
        SET used = TRUE 
        WHERE id = $1
    """, token_record["id"])

    # Invalidate all other tokens for this user
    await conn.execute("""
        UPDATE password_reset_tokens 
        SET used = TRUE 
        WHERE user_id = $1 AND id != $2
    """, token_record["user_id"], token_record["id"])

    return {"message": "Password reset successful"}
