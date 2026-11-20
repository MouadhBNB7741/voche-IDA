"""
Data for the admin portal's "System & audit logs" tab: platform health, what waits for
review, a few platform figures, and the audit log of admin decisions.
"""
import json
import logging
import time
from typing import Any, Dict, Optional

from app.db.redis import get_redis_client
from app.models.moderation_model import OPEN_REPORT_STATUSES
from app.services.connection_manager import manager as live_notifications
from app.services.system_service import _app_start_time

logger = logging.getLogger(__name__)

# Audit log categories shown as filters in the portal, by action name prefix
AUDIT_CATEGORIES = {
    "moderation": "moderation.%",
    "verification": "verification.%",
    "resource": "resource.%",
    "event": "event.%",
}


async def admin_overview(conn) -> Dict[str, Any]:
    database = "connected"
    try:
        await conn.fetchval("SELECT 1")
    except Exception:  # noqa: BLE001
        database = "disconnected"

    redis = "connected"
    try:
        client = await get_redis_client()
        await client.ping()
    except Exception:  # noqa: BLE001
        redis = "unavailable"

    queues = await conn.fetchrow(
        """
        SELECT
            (SELECT COUNT(*) FROM content_reports WHERE status = ANY($1::text[])) AS open_reports,
            (SELECT COUNT(*) FROM content_reports
              WHERE status = ANY($1::text[]) AND priority = 'critical') AS critical_reports,
            (SELECT COUNT(*) FROM doctor_verifications WHERE status = 'pending') AS pending_licences,
            (SELECT COUNT(*) FROM resources WHERE approval_status = 'pending') AS pending_resources,
            (SELECT COUNT(*) FROM events WHERE approval_status = 'pending') AS pending_events
        """,
        list(OPEN_REPORT_STATUSES),
    )
    by_type = await conn.fetch(
        "SELECT COALESCE(user_type, 'no_role') AS user_type, COUNT(*) AS total "
        "FROM users WHERE status <> 'deleted' GROUP BY 1 ORDER BY 2 DESC"
    )
    activity = await conn.fetchrow(
        """
        SELECT
            (SELECT COUNT(*) FROM users
              WHERE status <> 'deleted' AND created_at > NOW() - INTERVAL '7 days') AS new_users,
            (SELECT COUNT(*) FROM users WHERE status = 'suspended') AS suspended,
            (SELECT COUNT(*) FROM forum_posts
              WHERE NOT COALESCE(is_deleted, FALSE) AND created_at > NOW() - INTERVAL '7 days') AS posts,
            (SELECT COUNT(*) FROM moderation_actions
              WHERE created_at > NOW() - INTERVAL '7 days') AS moderation_actions
        """
    )

    return {
        "health": {
            "status": "operational" if database == "connected" else "degraded",
            "database": database,
            "redis": redis,
            "uptime_seconds": round(time.time() - _app_start_time),
            # Counted on the backend instance that answered this request
            "live_connections": live_notifications.connection_count(),
            "live_via_redis": live_notifications.is_listening(),
        },
        "queues": dict(queues),
        "users": {
            "total": sum(r["total"] for r in by_type),
            "by_type": {r["user_type"]: r["total"] for r in by_type},
            "new_last_7_days": activity["new_users"],
            "suspended": activity["suspended"],
        },
        "activity": {
            "posts_last_7_days": activity["posts"],
            "moderation_actions_last_7_days": activity["moderation_actions"],
        },
    }


async def list_audit_logs(conn, category: Optional[str], page: int, limit: int) -> Dict[str, Any]:
    """Most recent first, with the name of the admin who acted."""
    pattern = AUDIT_CATEGORIES.get(category) if category else None
    total = await conn.fetchval(
        "SELECT COUNT(*) FROM audit_logs WHERE ($1::text IS NULL OR action LIKE $1)", pattern
    )
    rows = await conn.fetch(
        """
        SELECT a.log_id, a.user_id, a.action, a.target_type, a.target_id, a.metadata, a.created_at,
               COALESCE(NULLIF(TRIM(u.display_name), ''), u.email) AS actor_name
        FROM audit_logs a
        LEFT JOIN users u ON u.id = a.user_id
        WHERE ($1::text IS NULL OR a.action LIKE $1)
        ORDER BY a.created_at DESC
        LIMIT $2 OFFSET $3
        """,
        pattern, limit, (page - 1) * limit,
    )
    data = []
    for row in rows:
        item = dict(row)
        if isinstance(item.get("metadata"), str):
            try:
                item["metadata"] = json.loads(item["metadata"])
            except ValueError:
                item["metadata"] = {}
        data.append(item)
    return {
        "data": data,
        "meta": {"total": total, "page": page, "limit": limit, "total_pages": max(1, -(-total // limit))},
    }
