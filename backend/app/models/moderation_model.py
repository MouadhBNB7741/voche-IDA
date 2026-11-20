from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.base_model import DBModel

OPEN_REPORT_STATUSES = ("pending", "under_review")
CLOSED_REPORT_STATUSES = ("actioned", "dismissed", "reviewed", "resolved")
VISIBLE_STATUSES_FOR_AUTHOR = ("pending", "flagged")

# Reports from this many different users hide the content until a moderator reviews it
USER_REPORTS_TO_FLAG = 3

_TABLES = {
    "post": ("forum_posts", "post_id"),
    "comment": ("comments", "comment_id"),
}


class ModerationModel(DBModel):
    """Database access for content reports, content states and moderator actions."""

    # ------------------------------------------------------------------
    # Reports raised by the automatic filter
    # ------------------------------------------------------------------
    async def save_auto_report(
        self,
        target_type: str,
        target_id: str,
        content: str,
        reason: str,
        description: str,
        priority: str,
    ) -> Dict[str, Any]:
        """One open automatic report per post or comment: a later edit refreshes it.
        The result's "was_critical" says whether the report was already critical before."""
        existing = await self.conn.fetchrow(
            """
            SELECT report_id, priority FROM content_reports
            WHERE target_type = $1 AND target_id = $2
              AND source = 'auto_filter' AND status = ANY($3::text[])
            """,
            target_type, target_id, list(OPEN_REPORT_STATUSES),
        )
        if existing:
            row = await self.conn.fetchrow(
                """
                UPDATE content_reports
                SET reason = $2, description = $3, priority = $4, target_content = $5
                WHERE report_id = $1
                RETURNING *
                """,
                existing["report_id"], reason, description, priority, content,
            )
        else:
            row = await self.conn.fetchrow(
                """
                INSERT INTO content_reports (
                    reporter_id, target_type, target_id, target_content,
                    reason, description, status, source, priority, created_at
                )
                VALUES (NULL, $1, $2, $3, $4, $5, 'pending', 'auto_filter', $6, NOW())
                RETURNING *
                """,
                target_type, target_id, content, reason, description, priority,
            )
        return {
            **self._record_to_dict(row),
            "was_critical": bool(existing and existing["priority"] == "critical"),
        }

    # ------------------------------------------------------------------
    # User reports: flag content once enough different users report it
    # ------------------------------------------------------------------
    async def flag_if_reported_enough(self, target_type: str, target_id: str) -> bool:
        if target_type not in _TABLES:
            return False
        reporters = await self.conn.fetchval(
            """
            SELECT COUNT(DISTINCT reporter_id) FROM content_reports
            WHERE target_type = $1 AND target_id = $2
              AND source = 'user' AND status = ANY($3::text[])
            """,
            target_type, target_id, list(OPEN_REPORT_STATUSES),
        )
        if reporters < USER_REPORTS_TO_FLAG:
            return False
        table, key = _TABLES[target_type]
        flagged = await self.conn.fetchval(
            f"""
            UPDATE {table}
            SET moderation_status = 'flagged',
                flagged_reason = $2
            WHERE {key} = $1 AND moderation_status = 'approved'
            RETURNING {key}
            """,
            target_id, f"Reported by {reporters} users",
        )
        if flagged:
            await self.conn.execute(
                """
                UPDATE content_reports SET priority = 'high'
                WHERE target_type = $1 AND target_id = $2
                  AND status = ANY($3::text[]) AND priority = 'normal'
                """,
                target_type, target_id, list(OPEN_REPORT_STATUSES),
            )
            if target_type == "comment":
                post_id = await self.conn.fetchval("SELECT post_id FROM comments WHERE comment_id = $1", target_id)
                await self.recount_replies(str(post_id))
        return bool(flagged)

    # ------------------------------------------------------------------
    # Decisions
    # ------------------------------------------------------------------
    async def get_report_for_update(self, report_id: str) -> Optional[Dict[str, Any]]:
        row = await self.conn.fetchrow(
            "SELECT * FROM content_reports WHERE report_id = $1 FOR UPDATE", report_id
        )
        return self._record_to_dict(row) if row else None

    async def get_target(self, target_type: str, target_id: str) -> Optional[Dict[str, Any]]:
        """The reported post or comment, with its author and where it lives."""
        if target_type == "post":
            row = await self.conn.fetchrow(
                """
                SELECT post_id, community_id, user_id AS author_id, title, content,
                       moderation_status, is_deleted
                FROM forum_posts WHERE post_id = $1
                """,
                target_id,
            )
        elif target_type == "comment":
            row = await self.conn.fetchrow(
                """
                SELECT c.comment_id, c.post_id, p.community_id, c.user_id AS author_id,
                       p.title, c.content, c.moderation_status, c.is_deleted
                FROM comments c JOIN forum_posts p ON p.post_id = c.post_id
                WHERE c.comment_id = $1
                """,
                target_id,
            )
        else:
            return None
        return self._record_to_dict(row) if row else None

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        row = await self.conn.fetchrow(
            "SELECT id, user_type, status, display_name, suspended_until FROM users WHERE id = $1",
            user_id,
        )
        return self._record_to_dict(row) if row else None

    async def set_content_status(
        self, target_type: str, target_id: str, status: str, clear_flag: bool = False
    ) -> None:
        table, key = _TABLES[target_type]
        await self.conn.execute(
            f"""
            UPDATE {table}
            SET moderation_status = $2,
                flagged_reason = CASE WHEN $3 THEN NULL ELSE flagged_reason END,
                updated_at = NOW()
            WHERE {key} = $1
            """,
            target_id, status, clear_flag,
        )

    async def recount_replies(self, post_id: str) -> None:
        """replies_count counts only the comments everyone can see."""
        await self.conn.execute(
            """
            UPDATE forum_posts SET replies_count = (
                SELECT COUNT(*) FROM comments
                WHERE post_id = $1 AND is_deleted = FALSE AND moderation_status = 'approved'
            )
            WHERE post_id = $1
            """,
            post_id,
        )

    async def suspend_user(self, user_id: str, until: Optional[datetime], reason: Optional[str]) -> None:
        """A suspension with no end date is a ban. The auth middleware refuses suspended users' tokens."""
        await self.conn.execute(
            """
            UPDATE users
            SET status = 'suspended', suspended_until = $2, suspended_reason = $3, updated_at = NOW()
            WHERE id = $1
            """,
            user_id, until, reason,
        )

    async def close_reports(
        self,
        report: Dict[str, Any],
        status: str,
        moderator_id: str,
        action: str,
        notes: Optional[str],
        whole_target: bool,
    ) -> int:
        """Close this report and, when the decision is about the content, every other open report on it."""
        if whole_target:
            result = await self.conn.execute(
                """
                UPDATE content_reports
                SET status = $3, moderator_id = $4, action_taken = $5,
                    resolution_notes = $6, resolved_at = NOW()
                WHERE target_type = $1 AND target_id = $2 AND status = ANY($7::text[])
                """,
                report["target_type"], report["target_id"], status, moderator_id, action, notes,
                list(OPEN_REPORT_STATUSES),
            )
        else:
            result = await self.conn.execute(
                """
                UPDATE content_reports
                SET status = $2, moderator_id = $3, action_taken = $4,
                    resolution_notes = $5, resolved_at = NOW()
                WHERE report_id = $1
                """,
                report["report_id"], status, moderator_id, action, notes,
            )
        return int(result.split()[-1])

    async def record_action(
        self,
        moderator_id: str,
        target_user_id: Optional[str],
        report_id: Optional[str],
        target_type: Optional[str],
        target_id: Optional[str],
        action_type: str,
        reason: Optional[str] = None,
        duration_hours: Optional[int] = None,
    ) -> Dict[str, Any]:
        row = await self.conn.fetchrow(
            """
            INSERT INTO moderation_actions (
                moderator_id, target_user_id, report_id, target_type, target_id,
                action_type, reason, duration_hours
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
            """,
            moderator_id, target_user_id, report_id, target_type, target_id,
            action_type, reason, duration_hours,
        )
        return self._record_to_dict(row)

    # ------------------------------------------------------------------
    # Queue
    # ------------------------------------------------------------------
    async def list_queue(
        self,
        status: str = "open",
        target_type: Optional[str] = None,
        priority: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        if status == "open":
            statuses = list(OPEN_REPORT_STATUSES)
        elif status == "closed":
            statuses = list(CLOSED_REPORT_STATUSES)
        else:
            statuses = [status]

        params: List[Any] = [statuses]
        conditions = ["cr.status = ANY($1::text[])"]
        if target_type:
            params.append(target_type)
            conditions.append(f"cr.target_type = ${len(params)}")
        if priority:
            params.append(priority)
            conditions.append(f"cr.priority = ${len(params)}")
        where = " AND ".join(conditions)

        total = await self.conn.fetchval(f"SELECT COUNT(*) FROM content_reports cr WHERE {where}", *params)

        # Open reports: most urgent first, then oldest first. Closed reports: latest decision first.
        order = (
            "CASE cr.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 ELSE 2 END, cr.created_at ASC"
            if status == "open"
            else "cr.resolved_at DESC NULLS LAST, cr.created_at DESC"
        )
        params.extend([limit, (page - 1) * limit])
        rows = await self.conn.fetch(
            f"""
            SELECT
                cr.report_id, cr.target_type, cr.target_id, cr.reason, cr.description,
                cr.source, cr.priority, cr.status, cr.created_at, cr.resolved_at,
                cr.action_taken, cr.resolution_notes, cr.target_content AS reported_content,
                cr.reporter_id, ru.display_name AS reporter_name,
                cr.moderator_id, mu.display_name AS moderator_name,
                COALESCE(p.post_id, c.post_id) AS post_id,
                COALESCE(p.community_id, cp.community_id) AS community_id,
                COALESCE(p.title, cp.title) AS post_title,
                COALESCE(p.content, c.content) AS current_content,
                COALESCE(p.moderation_status, c.moderation_status) AS content_status,
                COALESCE(p.moderation_score, c.moderation_score) AS moderation_score,
                COALESCE(p.flagged_reason, c.flagged_reason) AS flagged_reason,
                COALESCE(p.is_deleted, c.is_deleted) AS content_deleted,
                au.id AS author_id, au.display_name AS author_name, au.user_type AS author_type,
                au.status AS author_status, au.suspended_until AS author_suspended_until,
                (
                    SELECT COUNT(*) FROM content_reports o
                    WHERE o.target_type = cr.target_type AND o.target_id = cr.target_id
                      AND o.status IN ('pending', 'under_review')
                ) AS open_reports_on_target
            FROM content_reports cr
            LEFT JOIN users ru ON ru.id = cr.reporter_id
            LEFT JOIN users mu ON mu.id = cr.moderator_id
            LEFT JOIN forum_posts p ON cr.target_type = 'post' AND p.post_id = cr.target_id
            LEFT JOIN comments c ON cr.target_type = 'comment' AND c.comment_id = cr.target_id
            LEFT JOIN forum_posts cp ON cp.post_id = c.post_id
            LEFT JOIN users au ON au.id = CASE
                WHEN cr.target_type = 'user' THEN cr.target_id
                ELSE COALESCE(p.user_id, c.user_id)
            END
            WHERE {where}
            ORDER BY {order}
            LIMIT ${len(params) - 1} OFFSET ${len(params)}
            """,
            *params,
        )
        items = self._records_to_list(rows)

        history = await self.author_history([i["author_id"] for i in items if i["author_id"]])
        for item in items:
            item["author_history"] = history.get(item["author_id"], _empty_history()) if item["author_id"] else None

        return {
            "data": items,
            "meta": {
                "total": total,
                "page": page,
                "limit": limit,
                "pages": (total + limit - 1) // limit if limit else 0,
            },
        }

    async def author_history(self, author_ids: List[Any]) -> Dict[Any, Dict[str, Any]]:
        """Past moderator actions against each author, and reports made about their content."""
        ids = list({str(a) for a in author_ids})
        if not ids:
            return {}
        actions = await self.conn.fetch(
            """
            SELECT target_user_id,
                   COUNT(*) FILTER (WHERE action_type = 'warn_user') AS warnings,
                   COUNT(*) FILTER (WHERE action_type = 'suspend_user') AS suspensions,
                   COUNT(*) FILTER (WHERE action_type = 'ban_user') AS bans,
                   COUNT(*) FILTER (WHERE action_type IN ('hide_content', 'delete_content')) AS content_removed,
                   MAX(created_at) AS last_action_at
            FROM moderation_actions
            WHERE target_user_id = ANY($1::uuid[])
            GROUP BY target_user_id
            """,
            ids,
        )
        reports = await self.conn.fetch(
            """
            SELECT COALESCE(p.user_id, c.user_id) AS author_id,
                   COUNT(*) AS reports_received,
                   COUNT(*) FILTER (WHERE cr.status = 'actioned') AS reports_upheld
            FROM content_reports cr
            LEFT JOIN forum_posts p ON cr.target_type = 'post' AND p.post_id = cr.target_id
            LEFT JOIN comments c ON cr.target_type = 'comment' AND c.comment_id = cr.target_id
            WHERE COALESCE(p.user_id, c.user_id) = ANY($1::uuid[])
            GROUP BY 1
            """,
            ids,
        )
        history: Dict[Any, Dict[str, Any]] = {}
        for row in actions:
            entry = history.setdefault(row["target_user_id"], _empty_history())
            entry.update({k: row[k] for k in ("warnings", "suspensions", "bans", "content_removed", "last_action_at")})
        for row in reports:
            entry = history.setdefault(row["author_id"], _empty_history())
            entry.update({"reports_received": row["reports_received"], "reports_upheld": row["reports_upheld"]})
        return history


def _empty_history() -> Dict[str, Any]:
    return {
        "warnings": 0,
        "suspensions": 0,
        "bans": 0,
        "content_removed": 0,
        "reports_received": 0,
        "reports_upheld": 0,
        "last_action_at": None,
    }
