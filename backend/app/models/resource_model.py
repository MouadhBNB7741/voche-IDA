import json
from typing import Any, Dict, List, Optional
from uuid import UUID
from app.models.base_model import DBModel


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
        sort: str = "newest",
    ) -> Dict[str, Any]:
        params: list = []

        def add_param(value: Any) -> str:
            params.append(value)
            return f"${len(params)}"

        conditions = ["1=1"]

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
            SELECT
                resource_id, title, type, category, description,
                url, language, duration, author, tags, published_date,
                downloads, rating, featured, requires_auth,
                created_at, updated_at
            FROM resources
            {where_clause}
            ORDER BY {order_by}
            OFFSET {offset_ph} LIMIT {limit_ph}
        """
        records = await self.conn.fetch(query, *params)
        items = self._records_to_list(records)

        for item in items:
            if isinstance(item.get("tags"), str):
                try:
                    item["tags"] = json.loads(item["tags"])
                except Exception:
                    item["tags"] = []
            if item.get("tags") is None:
                item["tags"] = []

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

    async def get_resource_details(self, resource_id: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT
                resource_id, title, type, category, description,
                url, language, duration, author, tags, published_date,
                downloads, rating, featured, requires_auth,
                created_at, updated_at
            FROM resources
            WHERE resource_id = $1
        """
        record = await self.conn.fetchrow(query, resource_id)
        if not record:
            return None

        data = self._record_to_dict(record)
        if isinstance(data.get("tags"), str):
            try:
                data["tags"] = json.loads(data["tags"])
            except Exception:
                data["tags"] = []
        if data.get("tags") is None:
            data["tags"] = []

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
        related_query = """
            SELECT
                resource_id, title, type, category, description,
                url, language, duration, author, tags, published_date,
                downloads, rating, featured, requires_auth,
                created_at, updated_at
            FROM resources
            WHERE category = $1 AND resource_id != $2
            ORDER BY downloads DESC, rating DESC
            LIMIT 3
        """
        related = await self.conn.fetch(related_query, data["category"], resource_id)
        related_data = self._records_to_list(related)
        for r_item in related_data:
            if isinstance(r_item.get("tags"), str):
                try:
                    r_item["tags"] = json.loads(r_item["tags"])
                except Exception:
                    r_item["tags"] = []
            if r_item.get("tags") is None:
                r_item["tags"] = []
                
        data["related_resources"] = related_data

        return data

    async def fetch_for_download(self, resource_id: str) -> Optional[Dict[str, Any]]:
        query = """
            UPDATE resources
            SET downloads = downloads + 1
            WHERE resource_id = $1
            RETURNING resource_id, url, requires_auth
        """
        record = await self.conn.fetchrow(query, resource_id)
        if not record:
            return None
        return self._record_to_dict(record)

    async def create_or_update_rating(
        self, resource_id: str, user_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Validate resource exists
        resource_check = await self.conn.fetchval(
            "SELECT 1 FROM resources WHERE resource_id = $1", resource_id
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
            "SELECT 1 FROM resources WHERE resource_id = $1", resource_id
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
