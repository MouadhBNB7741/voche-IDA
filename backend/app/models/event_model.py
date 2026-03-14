"""
Event Model — Database logic for Events & Webinars.

All business logic and raw SQL queries live here.
Routes must NOT interact with the database directly.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import date

from app.models.base_model import DBModel


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

        conditions = []

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
                e.type, e.organizer, e.location, e.participants, e.status
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
        query = """
            SELECT
                event_id, title, description, event_date, event_time,
                timezone, type, organizer, location, virtual_link,
                participants, max_participants, registration_deadline,
                status, tags, banner_image, created_at, updated_at
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
                WHERE event_id = $1
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
