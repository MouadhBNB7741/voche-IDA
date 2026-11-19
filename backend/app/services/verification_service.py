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
        return await model.create_verification(user_id, {**details, "document_url": key})
    except Exception:
        await delete_licence(key)
        raise
