from typing import Optional, Dict, Any
from app.models.base_model import DBModel
import json

class UserModel(DBModel):
    """
    User model for raw SQL queries.
    Encapsulates all SQL logic related to 'users' table.
    """
    
    _LOGIN_COLUMNS = """
        id, email, password_hash, user_type, is_active, status, deletion_scheduled_at,
        suspended_until, suspended_reason
    """

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Fetch user by email."""
        query = f"SELECT {self._LOGIN_COLUMNS} FROM users WHERE email = $1"
        user = await self.conn.fetchrow(query, email)
        return self._record_to_dict(user) if user else None

    async def get_by_email_any_case(self, email: str) -> Optional[Dict[str, Any]]:
        """Fetch user by email, ignoring upper and lower case (John@x.com is john@x.com)."""
        query = f"""
            SELECT {self._LOGIN_COLUMNS} FROM users
            WHERE LOWER(email) = LOWER($1)
            ORDER BY created_at
            LIMIT 1
        """
        user = await self.conn.fetchrow(query, email)
        return self._record_to_dict(user) if user else None

    # ── Social sign-in accounts ──────────────────────────────────────────────

    async def get_by_oauth_account(self, provider: str, provider_user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch the user linked to a Google (or other provider) account."""
        query = f"""
            SELECT {self._LOGIN_COLUMNS} FROM users
            WHERE id = (
                SELECT user_id FROM user_oauth_accounts
                WHERE provider = $1 AND provider_user_id = $2
            )
        """
        user = await self.conn.fetchrow(query, provider, provider_user_id)
        return self._record_to_dict(user) if user else None

    async def link_oauth_account(self, user_id: str, provider: str, provider_user_id: str, provider_email: str) -> None:
        await self.conn.execute("""
            INSERT INTO user_oauth_accounts (user_id, provider, provider_user_id, provider_email)
            VALUES ($1, $2, $3, $4)
        """, user_id, provider, provider_user_id, provider_email)

    async def update_oauth_email(self, provider: str, provider_user_id: str, provider_email: str) -> None:
        """Keep the provider's email up to date (the user may have changed it there)."""
        await self.conn.execute("""
            UPDATE user_oauth_accounts SET provider_email = $3
            WHERE provider = $1 AND provider_user_id = $2 AND provider_email IS DISTINCT FROM $3
        """, provider, provider_user_id, provider_email)

    # ── Account states ───────────────────────────────────────────────────────

    async def lift_expired_suspension(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """If this user's suspension has ended, make the account active again.
        Returns the user with its up-to-date status. A ban (no end date) never ends."""
        if user.get("status") != "suspended" or not user.get("suspended_until"):
            return user
        row = await self.conn.fetchrow("""
            UPDATE users
            SET status = 'active', suspended_until = NULL, suspended_reason = NULL, updated_at = NOW()
            WHERE id = $1 AND status = 'suspended' AND suspended_until <= NOW()
            RETURNING status, suspended_until, suspended_reason
        """, user["id"])
        return {**user, **dict(row)} if row else user

    async def lift_all_expired_suspensions(self) -> str:
        """Make every account whose suspension has ended active again."""
        return await self.conn.execute("""
            UPDATE users
            SET status = 'active', suspended_until = NULL, suspended_reason = NULL, updated_at = NOW()
            WHERE status = 'suspended' AND suspended_until <= NOW()
        """)

    async def complete_onboarding(self, user_id: str, user_type: Optional[str]) -> None:
        """Save the chosen role (if the user had none) and mark onboarding as finished."""
        await self.conn.execute("""
            UPDATE users SET
                user_type = COALESCE(user_type, $2),
                status = CASE WHEN status = 'onboarding' THEN 'active' ELSE status END,
                onboarding_completed_at = COALESCE(onboarding_completed_at, NOW()),
                updated_at = NOW()
            WHERE id = $1
        """, user_id, user_type)

    async def cancel_deletion(self, user_id: str) -> bool:
        """Cancel a scheduled account deletion. Returns False if none was scheduled."""
        cancelled = await self.conn.fetchval("""
            UPDATE users SET deletion_scheduled_at = NULL, updated_at = NOW()
            WHERE id = $1 AND deletion_scheduled_at IS NOT NULL
            RETURNING id
        """, user_id)
        return cancelled is not None

    async def get_users_due_for_deletion(self) -> list:
        """Users whose 7-day deletion grace period has passed and who are not anonymized yet."""
        rows = await self.conn.fetch("""
            SELECT id FROM users
            WHERE deletion_scheduled_at <= NOW() AND status <> 'deleted'
        """)
        return [row["id"] for row in rows]

    # Rows that only describe the person, removed when the account is anonymized.
    # Posts, comments, likes, ratings, reports, survey answers and event registrations
    # are kept and now belong to "Deleted User".
    _PERSONAL_DATA_TABLES = (
        "user_profiles", "doctor_verifications", "password_reset_tokens", "notifications",
        "trial_saves", "trial_alerts", "organization_members", "working_group_members",
        "user_oauth_accounts",
    )

    async def anonymize_user(self, user_id: str) -> Dict[str, Any]:
        """Remove a user's personal data but keep the account row, so their posts and
        comments stay and show "Deleted User". The user can no longer log in.
        Returns the old avatar URL and licence files, so the caller can delete the files."""
        async with self.conn.transaction():
            avatar = await self.conn.fetchval(
                "SELECT avatar FROM users WHERE id = $1 FOR UPDATE", user_id
            )
            documents = await self.conn.fetch(
                "SELECT document_url FROM doctor_verifications WHERE user_id = $1 AND document_url IS NOT NULL",
                user_id,
            )
            await self.conn.execute("""
                UPDATE users SET
                    email = 'deleted-' || id || '@deleted.invalid',
                    password_hash = NULL,
                    display_name = 'Deleted User',
                    first_name = NULL,
                    last_name = NULL,
                    country = NULL,
                    avatar = NULL,
                    verification = '{"status": "not_submitted"}'::jsonb,
                    status = 'deleted',
                    is_active = FALSE,
                    is_verified = FALSE,
                    suspended_until = NULL,
                    suspended_reason = NULL,
                    last_login = NULL,
                    updated_at = NOW()
                WHERE id = $1
            """, user_id)
            for table in self._PERSONAL_DATA_TABLES:
                await self.conn.execute(f"DELETE FROM {table} WHERE user_id = $1", user_id)
            for table in ("user_activity_log", "platform_feedback"):
                await self.conn.execute(
                    f"UPDATE {table} SET ip_address = NULL, user_agent = NULL WHERE user_id = $1", user_id
                )
        return {"avatar": avatar, "documents": [row["document_url"] for row in documents]}

    async def get_display_name(self, user_id: str, default: str = "Someone") -> str:
        """The name other members see: display name, else first and last name."""
        name = await self.conn.fetchval(
            "SELECT COALESCE(NULLIF(TRIM(display_name), ''), NULLIF(TRIM(CONCAT(first_name, ' ', last_name)), '')) "
            "FROM users WHERE id = $1",
            user_id,
        )
        return name or default

    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch user by ID."""
        query = """
            SELECT id, email, user_type, is_active, status, 
                   first_name, last_name, display_name, profile_completed, is_verified,
                   last_login, created_at, notification_preferences, verification, deletion_scheduled_at
            FROM users
            WHERE id = $1
        """
        user = await self.conn.fetchrow(query, user_id)
        if not user:
            return None
            
        data = self._record_to_dict(user)
        for field in ['notification_preferences', 'verification']:
            if isinstance(data.get(field), str):
                try:
                    data[field] = json.loads(data[field])
                except:
                    pass
        return data

    async def create_user(
        self, 
        email: str,
        password_hash: Optional[str],
        user_type: Optional[str],
        first_name: str,
        last_name: str,
        display_name: str,
        status: str = "active",
    ) -> Dict[str, Any]:
        """Create new user and associated profile atomically.
        Google sign-in users have no password, and no role until onboarding ("onboarding" status)."""
        query_user = """
            INSERT INTO users (
                email, password_hash, user_type,
                first_name, last_name, display_name,
                status, is_active, is_verified, profile_completed,
                notification_preferences, verification
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, FALSE, FALSE, '{"emailAlerts": true, "pushNotifications": true, "frequency": "instant", "notificationTypes": {"trial_match": true, "trial_alert": true, "community_reply": true, "community_like": true, "event_reminder": true, "event_update": true, "org_request_update": true, "resource_update": true, "survey_available": true, "system_announcement": true}}'::jsonb, '{"status": "not_submitted"}'::jsonb)
            RETURNING id, user_type
        """
        
        user = await self.conn.fetchrow(
            query_user, 
            email, password_hash, user_type, first_name, last_name, display_name, status
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
