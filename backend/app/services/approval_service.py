"""
Resources that members submit and events they suggest: who may submit, uploaded files,
and the admin's decision (with a notification, an email and an audit log entry).

Admins' own resources and events are published straight away; everything else waits as "pending".
"""
import logging
import uuid
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException, UploadFile

from app.core.config import settings
from app.models.event_model import EventModel
from app.models.resource_model import ResourceModel
from app.models.user_model import UserModel
from app.schemas.notification import NotificationType
from app.services.audit_service import AuditService
from app.services.email import EmailService
from app.services.notification_service import NotificationService
from app.services.storage_service import get_private_storage

logger = logging.getLogger(__name__)

MB = 1024 * 1024
# Mouadh's answer Q37: PDFs up to 5 MB, videos (MP4, WebM) up to 20 MB; longer videos as a YouTube or Vimeo link
RESOURCE_FILE_LIMITS = {"pdf": 5 * MB, "mp4": 20 * MB, "webm": 20 * MB}
RESOURCE_CONTENT_TYPES = {"pdf": "application/pdf", "mp4": "video/mp4", "webm": "video/webm"}
# Which files fit which kind of resource
FILES_FOR_RESOURCE_TYPE = {
    "document": {"pdf"},
    "toolkit": {"pdf"},
    "video": {"mp4", "webm"},
    "course": {"pdf", "mp4", "webm"},
}

CANT_SUBMIT = (
    "Only verified healthcare professionals, approved members of an organization "
    "and admins can share resources."
)
VERIFY_FIRST = "Verify your medical license first, then you can share resources."


class ApprovalError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


