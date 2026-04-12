"""
Notification Model — Raw SQL queries for the notifications table.
Follows Phase 1 DBModel pattern: all DB access through parameterized asyncpg queries.
"""
import json
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from app.models.base_model import DBModel


class NotificationModel(DBModel):
    """
    Encapsulates all SQL logic for the `notifications` table.
    """

    # ── READ ────────────────────────────────────────────────────────────

    async def get_by_id(self, notification_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single notification by ID."""
        query = """
            SELECT notification_id, user_id, type, title, message,
                   link, read, expires_at, created_at
            FROM notifications
            WHERE notification_id = $1
        """
        row = await self.conn.fetchrow(query, notification_id)
        return self._record_to_dict(row) if row else None

    async def get_user_notifications(
        self,
        user_id: str,
        *,
        read_status: Optional[bool] = None,
        notif_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Paginated list of notifications for a user with optional filters.
        Returns dict with 'data', 'unread_count', and 'meta'.
        """
        conditions = ["n.user_id = $1"]
        params: list = [user_id]
        idx = 2

        if read_status is not None:
            conditions.append(f"n.read = ${idx}")
            params.append(read_status)
            idx += 1

        if notif_type:
            conditions.append(f"n.type = ${idx}")
            params.append(notif_type)
            idx += 1

        if date_from:
            conditions.append(f"n.created_at >= ${idx}")
            params.append(date_from)
            idx += 1

        if date_to:
            conditions.append(f"n.created_at <= ${idx}")
            params.append(date_to)
            idx += 1

        where_clause = " AND ".join(conditions)

        # Total count
        count_query = f"SELECT COUNT(*) FROM notifications n WHERE {where_clause}"
        total = await self.conn.fetchval(count_query, *params)

        # Unread count (always for this user, ignoring other filters)
        unread_count = await self.conn.fetchval(
            "SELECT COUNT(*) FROM notifications WHERE user_id = $1 AND read = FALSE",
            user_id,
        )

        # Data
        offset = (page - 1) * limit
        data_query = f"""
            SELECT notification_id, user_id, type, title, message,
                   link, read, expires_at, created_at
            FROM notifications n
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
        """
        params.extend([limit, offset])
        rows = await self.conn.fetch(data_query, *params)

        return {
            "data": self._records_to_list(rows),
            "unread_count": unread_count,
            "meta": {
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": max(1, -(-total // limit)),  # ceil division
            },
        }

    async def get_unread_count(self, user_id: str) -> int:
        """Return unread notification count for a user."""
        query = "SELECT COUNT(*) FROM notifications WHERE user_id = $1 AND read = FALSE"
        return await self.conn.fetchval(query, user_id) or 0

    # ── WRITE ───────────────────────────────────────────────────────────

    async def create(
        self,
        user_id: str,
        notif_type: str,
        title: str,
        message: str,
        link: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Insert a new notification."""
        query = """
            INSERT INTO notifications (user_id, type, title, message, link, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING notification_id, user_id, type, title, message,
                      link, read, expires_at, created_at
        """
        row = await self.conn.fetchrow(
            query, user_id, notif_type, title, message, link, expires_at
        )
        return self._record_to_dict(row)

    async def bulk_create(
        self,
        notifications: List[Dict[str, Any]],
    ) -> int:
        """
        Insert multiple notifications at once. Returns count of inserted rows.
        Each dict must have: user_id, type, title, message. Optional: link, expires_at.
        """
        if not notifications:
            return 0

        values_parts = []
        params: list = []
        idx = 1

        for n in notifications:
            values_parts.append(
                f"(${idx}, ${idx+1}, ${idx+2}, ${idx+3}, ${idx+4}, ${idx+5})"
            )
            params.extend([
                n["user_id"],
                n["type"],
                n["title"],
                n["message"],
                n.get("link"),
                n.get("expires_at"),
            ])
            idx += 6

        query = f"""
            INSERT INTO notifications (user_id, type, title, message, link, expires_at)
            VALUES {', '.join(values_parts)}
        """
        result = await self.conn.execute(query, *params)
        # result is like 'INSERT 0 5'
        return int(result.split()[-1])

    # ── UPDATE ──────────────────────────────────────────────────────────

    async def mark_read(self, notification_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Mark a single notification as read (with ownership check)."""
        query = """
            UPDATE notifications
            SET read = TRUE
            WHERE notification_id = $1 AND user_id = $2
            RETURNING notification_id, user_id, type, title, message,
                      link, read, expires_at, created_at
        """
        row = await self.conn.fetchrow(query, notification_id, user_id)
        return self._record_to_dict(row) if row else None

    async def mark_all_read(self, user_id: str) -> int:
        """Mark all unread notifications as read for a user. Returns affected count."""
        result = await self.conn.execute(
            "UPDATE notifications SET read = TRUE WHERE user_id = $1 AND read = FALSE",
            user_id,
        )
        return int(result.split()[-1])

    # ── DELETE ──────────────────────────────────────────────────────────

    async def delete(self, notification_id: str, user_id: str) -> bool:
        """Delete notification (ownership-checked). Returns True if deleted."""
        result = await self.conn.execute(
            "DELETE FROM notifications WHERE notification_id = $1 AND user_id = $2",
            notification_id,
            user_id,
        )
        return result.endswith("1")

    async def delete_expired(self) -> int:
        """Cleanup expired notifications. Returns deleted count."""
        result = await self.conn.execute(
            "DELETE FROM notifications WHERE expires_at IS NOT NULL AND expires_at < NOW()"
        )
        return int(result.split()[-1])

    # ── ADMIN HELPERS ───────────────────────────────────────────────────

    async def get_all_active_user_ids(self) -> List[str]:
        """Return IDs of all active users on the platform."""
        rows = await self.conn.fetch(
            "SELECT id FROM users WHERE is_active = TRUE AND status = 'active'"
        )
        return [str(row["id"]) for row in rows]

    async def get_org_user_ids(self, org_id: str) -> List[str]:
        """Return IDs of all approved members of a specific organization."""
        rows = await self.conn.fetch(
            "SELECT user_id FROM organization_members WHERE org_id = $1 AND status = 'approved'",
            org_id
        )
        return [str(row["user_id"]) for row in rows]

    async def get_group_user_ids(self, group_id: str) -> List[str]:
        """Return IDs of all approved members of a working group."""
        rows = await self.conn.fetch(
            "SELECT user_id FROM working_group_members WHERE group_id = $1 AND status = 'approved'",
            group_id
        )
        return [str(row["user_id"]) for row in rows]

    async def get_admin_user_ids(self) -> List[str]:
        """Return IDs of all active admin users."""
        rows = await self.conn.fetch(
            "SELECT id FROM users WHERE user_type = 'admin' AND is_active = TRUE AND status = 'active'"
        )
        return [str(row["id"]) for row in rows]
