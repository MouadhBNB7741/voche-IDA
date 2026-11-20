"""
Event Model — Database logic for Events & Webinars.

All business logic and raw SQL queries live here.
Routes must NOT interact with the database directly.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import date

from app.models.base_model import DBModel

DETAIL_COLUMNS = """
    event_id, title, description, event_date, event_time,
    timezone, type, organizer, location, virtual_link,
    participants, max_participants, registration_deadline,
    status, tags, banner_image, approval_status, created_by,
    rejection_reason, reviewed_at, created_at, updated_at
"""


def can_view_event(event: Dict[str, Any], viewer: Optional[Dict[str, Any]]) -> bool:
    """Approved events are public. Others only show to the person who suggested them and to admins."""
    if event.get("approval_status", "approved") == "approved":
        return True
    if not viewer:
        return False
    return viewer.get("user_type") == "admin" or str(event.get("created_by")) == str(viewer.get("id"))


class EventModel(DBModel):
    """
    Model for Events & Webinars domain.
    Handles event listing, details, registration, cancellation, and user events.
    Uses raw asyncpg SQL — no ORM.
    """

    # ──────────────────────────────────────────────────────────────────────
    # HELPER: Deserialize JSONB → Python list
    # ──────────────────────────────────────────────────────────────────────
    @staticmethod
    def _deserialize_tags(data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure tags JSONB field is a proper Python list."""
        if isinstance(data.get("tags"), str):
            try:
                data["tags"] = json.loads(data["tags"])
            except Exception:
                data["tags"] = []
        if data.get("tags") is None:
            data["tags"] = []
        return data

    # ──────────────────────────────────────────────────────────────────────
    # 1. LIST EVENTS — with filters, sorting, pagination
    # ──────────────────────────────────────────────────────────────────────
    async def list_events(
        self,
        *,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        event_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        location: Optional[str] = None,
        organizer: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: list = []

        def add_param(value: Any) -> str:
            params.append(value)
            return f"${len(params)}"

        # The public list only shows approved events
        conditions = ["e.approval_status = 'approved'"]

        if event_type:
            ph = add_param(event_type)
            conditions.append(f"e.type = {ph}")
        if date_from:
            ph = add_param(date_from)
            conditions.append(f"e.event_date >= {ph}")
        if date_to:
            ph = add_param(date_to)
            conditions.append(f"e.event_date <= {ph}")
        if location:
            ph = add_param(f"%{location}%")
            conditions.append(f"e.location ILIKE {ph}")
        if organizer:
            ph = add_param(f"%{organizer}%")
            conditions.append(f"e.organizer ILIKE {ph}")
        
        if status:
            ph = add_param(status)
            conditions.append(f"e.status = {ph}")
        else:
            # Default: hide cancelled events
            conditions.append("e.status != 'cancelled'")

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        # Count query
        count_sql = f"SELECT COUNT(*) FROM events e {where_clause}"
        total = await self.conn.fetchval(count_sql, *params) or 0

        # Sorting: upcoming events first, then by event_date ASC
        order_by = """
            CASE WHEN e.event_date >= CURRENT_DATE THEN 0 ELSE 1 END ASC,
            e.event_date ASC
        """

        # Pagination: apply only when page/limit are provided
        pagination_clause = ""
        if page is not None and limit is not None:
            offset = (page - 1) * limit
            offset_ph = add_param(offset)
            limit_ph = add_param(limit)
            pagination_clause = f"OFFSET {offset_ph} LIMIT {limit_ph}"

        query = f"""
            SELECT
                e.event_id, e.title, e.event_date, e.event_time,
                e.type, e.organizer, e.location, e.participants, e.status,
                e.registration_deadline
            FROM events e
            {where_clause}
            ORDER BY {order_by}
            {pagination_clause}
        """
        records = await self.conn.fetch(query, *params)
        items = self._records_to_list(records)

        # If authenticated, attach registration_status per event
        if user_id:
            event_ids = [item["event_id"] for item in items]
            if event_ids:
                reg_query = """
                    SELECT event_id, status
                    FROM event_registrations
                    WHERE user_id = $1
                      AND event_id = ANY($2)
                """
                reg_records = await self.conn.fetch(reg_query, user_id, event_ids)
                reg_map = {str(r["event_id"]): r["status"] for r in reg_records}
                for item in items:
                    item["registration_status"] = reg_map.get(
                        str(item["event_id"]), None
                    )

        # Build meta
        effective_limit = limit if limit else total
        pages = (total + effective_limit - 1) // effective_limit if effective_limit > 0 else 0
        effective_page = page if page else 1

        return {
            "data": items,
            "meta": {
                "total": total,
                "page": effective_page,
                "limit": effective_limit,
                "pages": pages,
            },
        }

    # ──────────────────────────────────────────────────────────────────────
    # 2. GET EVENT DETAILS
    # ──────────────────────────────────────────────────────────────────────
    async def get_event_details(
        self,
        event_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        query = f"""
            SELECT {DETAIL_COLUMNS}
            FROM events
            WHERE event_id = $1
        """
        record = await self.conn.fetchrow(query, event_id)
        if not record:
            return None

        data = self._record_to_dict(record)
        data = self._deserialize_tags(data)

        # Attach registration_status if authenticated
        if user_id:
            reg_query = """
                SELECT status FROM event_registrations
                WHERE event_id = $1 AND user_id = $2
                  AND status != 'cancelled'
            """
            reg = await self.conn.fetchrow(reg_query, event_id, user_id)
            data["registration_status"] = reg["status"] if reg else None
        else:
            data["registration_status"] = None

        return data

    # ──────────────────────────────────────────────────────────────────────
    # 3. REGISTER FOR EVENT — full transactional logic
    # ──────────────────────────────────────────────────────────────────────
    async def register_for_event(
        self,
        event_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        async with self.conn.transaction():
            # 1. Prevent duplicate registration (active)
            existing = await self.conn.fetchrow(
                """
                SELECT registration_id, status
                FROM event_registrations
                WHERE event_id = $1 AND user_id = $2
                """,
                event_id,
                user_id,
            )
            if existing:
                if existing["status"] != "cancelled":
                    raise ValueError("You are already registered for this event")

            # 2. Verify event exists
            event = await self.conn.fetchrow(
                """
                SELECT event_id, registration_deadline, participants,
                       max_participants, status
                FROM events
                WHERE event_id = $1 AND approval_status = 'approved'
                """,
                event_id,
            )
            if not event:
                raise ValueError("Event not found")

            # 3. Check event is not cancelled/completed
            if event["status"] in ("cancelled", "completed"):
                raise ValueError(f"Event is {event['status']} and cannot accept registrations")

            # 4. Check registration deadline
            from datetime import datetime, timezone as tz

            if event["registration_deadline"]:
                now = datetime.now(tz.utc)
                if now > event["registration_deadline"]:
                    raise ValueError("Registration deadline has passed")

            # 5. Check capacity
            if event["max_participants"] is not None:
                if event["participants"] >= event["max_participants"]:
                    raise ValueError("Event is full — no more spots available")

            if existing and existing["status"] == "cancelled":
                # Re-activate cancelled registration
                await self.conn.execute(
                    """
                    UPDATE event_registrations
                    SET status = 'registered', updated_at = NOW()
                    WHERE event_id = $1 AND user_id = $2
                    """,
                    event_id,
                    user_id,
                )
                # Increment participants
                await self.conn.execute(
                    """
                    UPDATE events
                    SET participants = participants + 1, updated_at = NOW()
                    WHERE event_id = $1
                    """,
                    event_id,
                )
                return {
                    "status": "registered",
                    "message": "You have successfully registered for this event.",
                }

            # 6. Insert registration
            await self.conn.execute(
                """
                INSERT INTO event_registrations (event_id, user_id, status, registered_at)
                VALUES ($1, $2, 'registered', NOW())
                """,
                event_id,
                user_id,
            )

            # 7. Increment participants
            await self.conn.execute(
                """
                UPDATE events
                SET participants = participants + 1, updated_at = NOW()
                WHERE event_id = $1
                """,
                event_id,
            )

        return {
            "status": "registered",
            "message": "You have successfully registered for this event.",
        }

    # ──────────────────────────────────────────────────────────────────────
    # 4. CANCEL REGISTRATION — transactional
    # ──────────────────────────────────────────────────────────────────────
    async def cancel_registration(
        self,
        event_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        async with self.conn.transaction():
            # 1. Check registration exists and is active
            reg = await self.conn.fetchrow(
                """
                SELECT registration_id, status
                FROM event_registrations
                WHERE event_id = $1 AND user_id = $2
                """,
                event_id,
                user_id,
            )
            if not reg:
                raise ValueError("No registration found for this event")
            if reg["status"] == "cancelled":
                raise ValueError("Registration is already cancelled")

            # 2. Update status to cancelled
            await self.conn.execute(
                """
                UPDATE event_registrations
                SET status = 'cancelled', updated_at = NOW()
                WHERE event_id = $1 AND user_id = $2
                """,
                event_id,
                user_id,
            )

            # 3. Decrement participants
            await self.conn.execute(
                """
                UPDATE events
                SET participants = GREATEST(participants - 1, 0), updated_at = NOW()
                WHERE event_id = $1
                """,
                event_id,
            )

        return {
            "status": "cancelled",
            "message": "Registration cancelled successfully.",
        }

    # ──────────────────────────────────────────────────────────────────────
    # 5. GET USER EVENTS (My Events)
    # ──────────────────────────────────────────────────────────────────────
    async def get_user_events(
        self,
        user_id: str,
        *,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        params: list = [user_id]

        def add_param(value: Any) -> str:
            params.append(value)
            return f"${len(params)}"

        where_clause = """
            WHERE er.user_id = $1
              AND er.status != 'cancelled'
        """

        # Count
        count_sql = f"""
            SELECT COUNT(*)
            FROM event_registrations er
            JOIN events e ON er.event_id = e.event_id
            {where_clause}
        """
        total = await self.conn.fetchval(count_sql, *params) or 0

        # Pagination
        pagination_clause = ""
        if page is not None and limit is not None:
            offset = (page - 1) * limit
            offset_ph = add_param(offset)
            limit_ph = add_param(limit)
            pagination_clause = f"OFFSET {offset_ph} LIMIT {limit_ph}"

        query = f"""
            SELECT
                e.event_id, e.title, e.event_date, e.event_time,
                e.type, e.organizer, e.location, e.virtual_link,
                e.participants, e.status as status,
                er.status as registration_status
            FROM event_registrations er
            JOIN events e ON er.event_id = e.event_id
            {where_clause}
            ORDER BY e.event_date ASC
            {pagination_clause}
        """
        records = await self.conn.fetch(query, *params)
        items = self._records_to_list(records)

        effective_limit = limit if limit else (total if total > 0 else 1)
        pages = (total + effective_limit - 1) // effective_limit if effective_limit > 0 else 0
        effective_page = page if page else 1

        return {
            "data": items,
            "meta": {
                "total": total,
                "page": effective_page,
                "limit": effective_limit,
                "pages": pages,
            },
        }

    # ──────────────────────────────────────────────────────────────────────
    # 6. SUGGESTED EVENTS AND APPROVAL
    # ──────────────────────────────────────────────────────────────────────
    async def create_event(
        self, created_by: str, payload: Dict[str, Any], approval_status: str
    ) -> Dict[str, Any]:
        row = await self.conn.fetchrow(
            f"""
            INSERT INTO events (
                title, description, type, organizer, event_date, event_time, timezone,
                location, virtual_link, max_participants, registration_deadline, tags,
                status, approval_status, created_by,
                reviewed_by, reviewed_at
            )
            VALUES (
                $1, $2, $3, $4, $5, $6, $7,
                $8, $9, $10, $11, $12::jsonb,
                'upcoming', $13::varchar, $14::uuid,
                CASE WHEN $13::varchar = 'approved' THEN $14::uuid ELSE NULL END,
                CASE WHEN $13::varchar = 'approved' THEN NOW() ELSE NULL END
            )
            RETURNING {DETAIL_COLUMNS}
            """,
            payload["title"], payload["description"], payload["type"], payload["organizer"],
            payload["event_date"], payload["event_time"], payload.get("timezone") or "UTC",
            payload.get("location"), payload.get("virtual_link"), payload.get("max_participants"),
            payload.get("registration_deadline"), json.dumps(payload.get("tags") or []),
            approval_status, created_by,
        )
        data = self._deserialize_tags(self._record_to_dict(row))
        data["registration_status"] = None
        return data

    async def list_by_creator(self, user_id: str, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        total = await self.conn.fetchval("SELECT COUNT(*) FROM events WHERE created_by = $1", user_id) or 0
        rows = await self.conn.fetch(
            f"""
            SELECT {DETAIL_COLUMNS} FROM events
            WHERE created_by = $1
            ORDER BY created_at DESC
            OFFSET $2 LIMIT $3
            """,
            user_id, (page - 1) * limit, limit,
        )
        return {
            "data": [self._deserialize_tags(r) for r in self._records_to_list(rows)],
            "meta": {"total": total, "page": page, "limit": limit, "pages": (total + limit - 1) // limit},
        }

    async def list_pending(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        total = await self.conn.fetchval("SELECT COUNT(*) FROM events WHERE approval_status = 'pending'") or 0
        rows = await self.conn.fetch(
            f"""
            SELECT s.*, u.display_name AS suggester_name, u.email AS suggester_email, u.user_type AS suggester_type
            FROM (SELECT {DETAIL_COLUMNS} FROM events WHERE approval_status = 'pending') s
            LEFT JOIN users u ON u.id = s.created_by
            ORDER BY s.created_at ASC
            OFFSET $1 LIMIT $2
            """,
            (page - 1) * limit, limit,
        )
        return {
            "data": [self._deserialize_tags(r) for r in self._records_to_list(rows)],
            "meta": {"total": total, "page": page, "limit": limit, "pages": (total + limit - 1) // limit},
        }

    async def get_for_decision(self, event_id: str) -> Optional[Dict[str, Any]]:
        row = await self.conn.fetchrow(
            "SELECT event_id, title, approval_status, created_by FROM events WHERE event_id = $1 FOR UPDATE",
            event_id,
        )
        return self._record_to_dict(row) if row else None

    async def set_approval(
        self, event_id: str, status: str, reviewer_id: str, reason: Optional[str]
    ) -> Dict[str, Any]:
        row = await self.conn.fetchrow(
            """
            UPDATE events
            SET approval_status = $2::varchar,
                reviewed_by = $3,
                reviewed_at = NOW(),
                rejection_reason = CASE WHEN $2::varchar = 'rejected' THEN $4 ELSE NULL END,
                updated_at = NOW()
            WHERE event_id = $1
            RETURNING event_id AS id, approval_status, reviewed_at, rejection_reason
            """,
            event_id, status, reviewer_id, reason,
        )
        return self._record_to_dict(row)
