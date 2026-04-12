"""
System Service — Business logic for health, feedback, metadata, and system status.
"""
import time
import logging
from typing import Optional, Dict, Any

from app.models.system_model import SystemModel
from app.db.postgres import PostgresDB
from app.services.notification_service import NotificationService
from app.schemas.notification import NotificationType
from app.models.notification_model import NotificationModel

logger = logging.getLogger(__name__)

# Track application start time for uptime calculation
_app_start_time = time.time()


class SystemService:
    """
    High-level system operations.
    Instantiate with an asyncpg connection (injected by route layer).
    """

    def __init__(self, conn):
        self.conn = conn
        self.model = SystemModel(conn)

    # ── FEEDBACK ────────────────────────────────────────────────────────

    async def submit_feedback(
        self,
        user_id: Optional[str],
        category: str,
        message: str,
        rating: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Store user feedback and return a ticket reference.
        """
        result = await self.model.store_feedback(
            user_id=user_id,
            category=category,
            message=message,
            rating=rating,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return {
            "ticket_id": result.get("feedback_id"),
            "message": "Feedback submitted successfully",
            "rating": result.get("rating"),
            "created_at": result.get("created_at"),
        }

    # ── HEALTH CHECK ────────────────────────────────────────────────────

    async def health_check(self) -> Dict[str, Any]:
        """
        Returns API health status with DB connectivity.
        """
        from datetime import datetime, timezone

        db_ok = await self.model.check_db_connectivity()

        return {
            "status": "healthy" if db_ok else "degraded",
            "version": "1.0.0",
            "database": "connected" if db_ok else "disconnected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── SYSTEM STATUS ───────────────────────────────────────────────────

    async def system_status(self) -> Dict[str, Any]:
        """
        Returns detailed system status for monitoring.
        """
        db_ok = await self.model.check_db_connectivity()
        db_stats = await self.model.get_db_stats()
        uptime = time.time() - _app_start_time

        return {
            "api_version": "v1",
            "status": "operational" if db_ok else "degraded",
            "uptime_seconds": round(uptime, 2),
            "database": {
                "status": "connected" if db_ok else "disconnected",
                **db_stats,
            },
            "features": {
                "ai_assistant": True,
                "forums": True,
                "events": True,
                "surveys": True,
                "resources": True,
                "organizations": True,
                "notifications": True,
            },
        }

    # ── METADATA ────────────────────────────────────────────────────────

    @staticmethod
    def get_metadata() -> Dict[str, Any]:
        """
        Return platform enums/metadata for frontend dropdowns.
        Can be switched to DB-backed if needed in the future.
        """
        return {
            "countries": [
                "Algeria", "Angola", "Benin", "Botswana", "Burkina Faso",
                "Cameroon", "Côte d'Ivoire", "DR Congo", "Egypt", "Ethiopia",
                "Ghana", "Kenya", "Madagascar", "Malawi", "Mali", "Morocco",
                "Mozambique", "Nigeria", "Rwanda", "Senegal", "South Africa",
                "Tanzania", "Tunisia", "Uganda", "Zambia", "Zimbabwe",
            ],
            "disease_areas": [
                "HIV/AIDS", "Malaria", "Tuberculosis", "Cancer", "Diabetes",
                "Cardiovascular Disease", "Hepatitis", "Ebola", "COVID-19",
                "Sickle Cell Disease", "Neglected Tropical Diseases",
                "Mental Health", "Maternal Health", "Respiratory Diseases",
                "Infectious Diseases", "Other",
            ],
            "languages": [
                {"code": "en", "name": "English"},
                {"code": "fr", "name": "French"},
                {"code": "pt", "name": "Portuguese"},
                {"code": "ar", "name": "Arabic"},
                {"code": "sw", "name": "Swahili"},
                {"code": "ha", "name": "Hausa"},
                {"code": "yo", "name": "Yoruba"},
                {"code": "zu", "name": "Zulu"},
                {"code": "am", "name": "Amharic"},
            ],
            "trial_phases": [
                "Phase 1", "Phase 2", "Phase 3", "Phase 4", "Post-Market",
            ],
            "trial_statuses": [
                "Recruiting", "Active", "Completed", "Suspended", "Not yet recruiting",
            ],
            "roles": [
                "patient", "hcp", "org_member", "admin", "caregiver",
            ],
            "community_types": [
                "disease_specific", "general", "hcp_only",
            ],
            "event_types": [
                "webinar", "conference", "training", "roundtable",
            ],
            "resource_types": [
                "video", "document", "toolkit", "course",
            ],
            "feedback_categories": [
                "platform", "trial", "patient", "feature", "bug", "other",
            ],
        }

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
        """Log a user activity (fire-and-forget pattern)."""
        try:
            await self.model.log_activity(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                metadata=metadata,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")

    # ── SYSTEM ANNOUNCEMENT ─────────────────────────────────────────────

    async def send_announcement(
        self,
        title: str,
        message: str,
        link: Optional[str] = None,
        org_id: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a scoped platform announcement.
        - Global: All active users
        - Org: Members of specified organization
        - Group: Members of specified working group
        """
        notif_service = NotificationService(self.conn)
        notif_model = NotificationModel(self.conn)

        target_uids = []
        scope = "global"

        # Priority: Group > Org > Global
        if group_id:
            target_uids = await notif_model.get_group_user_ids(str(group_id))
            scope = "working_group"
        elif org_id:
            target_uids = await notif_model.get_org_user_ids(str(org_id))
            scope = "organization"
        else:
            target_uids = await notif_model.get_all_active_user_ids()
            scope = "global"

        if not target_uids:
            return {"sent_count": 0, "scope": scope, "target_total": 0}

        sent_count = await notif_service.notify_bulk(
            user_ids=target_uids,
            notif_type=NotificationType.SYSTEM_ANNOUNCEMENT,
            data={"title": title, "message": message, "link": link}
        )

        return {
            "sent_count": sent_count,
            "scope": scope,
            "target_total": len(target_uids),
            "message": f"Successfully sent announcement to {sent_count} users."
        }
