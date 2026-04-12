"""
Admin middleware — Restricts endpoints to Platform Admin users.
Phase 2 extension: composable with auth_middleware.
"""
from fastapi import Depends, HTTPException, Request
from app.api.middleware.auth_middleware import auth_middleware


async def admin_required(
    current_user: dict = Depends(auth_middleware),
) -> dict:
    """
    Require Platform Admin role.
    Must be used AFTER auth_middleware (composable via Depends chain).

    Raises 403 if user is not an admin.
    """
    if current_user.get("user_type") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Platform admin access required",
        )
    return current_user
