from fastapi import Header, HTTPException, Depends
from app.core.security import decode_jwt
from app.api.dependencies.connections import get_connection


async def get_current_user(
    authorization: str = Header(...),
    conn=Depends(get_connection)
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Invalid Authorization header")

    token = authorization.split(" ")[1]
    payload = decode_jwt(token)

    user_id = payload.get("sub")
    role = payload.get("role")

    if not user_id or not role:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await conn.fetchrow("""
        SELECT id, email, role, is_active, subscription_tier_id, api_key
        FROM users
        WHERE id = $1
    """, user_id)

    if not user or not user["is_active"]:
        raise HTTPException(
            status_code=401, detail="User not found or inactive")

    return {
        "id": str(user["id"]),
        "email": user["email"],
        "role": user["role"],
        "subscription_tier_id": user.get("subscription_tier_id"),
        "api_key": user.get("api_key")
    }
