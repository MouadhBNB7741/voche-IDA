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
                   last_login, created_at, notification_preferences, verification
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
                status, is_active, is_verified, profile_completed,
                notification_preferences, verification
            )
            VALUES ($1, $2, $3, $4, $5, $6, 'active', TRUE, FALSE, FALSE, '{"emailAlerts": true, "pushNotifications": true, "frequency": "instant"}'::jsonb, '{"status": "not_submitted"}'::jsonb)
            RETURNING id, user_type
        """
        
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

    async def update_notification_preferences(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update notification preferences with deep merge."""
        import json
        
        # Fetch current
        current_query = "SELECT notification_preferences FROM users WHERE id = $1"
        current_raw = await self.conn.fetchval(current_query, user_id)
        
        current_dict = {}
        if current_raw:
            if isinstance(current_raw, str):
                current_dict = json.loads(current_raw)
            else:
                current_dict = dict(current_raw) # Assuming asyncpg parses jsonb directly if configured, or returns dict-like
        
        # Deep Merge
        def deep_merge(target, source):
            for k, v in source.items():
                if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                    deep_merge(target[k], v)
                else:
                    target[k] = v
            return target

        updated_dict = deep_merge(current_dict, updates)
        
        # Update
        update_query = "UPDATE users SET notification_preferences = $1 WHERE id = $2 RETURNING notification_preferences"
        # Converting to json string to be safe with asyncpg default jsonb handling
        new_prefs = await self.conn.fetchval(update_query, json.dumps(updated_dict), user_id)
        
        if new_prefs and isinstance(new_prefs, str):
            new_prefs = json.loads(new_prefs)
        
        return {"notification_preferences": new_prefs} if new_prefs else {}

    async def submit_verification(self, user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Submit verification documents."""
        import json
        
        # Check current status
        query_check = "SELECT verification FROM users WHERE id = $1"
        current_raw = await self.conn.fetchval(query_check, user_id)
        
        current_ver = {}
        if current_raw:
             current_ver = json.loads(current_raw) if isinstance(current_raw, str) else dict(current_raw)
             
        if current_ver.get("status") == "pending_verification":
             raise ValueError("Verification already pending")
             
        update_query = "UPDATE users SET verification = $1 WHERE id = $2 RETURNING verification"
        new_ver_raw = await self.conn.fetchval(update_query, json.dumps(payload), user_id)
        
        if new_ver_raw and isinstance(new_ver_raw, str):
            new_ver_raw = json.loads(new_ver_raw)
        
        # Identify Admins and Notify
        try:
             admin_query = "SELECT id FROM users WHERE user_type = 'admin'"
             admins = await self.conn.fetch(admin_query)
             
             notif_query = """
                 INSERT INTO notifications (user_id, type, title, message, created_at)
                 VALUES ($1, 'system', 'Verification Request', 'A new verification request has been submitted.', NOW())
             """
             for admin in admins:
                  await self.conn.execute(notif_query, admin['id'])
        except Exception as e:
             print(f"Failed to notify admins: {e}")
             pass

        return {"verification": new_ver_raw} if new_ver_raw else {}

    async def delete_verification(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Delete verification data."""
        import json
        
        # Get current to return it
        query_get = "SELECT verification FROM users WHERE id = $1"
        current_raw = await self.conn.fetchval(query_get, user_id)
        
        current_ver = {}
        if current_raw:
             current_ver = json.loads(current_raw) if isinstance(current_raw, str) else dict(current_raw)
        
        # Reset to not_submitted
        reset_payload = {"status": "not_submitted"}
        query_update = "UPDATE users SET verification = $1 WHERE id = $2"
        await self.conn.execute(query_update, json.dumps(reset_payload), user_id)
        
        return current_ver

    async def update_verification(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update verification data."""
        import json
        
        # Get current
        query_get = "SELECT verification FROM users WHERE id = $1"
        current_raw = await self.conn.fetchval(query_get, user_id)
        
        current_ver = {}
        if current_raw:
             current_ver = json.loads(current_raw) if isinstance(current_raw, str) else dict(current_raw)
             
        # Merge updates
        current_ver.update(updates)
        
        # Save
        query_update = "UPDATE users SET verification = $1 WHERE id = $2 RETURNING verification"
        new_ver_raw = await self.conn.fetchval(query_update, json.dumps(current_ver), user_id)
        
        if new_ver_raw and isinstance(new_ver_raw, str):
            new_ver_raw = json.loads(new_ver_raw)
            
        return {"verification": new_ver_raw} if new_ver_raw else {}
