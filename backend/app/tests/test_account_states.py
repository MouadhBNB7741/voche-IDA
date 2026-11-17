"""
Account states: suspension (with reason and end date), cancelling a scheduled
deletion, and anonymizing accounts once the 7-day deletion period has passed.
"""
import os
import secrets
import uuid

import pytest
from httpx import AsyncClient

from app.core import cron_manager
from app.db.postgres import PostgresDB
from app.models.user_model import UserModel

BASE = "/api/v1"
PASSWORD = "StrongPassword123!"


# ── Helpers ──────────────────────────────────────────────────────────────────

async def create_user(client: AsyncClient, user_type: str = "patient") -> tuple[str, str, str]:
    """Register and log in a user. Returns (email, user_id, token)."""
    email = f"state_{secrets.token_hex(4)}@example.com"
    res = await client.post(f"{BASE}/auth/register", json={
        "email": email, "password": PASSWORD,
        "first_name": "State", "last_name": "Tester", "user_type": user_type,
    })
    assert res.status_code == 201, res.text
    token = res.json()["access_token"]
    user_id = await db_value("SELECT id FROM users WHERE email = $1", email)
    return email, str(user_id), token


async def db_value(query: str, *args):
    async with PostgresDB.get_pool().acquire() as conn:
        return await conn.fetchval(query, *args)


async def db_row(query: str, *args):
    async with PostgresDB.get_pool().acquire() as conn:
        return await conn.fetchrow(query, *args)


async def db_execute(query: str, *args):
    async with PostgresDB.get_pool().acquire() as conn:
        return await conn.execute(query, *args)


async def suspend(user_id: str, until_sql: str = "NOW() + INTERVAL '3 days'", reason: str | None = "Spam"):
    """Suspend a user. until_sql is an SQL expression, or NULL for a ban."""
    await db_execute(
        f"UPDATE users SET status = 'suspended', suspended_until = {until_sql}, suspended_reason = $2 WHERE id = $1",
        user_id, reason,
    )


async def login(client: AsyncClient, email: str):
    return await client.post(f"{BASE}/auth/login", json={"email": email, "password": PASSWORD})


async def seed_post_and_comment(user_id: str) -> tuple[str, str]:
    """Insert a community, a post and a comment written by the user."""
    community_id, post_id, comment_id = (str(uuid.uuid4()) for _ in range(3))
    await db_execute("""
        INSERT INTO communities (community_id, name, description, type, moderation_level, is_active)
        VALUES ($1, 'General Health', 'A general community', 'general', 'open', TRUE)
    """, community_id)
    await db_execute("""
        INSERT INTO forum_posts (post_id, user_id, community_id, title, content, post_type)
        VALUES ($1, $2, $3, 'My story', 'Some content', 'story')
    """, post_id, user_id, community_id)
    await db_execute("""
        INSERT INTO comments (comment_id, post_id, user_id, content) VALUES ($1, $2, $3, 'A reply')
    """, comment_id, post_id, user_id)
    return post_id, comment_id


# ── Suspension ───────────────────────────────────────────────────────────────

async def test_suspended_user_login_returns_reason_and_end_date(client: AsyncClient):
    email, user_id, _ = await create_user(client)
    await suspend(user_id, reason="Repeated spam")

    res = await login(client, email)

    assert res.status_code == 403
    detail = res.json()["detail"]
    assert detail["code"] == "account_suspended"
    assert detail["suspended_reason"] == "Repeated spam"
    assert detail["suspended_until"] is not None
    assert "suspended until" in detail["message"]
    assert "Reason: Repeated spam" in detail["message"]


async def test_banned_user_login_has_no_end_date(client: AsyncClient):
    email, user_id, _ = await create_user(client)
    await suspend(user_id, until_sql="NULL", reason="Harassment")

    res = await login(client, email)

    assert res.status_code == 403
    detail = res.json()["detail"]
    assert detail["suspended_until"] is None
    assert detail["message"] == "Your account is suspended. Reason: Harassment"


async def test_suspended_user_with_wrong_password_gets_401(client: AsyncClient):
    """A wrong password must not reveal that the account is suspended."""
    email, user_id, _ = await create_user(client)
    await suspend(user_id)

    res = await client.post(f"{BASE}/auth/login", json={"email": email, "password": "WrongPassword123!"})

    assert res.status_code == 401