# ======================================================================
# Who may submit resources (Mouadh's answer Q36)
# ======================================================================
async def resource_submission_access(conn, user: Optional[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    if not user:
        return False, "Sign in to share a resource."
    if user.get("user_type") == "admin":
        return True, None
    row = await conn.fetchrow(
        """
        SELECT u.user_type, u.is_verified,
               EXISTS (
                   SELECT 1 FROM organization_members m
                   WHERE m.user_id = u.id AND m.status = 'approved'
               ) AS approved_member
        FROM users u WHERE u.id = $1
        """,
        user["id"],
    )
    if not row:
        return False, CANT_SUBMIT
    if row["user_type"] == "hcp":
        if row["is_verified"]:
            return True, None
        if not row["approved_member"]:
            return False, VERIFY_FIRST
    if row["approved_member"]:
        return True, None
    return False, CANT_SUBMIT


async def submitter_organization(conn, user_id: str) -> Optional[str]:
    """The organization a member submits for: their first approved membership."""
    org_id = await conn.fetchval(
        """
        SELECT org_id FROM organization_members
        WHERE user_id = $1 AND status = 'approved'
        ORDER BY joined_at LIMIT 1
        """,
        user_id,
    )
    return str(org_id) if org_id else None


# ======================================================================
# Uploaded files
# ======================================================================
def detect_resource_file(data: bytes) -> Optional[str]:
    """Identify the file from its first bytes: the name and type sent by the browser can be faked."""
    if data.startswith(b"%PDF-"):
        return "pdf"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return "mp4"
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return "webm"
    return None


async def store_resource_file(file: UploadFile, resource_type: str) -> Dict[str, Any]:
    """Check an uploaded resource file and save it privately. Returns what to record about it."""
    largest = max(RESOURCE_FILE_LIMITS.values())
    data = await file.read(largest + 1)
    kind = detect_resource_file(data)
    if not kind:
        raise HTTPException(status_code=400, detail="Upload a PDF document or an MP4 or WebM video.")
    if len(data) > RESOURCE_FILE_LIMITS[kind]:
        limit_mb = RESOURCE_FILE_LIMITS[kind] // MB
        label = "PDF files" if kind == "pdf" else "Videos"
        hint = "" if kind == "pdf" else " For a longer video, add a YouTube or Vimeo link instead."
        raise HTTPException(status_code=400, detail=f"{label} can be at most {limit_mb} MB.{hint}")
    if kind not in FILES_FOR_RESOURCE_TYPE.get(resource_type, set()):
        wanted = "a video (MP4 or WebM)" if resource_type == "video" else "a PDF"
        raise HTTPException(status_code=400, detail=f"A {resource_type} needs {wanted}.")

    key = f"resources/{uuid.uuid4().hex}.{kind}"
    await get_private_storage().save(key, data, RESOURCE_CONTENT_TYPES[kind])
    name = (file.filename or f"resource.{kind}").replace("\\", "/").split("/")[-1][:255]
    return {"file_key": key, "file_name": name, "file_type": RESOURCE_CONTENT_TYPES[kind], "file_size": len(data)}


async def delete_resource_file(key: Optional[str]) -> None:
    if not key:
        return
    try:
        await get_private_storage().delete(key)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not delete resource file {key}: {e}")


async def read_resource_file(key: str) -> Optional[bytes]:
    return await get_private_storage().read(key)


# ======================================================================
# Admin decisions
# ======================================================================
async def decide_resource(conn, resource_id: str, admin: Dict[str, Any], decision: str, reason: Optional[str]) -> Dict[str, Any]:
    model = ResourceModel(conn)
    new_status = "approved" if decision == "approve" else "rejected"
    async with conn.transaction():
        resource = await model.get_for_decision(resource_id)
        if not resource:
            raise ApprovalError(404, "NOT_FOUND", "Resource not found")
        if resource["approval_status"] != "pending":
            raise ApprovalError(409, "ALREADY_DECIDED", f"This resource is already {resource['approval_status']}")
        updated = await model.set_approval(resource_id, new_status, str(admin["id"]), reason)
        await AuditService(conn).log_action(
            user_id=str(admin["id"]),
            action=f"resource.{new_status}",
            target_type="resource",
            target_id=resource_id,
            metadata={"title": resource["title"], "reason": reason, "submitted_by": _str(resource["submitted_by"])},
        )

    title = resource["title"]
    if new_status == "approved":
        message = {
            "title": "Your resource is published",
            "message": f"\"{title}\" was approved and is now in the Resources hub.",
            "link": f"/resources/{resource_id}",
        }
    else:
        message = {
            "title": "Your resource wasn't approved",
            "message": f"\"{title}\" wasn't approved. Reason: {reason}",
            "link": "/resources",
        }
    await tell_user(conn, resource["submitted_by"], NotificationType.RESOURCE_UPDATE, message)
    return updated


async def decide_event(conn, event_id: str, admin: Dict[str, Any], decision: str, reason: Optional[str]) -> Dict[str, Any]:
    model = EventModel(conn)
    new_status = "approved" if decision == "approve" else "rejected"
    async with conn.transaction():
        event = await model.get_for_decision(event_id)
        if not event:
            raise ApprovalError(404, "NOT_FOUND", "Event not found")
        if event["approval_status"] != "pending":
            raise ApprovalError(409, "ALREADY_DECIDED", f"This event is already {event['approval_status']}")
        updated = await model.set_approval(event_id, new_status, str(admin["id"]), reason)
        await AuditService(conn).log_action(
            user_id=str(admin["id"]),
            action=f"event.{new_status}",
            target_type="event",
            target_id=event_id,
            metadata={"title": event["title"], "reason": reason, "created_by": _str(event["created_by"])},
        )

    title = event["title"]
    if new_status == "approved":
        message = {
            "title": "Your event is published",
            "message": f"\"{title}\" was approved and is now listed in Events.",
            "link": f"/events/{event_id}",
        }
    else:
        message = {
            "title": "Your event suggestion wasn't approved",
            "message": f"\"{title}\" wasn't approved. Reason: {reason}",
            "link": "/events",
        }
    await tell_user(conn, event["created_by"], NotificationType.EVENT_UPDATE, message)
    return updated


async def tell_admins_resource_submitted(conn, resource: Dict[str, Any]) -> None:
    """Let admins know a resource is waiting for review."""
    name = await UserModel(conn).get_display_name(resource["submitted_by"], "A member")
    await tell_admins(conn, NotificationType.RESOURCE_UPDATE, {
        "title": "New resource to review",
        "message": f"{name} shared \"{resource['title']}\". It is waiting for approval.",
        "link": f"/resources/{resource['resource_id']}",
    })


async def tell_admins_event_suggested(conn, event: Dict[str, Any]) -> None:
    """Let admins know an event suggestion is waiting for review."""
    name = await UserModel(conn).get_display_name(event["created_by"], "A member")
    await tell_admins(conn, NotificationType.EVENT_UPDATE, {
        "title": "New event to review",
        "message": f"{name} suggested \"{event['title']}\". It is waiting for approval.",
        "link": f"/events/{event['event_id']}",
    })


async def tell_admins(conn, notif_type: NotificationType, message: Dict[str, Any]) -> None:
    """Notify every admin. A failure is logged and never fails the submission."""
    try:
        await NotificationService(conn).notify_admins(notif_type, message)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not notify admins: {e}")


async def tell_user(conn, user_id: Any, notif_type: NotificationType, message: Dict[str, str]) -> None:
    """In-app notification and email. Failures are logged and never undo the decision."""
    if not user_id:
        return
    try:
        await NotificationService(conn).notify_user(user_id=str(user_id), notif_type=notif_type, data=message)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not notify user {user_id}: {e}")

    email = await conn.fetchval(
        "SELECT email FROM users WHERE id = $1 AND status NOT IN ('deleted')", user_id
    )
    if email:
        link = f"{settings.frontend_url.rstrip('/')}{message['link']}" if message.get("link") else None
        await EmailService.send_message(to=email, subject=message["title"], text=message["message"], link=link)


def _str(value: Any) -> Optional[str]:
    return str(value) if value else None
