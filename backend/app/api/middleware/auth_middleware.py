from typing import Optional
from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_jwt
from app.api.dependencies.connections import get_connection

# Define schemes
security_strict = HTTPBearer(auto_error=True)
security_optional = HTTPBearer(auto_error=False)

async def _verify_token(token_creds: Optional[HTTPAuthorizationCredentials], conn) -> Optional[dict]:
    """Shared logic for decoding and verifying user."""
    if not token_creds:
        return None
        
    try:
        payload = decode_jwt(token_creds.credentials)
        user_id = payload.get("sub")
        if not user_id:
            return None
            
        user = await conn.fetchrow("""
            SELECT id, email, user_type, is_active, status 
            FROM users 
            WHERE id = $1
        """, user_id)

        if not user:
            return None
            
        # Global active check
        if not user["is_active"] or user["status"] != 'active':
            return None
            
        return dict(user)
    except Exception:
        return None

async def auth_middleware(
    request: Request,
    token: HTTPAuthorizationCredentials = Security(security_strict),
    conn=Depends(get_connection)
):
    """
    STRICT authentication. Raises 401/403 if invalid.
    Used for protected routes (e.g. /me, /update-password).
    """
    user = await _verify_token(token, conn)
    
    if not user:
        # If _verify_token failed but token was present (and strict), it means invalid/inactive
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
