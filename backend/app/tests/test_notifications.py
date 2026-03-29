"""
Test suite for Notifications API — /api/v1/notifications

Covers:
  - Auth protection on all endpoints
  - CRUD operations (list, mark-read, mark-all-read, delete)
  - Pagination and filtering
  - Ownership enforcement (IDOR prevention)
  - Edge cases (empty inbox, invalid IDs, unauthorized)
  - Notification preferences
"""
import pytest
import secrets
from uuid import uuid4
from httpx import AsyncClient

pytestmark = pytest.mark.anyio

BASE = "/api/v1"


# ── HELPERS ──────────────────────────────────────────────────────────────────

async def register_user(client: AsyncClient, email: str = None, user_type: str = "patient"):
    """Register a user and return (token, user_id)."""
    email = email or f"test_{secrets.token_hex(4)}@example.com"
    resp = await client.post(f"{BASE}/auth/register", json={
        "email": email,
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
        "user_type": user_type,
    })
    assert resp.status_code == 201, f"Registration failed: {resp.text}"
    data = resp.json()
    # Decode JWT to get user_id (sub claim)
    import jwt
    payload = jwt.decode(data["access_token"], options={"verify_signature": False})
    return data["access_token"], payload["sub"]


def auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


async def seed_notification(client: AsyncClient, conn, user_id: str, **overrides):
    """Directly insert a notification into the DB for testing."""
    from app.models.notification_model import NotificationModel
    model = NotificationModel(conn)
    defaults = {
        "user_id": user_id,
        "notif_type": "system",
        "title": "Test Notification",
        "message": "This is a test notification.",
        "link": "/test",
    }
    defaults.update(overrides)
    return await model.create(**defaults)


# ── AUTH PROTECTION ──────────────────────────────────────────────────────────

class TestNotificationsAuth:
    """All notification endpoints must require authentication."""

    async def test_get_notifications_unauthorized(self, client: AsyncClient):
        resp = await client.get(f"{BASE}/notifications")
        assert resp.status_code in (401, 403)

    async def test_mark_read_unauthorized(self, client: AsyncClient):
        resp = await client.patch(f"{BASE}/notifications/{uuid4()}/read")
        assert resp.status_code in (401, 403)

    async def test_mark_all_read_unauthorized(self, client: AsyncClient):
        resp = await client.patch(f"{BASE}/notifications/mark-all-read")
        assert resp.status_code in (401, 403)

    async def test_delete_unauthorized(self, client: AsyncClient):
        resp = await client.delete(f"{BASE}/notifications/{uuid4()}")
        assert resp.status_code in (401, 403)

    async def test_preferences_unauthorized(self, client: AsyncClient):
        resp = await client.get(f"{BASE}/users/me/preferences/notifications")
        assert resp.status_code in (401, 403)


# ── GET NOTIFICATIONS ────────────────────────────────────────────────────────

