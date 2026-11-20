import json
from typing import Any, Dict, List, Optional
from uuid import UUID
from app.models.base_model import DBModel

# What any reader may see about a resource (the storage key of its file stays internal)
PUBLIC_COLUMNS = """
    resource_id, title, type, category, description,
    url, language, duration, author, tags, published_date,
    downloads, rating, featured, requires_auth,
    approval_status, (file_key IS NOT NULL) AS has_file, file_name, file_type, file_size,
    created_at, updated_at
"""
SUBMISSION_COLUMNS = PUBLIC_COLUMNS + ", submitted_by, rejection_reason, reviewed_at"


def _clean_tags(item: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(item.get("tags"), str):
        try:
            item["tags"] = json.loads(item["tags"])
        except Exception:
            item["tags"] = []
    if item.get("tags") is None:
        item["tags"] = []
    return item


def can_view_resource(resource: Dict[str, Any], viewer: Optional[Dict[str, Any]]) -> bool:
    """Approved resources are public. Others only show to the person who submitted them and to admins."""
    if resource.get("approval_status", "approved") == "approved":
        return True
    if not viewer:
        return False
    return viewer.get("user_type") == "admin" or str(resource.get("submitted_by")) == str(viewer.get("id"))


class ResourceModel(DBModel):
    """
    Model for Educational Resources & Toolkits.
    """

    async def list_resources(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        resource_type: Optional[str] = None,
        category: Optional[str] = None,
        language: Optional[str] = None,
        featured: Optional[bool] = None,
        search: Optional[str] = None,
        sort: str = "newest",
    ) -> Dict[str, Any]:
        params: list = []

        def add_param(value: Any) -> str:
            params.append(value)
            return f"${len(params)}"

        # The public hub only lists approved resources
        conditions = ["approval_status = 'approved'"]

        if resource_type:
            ph = add_param(resource_type)
            conditions.append(f"type = {ph}")
        if category:
            ph = add_param(category)
            conditions.append(f"category = {ph}")
        if language:
            ph = add_param(language)
            conditions.append(f"language = {ph}")
        if featured is not None:
            ph = add_param(featured)
            conditions.append(f"featured = {ph}")
        if search:
            ph = add_param(f"%{search}%")
            conditions.append(f"(title ILIKE {ph} OR description ILIKE {ph} OR CAST(tags AS TEXT) ILIKE {ph})")

        where_clause = "WHERE " + " AND ".join(conditions)

        sort_map = {
            "newest": "created_at DESC",
            "most_popular": "downloads DESC",
            "highest_rated": "rating DESC",
        }
        order_by = sort_map.get(sort, "created_at DESC")

        count_sql = f"SELECT COUNT(*) FROM resources {where_clause}"
        total = await self.conn.fetchval(count_sql, *params) or 0

        offset = (page - 1) * limit
        offset_ph = add_param(offset)
        limit_ph = add_param(limit)

        query = f"""
            SELECT {PUBLIC_COLUMNS}
            FROM resources
            {where_clause}
            ORDER BY {order_by}
            OFFSET {offset_ph} LIMIT {limit_ph}
        """
        records = await self.conn.fetch(query, *params)
        items = [_clean_tags(item) for item in self._records_to_list(records)]

        pages = (total + limit - 1) // limit if limit > 0 else 0

        return {
            "data": items,
            "meta": {
                "total": total,
                "page": page,
                "limit": limit,
                "pages": pages,
            },
        }

    async def get_resource_details(
        self, resource_id: str, viewer: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """The resource with its reviews, or None if it doesn't exist or this viewer may not see it."""
        query = f"""
            SELECT {SUBMISSION_COLUMNS}
            FROM resources
            WHERE resource_id = $1
        """
        record = await self.conn.fetchrow(query, resource_id)
        if not record:
            return None

        data = _clean_tags(self._record_to_dict(record))
        if not can_view_resource(data, viewer):
            return None

        # ratings count
        count_query = "SELECT COUNT(*) FROM resource_ratings WHERE resource_id = $1"
        data["ratings_count"] = await self.conn.fetchval(count_query, resource_id) or 0

        # reviews
        reviews_query = """
            SELECT r.rating_id, r.user_id, r.resource_id, r.rating, r.review, r.created_at,
                   u.display_name AS user_display_name
            FROM resource_ratings r
            LEFT JOIN users u ON r.user_id = u.id
            WHERE r.resource_id = $1
            ORDER BY r.created_at DESC
        """
        reviews = await self.conn.fetch(reviews_query, resource_id)
        data["reviews"] = self._records_to_list(reviews)

        # related resources (same category, limit 3)
        related_query = f"""
            SELECT {PUBLIC_COLUMNS}
            FROM resources
            WHERE category = $1 AND resource_id != $2 AND approval_status = 'approved'
            ORDER BY downloads DESC, rating DESC
            LIMIT 3
        """
        related = await self.conn.fetch(related_query, data["category"], resource_id)
        data["related_resources"] = [_clean_tags(r) for r in self._records_to_list(related)]

        return data

    async def count_download(self, resource_id: str) -> None:
        await self.conn.execute(
            "UPDATE resources SET downloads = downloads + 1 WHERE resource_id = $1", resource_id
        )

    async def get_file_info(self, resource_id: str) -> Optional[Dict[str, Any]]:
        row = await self.conn.fetchrow(
            """
            SELECT resource_id, approval_status, submitted_by, requires_auth,
                   url, file_key, file_name, file_type
            FROM resources WHERE resource_id = $1
            """,
            resource_id,
        )
        return self._record_to_dict(row) if row else None

    # ------------------------------------------------------------------
    # Submissions and approval
    # ------------------------------------------------------------------
    async def create_submission(
        self,
        submitted_by: str,
        payload: Dict[str, Any],
        approval_status: str,
        organization_id: Optional[str] = None,
        file_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        file_info = file_info or {}
        row = await self.conn.fetchrow(
            f"""
            INSERT INTO resources (
                title, type, category, description, url, language, duration, author,
                organization_id, tags, requires_auth,
                approval_status, submitted_by, published_date,
                reviewed_by, reviewed_at,
                file_key, file_name, file_type, file_size
            )
            VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8,
                $9, $10::jsonb, $11,
                $12::varchar, $13::uuid, CASE WHEN $12::varchar = 'approved' THEN CURRENT_DATE ELSE NULL END,
                CASE WHEN $12::varchar = 'approved' THEN $13::uuid ELSE NULL END,
                CASE WHEN $12::varchar = 'approved' THEN NOW() ELSE NULL END,
                $14, $15, $16, $17
            )
            RETURNING {SUBMISSION_COLUMNS}
            """,
            payload["title"], payload["type"], payload["category"], payload["description"],
            payload.get("url"), payload.get("language") or "en", payload.get("duration"), payload.get("author"),
            organization_id, json.dumps(payload.get("tags") or []), bool(payload.get("requires_auth")),
            approval_status, submitted_by,
            file_info.get("file_key"), file_info.get("file_name"), file_info.get("file_type"), file_info.get("file_size"),
        )
        return _clean_tags(self._record_to_dict(row))

    async def list_by_submitter(self, user_id: str, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        total = await self.conn.fetchval("SELECT COUNT(*) FROM resources WHERE submitted_by = $1", user_id) or 0
        rows = await self.conn.fetch(
            f"""
            SELECT {SUBMISSION_COLUMNS} FROM resources
            WHERE submitted_by = $1
            ORDER BY created_at DESC
            OFFSET $2 LIMIT $3
            """,
            user_id, (page - 1) * limit, limit,
        )
        return {
            "data": [_clean_tags(r) for r in self._records_to_list(rows)],
            "meta": {"total": total, "page": page, "limit": limit, "pages": (total + limit - 1) // limit},
        }

    async def list_pending(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        total = await self.conn.fetchval("SELECT COUNT(*) FROM resources WHERE approval_status = 'pending'") or 0
        rows = await self.conn.fetch(
            f"""
            SELECT s.*, u.display_name AS submitter_name, u.email AS submitter_email, u.user_type AS submitter_type
            FROM (SELECT {SUBMISSION_COLUMNS} FROM resources WHERE approval_status = 'pending') s
            LEFT JOIN users u ON u.id = s.submitted_by
            ORDER BY s.created_at ASC
            OFFSET $1 LIMIT $2
            """,
            (page - 1) * limit, limit,
        )
        return {
            "data": [_clean_tags(r) for r in self._records_to_list(rows)],
            "meta": {"total": total, "page": page, "limit": limit, "pages": (total + limit - 1) // limit},
        }

    async def get_for_decision(self, resource_id: str) -> Optional[Dict[str, Any]]:
        row = await self.conn.fetchrow(
            "SELECT resource_id, title, approval_status, submitted_by FROM resources WHERE resource_id = $1 FOR UPDATE",
            resource_id,
        )
        return self._record_to_dict(row) if row else None

    async def set_approval(
        self, resource_id: str, status: str, reviewer_id: str, reason: Optional[str]
    ) -> Dict[str, Any]:
        row = await self.conn.fetchrow(
            """
            UPDATE resources
            SET approval_status = $2::varchar,
                reviewed_by = $3,
                reviewed_at = NOW(),
                rejection_reason = CASE WHEN $2::varchar = 'rejected' THEN $4 ELSE NULL END,
                published_date = CASE WHEN $2::varchar = 'approved' THEN COALESCE(published_date, CURRENT_DATE) ELSE published_date END,
                updated_at = NOW()
            WHERE resource_id = $1
            RETURNING resource_id AS id, approval_status, reviewed_at, rejection_reason
            """,
            resource_id, status, reviewer_id, reason,
        )
        return self._record_to_dict(row)

    async def create_or_update_rating(
        self, resource_id: str, user_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Validate resource exists
        resource_check = await self.conn.fetchval(
            "SELECT 1 FROM resources WHERE resource_id = $1 AND approval_status = 'approved'", resource_id
        )
        if not resource_check:
            raise ValueError("Resource not found")

        rating_val = payload["rating"]
        review_val = payload.get("review")

        async with self.conn.transaction():
            query = """
                INSERT INTO resource_ratings (resource_id, user_id, rating, review, created_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (resource_id, user_id) 
                DO UPDATE SET rating = EXCLUDED.rating, review = EXCLUDED.review
                RETURNING rating_id, user_id, resource_id, rating, review, created_at
            """
            row = await self.conn.fetchrow(
                query, resource_id, user_id, rating_val, review_val
            )

            # Recalculate avg
            recalc_query = """
                UPDATE resources
                SET rating = (
                    SELECT COALESCE(ROUND(AVG(rating)::numeric, 2), 0.0)
                    FROM resource_ratings
                    WHERE resource_id = $1
                )
                WHERE resource_id = $1
                RETURNING rating
            """
            new_avg = await self.conn.fetchval(recalc_query, resource_id)

        data = self._record_to_dict(row)
        data["new_average"] = new_avg
        return data

    async def update_progress(
        self, resource_id: str, user_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        resource_check = await self.conn.fetchval(
            "SELECT 1 FROM resources WHERE resource_id = $1 AND approval_status = 'approved'", resource_id
        )
        if not resource_check:
            raise ValueError("Resource not found")

        prog_val = payload["progress"]
        last_pos = payload.get("last_position")

        query = """
            INSERT INTO resource_progress (resource_id, user_id, progress, last_position, updated_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (resource_id, user_id) 
            DO UPDATE SET progress = EXCLUDED.progress, 
                          last_position = EXCLUDED.last_position, 
                          updated_at = NOW()
            RETURNING resource_id, progress, last_position
        """
        
        row = await self.conn.fetchrow(
            query, resource_id, user_id, prog_val, last_pos
        )
        
        return {
            "success": True,
            "resource_id": str(row["resource_id"]),
            "progress": row["progress"],
            "last_position": row["last_position"]
        }
