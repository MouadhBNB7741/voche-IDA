import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.models.base_model import DBModel
from app.models.moderation_model import ModerationModel, VISIBLE_STATUSES_FOR_AUTHOR
from app.services.moderation_service import FilterResult, score_content

# Shown next to a verified doctor's name
VERIFIED_HCP_SQL = "(u.user_type = 'hcp' AND u.is_verified = TRUE) AS author_is_verified_hcp"

# Content a moderator hid or removed can't be edited by its author any more
LOCKED_BY_MODERATOR = ("hidden", "removed")


def can_view_content(item: Dict[str, Any], viewer: Optional[Dict[str, Any]]) -> bool:
    """Everyone sees approved content. Authors also see their own held or flagged content; admins see all."""
    status = item.get("moderation_status") or "approved"
    if status == "approved":
        return True
    if not viewer:
        return False
    if viewer.get("user_type") == "admin":
        return True
    return str(item.get("user_id")) == str(viewer.get("id")) and status in VISIBLE_STATUSES_FOR_AUTHOR


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

        conditions = ["fp.is_deleted = FALSE"]

        # Everyone sees approved posts; authors also see their own posts waiting for review
        if user_id:
            viewer_ph = add_param(user_id)
            visible_ph = add_param(list(VISIBLE_STATUSES_FOR_AUTHOR))
            conditions.append(
                f"(fp.moderation_status = 'approved' OR "
                f"(fp.user_id = {viewer_ph} AND fp.moderation_status = ANY({visible_ph}::text[])))"
            )
        else:
            conditions.append("fp.moderation_status = 'approved'")

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

        count_sql = f"""
            SELECT COUNT(*)
            FROM forum_posts fp
            JOIN communities c ON fp.community_id = c.community_id
            {where_clause}
        """
        total = await self.conn.fetchval(count_sql, *params) or 0

        # Data query
        offset = (page - 1) * limit
        offset_ph = add_param(offset)
        limit_ph = add_param(limit)

        if user_id:
            is_liked_clause = f"EXISTS (SELECT 1 FROM post_likes WHERE post_id = fp.post_id AND user_id = {viewer_ph}) AS is_liked_by_me"
        else:
            is_liked_clause = "FALSE AS is_liked_by_me"

        query = f"""
            SELECT
                fp.post_id,
                fp.community_id,
                fp.user_id,
                fp.title,
                fp.content,
                fp.post_type,
                fp.tags,
                fp.moderation_status,
                u.display_name AS author_display_name,
                u.display_name AS author_name,
                u.avatar AS author_avatar,
                {VERIFIED_HCP_SQL},
                c.name AS community_name,
                fp.created_at,
                fp.likes_count,
                fp.replies_count,
                {is_liked_clause}
            FROM forum_posts fp
            JOIN users u ON fp.user_id = u.id
            JOIN communities c ON fp.community_id = c.community_id
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

    # ------------------------------------------------------------------
    # 3. GET POST DETAILS
    # ------------------------------------------------------------------
    async def get_post_details(
        self, post_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        if user_id:
            is_liked_clause = ", EXISTS (SELECT 1 FROM post_likes WHERE post_id = fp.post_id AND user_id = $2) AS is_liked_by_me"
            params = [post_id, user_id]
        else:
            is_liked_clause = ", FALSE AS is_liked_by_me"
            params = [post_id]

        query = f"""
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
                u.display_name AS author_name,
                u.avatar AS author_avatar,
                {VERIFIED_HCP_SQL},
                c.name AS community_name
                {is_liked_clause}
            FROM forum_posts fp
            JOIN users u ON fp.user_id = u.id
            JOIN communities c ON fp.community_id = c.community_id
            WHERE fp.post_id = $1
              AND fp.is_deleted = FALSE
        """
        record = await self.conn.fetchrow(query, *params)
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

    async def get_post_comments(
        self, post_id: str, user_id: Optional[str] = None, is_admin: bool = False
    ) -> List[Dict[str, Any]]:
        if user_id:
            is_liked_clause = ", EXISTS (SELECT 1 FROM comment_likes WHERE comment_id = cm.comment_id AND user_id = $2) AS is_liked_by_me"
            params = [post_id, user_id]
        else:
            is_liked_clause = ", FALSE AS is_liked_by_me"
            params = [post_id]

        # Everyone sees approved comments; authors also see their own comments waiting
        # for review; admins see every comment so they can moderate the thread.
        if is_admin:
            visibility = ""
        elif user_id:
            params.append(list(VISIBLE_STATUSES_FOR_AUTHOR))
            visibility = (
                f"AND (cm.moderation_status = 'approved' OR "
                f"(cm.user_id = $2 AND cm.moderation_status = ANY(${len(params)}::text[])))"
            )
        else:
            visibility = "AND cm.moderation_status = 'approved'"

        query = f"""
            SELECT
                cm.comment_id,
                cm.post_id,
                cm.user_id,
                cm.parent_comment_id,
                cm.content,
                u.display_name AS author_display_name,
                u.display_name AS author_name,
                u.avatar AS author_avatar,
                {VERIFIED_HCP_SQL},
                cm.likes_count,
                cm.moderation_status,
                cm.is_deleted,
                cm.created_at,
                cm.updated_at
                {is_liked_clause}
            FROM comments cm
            JOIN users u ON cm.user_id = u.id
            WHERE cm.post_id = $1
              AND cm.is_deleted = FALSE
              {visibility}
            ORDER BY cm.created_at ASC
        """
        records = await self.conn.fetch(query, *params)
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

        title = payload["title"]
        content = payload["content"]

        # Automatic filter: held posts wait for a moderator, borderline ones go to the queue
        check = score_content(title, content)
        moderation_status = "approved"
        if check.held or community["moderation_level"] == "pre_moderated":
            moderation_status = "pending"

        post_type = payload.get("post_type", "discussion")
        tags = json.dumps(payload.get("tags", []))

        async with self.conn.transaction():
            query = """
                INSERT INTO forum_posts (
                    user_id, community_id, title, content,
                    post_type, moderation_status, tags,
                    moderation_score, flagged_reason,
                    created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
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
                check.score,
                check.reason,
            )
            await self._report_if_needed("post", str(row["post_id"]), content, check)
            if moderation_status == "pending" and not check.needs_review:
                # Held only because the community approves every post: it still needs to reach the queue
                await ModerationModel(self.conn).save_auto_report(
                    target_type="post",
                    target_id=str(row["post_id"]),
                    content=content,
                    reason="other",
                    description="Waiting for approval: this community checks every post before it appears",
                    priority="normal",
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
            "SELECT user_id, title, content, moderation_status FROM forum_posts WHERE post_id = $1 AND is_deleted = FALSE",
            post_id,
        )
        if not post:
            return None
        if str(post["user_id"]) != str(user_id) and not is_admin:
            raise PermissionError("Not authorized to edit this post")
        if post["moderation_status"] in LOCKED_BY_MODERATOR and not is_admin:
            raise PermissionError("A moderator removed this post, so it can't be edited")

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

        # An author's edit is checked again; it can be held, but an edit never releases held content
        check = FilterResult()
        if not is_admin:
            new_title = payload.get("title") or post["title"]
            new_content = payload.get("content") or post["content"]
            check = score_content(new_title, new_content)
            vals.extend([check.score, check.reason])
            set_parts.append(f"moderation_score = ${len(vals) - 1}")
            set_parts.append(f"flagged_reason = ${len(vals)}")
            set_parts.append("edited_at = NOW()")
            if check.held and post["moderation_status"] == "approved":
                set_parts.append("moderation_status = 'pending'")

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
        async with self.conn.transaction():
            row = await self.conn.fetchrow(query, *vals)
            if row:
                await self._report_if_needed("post", post_id, row["content"], check)
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

        # Automatic filter: a held reply waits for a moderator and isn't counted yet
        check = score_content(content)
        moderation_status = "pending" if check.held else "approved"

        async with self.conn.transaction():
            query = """
                INSERT INTO comments (
                    post_id, user_id, parent_comment_id, content,
                    moderation_status, moderation_score, flagged_reason,
                    created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                RETURNING comment_id, post_id, user_id, parent_comment_id,
                          content, likes_count, moderation_status, is_deleted,
                          created_at, updated_at
            """
            row = await self.conn.fetchrow(
                query, post_id, user_id, parent_comment_id, content,
                moderation_status, check.score, check.reason,
            )
            await self._report_if_needed("comment", str(row["comment_id"]), content, check)

            # Update replies_count
            if moderation_status == "approved":
                await self.conn.execute(
                    "UPDATE forum_posts SET replies_count = replies_count + 1, updated_at = NOW() WHERE post_id = $1",
                    post_id,
                )

        data = self._record_to_dict(row)
        await self._add_comment_author(data, user_id)
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
            "SELECT user_id, post_id, moderation_status FROM comments WHERE comment_id = $1 AND is_deleted = FALSE",
            comment_id,
        )
        if not comment:
            return None
        if str(comment["user_id"]) != str(user_id) and not is_admin:
            raise PermissionError("Not authorized to edit this comment")
        if comment["moderation_status"] in LOCKED_BY_MODERATOR and not is_admin:
            raise PermissionError("A moderator removed this comment, so it can't be edited")

        # An author's edit is checked again; it can be held, but an edit never releases held content
        check = FilterResult()
        new_status = comment["moderation_status"]
        if not is_admin:
            check = score_content(content)
            if check.held and new_status == "approved":
                new_status = "pending"

        query = """
            UPDATE comments
            SET content = $2, updated_at = NOW(),
                moderation_status = $3,
                moderation_score = CASE WHEN $4 THEN $5 ELSE moderation_score END,
                flagged_reason = CASE WHEN $4 THEN $6 ELSE flagged_reason END,
                edited_at = CASE WHEN $4 THEN NOW() ELSE edited_at END
            WHERE comment_id = $1 AND is_deleted = FALSE
            RETURNING comment_id, post_id, user_id, parent_comment_id,
                      content, likes_count, moderation_status, is_deleted,
                      created_at, updated_at
        """
        async with self.conn.transaction():
            row = await self.conn.fetchrow(
                query, comment_id, content, new_status, not is_admin, check.score, check.reason
            )
            if row:
                await self._report_if_needed("comment", comment_id, content, check)
                if new_status != comment["moderation_status"]:
                    await ModerationModel(self.conn).recount_replies(str(comment["post_id"]))
        if not row:
            return None

        data = self._record_to_dict(row)
        await self._add_comment_author(data, comment["user_id"])
        return data

    async def _add_comment_author(self, data: Dict[str, Any], author_id: Any) -> None:
        user = await self.conn.fetchrow(
            "SELECT display_name, avatar, user_type, is_verified FROM users WHERE id = $1", author_id
        )
        if user:
            data["author_display_name"] = user["display_name"]
            data["author_avatar"] = user["avatar"]
            data["author_is_verified_hcp"] = user["user_type"] == "hcp" and bool(user["is_verified"])
        else:
            data["author_display_name"] = "Unknown User"
            data["author_avatar"] = None
            data["author_is_verified_hcp"] = False

    async def _report_if_needed(
        self, target_type: str, target_id: str, content: str, check: FilterResult
    ) -> None:
        """Send content the automatic filter flagged to the moderation queue."""
        if not check.needs_review:
            return
        await ModerationModel(self.conn).save_auto_report(
            target_type=target_type,
            target_id=target_id,
            content=content,
            reason=check.category or "other",
            description=check.reason,
            priority=check.priority,
        )

    # ------------------------------------------------------------------
    # 7c. DELETE COMMENT (soft delete)
    # ------------------------------------------------------------------
    async def soft_delete_comment(
        self, comment_id: str, user_id: str, is_admin: bool = False
    ) -> bool:
        comment = await self.conn.fetchrow(
            "SELECT user_id, post_id, moderation_status FROM comments WHERE comment_id = $1 AND is_deleted = FALSE",
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
            # Decrement replies_count (only visible replies are counted)
            if comment["moderation_status"] == "approved":
                await self.conn.execute(
                    "UPDATE forum_posts SET replies_count = GREATEST(replies_count - 1, 0), updated_at = NOW() WHERE post_id = $1",
                    comment["post_id"],
                )
        return True

    # ------------------------------------------------------------------
    # 8. LIKE POST / LIKE COMMENT
    # ------------------------------------------------------------------
    async def like_post(self, post_id: str, user_id: str) -> Dict[str, Any]:
        async with self.conn.transaction():
            try:
                await self.conn.execute(
                    "INSERT INTO post_likes (post_id, user_id) VALUES ($1, $2)",
                    post_id,
                    user_id,
                )
            except Exception:
                raise ValueError("You have already liked this post")

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

    async def unlike_post(self, post_id: str, user_id: str) -> Dict[str, Any]:
        async with self.conn.transaction():
            res = await self.conn.execute(
                "DELETE FROM post_likes WHERE post_id = $1 AND user_id = $2",
                post_id,
                user_id,
            )
            if res == "DELETE 0":
                raise ValueError("You have not liked this post yet")

            row = await self.conn.fetchrow(
                """
                UPDATE forum_posts
                SET likes_count = GREATEST(likes_count - 1, 0)
                WHERE post_id = $1 AND is_deleted = FALSE
                RETURNING post_id, likes_count
                """,
                post_id,
            )
            if not row:
                raise ValueError("Post not found")
            return self._record_to_dict(row)

    async def like_comment(self, comment_id: str, user_id: str) -> Dict[str, Any]:
        async with self.conn.transaction():
            try:
                await self.conn.execute(
                    "INSERT INTO comment_likes (comment_id, user_id) VALUES ($1, $2)",
                    comment_id,
                    user_id,
                )
            except Exception:
                raise ValueError("You have already liked this comment")

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

    async def unlike_comment(self, comment_id: str, user_id: str) -> Dict[str, Any]:
        async with self.conn.transaction():
            res = await self.conn.execute(
                "DELETE FROM comment_likes WHERE comment_id = $1 AND user_id = $2",
                comment_id,
                user_id,
            )
            if res == "DELETE 0":
                raise ValueError("You have not liked this comment yet")

            row = await self.conn.fetchrow(
                """
                UPDATE comments
                SET likes_count = GREATEST(likes_count - 1, 0)
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
        self, reporter_id: str, payload: Dict[str, Any], community_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Raises LookupError if the content doesn't exist and ValueError for a repeat report."""
        target_type = payload["target_type"]
        target_id = str(payload["target_id"])
        reason = payload["reason"]
        description = payload.get("description")

        # The reported post or comment must exist in this community; keep a snapshot of it
        target = await ModerationModel(self.conn).get_target(target_type, target_id)
        if (
            not target
            or target["is_deleted"]
            or (community_id and str(target["community_id"]) != str(community_id))
        ):
            raise LookupError(f"{target_type.capitalize()} not found")
        target_content = target["content"]
        priority = "critical" if reason == "self_harm" else "normal"

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
                    reason, description, status, source, priority, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, 'pending', 'user', $7, NOW())
                RETURNING report_id, reporter_id, target_type, target_id,
                          reason, status, priority, created_at
            """
            row = await self.conn.fetchrow(
                query,
                reporter_id,
                target_type,
                target_id,
                target_content,
                reason,
                description,
                priority,
            )

            # Reports from 3 different users hide the content until a moderator reviews it
            await ModerationModel(self.conn).flag_if_reported_enough(target_type, target_id)

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
                cr.source, cr.priority,
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
