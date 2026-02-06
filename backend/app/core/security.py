from fastapi import HTTPException
import jwt
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
from app.core.config import settings

# Changed scheme to argon2
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

JWT_ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)

def create_jwt(payload: dict, expires_minutes: int = 60):
    payload = payload.copy()
    # Use timezone-aware UTC to avoid deprecation warnings in Python 3.12+
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    return jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)

def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(
            token, 
            settings.secret_key, 
            algorithms=[JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError: # Generic catch for any JWT issue
        raise HTTPException(status_code=401, detail="Invalid token")