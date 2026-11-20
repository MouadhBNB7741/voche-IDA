"""
Doctor licence submissions: checks the uploaded file, stores it privately
and records the request in doctor_verifications.
"""
import logging
import uuid
from datetime import date
from typing import Any, Dict, Optional

from fastapi import HTTPException, UploadFile

from app.models.doctor_model import DoctorModel
from app.models.user_model import UserModel
from app.schemas.notification import NotificationType
from app.services.approval_service import tell_admins, tell_user
from app.services.audit_service import AuditService
from app.services.storage_service import get_private_storage

logger = logging.getLogger(__name__)

MAX_LICENCE_BYTES = 5 * 1024 * 1024

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


def detect_licence_type(data: bytes) -> Optional[str]:
    """Identify the file from its first bytes: the name and type sent by the browser can be faked."""
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def content_type_for(key: str) -> str:
    return CONTENT_TYPES.get(key.rsplit(".", 1)[-1], "application/octet-stream")


async def store_licence(user_id: str, file: UploadFile) -> str:
    """Validate an uploaded licence and save it privately. Returns its storage key."""
    data = await file.read(MAX_LICENCE_BYTES + 1)
    if len(data) > MAX_LICENCE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds the maximum limit of 5MB.")
    file_type = detect_licence_type(data)
    if not file_type:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: PDF, JPG, PNG, WEBP.")

    key = f"licenses/{user_id}/{uuid.uuid4().hex}.{file_type}"
    return await get_private_storage().save(key, data, CONTENT_TYPES[file_type])


async def delete_licence(key: Optional[str]) -> None:
    """Remove a stored licence. A failure is logged and never blocks the caller."""
    if not key:
        return
    try:
        await get_private_storage().delete(key)
    except Exception as e:
        logger.warning(f"Could not delete licence file {key}: {e}")


def check_expiration_date(expiration_date: Optional[date]) -> None:
    if expiration_date and expiration_date < date.today():
        raise HTTPException(status_code=400, detail="This license has already expired.")


async def submit_licence(conn, user_id: str, details: Dict[str, Any], file: UploadFile) -> Dict[str, Any]:
    """Create a verification request with its document."""
    model = DoctorModel(conn)
    existing = await model.get_verification_by_user(user_id)
    if existing and existing["status"] in ("pending", "approved"):
        raise HTTPException(status_code=400, detail=f"Verification already {existing['status']}")
    check_expiration_date(details.get("expiration_date"))

    key = await store_licence(user_id, file)
    try:
        row = await model.create_verification(user_id, {**details, "document_url": key})
    except Exception:
        await delete_licence(key)
        raise
    await tell_admins_licence_submitted(conn, user_id)
    return row


async def tell_admins_licence_submitted(conn, user_id: str) -> None:
    """Let admins know a licence is waiting for review."""
    name = await UserModel(conn).get_display_name(user_id, "A doctor")
    await tell_admins(conn, NotificationType.VERIFICATION_UPDATE, {
        "title": "New licence to review",
        "message": f"{name} sent a licence for verification.",
        "link": "/admin?tab=licences",
    })


async def decide_licence(conn, verification_id: str, admin: Dict[str, Any], status: str,
                         reason: Optional[str]) -> Dict[str, Any]:
    """Approve or reject a pending licence. The decision goes in the audit log, and the
    doctor gets a notification and an email."""
    async with conn.transaction():
        request = await conn.fetchrow(
            "SELECT user_id, status, license_number FROM doctor_verifications "
            "WHERE verification_id = $1 FOR UPDATE",
            verification_id,
        )
        if not request:
            raise HTTPException(status_code=404, detail="Verification not found")
        if request["status"] != "pending":
            raise HTTPException(status_code=409, detail=f"This licence is already {request['status']}")
        result = await DoctorModel(conn).review_verification(verification_id, str(admin["id"]), status, reason)
        await AuditService(conn).log_action(
            user_id=str(admin["id"]),
            action=f"verification.{status}",
            target_type="doctor_verification",
            target_id=verification_id,
            metadata={"doctor_id": str(request["user_id"]), "license_number": request["license_number"], "reason": reason},
        )

    if status == "approved":
        message = {
            "title": "Your licence is verified",
            "message": "An admin approved your licence. Your posts now show the Verified HCP badge, "
                       "and you can share resources.",
            "link": "/hcpdashboard",
        }
    else:
        message = {
            "title": "Your licence wasn't approved",
            "message": f"An admin couldn't approve your licence. Reason: {reason} "
                       "You can send a new document from your dashboard.",
            "link": "/hcpdashboard",
        }
    await tell_user(conn, request["user_id"], NotificationType.VERIFICATION_UPDATE, message)
    return result
