from datetime import timezone
from typing import Optional
from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_jwt
from app.core.token_blacklist import is_token_revoked
from app.api.dependencies.connections import get_connection
from app.models.user_model import UserModel

# Define schemes
security_strict = HTTPBearer(auto_error=True)
security_optional = HTTPBearer(auto_error=False)


def account_suspended_error(user: dict) -> HTTPException:
    """403 telling a suspended user why and until when. No end date means banned."""
    until = user.get("suspended_until")
    reason = user.get("suspended_reason")
    if until:
        message = f"Your account is suspended until {until.astimezone(timezone.utc):%d %B %Y, %H:%M} UTC."
    else:
        message = "Your account is suspended."
    if reason:
        message += f" Reason: {reason}"
    return HTTPException(status_code=403, detail={
        "code": "account_suspended",
        "message": message,
        "suspended_reason": reason,
        "suspended_until": until.isoformat() if until else None,
    })


async def _get_token_user(token_creds: Optional[HTTPAuthorizationCredentials], conn) -> Optional[dict]:
    """Decode the token and load its user, lifting a suspension that has ended.
    Returns None if the token is missing or invalid, or the user no longer exists."""
    if not token_creds:
        return None

    try:
        payload = decode_jwt(token_creds.credentials)
        user_id = payload.get("sub")
        if not user_id or await is_token_revoked(payload):
            return None

        user = await conn.fetchrow("""
            SELECT id, email, user_type, is_active, status, suspended_until, suspended_reason
            FROM users
            WHERE id = $1
        """, user_id)

        if not user:
            return None

        return await UserModel(conn).lift_expired_suspension(dict(user))
    except Exception:
        return None


def _is_active(user: dict) -> bool:
    return bool(user["is_active"]) and user["status"] == 'active'


async def _verify_token(token_creds: Optional[HTTPAuthorizationCredentials], conn) -> Optional[dict]:
    """Shared logic for decoding and verifying user. Returns None unless the account is active."""
    user = await _get_token_user(token_creds, conn)
    return user if user and _is_active(user) else None

async def auth_middleware(
    request: Request,
    token: HTTPAuthorizationCredentials = Security(security_strict),
    conn=Depends(get_connection)
):
    """
    STRICT authentication. Raises 401/403 if invalid.
    Used for protected routes (e.g. /me, /update-password).
    """
    user = await _get_token_user(token, conn)

    if user and user["status"] == 'suspended':
        raise account_suspended_error(user)

    if not user or not _is_active(user):
        # If _verify_token failed but token was present (and strict), it means invalid/inactive
        raise HTTPException(status_code=401, detail="Invalid token or inactive user")

    request.state.user = user
    return user

async def auth_middleware_onboarding(
    request: Request,
    token: HTTPAuthorizationCredentials = Security(security_strict),
    conn=Depends(get_connection)
):
    """
    Like auth_middleware, but also accepts users who have not finished onboarding yet.
    Only for the routes the onboarding wizard needs.
    """
    user = await _get_token_user(token, conn)

    if user and user["status"] == 'suspended':
        raise account_suspended_error(user)

    if not user or not user["is_active"] or user["status"] not in ('active', 'onboarding'):
        raise HTTPException(status_code=401, detail="Invalid token or inactive user")

    request.state.user = user
    return user

async def auth_middleware_optional(
    request: Request,
    token: Optional[HTTPAuthorizationCredentials] = Security(security_optional),
    conn=Depends(get_connection)
):
    """
    OPTIONAL authentication. Returns None if invalid/missing.
    Used for public routes that adapt to user context (e.g. /trials search).
    """
    user = await _verify_token(token, conn)
    if user:
        request.state.user = user
    return user
