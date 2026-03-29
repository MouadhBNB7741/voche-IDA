"""
Notification Service — Reusable business logic for notifications.

This is the CENTRAL notification dispatch service used across the entire platform:
  - HCP verification flow
  - Content moderation
  - Admin actions
  - Trial alerts
  - Event reminders
  - Organization membership

Routes call this service; this service calls NotificationModel.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.models.notification_model import NotificationModel
from app.schemas.notification import NotificationType, NotificationPreferences

logger = logging.getLogger(__name__)


class NotificationService:
    """
    High-level notification operations.
    Transform events into specific, guarded notifications.
    """

    def __init__(self, conn):
        self.conn = conn
        self.model = NotificationModel(conn)
        # Internal imports to avoid circular deps
        from app.models.system_model import SystemModel
        from app.models.user_model import UserModel
        self.system_model = SystemModel(conn)
        self.user_model = UserModel(conn)

    # ── PUBLIC API ──────────────────────────────────────────────────────

    async def notify_user(
        self,
        user_id: str,
        notif_type: NotificationType,
        data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        CENTRAL DISPATCH: Send a notification to a specific user.
        - Checks guard layer (preferences)
        - Maps data → title/message
        - Persists to DB
        """
        # 1. Guard Check: Is this type enabled for this user?
        if not await self._should_notify(user_id, notif_type):
            logger.debug(f"Notification suppressed for user {user_id} (Type: {notif_type})")
            return None

        # 2. Content Mapping: Get localized title/message/link
        content = self._map_event_to_notification(notif_type, data)
        if not content:
            logger.warning(f"No mapping found for notification type: {notif_type}")
            return None

        # 3. Persistence
        return await self.create_notification(
            user_id=user_id,
            notif_type=notif_type.value, # Persist as string value
            title=content["title"],
            message=content["message"],
            link=content.get("link"),
        )

    async def create_notification(
        self,
        user_id: str,
        notif_type: str,
        title: str,
        message: str,
        link: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Low-level create (bypass guard if needed, e.g. for critical system alerts)."""
        try:
            return await self.model.create(
                user_id=user_id,
                notif_type=notif_type,
                title=title,
                message=message,
                link=link,
                expires_at=expires_at,
            )
        except Exception as e:
            logger.error(f"Failed to create notification for user {user_id}: {e}")
            return {}

    async def notify_admins(
        self,
        notif_type: NotificationType,
        data: Dict[str, Any],
    ) -> int:
        """Shorthand for notifying all active admins (usually bypasses patient guards)."""
        try:
            admin_ids = await self.model.get_admin_user_ids()
            if not admin_ids:
                return 0

            content = self._map_event_to_notification(notif_type, data)
            if not content:
                return 0

            notifications = [
                {
                    "user_id": admin_id,
                    "type": notif_type.value,
                    "title": content["title"],
                    "message": content["message"],
                    "link": content.get("link"),
                    "expires_at": None,
                }
                for admin_id in admin_ids
            ]

            return await self.model.bulk_create(notifications)
        except Exception as e:
            logger.error(f"Failed to notify admins: {e}")
            return 0

    async def notify_bulk(
        self,
        user_ids: List[str],
        notif_type: NotificationType,
        data: Dict[str, Any],
    ) -> int:
        """
        Send the same notification to multiple users (with preference checks).
        """
        if not user_ids:
            return 0

        try:
            content = self._map_event_to_notification(notif_type, data)
            if not content:
                return 0

            notifications = []
            for uid in user_ids:
                if await self._should_notify(uid, notif_type):
                    notifications.append({
                        "user_id": uid,
                        "type": notif_type.value,
                        "title": content["title"],
                        "message": content["message"],
                        "link": content.get("link"),
                        "expires_at": None,
                    })

            if not notifications:
                return 0
                
            return await self.model.bulk_create(notifications)
        except Exception as e:
            logger.error(f"Failed to bulk notify: {e}")
            return 0

    # ── GUARD LAYER ───────────────────────────────────────────────────

    async def _should_notify(self, user_id: str, notif_type: NotificationType) -> bool:
        """
        Check if the user wants this specific notification type.
        Fetches 'notification_preferences' and validates against schema.
        """
        try:
            user = await self.user_model.get_by_id(user_id)
            if not user or not user.get("notification_preferences"):
                return True # Default to true if no prefs found

            prefs_raw = user["notification_preferences"]
            
            # Use Pydantic to normalize and validate
            prefs = NotificationPreferences(**prefs_raw)
            
            # Check if this type is explicitly disabled in the map
            # Types not listed are considered ENABLED by default
            return prefs.notificationTypes.get(notif_type, True)
        except Exception as e:
            logger.error(f"Guard check failed for user {user_id}: {e}")
            return True # Fallback to true (safety first)

    # ── EVENT MAPPING ──────────────────────────────────────────────────

    @staticmethod
    def _map_event_to_notification(
        notif_type: NotificationType, data: Dict[str, Any]
    ) -> Optional[Dict[str, str]]:
        """
        CENTRAL COPY: Map enum key to title/message.
        Everything user-facing is defined HERE.
        """
        m = {
            # Clinical
            NotificationType.TRIAL_MATCH: {
                "title": "New Trial Match Found 🔬",
                "message": f"Good news! A new trial matches your profile: {data.get('trial_title')}",
                "link": f"/trials/{data.get('trial_id')}",
            },
            NotificationType.TRIAL_ALERT: {
                "title": "Clinical Trial Alert",
                "message": f"Update for trial {data.get('trial_title')}: {data.get('reason')}",
                "link": f"/trials/{data.get('trial_id')}",
            },

            # Community
            NotificationType.COMMUNITY_REPLY: {
                "title": "New Post Reply",
                "message": f"{data.get('replier_name', 'Someone')} replied to your post: \"{data.get('post_title')}\"",
                "link": data.get("link"),
            },
            NotificationType.COMMUNITY_LIKE: {
                "title": "Post Liked ❤️",
                "message": f"{data.get('user_name', 'Someone')} liked your post.",
                "link": data.get("link"),
            },

            # Events
            NotificationType.EVENT_REMINDER: {
                "title": f"Upcoming Event: {data.get('event_title')}",
                "message": f"Your registered event is starting in {data.get('hours', '24')} hours. Don't miss out!",
                "link": f"/events/{data.get('event_id')}",
            },
            NotificationType.EVENT_UPDATE: {
                "title": "Event Update",
                "message": f"An update was posted for {data.get('event_title')}.",
                "link": f"/events/{data.get('event_id')}",
            },

            # Organizations
            NotificationType.ORG_REQUEST_UPDATE: {
                "title": "Organization Request Update",
                "message": f"Your request to join {data.get('org_name')} has been {data.get('status', 'updated')}.",
                "link": f"/organizations/{data.get('org_id')}",
            },

            # Resources
            NotificationType.RESOURCE_UPDATE: {
                "title": "New Resource Available",
                "message": f"A new resource was added: {data.get('resource_title')}",
                "link": f"/resources/{data.get('resource_id')}",
            },

            # Surveys
            NotificationType.SURVEY_AVAILABLE: {
                "title": "New Research Survey 📝",
                "message": f"A new survey is available for completion: {data.get('survey_title')}",
                "link": f"/surveys/{data.get('survey_id')}",
            },

            # System
            NotificationType.SYSTEM_ANNOUNCEMENT: {
                "title": data.get("title", "System Announcement"),
                "message": data.get("message", "A new system update is available."),
                "link": data.get("link"),
            },
        }

        # Fallback to old keys for backward compatibility or Phase 2 types if needed
        # but here we strictly follow the enum m.get(notif_type)
        return m.get(notif_type)


    # ── CRUD (called by routes) ─────────────────────────────────────────

    async def get_user_notifications(
        self,
        user_id: str,
        *,
        read_status: Optional[bool] = None,
        notif_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Get paginated notifications for a user."""
        result = await self.model.get_user_notifications(
            user_id,
            read_status=read_status,
            notif_type=notif_type,
            date_from=date_from,
            date_to=date_to,
            page=page,
            limit=limit,
        )

        # Log action (non-blocking analytics)
        try:
            await self.system_model.log_activity(
                user_id=user_id,
                action="list_notifications",
                entity_type="notification",
                metadata={"filters": {"read_status": read_status, "type": notif_type}},
            )
        except Exception:
            pass

        return result

    async def mark_read(self, notification_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Mark a single notification as read."""
        return await self.model.mark_read(notification_id, user_id)

    async def mark_all_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user."""
        return await self.model.mark_all_read(user_id)

    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Delete a notification (with ownership check)."""
        return await self.model.delete(notification_id, user_id)
