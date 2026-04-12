"""
System Model — Raw SQL queries for system/health/feedback/audit.
Covers: feedback storage, audit_logs, user_activity_log, and health checks.
"""
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.models.base_model import DBModel


class SystemModel(DBModel):
    """
    Encapsulates all SQL logic for system-level tables:
    - user_activity_log (insert + query)
    - health / DB connectivity checks
    - feedback (stored in user_activity_log as action='submit_feedback')
    """

    # ── FEEDBACK ────────────────────────────────────────────────────────

    async def store_feedback(
        self,
        user_id: Optional[str],
        category: str,
        message: str,
        rating: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Store user feedback in the platform_feedback table.
        Returns the created feedback record.
        """
        query = """
            INSERT INTO platform_feedback
                (user_id, category, message, rating, ip_address, user_agent)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING feedback_id, user_id, category, message, rating, ip_address, created_at
        """
        row = await self.conn.fetchrow(query, user_id, category, message, rating, ip_address, user_agent)
        return self._record_to_dict(row) if row else {}

    # ── ACTIVITY LOGGING ────────────────────────────────────────────────

    async def log_activity(
        self,
        user_id: Optional[str],
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Insert a user activity log entry."""
        query = """
            INSERT INTO user_activity_log
                (user_id, action, entity_type, entity_id, metadata, ip_address, user_agent)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        meta_str = json.dumps(metadata) if metadata else "{}"
        await self.conn.execute(
            query, user_id, action, entity_type, entity_id, meta_str, ip_address, user_agent
        )

    # ── HEALTH CHECK ────────────────────────────────────────────────────

    async def check_db_connectivity(self) -> bool:
        """Simple SELECT 1 to verify DB is reachable."""
        try:
            result = await self.conn.fetchval("SELECT 1")
            return result == 1
        except Exception:
            return False

    async def get_db_stats(self) -> Dict[str, Any]:
        """Returns basic DB metrics: table count, DB size, active connections."""
        try:
            table_count = await self.conn.fetchval(
                "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public'"
            )
            db_size = await self.conn.fetchval(
                "SELECT pg_size_pretty(pg_database_size(current_database()))"
            )
            active_conns = await self.conn.fetchval(
                "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'"
            )
            return {
                "table_count": table_count,
                "database_size": db_size,
                "active_connections": active_conns,
            }
        except Exception:
            return {"table_count": None, "database_size": None, "active_connections": None}


class AuditLogModel(DBModel):
    """
    Encapsulates SQL logic for the `audit_logs` table (Phase 2).
    This table may not exist yet — operations gracefully handle that case.
    """

    async def _table_exists(self) -> bool:
        """Check if audit_logs table exists."""
        result = await self.conn.fetchval(
            "SELECT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'audit_logs')"
        )
        return bool(result)

    async def log_action(
        self,
        user_id: Optional[str],
        action: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Insert an audit log entry. If the audit_logs table doesn't exist yet,
        falls back to user_activity_log.
        """
        meta_str = json.dumps(metadata) if metadata else "{}"

        if await self._table_exists():
            query = """
                INSERT INTO audit_logs
                    (user_id, action, target_type, target_id, metadata, ip_address)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING log_id, user_id, action, target_type, target_id, metadata, ip_address, created_at
            """
            row = await self.conn.fetchrow(
                query, user_id, action, target_type, target_id, meta_str, ip_address
            )
            if row:
                data = self._record_to_dict(row)
                if isinstance(data.get("metadata"), str):
                    try:
                        data["metadata"] = json.loads(data["metadata"])
                    except Exception:
                        pass
                return data
            return None
        else:
            # Fallback: store in user_activity_log
            query = """
                INSERT INTO user_activity_log
                    (user_id, action, entity_type, entity_id, metadata, ip_address)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING activity_id, user_id, action, entity_type, entity_id, metadata, created_at
            """
            row = await self.conn.fetchrow(
                query, user_id, action, target_type, target_id, meta_str, ip_address
            )
            if row:
                data = self._record_to_dict(row)
                if isinstance(data.get("metadata"), str):
                    try:
                        data["metadata"] = json.loads(data["metadata"])
                    except Exception:
                        pass
                return data
            return None

    async def get_logs(
        self,
        *,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        target_type: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Query audit logs with optional filters. Falls back to activity log."""
        if not await self._table_exists():
            return {"data": [], "meta": {"total": 0, "page": page, "limit": limit, "total_pages": 0}}

        conditions = []
        params: list = []
        idx = 1

        if user_id:
            conditions.append(f"user_id = ${idx}")
            params.append(user_id)
            idx += 1
        if action:
            conditions.append(f"action = ${idx}")
            params.append(action)
            idx += 1
        if target_type:
            conditions.append(f"target_type = ${idx}")
            params.append(target_type)
            idx += 1

        where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""

        total = await self.conn.fetchval(f"SELECT COUNT(*) FROM audit_logs{where_clause}", *params)
        offset = (page - 1) * limit
        data_query = f"""
            SELECT log_id, user_id, action, target_type, target_id, metadata, ip_address, created_at
            FROM audit_logs{where_clause}
            ORDER BY created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
        """
        params.extend([limit, offset])
        rows = await self.conn.fetch(data_query, *params)

        results = []
        for r in rows:
            d = self._record_to_dict(r)
            if isinstance(d.get("metadata"), str):
                try:
                    d["metadata"] = json.loads(d["metadata"])
                except Exception:
                    pass
            results.append(d)

        return {
            "data": results,
            "meta": {
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": max(1, -(-total // limit)),
            },
        }
