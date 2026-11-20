"""
HCP middleware — restricts endpoints to verified healthcare professionals.
Composable with auth_middleware, like admin_middleware.
"""
from fastapi import Depends, HTTPException

from app.api.dependencies.connections import get_connection
from app.api.middleware.auth_middleware import auth_middleware


async def verified_hcp_required(
    current_user: dict = Depends(auth_middleware),
    conn=Depends(get_connection),
) -> dict:
    """Require user_type 'hcp' with an approved verification (users.is_verified)."""
    if current_user.get("user_type") != "hcp":
        raise HTTPException(status_code=403, detail="HCP role required")
    if not await conn.fetchval("SELECT is_verified FROM users WHERE id = $1", current_user["id"]):
        raise HTTPException(status_code=403, detail="HCP verification required")
    return current_user