async def test_ended_suspension_is_lifted_at_login(client: AsyncClient):
    email, user_id, _ = await create_user(client)
    await suspend(user_id, until_sql="NOW() - INTERVAL '1 hour'")

    res = await login(client, email)

    assert res.status_code == 200, res.text
    row = await db_row("SELECT status, suspended_until, suspended_reason FROM users WHERE id = $1", user_id)
    assert row["status"] == "active"
    assert row["suspended_until"] is None
    assert row["suspended_reason"] is None


async def test_suspended_user_token_is_blocked_with_details(client: AsyncClient, auth_headers):
    _, user_id, token = await create_user(client)
    await suspend(user_id, reason="Spam")

    res = await client.get(f"{BASE}/auth/me", headers=auth_headers(token))

    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "account_suspended"


async def test_suspended_user_is_anonymous_on_public_routes(client: AsyncClient, auth_headers):
    """Routes with optional login treat a suspended user as not logged in."""
    _, user_id, token = await create_user(client)
    await suspend(user_id)

    res = await client.get(f"{BASE}/events/", headers=auth_headers(token))

    assert res.status_code == 200


async def test_ended_suspension_is_lifted_on_request(client: AsyncClient, auth_headers):
    _, user_id, token = await create_user(client)
    await suspend(user_id, until_sql="NOW() - INTERVAL '1 minute'")

    res = await client.get(f"{BASE}/auth/me", headers=auth_headers(token))

    assert res.status_code == 200, res.text
    assert await db_value("SELECT status FROM users WHERE id = $1", user_id) == "active"


async def test_hourly_job_lifts_only_ended_suspensions(client: AsyncClient):
    _, ended, _ = await create_user(client)
    _, running, _ = await create_user(client)
    _, banned, _ = await create_user(client)
    await suspend(ended, until_sql="NOW() - INTERVAL '1 hour'")
    await suspend(running, until_sql="NOW() + INTERVAL '1 day'")
    await suspend(banned, until_sql="NULL")

    await cron_manager.lift_expired_suspensions()

    assert await db_value("SELECT status FROM users WHERE id = $1", ended) == "active"
    assert await db_value("SELECT status FROM users WHERE id = $1", running) == "suspended"
    assert await db_value("SELECT status FROM users WHERE id = $1", banned) == "suspended"


# ── Cancelling a scheduled deletion ─────────────────────────────────────────

async def test_cancel_deletion(client: AsyncClient, auth_headers):
    _, user_id, token = await create_user(client)
    res = await client.delete(f"{BASE}/users/me", headers=auth_headers(token))
    assert res.status_code == 200
    assert await db_value("SELECT deletion_scheduled_at FROM users WHERE id = $1", user_id) is not None

    res = await client.post(f"{BASE}/users/me/cancel-deletion", headers=auth_headers(token))

    assert res.status_code == 200
    assert res.json()["message"] == "Your account deletion has been cancelled."
    assert await db_value("SELECT deletion_scheduled_at FROM users WHERE id = $1", user_id) is None


async def test_cancel_deletion_when_nothing_is_scheduled(client: AsyncClient, auth_headers):
    _, _, token = await create_user(client)

    res = await client.post(f"{BASE}/users/me/cancel-deletion", headers=auth_headers(token))

    assert res.status_code == 200
    assert res.json()["message"] == "Your account is not scheduled for deletion."


async def test_cancel_deletion_requires_login(client: AsyncClient):
    res = await client.post(f"{BASE}/users/me/cancel-deletion")
    assert res.status_code == 401


# ── Anonymizing accounts after the 7 days ───────────────────────────────────

