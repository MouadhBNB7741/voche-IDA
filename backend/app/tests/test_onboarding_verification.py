"""
Onboarding wizard, doctor licence uploads (private files) and the storage module.
"""
import io
import os
import secrets
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from app.core import cron_manager
from app.core.config import settings
from app.core.security import create_jwt
from app.db.postgres import PostgresDB
from app.services.storage_service import LocalStorage, S3Storage

BASE = "/api/v1"
PASSWORD = "StrongPassword123!"
PDF_BYTES = b"%PDF-1.7\n fake licence content"
PNG_BYTES = b"\x89PNG\r\n\x1a\n fake image content"


# ── Helpers ──────────────────────────────────────────────────────────────────

async def db_value(query: str, *args):
    async with PostgresDB.get_pool().acquire() as conn:
        return await conn.fetchval(query, *args)


async def db_row(query: str, *args):
    async with PostgresDB.get_pool().acquire() as conn:
        return await conn.fetchrow(query, *args)


async def db_execute(query: str, *args):
    async with PostgresDB.get_pool().acquire() as conn:
        return await conn.execute(query, *args)


async def create_user(client: AsyncClient, user_type: str = "hcp") -> tuple[str, dict]:
    """Register a user. Returns (user_id, auth headers)."""
    email = f"onboard_{secrets.token_hex(4)}@example.com"
    res = await client.post(f"{BASE}/auth/register", json={
        "email": email, "password": PASSWORD,
        "first_name": "On", "last_name": "Board", "user_type": user_type,
    })
    assert res.status_code == 201, res.text
    user_id = str(await db_value("SELECT id FROM users WHERE email = $1", email))
    return user_id, {"Authorization": f"Bearer {res.json()['access_token']}"}


async def create_admin(client: AsyncClient) -> dict:
    user_id, headers = await create_user(client, "patient")
    await db_execute("UPDATE users SET user_type = 'admin' WHERE id = $1", user_id)
    return headers


async def create_user_without_role() -> tuple[str, dict]:
    """A Google sign-in user who has not chosen a role yet."""
    email = f"norole_{secrets.token_hex(4)}@example.com"
    user_id = str(await db_value("""
        INSERT INTO users (email, password_hash, user_type, display_name, status)
        VALUES ($1, NULL, NULL, 'New User', 'onboarding') RETURNING id
    """, email))
    return user_id, {"Authorization": f"Bearer {create_jwt({'sub': user_id})}"}


def licence_form(**overrides) -> dict:
    return {
        "license_number": "MD-12345",
        "institution": "General Hospital",
        "country": "Nigeria",
        "specialization": "Cardiology",
        "issuing_region": "Lagos",
        "expiration_date": (date.today() + timedelta(days=365)).isoformat(),
        **overrides,
    }


async def upload_licence(client: AsyncClient, headers: dict, content: bytes = PDF_BYTES,
                         filename: str = "licence.pdf", **form):
    return await client.post(
        f"{BASE}/doctors/verification/upload",
        data=licence_form(**form),
        files={"file": (filename, io.BytesIO(content), "application/pdf")},
        headers=headers,
    )


def stored_path(key: str) -> str:
    return os.path.join(settings.private_uploads_dir, *key.split("/"))


# ── Onboarding ───────────────────────────────────────────────────────────────

async def test_onboarding_saves_interests_and_location(client: AsyncClient):
    user_id, headers = await create_user(client, "patient")

    res = await client.post(f"{BASE}/users/onboarding/complete", json={
        "interests": ["Malaria", "Vaccines"], "location": "Lagos",
    }, headers=headers)

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["interests"] == ["Malaria", "Vaccines"]
    assert data["location"] == "Lagos"
    assert data["onboarding_completed_at"] is not None
    assert data["status"] == "active"


async def test_onboarding_can_be_skipped(client: AsyncClient):
    user_id, headers = await create_user(client, "patient")

    res = await client.post(f"{BASE}/users/onboarding/complete", json={}, headers=headers)

    assert res.status_code == 200, res.text
    assert await db_value("SELECT onboarding_completed_at FROM users WHERE id = $1", user_id) is not None


async def test_onboarding_keeps_the_first_completion_date(client: AsyncClient):
    user_id, headers = await create_user(client, "patient")
    await client.post(f"{BASE}/users/onboarding/complete", json={}, headers=headers)
    first = await db_value("SELECT onboarding_completed_at FROM users WHERE id = $1", user_id)

    await client.post(f"{BASE}/users/onboarding/complete", json={"location": "Abuja"}, headers=headers)

    assert await db_value("SELECT onboarding_completed_at FROM users WHERE id = $1", user_id) == first


async def test_onboarding_cannot_change_an_existing_role(client: AsyncClient):
    user_id, headers = await create_user(client, "patient")

    res = await client.post(f"{BASE}/users/onboarding/complete", json={"user_type": "hcp"}, headers=headers)

    assert res.status_code == 400
    assert await db_value("SELECT user_type FROM users WHERE id = $1", user_id) == "patient"


