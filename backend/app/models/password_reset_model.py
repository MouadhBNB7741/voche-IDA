from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from app.models.base_model import DBModel
import secrets

class PasswordResetModel(DBModel):
    """
    Password reset token management.
    Handles SQL for creating and validating tokens.
    """

    async def create_token(self, user_id: str) -> str:
        """Create new token, invalidate old ones."""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # Atomically replace old token
        async with self.conn.transaction():
            # Invalidate old tokens for user
            await self.conn.execute(
                "UPDATE password_reset_tokens SET used = TRUE WHERE user_id = $1", 
                user_id
            )
            # Insert new token
            await self.conn.execute(
                """
                INSERT INTO password_reset_tokens (user_id, token, expires_at)
                VALUES ($1, $2, $3)
                """,
                user_id, token, expires_at
            )
        return token

    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Check if token is valid, unused, and not expired.
        """
        query = """
            SELECT id, user_id, expires_at, used
            FROM password_reset_tokens
            WHERE token = $1
        """
        row = await self.conn.fetchrow(query, token)
        
        if not row:
            return None
            
        record = self._record_to_dict(row)
        
        if record["used"]:
            return {"valid": False, "reason": "used"}
            
        if datetime.now(timezone.utc) > record["expires_at"]:
            return {"valid": False, "reason": "expired"}
            
        return {"valid": True, "user_id": record["user_id"], "token_id": record["id"]}

    async def mark_token_used(self, token_id: str):
        """Mark specific token as used."""
        await self.conn.execute(
            "UPDATE password_reset_tokens SET used = TRUE, used_at = NOW() WHERE id = $1",
            token_id
        )
