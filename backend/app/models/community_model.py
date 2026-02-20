import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.models.base_model import DBModel


# Simple profanity filter placeholder
PROFANITY_WORDS = {"badword1", "badword2", "offensive"}


def check_profanity(text: str) -> bool:
    """Return True if text contains profanity."""
    lower = text.lower()
    for word in PROFANITY_WORDS:
        if word in lower:
            return True
    return False


class CommunityModel(DBModel):
    """
    Model for Community & Forums domain.
    Handles communities, forum posts, comments, likes, and content reports.
    Strict adhesion to DB schema: communities, forum_posts, comments, content_reports.
    """

    # ------------------------------------------------------------------
    # 1. LIST ACTIVE COMMUNITIES (paginated, filtered, sorted)
    # ------------------------------------------------------------------
    async def list_active_communities(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        community_type: Optional[str] = None,
        sort: str = "most_members",
    ) -> Dict[str, Any]:
        params: list = []

        def add_param(value: Any) -> str:
            params.append(value)
            return f"${len(params)}"

        conditions = ["is_active = TRUE"]

        if community_type:
            ph = add_param(community_type)
            conditions.append(f"type = {ph}")

        where_clause = "WHERE " + " AND ".join(conditions)

        # Sort mapping
        sort_map = {
            "most_members": "member_count DESC",
            "most_posts": "post_count DESC",
            "newest": "created_at DESC",
            "name_asc": "name ASC",
        }
        order_by = sort_map.get(sort, "member_count DESC")

        # Count query
        count_sql = f"SELECT COUNT(*) FROM communities {where_clause}"
        total = await self.conn.fetchval(count_sql, *params) or 0

        # Data query
        offset = (page - 1) * limit
        offset_ph = add_param(offset)
        limit_ph = add_param(limit)

        query = f"""
            SELECT
                community_id, name, description, type, icon,
                moderation_level, member_count, post_count,
                is_active, created_at, updated_at
            FROM communities
            {where_clause}
            ORDER BY {order_by}
            OFFSET {offset_ph} LIMIT {limit_ph}
        """
        records = await self.conn.fetch(query, *params)
        items = self._records_to_list(records)

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

    # ------------------------------------------------------------------
    # 1b. GET SINGLE COMMUNITY
    # ------------------------------------------------------------------
    async def get_community_by_id(self, community_id: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT
                community_id, name, description, type, icon,
                moderation_level, member_count, post_count,
                is_active, created_at, updated_at
            FROM communities
            WHERE community_id = $1 AND is_active = TRUE
        """
        record = await self.conn.fetchrow(query, community_id)
        if not record:
            return None
        return self._record_to_dict(record)

    # ------------------------------------------------------------------
    # 2. LIST FORUM POSTS (paginated, filtered, sorted)
    # ------------------------------------------------------------------
    async def list_forum_posts(
        self,
        *,
        user_id: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
        category: Optional[str] = None,
        sort: str = "recent",
    ) -> Dict[str, Any]:
        params: list = []

        def add_param(value: Any) -> str:
            params.append(value)
            return f"${len(params)}"

        conditions = [
            "fp.is_deleted = FALSE",
            "fp.moderation_status = 'approved'",
        ]

        if category:
            # Support both community_id (UUID) and community name
            cat_ph = add_param(category)
            conditions.append(
                f"(c.name ILIKE {cat_ph} OR c.community_id::text = {cat_ph})"
            )

        where_clause = "WHERE " + " AND ".join(conditions)

        # Sort mapping
        sort_map = {
            "recent": "fp.created_at DESC",
            "popular": "fp.likes_count DESC",
            "replies": "fp.replies_count DESC",
        }
        order_by = sort_map.get(sort, "fp.created_at DESC")

        # Count query
        count_sql = f"""
            SELECT COUNT(*)
            FROM forum_posts fp
            JOIN communities c ON fp.community_id = c.community_id
            {where_clause}
        """
        count_params: list = []
        # Rebuild params for count query
        count_conditions = [
            "fp.is_deleted = FALSE",
            "fp.moderation_status = 'approved'",
        ]
        if category:
            count_params.append(category)
            c_ph = f"${len(count_params)}"
            count_conditions.append(
                f"(c.name ILIKE {c_ph} OR c.community_id::text = {c_ph})"
            )
        count_where = "WHERE " + " AND ".join(count_conditions)
        count_sql = f"""
            SELECT COUNT(*)
            FROM forum_posts fp
            JOIN communities c ON fp.community_id = c.community_id
            {count_where}
        """
        total = await self.conn.fetchval(count_sql, *count_params) or 0

        # Data query
        offset = (page - 1) * limit
        offset_ph = add_param(offset)
        limit_ph = add_param(limit)

        query = f"""
            SELECT
                fp.post_id,
                fp.title,
                u.display_name AS author_display_name,
                u.avatar AS author_avatar,
                c.name AS community_name,
                fp.created_at,
                fp.likes_count,
                fp.replies_count,
                FALSE AS is_liked_by_me
            FROM forum_posts fp
            JOIN users u ON fp.user_id = u.id
            JOIN communities c ON fp.community_id = c.community_id
            {where_clause}
            ORDER BY {order_by}
            OFFSET {offset_ph} LIMIT {limit_ph}
        """
        records = await self.conn.fetch(query, *params)
        items = self._records_to_list(records)

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

    # ------------------------------------------------------------------
    # 3. GET POST DETAILS
    # ------------------------------------------------------------------
    async def get_post_details(
        self, post_id: str
    ) -> Optional[Dict[str, Any]]:
        query = """
            SELECT
                fp.post_id,
                fp.user_id,
                fp.community_id,
                fp.title,
                fp.content,
                fp.post_type,
                fp.moderation_status,
                fp.views_count,
                fp.replies_count,
                fp.likes_count,
                fp.is_pinned,
                fp.is_locked,
                fp.is_deleted,
                fp.tags,
                fp.created_at,
                fp.updated_at,
                u.display_name AS author_display_name,
                u.avatar AS author_avatar,
                c.name AS community_name
            FROM forum_posts fp
            JOIN users u ON fp.user_id = u.id
            JOIN communities c ON fp.community_id = c.community_id
            WHERE fp.post_id = $1
              AND fp.is_deleted = FALSE
        """
        record = await self.conn.fetchrow(query, post_id)
        if not record:
            return None
        data = self._record_to_dict(record)
        # Deserialize tags if string
        if isinstance(data.get("tags"), str):
            try:
                data["tags"] = json.loads(data["tags"])
            except Exception:
                data["tags"] = []
        if data.get("tags") is None:
            data["tags"] = []
        return data

    async def get_post_comments(self, post_id: str) -> List[Dict[str, Any]]:
        query = """
            SELECT
                cm.comment_id,
                cm.post_id,
                cm.user_id,
                cm.parent_comment_id,
                cm.content,
                u.display_name AS author_display_name,
                u.avatar AS author_avatar,
                cm.likes_count,
                cm.moderation_status,
                cm.is_deleted,
                cm.created_at,
                cm.updated_at
            FROM comments cm
            JOIN users u ON cm.user_id = u.id
            WHERE cm.post_id = $1
              AND cm.is_deleted = FALSE
            ORDER BY cm.created_at ASC
        """
        records = await self.conn.fetch(query, post_id)
        return self._records_to_list(records)

    async def increment_post_views(self, post_id: str) -> None:
        await self.conn.execute(
            "UPDATE forum_posts SET views_count = views_count + 1 WHERE post_id = $1",
            post_id,
        )

    # ------------------------------------------------------------------
    # 4. CREATE POST
    # ------------------------------------------------------------------
    async def create_post(
        self, user_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        community_id = str(payload["community_id"])

        # Validate community exists
        community = await self.conn.fetchrow(
            "SELECT community_id, moderation_level FROM communities WHERE community_id = $1 AND is_active = TRUE",
            community_id,
        )
        if not community:
            raise ValueError("Community not found")

        # Profanity check
        title = payload["title"]
        content = payload["content"]
        if check_profanity(title) or check_profanity(content):
            raise ValueError("Content contains inappropriate language")

        # Determine moderation status
        moderation_status = "approved"
        if community["moderation_level"] == "pre_moderated":
            moderation_status = "pending"

        post_type = payload.get("post_type", "discussion")
        tags = json.dumps(payload.get("tags", []))

        async with self.conn.transaction():
            query = """
                INSERT INTO forum_posts (
                    user_id, community_id, title, content,
                    post_type, moderation_status, tags,
                    created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                RETURNING post_id, user_id, community_id, title, content,
                          post_type, moderation_status, tags,
                          views_count, replies_count, likes_count,
                          is_pinned, is_locked, is_deleted,
                          created_at, updated_at
            """
            row = await self.conn.fetchrow(
                query,
                user_id,
                community_id,
                title,
                content,
                post_type,
                moderation_status,
                tags,
            )

            # Update community post_count
            await self.conn.execute(
                "UPDATE communities SET post_count = post_count + 1, updated_at = NOW() WHERE community_id = $1",
                community_id,
            )

        data = self._record_to_dict(row)
        if isinstance(data.get("tags"), str):
            try:
                data["tags"] = json.loads(data["tags"])
            except Exception:
                data["tags"] = []
        return data

    # ------------------------------------------------------------------
    # 5. EDIT POST
    # ------------------------------------------------------------------
    async def edit_post(
        self,
        post_id: str,
        user_id: str,
        payload: Dict[str, Any],
        is_admin: bool = False,
    ) -> Optional[Dict[str, Any]]:
        # Verify ownership or admin
        post = await self.conn.fetchrow(
            "SELECT user_id FROM forum_posts WHERE post_id = $1 AND is_deleted = FALSE",
            post_id,
        )
        if not post:
            return None
        if str(post["user_id"]) != str(user_id) and not is_admin:
            raise PermissionError("Not authorized to edit this post")

        set_parts = []
        vals: list = [post_id]

        if "title" in payload and payload["title"] is not None:
            vals.append(payload["title"])
            set_parts.append(f"title = ${len(vals)}")

        if "content" in payload and payload["content"] is not None:
            vals.append(payload["content"])
            set_parts.append(f"content = ${len(vals)}")

        if not set_parts:
            return None

        set_parts.append("updated_at = NOW()")

        query = f"""
            UPDATE forum_posts
            SET {", ".join(set_parts)}
            WHERE post_id = $1 AND is_deleted = FALSE
            RETURNING post_id, user_id, community_id, title, content,
                      post_type, moderation_status, tags,
                      views_count, replies_count, likes_count,
                      is_pinned, is_locked, is_deleted,
                      created_at, updated_at
        """
        row = await self.conn.fetchrow(query, *vals)
        if not row:
            return None
        data = self._record_to_dict(row)
        if isinstance(data.get("tags"), str):
            try:
                data["tags"] = json.loads(data["tags"])
            except Exception:
                data["tags"] = []
        return data

    # ------------------------------------------------------------------
    # 6. SOFT DELETE POST
    # ------------------------------------------------------------------
    async def soft_delete_post(
        self, post_id: str, user_id: str, is_admin: bool = False
    ) -> bool:
        post = await self.conn.fetchrow(
            "SELECT user_id, community_id FROM forum_posts WHERE post_id = $1 AND is_deleted = FALSE",
            post_id,
        )
        if not post:
            return False
        if str(post["user_id"]) != str(user_id) and not is_admin:
            raise PermissionError("Not authorized to delete this post")

        async with self.conn.transaction():
            await self.conn.execute(
                "UPDATE forum_posts SET is_deleted = TRUE, updated_at = NOW() WHERE post_id = $1",
                post_id,
            )
            # Decrement community post_count
            await self.conn.execute(
                "UPDATE communities SET post_count = GREATEST(post_count - 1, 0), updated_at = NOW() WHERE community_id = $1",
                post["community_id"],
            )
        return True

    # ------------------------------------------------------------------
    # 7. CREATE COMMENT (reply to post)
    # ------------------------------------------------------------------
    async def create_comment(
        self,
        post_id: str,
        user_id: str,
        content: str,
        parent_comment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Validate post is not locked
        post = await self.conn.fetchrow(
            "SELECT is_locked, is_deleted FROM forum_posts WHERE post_id = $1",
            post_id,
        )
        if not post:
            raise ValueError("Post not found")
        if post["is_deleted"]:
            raise ValueError("Post has been deleted")
        if post["is_locked"]:
            raise ValueError("Post is locked for new replies")

        async with self.conn.transaction():
            query = """
                INSERT INTO comments (
                    post_id, user_id, parent_comment_id, content,
                    created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, NOW(), NOW())
                RETURNING comment_id, post_id, user_id, parent_comment_id,
                          content, likes_count, moderation_status, is_deleted,
                          created_at, updated_at
            """
            row = await self.conn.fetchrow(
                query, post_id, user_id, parent_comment_id, content
            )

            # Update replies_count
            await self.conn.execute(
                "UPDATE forum_posts SET replies_count = replies_count + 1, updated_at = NOW() WHERE post_id = $1",
                post_id,
            )

        data = self._record_to_dict(row)

        # Populate author info from DB
        user = await self.conn.fetchrow(
            "SELECT display_name, avatar FROM users WHERE id = $1", user_id
        )
        if user:
            data["author_display_name"] = user["display_name"]
            data["author_avatar"] = user["avatar"]
        else:
             # Should not happen due to FK constraints
             data["author_display_name"] = "Unknown User"
             data["author_avatar"] = None

        return data

    # ------------------------------------------------------------------
    # 7b. EDIT COMMENT
    # ------------------------------------------------------------------
    async def edit_comment(
        self,
        comment_id: str,
        user_id: str,
        content: str,
        is_admin: bool = False,
    ) -> Optional[Dict[str, Any]]:
        comment = await self.conn.fetchrow(
            "SELECT user_id FROM comments WHERE comment_id = $1 AND is_deleted = FALSE",
            comment_id,
        )
        if not comment:
            return None
        if str(comment["user_id"]) != str(user_id) and not is_admin:
            raise PermissionError("Not authorized to edit this comment")

        query = """
            UPDATE comments
            SET content = $2, updated_at = NOW()
            WHERE comment_id = $1 AND is_deleted = FALSE
            RETURNING comment_id, post_id, user_id, parent_comment_id,
                      content, likes_count, moderation_status, is_deleted,
                      created_at, updated_at
        """
        row = await self.conn.fetchrow(query, comment_id, content)
        if not row:
            return None
        
        data = self._record_to_dict(row)

        # Populate author info - user_id is the author (verified above)
        user = await self.conn.fetchrow(
            "SELECT display_name, avatar FROM users WHERE id = $1", comment["user_id"]
        )
        if user:
            data["author_display_name"] = user["display_name"]
            data["author_avatar"] = user["avatar"]
        else:
             data["author_display_name"] = "Unknown User"
             data["author_avatar"] = None
        
        return data

    # ------------------------------------------------------------------
    # 7c. DELETE COMMENT (soft delete)
    # ------------------------------------------------------------------
    async def soft_delete_comment(
        self, comment_id: str, user_id: str, is_admin: bool = False
    ) -> bool:
        comment = await self.conn.fetchrow(
            "SELECT user_id, post_id FROM comments WHERE comment_id = $1 AND is_deleted = FALSE",
            comment_id,
        )
        if not comment:
            return False
        if str(comment["user_id"]) != str(user_id) and not is_admin:
            raise PermissionError("Not authorized to delete this comment")

        async with self.conn.transaction():
            await self.conn.execute(
                "UPDATE comments SET is_deleted = TRUE, updated_at = NOW() WHERE comment_id = $1",
                comment_id,
            )
            # Decrement replies_count
            await self.conn.execute(
                "UPDATE forum_posts SET replies_count = GREATEST(replies_count - 1, 0), updated_at = NOW() WHERE post_id = $1",
                comment["post_id"],
            )
        return True

    # ------------------------------------------------------------------
    # 8. LIKE POST / LIKE COMMENT
    # ------------------------------------------------------------------
    async def like_post(self, post_id: str, user_id: str) -> Dict[str, Any]:
        row = await self.conn.fetchrow(
            """
            UPDATE forum_posts
            SET likes_count = likes_count + 1
            WHERE post_id = $1 AND is_deleted = FALSE
            RETURNING post_id, likes_count
            """,
            post_id,
        )
        if not row:
            raise ValueError("Post not found")
        return self._record_to_dict(row)

    async def like_comment(self, comment_id: str, user_id: str) -> Dict[str, Any]:
        row = await self.conn.fetchrow(
            """
            UPDATE comments
            SET likes_count = likes_count + 1
            WHERE comment_id = $1 AND is_deleted = FALSE
            RETURNING comment_id, likes_count
            """,
            comment_id,
        )
        if not row:
            raise ValueError("Comment not found")
        return self._record_to_dict(row)

    # ------------------------------------------------------------------
    # 9. REPORT CONTENT
    # ------------------------------------------------------------------
    async def create_content_report(
        self, reporter_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        target_type = payload["target_type"]
        target_id = str(payload["target_id"])
        reason = payload["reason"]
        description = payload.get("description")

        # Snapshot target content
        target_content = None
        if target_type == "post":
            row = await self.conn.fetchrow(
                "SELECT content FROM forum_posts WHERE post_id = $1", target_id
            )
            if row:
                target_content = row["content"]
        elif target_type == "comment":
            row = await self.conn.fetchrow(
                "SELECT content FROM comments WHERE comment_id = $1", target_id
            )
            if row:
                target_content = row["content"]

        async with self.conn.transaction():
            # Check for existing report by this user on this target
            existing = await self.conn.fetchval(
                """
                SELECT report_id FROM content_reports
                WHERE reporter_id = $1 AND target_type = $2 AND target_id = $3
                """,
                reporter_id,
                target_type,
                target_id,
            )
            if existing:
                raise ValueError("You have already reported this content")

            query = """
                INSERT INTO content_reports (
                    reporter_id, target_type, target_id, target_content,
                    reason, description, status, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, 'pending', NOW())
                RETURNING report_id, reporter_id, target_type, target_id,
                          reason, status, created_at
            """
            row = await self.conn.fetchrow(
                query,
                reporter_id,
                target_type,
                target_id,
                target_content,
                reason,
                description,
            )

            # Auto-flag logic: count reports on same target
            report_count = await self.conn.fetchval(
                """
                SELECT COUNT(*) FROM content_reports
                WHERE target_type = $1 AND target_id = $2
                """,
                target_type,
                target_id,
            )

            if report_count >= 10:
                if target_type == "post":
                    await self.conn.execute(
                        "UPDATE forum_posts SET moderation_status = 'flagged' WHERE post_id = $1",
                        target_id,
                    )
                elif target_type == "comment":
                    await self.conn.execute(
                        "UPDATE comments SET moderation_status = 'flagged' WHERE comment_id = $1",
                        target_id,
                    )

        return self._record_to_dict(row)

    # ------------------------------------------------------------------
    # 10. ADMIN: LIST REPORTS
    # ------------------------------------------------------------------
    async def list_reports(
        self,
        page: int = 1,
        limit: int = 20,
        status: str = None,
    ) -> Dict[str, Any]:
        offset = (page - 1) * limit

        where_clause = ""
        params: list = []
        param_idx = 1

        if status:
            where_clause = f"WHERE cr.status = ${param_idx}"
            params.append(status)
            param_idx += 1

        # Count
        count_query = f"SELECT COUNT(*) FROM content_reports cr {where_clause}"
        total = await self.conn.fetchval(count_query, *params)

        # Fetch
        query = f"""
            SELECT
                cr.report_id, cr.reporter_id, cr.target_type, cr.target_id,
                cr.target_content, cr.reason, cr.description,
                cr.status, cr.moderator_id, cr.resolution_notes,
                cr.action_taken, cr.created_at, cr.resolved_at,
                u.display_name AS reporter_name
            FROM content_reports cr
            LEFT JOIN users u ON cr.reporter_id = u.id
            {where_clause}
            ORDER BY cr.created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])
        rows = await self.conn.fetch(query, *params)

        return {
            "reports": [self._record_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "limit": limit,
        }

    # ------------------------------------------------------------------
    # 11. ADMIN: RESOLVE REPORT
    # ------------------------------------------------------------------
    async def resolve_report(
        self,
        report_id: str,
        moderator_id: str,
        status: str,
        action_taken: str = None,
        resolution_notes: str = None,
    ) -> Dict[str, Any]:
        row = await self.conn.fetchrow(
            """
            UPDATE content_reports
            SET status = $2,
                moderator_id = $3,
                action_taken = $4,
                resolution_notes = $5,
                resolved_at = NOW()
            WHERE report_id = $1
            RETURNING report_id, reporter_id, target_type, target_id,
                      reason, status, moderator_id, action_taken,
                      resolution_notes, created_at, resolved_at
            """,
            report_id,
            status,
            moderator_id,
            action_taken,
            resolution_notes,
        )
        if not row:
            raise ValueError("Report not found")
        return self._record_to_dict(row)

    # ------------------------------------------------------------------
    # 12. ADMIN: DELETE REPORT
    # ------------------------------------------------------------------
    async def delete_report(self, report_id: str) -> bool:
        result = await self.conn.execute(
            "DELETE FROM content_reports WHERE report_id = $1",
            report_id,
        )
        if result == "DELETE 0":
            raise ValueError("Report not found")
        return True