async def test_due_account_is_anonymized_and_keeps_its_posts(client: AsyncClient, auth_headers):
    email, user_id, token = await create_user(client)
    await client.patch(f"{BASE}/users/me", json={"bio": "Private bio"}, headers=auth_headers(token))
    post_id, comment_id = await seed_post_and_comment(user_id)
    await db_execute(
        "INSERT INTO notifications (user_id, type, title, message) VALUES ($1, 'system_announcement', 'Hi', 'Hello')",
        user_id,
    )
    await db_execute("UPDATE users SET deletion_scheduled_at = NOW() - INTERVAL '1 minute' WHERE id = $1", user_id)

    await cron_manager.purge_deleted_accounts()

    user = await db_row("SELECT * FROM users WHERE id = $1", user_id)
    assert user["status"] == "deleted"
    assert user["is_active"] is False
    assert user["email"] == f"deleted-{user_id}@deleted.invalid"
    assert user["display_name"] == "Deleted User"
    assert user["first_name"] is None and user["last_name"] is None
    assert user["password_hash"] is None
    # Personal data is gone
    assert await db_value("SELECT COUNT(*) FROM user_profiles WHERE user_id = $1", user_id) == 0
    assert await db_value("SELECT COUNT(*) FROM notifications WHERE user_id = $1", user_id) == 0
    # Posts and comments stay, still linked to the (now anonymous) account
    assert str(await db_value("SELECT user_id FROM forum_posts WHERE post_id = $1", post_id)) == user_id
    assert str(await db_value("SELECT user_id FROM comments WHERE comment_id = $1", comment_id)) == user_id
    # The old email no longer logs in
    assert (await login(client, email)).status_code == 401


async def test_anonymizing_removes_the_avatar_file(client: AsyncClient):
    _, user_id, _ = await create_user(client)
    os.makedirs("uploads/avatars", exist_ok=True)
    filename = f"test_anonymize_{secrets.token_hex(4)}.png"
    path = os.path.join("uploads", "avatars", filename)
    with open(path, "wb") as f:
        f.write(b"fake image")
    await db_execute(
        "UPDATE users SET avatar = $2, deletion_scheduled_at = NOW() - INTERVAL '1 minute' WHERE id = $1",
        user_id, f"/static/avatars/{filename}",
    )

    try:
        await cron_manager.purge_deleted_accounts()
        assert not os.path.exists(path)
        assert await db_value("SELECT avatar FROM users WHERE id = $1", user_id) is None
    finally:
        if os.path.exists(path):
            os.remove(path)


async def test_accounts_still_in_their_7_days_are_kept(client: AsyncClient):
    _, user_id, token = await create_user(client)
    await client.delete(f"{BASE}/users/me", headers={"Authorization": f"Bearer {token}"})

    await cron_manager.purge_deleted_accounts()

    assert await db_value("SELECT status FROM users WHERE id = $1", user_id) == "active"


async def test_one_failing_account_does_not_block_the_others(client: AsyncClient, monkeypatch):
    _, failing_id, _ = await create_user(client)
    _, other_id, _ = await create_user(client)
    await db_execute(
        "UPDATE users SET deletion_scheduled_at = NOW() - INTERVAL '1 minute' WHERE id = ANY($1::uuid[])",
        [failing_id, other_id],
    )
    original = UserModel.anonymize_user

    async def anonymize_or_fail(self, user_id):
        if str(user_id) == failing_id:
            raise RuntimeError("simulated failure")
        return await original(self, user_id)

    monkeypatch.setattr(UserModel, "anonymize_user", anonymize_or_fail)

    await cron_manager.purge_deleted_accounts()

    assert await db_value("SELECT status FROM users WHERE id = $1", failing_id) == "active"
    assert await db_value("SELECT status FROM users WHERE id = $1", other_id) == "deleted"


async def test_user_who_posted_can_be_removed_from_the_database(client: AsyncClient):
    """Before migration 006, this DELETE failed because posts required an author."""
    _, user_id, _ = await create_user(client)
    post_id, comment_id = await seed_post_and_comment(user_id)

    await db_execute("DELETE FROM users WHERE id = $1", user_id)

    assert await db_value("SELECT user_id FROM forum_posts WHERE post_id = $1", post_id) is None
    assert await db_value("SELECT user_id FROM comments WHERE comment_id = $1", comment_id) is None


# ── New role and password-less accounts ──────────────────────────────────────

async def test_register_caregiver(client: AsyncClient):
    _, user_id, _ = await create_user(client, user_type="caregiver")
    assert await db_value("SELECT user_type FROM users WHERE id = $1", user_id) == "caregiver"


async def test_account_without_password_cannot_log_in_with_one(client: AsyncClient):
    """Google sign-in accounts have no password: password login must fail cleanly."""
    email = f"google_{secrets.token_hex(4)}@example.com"
    await db_execute(
        "INSERT INTO users (email, password_hash, user_type, display_name) VALUES ($1, NULL, 'patient', 'Google User')",
        email,
    )

    res = await login(client, email)

    assert res.status_code == 401
