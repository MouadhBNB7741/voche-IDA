from fastapi import Header, HTTPException, Depends
from app.core.security import decode_jwt
from app.api.dependencies.connections import get_connection


async def get_current_user(
    authorization: str = Header(..., description="Bearer <token>"),
    conn=Depends(get_connection)
):
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Invalid Authorization header")

    token = authorization.split(" ")[1]
    try:
        payload = decode_jwt(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    # user_type might be in the token, but we should verify against DB
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Adjusted query to match new schema: user_type instead of role
    user = await conn.fetchrow("""
        SELECT id, email, user_type, is_active, status
        FROM users
        WHERE id = $1
    """, user_id)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not user["is_active"] or user["status"] != 'active':
        raise HTTPException(status_code=401, detail="User inactive or suspended")

    return {
        "id": str(user["id"]),
        "email": user["email"],
        "user_type": user["user_type"],
        # Add other fields if needed
    }