async def test_onboarding_cannot_grant_admin(client: AsyncClient):
    user_id, headers = await create_user_without_role()

    res = await client.post(f"{BASE}/users/onboarding/complete", json={"user_type": "admin"}, headers=headers)

    assert res.status_code == 422
    assert await db_value("SELECT user_type FROM users WHERE id = $1", user_id) is None


async def test_user_without_role_must_choose_one(client: AsyncClient):
    user_id, headers = await create_user_without_role()

    me = await client.get(f"{BASE}/users/me", headers=headers)
    assert me.status_code == 200, me.text
    assert me.json()["user_type"] is None
    assert me.json()["status"] == "onboarding"

    # Normal routes stay closed until the role is chosen
    assert (await client.get(f"{BASE}/users/me/preferences/notifications", headers=headers)).status_code == 401

    res = await client.post(f"{BASE}/users/onboarding/complete", json={}, headers=headers)
    assert res.status_code == 400

    res = await client.post(f"{BASE}/users/onboarding/complete", json={"user_type": "caregiver"}, headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["user_type"] == "caregiver"
    assert res.json()["status"] == "active"
    assert (await client.get(f"{BASE}/users/me/preferences/notifications", headers=headers)).status_code == 200


async def test_onboarding_requires_login(client: AsyncClient):
    assert (await client.post(f"{BASE}/users/onboarding/complete", json={})).status_code == 401


# ── Licence upload ───────────────────────────────────────────────────────────

async def test_upload_is_stored_privately_and_reaches_the_admin_queue(client: AsyncClient):
    user_id, headers = await create_user(client)
    admin_headers = await create_admin(client)

    res = await upload_licence(client, headers)

    assert res.status_code == 201, res.text
    data = res.json()
    assert data["status"] == "pending"
    assert data["has_document"] is True
    assert data["issuing_region"] == "Lagos"
    assert "document_url" not in data  # The storage location is never exposed

    key = await db_value("SELECT document_url FROM doctor_verifications WHERE user_id = $1", user_id)
    assert key.startswith(f"licenses/{user_id}/") and key.endswith(".pdf")
    assert os.path.isfile(stored_path(key))
    assert not os.path.abspath(stored_path(key)).startswith(os.path.abspath("uploads") + os.sep)
    assert (await client.get(f"/static/{key}")).status_code == 404
    assert (await client.get(f"/static/private/{key}")).status_code == 404

    queue = await client.get(f"{BASE}/doctors/admin/verifications", headers=admin_headers)
    item = next(v for v in queue.json() if v["verification_id"] == data["verification_id"])
    assert item["has_document"] is True


async def test_only_the_owner_and_admins_can_open_a_licence(client: AsyncClient):
    _, owner = await create_user(client)
    _, other = await create_user(client)
    admin = await create_admin(client)
    verification_id = (await upload_licence(client, owner)).json()["verification_id"]
    url = f"{BASE}/doctors/verification/{verification_id}/document"

    for headers in (owner, admin):
        res = await client.get(url, headers=headers)
        assert res.status_code == 200, res.text
        assert res.content == PDF_BYTES
        assert res.headers["content-type"] == "application/pdf"
        assert res.headers["cache-control"] == "private, no-store"
        assert res.headers["x-content-type-options"] == "nosniff"

    assert (await client.get(url, headers=other)).status_code == 403
    assert (await client.get(url)).status_code == 401


@pytest.mark.parametrize("content", [b"just some text", b"<html><script>alert(1)</script></html>", b""])
async def test_files_that_are_not_documents_are_refused(client: AsyncClient, content):
    user_id, headers = await create_user(client)

    res = await upload_licence(client, headers, content=content)

    assert res.status_code == 400
    assert await db_value("SELECT COUNT(*) FROM doctor_verifications WHERE user_id = $1", user_id) == 0


async def test_file_over_5mb_is_refused(client: AsyncClient):
    _, headers = await create_user(client)

    res = await upload_licence(client, headers, content=PDF_BYTES + b"0" * (5 * 1024 * 1024))

    assert res.status_code == 400
    assert "5MB" in res.json()["detail"]


async def test_expired_licence_is_refused(client: AsyncClient):
    _, headers = await create_user(client)

    res = await upload_licence(client, headers, expiration_date=(date.today() - timedelta(days=1)).isoformat())

    assert res.status_code == 400


async def test_unsafe_file_name_is_ignored(client: AsyncClient):
    user_id, headers = await create_user(client)

    res = await upload_licence(client, headers, filename="../../../evil.pdf")

    assert res.status_code == 201, res.text
    key = await db_value("SELECT document_url FROM doctor_verifications WHERE user_id = $1", user_id)
    assert "evil" not in key and ".." not in key


async def test_second_upload_waits_for_the_first_review(client: AsyncClient):
    _, headers = await create_user(client)
    await upload_licence(client, headers)

    res = await upload_licence(client, headers)

    assert res.status_code == 400
    assert res.json()["detail"] == "Verification already pending"


async def test_rejected_doctor_can_submit_again(client: AsyncClient):
    _, headers = await create_user(client)
    admin = await create_admin(client)
    verification_id = (await upload_licence(client, headers)).json()["verification_id"]
    await client.patch(f"{BASE}/doctors/admin/verifications/{verification_id}",
                       json={"status": "rejected", "rejection_reason": "Blurry photo"}, headers=admin)

    res = await upload_licence(client, headers, content=PNG_BYTES, filename="licence.png")

    assert res.status_code == 201, res.text
    assert res.json()["verification_id"] != verification_id


# ── /users/me/verification uses the same table ──────────────────────────────

async def submit_through_users_route(client: AsyncClient, headers: dict):
    return await client.post(
        f"{BASE}/users/me/verification",
        data={"licenseNumber": "MD-777", "issuingRegion": "Accra",
              "expirationDate": (date.today() + timedelta(days=30)).isoformat()},
        files={"file": ("licence.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
        headers=headers,
    )


async def test_users_route_writes_to_doctor_verifications(client: AsyncClient):
    user_id, headers = await create_user(client)

    res = await submit_through_users_route(client, headers)

    assert res.status_code == 200, res.text
    assert res.json()["data"]["status"] == "pending"
    row = await db_row("SELECT * FROM doctor_verifications WHERE user_id = $1", user_id)
    assert row["license_number"] == "MD-777"
    assert row["issuing_region"] == "Accra"
    assert row["document_url"] is not None


async def test_users_route_is_for_doctors_only(client: AsyncClient):
    _, headers = await create_user(client, "patient")
    assert (await submit_through_users_route(client, headers)).status_code == 403


async def test_updating_a_pending_request_replaces_the_file(client: AsyncClient):
    user_id, headers = await create_user(client)
    await submit_through_users_route(client, headers)
    old_key = await db_value("SELECT document_url FROM doctor_verifications WHERE user_id = $1", user_id)

    res = await client.patch(
        f"{BASE}/users/me/verification",
        data={"licenseNumber": "MD-888"},
        files={"file": ("new.png", io.BytesIO(PNG_BYTES), "image/png")},
        headers=headers,
    )

    assert res.status_code == 200, res.text
    row = await db_row("SELECT * FROM doctor_verifications WHERE user_id = $1", user_id)
    assert row["license_number"] == "MD-888"
    assert row["document_url"].endswith(".png")
    assert os.path.isfile(stored_path(row["document_url"]))
    assert not os.path.exists(stored_path(old_key))


async def test_withdrawing_deletes_the_request_and_its_file(client: AsyncClient):
    user_id, headers = await create_user(client)
    await submit_through_users_route(client, headers)
    key = await db_value("SELECT document_url FROM doctor_verifications WHERE user_id = $1", user_id)

    res = await client.delete(f"{BASE}/users/me/verification", headers=headers)

    assert res.status_code == 200, res.text
    assert await db_value("SELECT COUNT(*) FROM doctor_verifications WHERE user_id = $1", user_id) == 0
    assert not os.path.exists(stored_path(key))
    assert (await client.delete(f"{BASE}/users/me/verification", headers=headers)).status_code == 404


async def test_deleted_account_loses_its_licence_files(client: AsyncClient):
    user_id, headers = await create_user(client)
    await upload_licence(client, headers)
    key = await db_value("SELECT document_url FROM doctor_verifications WHERE user_id = $1", user_id)
    await db_execute("UPDATE users SET deletion_scheduled_at = NOW() - INTERVAL '1 minute' WHERE id = $1", user_id)

    await cron_manager.purge_deleted_accounts()

    assert await db_value("SELECT status FROM users WHERE id = $1", user_id) == "deleted"
    assert not os.path.exists(stored_path(key))


# ── Storage module ───────────────────────────────────────────────────────────

class FakeS3Client:
    """Stands in for boto3, so these tests need no network."""
    class exceptions:
        class NoSuchKey(Exception):
            pass

    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[(Bucket, Key)] = (Body, ContentType)

    def get_object(self, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise self.exceptions.NoSuchKey()
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)][0])}

    def delete_object(self, Bucket, Key):
        self.objects.pop((Bucket, Key), None)


async def test_s3_storage_saves_reads_and_deletes():
    fake = FakeS3Client()
    storage = S3Storage(fake, "licences")

    await storage.save("licenses/u1/a.pdf", PDF_BYTES, "application/pdf")
    assert fake.objects[("licences", "licenses/u1/a.pdf")] == (PDF_BYTES, "application/pdf")
    assert await storage.read("licenses/u1/a.pdf") == PDF_BYTES

    await storage.delete("licenses/u1/a.pdf")
    assert await storage.read("licenses/u1/a.pdf") is None


@pytest.mark.parametrize("key", ["../outside.pdf", "licenses/../../outside.pdf", "/etc/passwd", "a\\b.pdf", ""])
async def test_storage_refuses_keys_that_leave_its_folder(tmp_path, key):
    storage = LocalStorage(str(tmp_path))
    with pytest.raises(ValueError):
        await storage.save(key, b"data", "text/plain")
