"""
Audit Service — Cross-cutting audit log service for admin/security actions.

Used across:
  - Admin actions (suspend, verify, moderate)
  - HCP verification decisions
  - Content moderation
  - Trial management
  - Resource approval

This service wraps AuditLogModel and provides a clean, reusable API.
"""
import logging
from typing import Optional, Dict, Any

from app.models.system_model import AuditLogModel

logger = logging.getLogger(__name__)


class AuditService:
    """
    Cross-cutting audit logging service.
    Instantiate with an asyncpg connection.
    """

    def __init__(self, conn):
        self.conn = conn
        self.model = AuditLogModel(conn)

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
        Log an auditable action. Gracefully handles missing audit_logs table.

        Args:
            user_id:     The actor performing the action (None for system actions)
            action:      Action name (e.g., 'hcp_verified', 'user_suspended')
            target_type: Entity type acted upon ('user', 'trial', 'report', etc.)
            target_id:   ID of the entity acted upon
            metadata:    Additional JSONB context (old values, new values, reason)
            ip_address:  Actor's IP address
        """
        try:
            return await self.model.log_action(
                user_id=user_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                metadata=metadata,
                ip_address=ip_address,
            )
        except Exception as e:
            # Audit logging should never break the main operation
            logger.error(f"Audit log failed (non-blocking): {e}")
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
        """Query audit logs with optional filters."""
        return await self.model.get_logs(
            user_id=user_id,
            action=action,
            target_type=target_type,
            page=page,
            limit=limit,
        )

    # ── CONVENIENCE METHODS ─────────────────────────────────────────────

    async def log_admin_action(
        self,
        admin_id: str,
        action: str,
        target_type: str,
        target_id: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Shorthand for logging admin-performed actions."""
        meta = {"performed_by": "admin", **(details or {})}
        return await self.log_action(
            user_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata=meta,
            ip_address=ip_address,
        )

    async def log_moderation(
        self,
        moderator_id: str,
        report_id: str,
        action_taken: str,
        target_type: str,
        target_id: str,
        notes: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Shorthand for logging moderation decisions."""
        return await self.log_action(
            user_id=moderator_id,
            action="report_resolved",
            target_type=target_type,
            target_id=target_id,
            metadata={
                "report_id": report_id,
                "action_taken": action_taken,
                "notes": notes,
            },
            ip_address=ip_address,
        )

    async def log_verification_decision(
        self,
        admin_id: str,
        user_id: str,
        decision: str,
        notes: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Shorthand for logging HCP verification decisions."""
        action = "hcp_verified" if decision == "approved" else "hcp_rejected"
        return await self.log_action(
            user_id=admin_id,
            action=action,
            target_type="user",
            target_id=user_id,
            metadata={"decision": decision, "notes": notes},
            ip_address=ip_address,
        )
