from typing import Optional, Dict, Any
from app.models.base_model import DBModel

class UserModel(DBModel):
    """
    User model for raw SQL queries.
    Encapsulates all SQL logic related to 'users' table.
    """
    
    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Fetch user by email."""
        query = """
            SELECT id, email, password_hash, user_type, is_active, status
            FROM users
            WHERE email = $1
        """
        user = await self.conn.fetchrow(query, email)
        return self._record_to_dict(user) if user else None

    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch user by ID."""
        query = """
            SELECT id, email, user_type, is_active, status, 
                   first_name, last_name, display_name, profile_completed, is_verified,
                   last_login, created_at
            FROM users
            WHERE id = $1
        """
        user = await self.conn.fetchrow(query, user_id)
        return self._record_to_dict(user) if user else None

    async def create_user(
        self, 
        email: str, 
        password_hash: str, 
        user_type: str, 
        first_name: str, 
        last_name: str, 
        display_name: str
    ) -> Dict[str, Any]:
        """Create new user and associated profile atomically."""
        query_user = """
            INSERT INTO users (
                email, password_hash, user_type, 
                first_name, last_name, display_name,
                status, is_active, is_verified, profile_completed
            )
            VALUES ($1, $2, $3, $4, $5, $6, 'active', TRUE, FALSE, FALSE)
            RETURNING id, user_type
        """
        
        # Transaction should be handled by caller (router dependency: get_transaction) which provides 'conn'
        # But if 'conn' is just a pool connection, inside models we assume caller manages transaction boundary
        # for complex operations, OR we do manual BEGIN? 
        # The prompt says 'conn=Depends(get_transaction)' in router, so self.conn is already in transaction context if needed.
        
        user = await self.conn.fetchrow(
            query_user, 
            email, password_hash, user_type, first_name, last_name, display_name
        )
        
        # Create empty profile
        query_profile = "INSERT INTO user_profiles (user_id) VALUES ($1)"
        await self.conn.execute(query_profile, user['id'])
        
        return self._record_to_dict(user)

    async def update_last_login(self, user_id: str):
        """Update last login timestamp."""
        query = "UPDATE users SET last_login = NOW() WHERE id = $1"
        await self.conn.execute(query, user_id)

    async def update_password(self, user_id: str, new_hash: str):
        """Update user password."""
        query = "UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2"
        await self.conn.execute(query, new_hash, user_id)

    async def get_password_hash(self, user_id: str) -> Optional[str]:
        """Get password hash for verification."""
        query = "SELECT password_hash FROM users WHERE id = $1"
        user = await self.conn.fetchrow(query, user_id)
        return user['password_hash'] if user else None

    async def check_email_exists(self, email: str) -> bool:
        """Check if email is already registered."""
        query = "SELECT 1 FROM users WHERE email = $1"
        exists = await self.conn.fetchval(query, email)
        return bool(exists)