class TestGetNotifications:

    async def test_empty_inbox(self, client: AsyncClient):
        token, user_id = await register_user(client)
        resp = await client.get(
            f"{BASE}/notifications",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"] == []
        assert data["unread_count"] == 0
        assert data["meta"]["total"] == 0

    async def test_list_with_notifications(self, client: AsyncClient):
        token, user_id = await register_user(client)

        # Seed notifications via the service
        from app.db.postgres import PostgresDB
        pool = PostgresDB.get_pool()
        async with pool.acquire() as conn:
            from app.models.notification_model import NotificationModel
            model = NotificationModel(conn)
            for i in range(3):
                await model.create(
                    user_id=user_id,
                    notif_type="system",
                    title=f"Notification {i}",
                    message=f"Message {i}",
                )

        resp = await client.get(
            f"{BASE}/notifications",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 3
        assert data["unread_count"] == 3
        assert data["meta"]["total"] == 3

    async def test_filter_by_read_status(self, client: AsyncClient):
        token, user_id = await register_user(client)

        from app.db.postgres import PostgresDB
        pool = PostgresDB.get_pool()
        async with pool.acquire() as conn:
            from app.models.notification_model import NotificationModel
            model = NotificationModel(conn)
            n1 = await model.create(user_id=user_id, notif_type="system", title="Read", message="msg")
            await model.create(user_id=user_id, notif_type="system", title="Unread", message="msg")
            await model.mark_read(str(n1["notification_id"]), user_id)

        # Filter unread only
        resp = await client.get(
            f"{BASE}/notifications?read=false",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    async def test_filter_by_type(self, client: AsyncClient):
        token, user_id = await register_user(client)

        from app.db.postgres import PostgresDB
        pool = PostgresDB.get_pool()
        async with pool.acquire() as conn:
            from app.models.notification_model import NotificationModel
            model = NotificationModel(conn)
            await model.create(user_id=user_id, notif_type="trial", title="Trial", message="m")
            await model.create(user_id=user_id, notif_type="system", title="System", message="m")

        resp = await client.get(
            f"{BASE}/notifications?type=trial",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["type"] == "trial"

    async def test_pagination(self, client: AsyncClient):
        token, user_id = await register_user(client)

        from app.db.postgres import PostgresDB
        pool = PostgresDB.get_pool()
        async with pool.acquire() as conn:
            from app.models.notification_model import NotificationModel
            model = NotificationModel(conn)
            for i in range(5):
                await model.create(user_id=user_id, notif_type="system", title=f"N{i}", message="m")

        resp = await client.get(
            f"{BASE}/notifications?page=1&limit=2",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 2
        assert data["meta"]["total"] == 5
        assert data["meta"]["total_pages"] == 3


# ── MARK READ ────────────────────────────────────────────────────────────────

class TestMarkRead:

    async def test_mark_single_read(self, client: AsyncClient):
        token, user_id = await register_user(client)

        from app.db.postgres import PostgresDB
        pool = PostgresDB.get_pool()
        async with pool.acquire() as conn:
            from app.models.notification_model import NotificationModel
            model = NotificationModel(conn)
            n = await model.create(user_id=user_id, notif_type="system", title="T", message="M")

        notif_id = str(n["notification_id"])
        resp = await client.patch(
            f"{BASE}/notifications/{notif_id}/read",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.json()["read"] is True

    async def test_mark_read_not_found(self, client: AsyncClient):
        token, _ = await register_user(client)
        resp = await client.patch(
            f"{BASE}/notifications/{uuid4()}/read",
            headers=auth_header(token),
        )
        assert resp.status_code == 404

    async def test_mark_read_other_users_notification(self, client: AsyncClient):
        """IDOR prevention: user A cannot mark user B's notification as read."""
        token_a, user_a = await register_user(client)
        token_b, user_b = await register_user(client)

        from app.db.postgres import PostgresDB
        pool = PostgresDB.get_pool()
        async with pool.acquire() as conn:
            from app.models.notification_model import NotificationModel
            model = NotificationModel(conn)
            n = await model.create(user_id=user_b, notif_type="system", title="B", message="M")

        resp = await client.patch(
            f"{BASE}/notifications/{n['notification_id']}/read",
            headers=auth_header(token_a),  # User A trying to mark B's notification
        )
        assert resp.status_code == 404  # Should not find it


# ── MARK ALL READ ────────────────────────────────────────────────────────────

class TestMarkAllRead:

    async def test_mark_all_read(self, client: AsyncClient):
        token, user_id = await register_user(client)

        from app.db.postgres import PostgresDB
        pool = PostgresDB.get_pool()
        async with pool.acquire() as conn:
            from app.models.notification_model import NotificationModel
            model = NotificationModel(conn)
            for i in range(3):
                await model.create(user_id=user_id, notif_type="system", title=f"N{i}", message="m")

        resp = await client.patch(
            f"{BASE}/notifications/mark-all-read",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.json()["updated_count"] == 3

        # Verify all are read
        resp2 = await client.get(
            f"{BASE}/notifications?read=false",
            headers=auth_header(token),
        )
        assert len(resp2.json()["data"]) == 0

    async def test_mark_all_read_empty(self, client: AsyncClient):
        token, _ = await register_user(client)
        resp = await client.patch(
            f"{BASE}/notifications/mark-all-read",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.json()["updated_count"] == 0


# ── DELETE ───────────────────────────────────────────────────────────────────

class TestDeleteNotification:

    async def test_delete_own_notification(self, client: AsyncClient):
        token, user_id = await register_user(client)

        from app.db.postgres import PostgresDB
        pool = PostgresDB.get_pool()
        async with pool.acquire() as conn:
            from app.models.notification_model import NotificationModel
            model = NotificationModel(conn)
            n = await model.create(user_id=user_id, notif_type="system", title="T", message="M")

        resp = await client.delete(
            f"{BASE}/notifications/{n['notification_id']}",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_delete_not_found(self, client: AsyncClient):
        token, _ = await register_user(client)
        resp = await client.delete(
            f"{BASE}/notifications/{uuid4()}",
            headers=auth_header(token),
        )
        assert resp.status_code == 404

    async def test_delete_other_users_notification(self, client: AsyncClient):
        """IDOR prevention: cannot delete another user's notification."""
        token_a, user_a = await register_user(client)
        token_b, user_b = await register_user(client)

        from app.db.postgres import PostgresDB
        pool = PostgresDB.get_pool()
        async with pool.acquire() as conn:
            from app.models.notification_model import NotificationModel
            model = NotificationModel(conn)
            n = await model.create(user_id=user_b, notif_type="system", title="B", message="M")

        resp = await client.delete(
            f"{BASE}/notifications/{n['notification_id']}",
            headers=auth_header(token_a),
        )
        assert resp.status_code == 404


# ── PREFERENCES ──────────────────────────────────────────────────────────────

class TestNotificationPreferences:

    async def test_get_preferences(self, client: AsyncClient):
        token, _ = await register_user(client)
        resp = await client.get(
            f"{BASE}/users/me/preferences/notifications",
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should have default structure (matches NotificationPreferences schema)
        assert "emailAlerts" in data
        assert "frequency" in data
