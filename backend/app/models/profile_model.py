from datetime import datetime
from typing import Optional, List, Dict, Union, Any
from app.models.base_model import DBModel
from app.schemas.user import UserDetailsResponse, UserProfileUpdate
import json

class ProfileModel(DBModel):
    """
    Profile model for raw SQL queries.
    Encapsulates all SQL logic related to 'user_profiles' table.
    """

    async def get_profile_by_user_id(self, user_id: str) -> Optional[UserDetailsResponse]:
        """
        Fetch complete profile joined with User data.
        Returns Pydantic model.
        """
        query = """
            SELECT 
                u.id, u.email, u.user_type, u.display_name, u.first_name, u.last_name, 
                u.country, u.language_preference, u.avatar, u.is_verified, 
                u.profile_completed, u.created_at, u.is_active,
                u.verification, u.notification_preferences,
                up.bio, up.interests, up.location, up.profile_visibility,
                up.notification_enabled, up.email_alerts, up.push_notifications
            FROM users u
            LEFT JOIN user_profiles up ON u.id = up.user_id
            WHERE u.id = $1
        """
        row = await self.conn.fetchrow(query, user_id)
        if not row:
            return None
            
        data = self._record_to_dict(row)

        if data.get("id"):
            data["id"] = str(data["id"])
        
        # Manually parse JSONB fields if they are strings (asyncpg default)
        if data.get("interests") and isinstance(data["interests"], str):
            try:
                data["interests"] = json.loads(data["interests"])
            except json.JSONDecodeError:
                data["interests"] = []
                
        for field in ['verification', 'notification_preferences']:
             if data.get(field) and isinstance(data[field], str):
                try:
                    data[field] = json.loads(data[field])
                except:
                    pass
                
        # Handle defaults for missing profile row (LEFT JOIN)
        if data.get("profile_visibility") is None:
            data["profile_visibility"] = "public"
            data["notification_enabled"] = True
            data["email_alerts"] = True
            data["push_notifications"] = False
            
        return UserDetailsResponse(**data)

    async def update_profile(self, user_id: str, updates: Dict[str, Any]):
        """
        Update user profile AND user base information.
        Separates user fields from profile fields.
        """
        users_fields = {
            "first_name", "last_name", "display_name", "country", "language_preference", "avatar"
        }
        profiles_fields = {
            "bio", "interests", "location", "profile_visibility", 
            "notification_enabled", "email_alerts", "push_notifications"
        }
        
        # Filter fields
        user_updates = {k: v for k, v in updates.items() if k in users_fields}
        profile_updates = {k: v for k, v in updates.items() if k in profiles_fields}

        # Handle JSON serialization for profile updates
        if "interests" in profile_updates and isinstance(profile_updates["interests"], (dict, list)):
            profile_updates["interests"] = json.dumps(profile_updates["interests"])

        # Update users table
        if user_updates:
            set_clauses = [f"{k} = ${i+2}" for i, k in enumerate(user_updates.keys())]
            set_clauses_str = ", ".join(set_clauses)
            query = f"UPDATE users SET {set_clauses_str}, updated_at = NOW() WHERE id = $1"
            await self.conn.execute(query, user_id, *user_updates.values())

        # Update user_profiles table
        if profile_updates:
            # Ensure profile exists
            exists_query = "SELECT 1 FROM user_profiles WHERE user_id = $1"
            exists = await self.conn.fetchval(exists_query, user_id)
            if not exists:
                await self.conn.execute(
                    "INSERT INTO user_profiles (user_id) VALUES ($1)", user_id
                )

            set_clauses = [f"{k} = ${i+2}" for i, k in enumerate(profile_updates.keys())]
            set_clauses_str = ", ".join(set_clauses)
            query = f"UPDATE user_profiles SET {set_clauses_str}, updated_at = NOW() WHERE user_id = $1"
            await self.conn.execute(query, user_id, *profile_updates.values())
            
        await self.recalculate_profile_completed(user_id)

    async def recalculate_profile_completed(self, user_id: str):
        """
        Recalculate 'profile_completed' flag based on required fields.
        """
        query = "SELECT first_name, last_name, country FROM users WHERE id = $1"
        row = await self.conn.fetchrow(query, user_id)
        
        if not row:
            return

        is_completed = all([row["first_name"], row["last_name"], row["country"] is not None])
        
        await self.conn.execute(
            "UPDATE users SET profile_completed = $1 WHERE id = $2", 
            is_completed, user_id
        )
