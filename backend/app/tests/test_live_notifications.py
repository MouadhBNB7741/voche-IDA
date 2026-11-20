"""Live notifications over WebSocket, licence review decisions, and alerts to admins."""
import asyncio
import io
import json
import time
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from app.api.v1 import notifications as ws_routes
from app.db import redis as redis_db
from app.db.postgres import PostgresDB
from app.services.connection_manager import CHANNEL, ConnectionManager, manager
from app.services.email import EmailService
from app.services.notification_service import NotificationService

BASE = "/api/v1"
PASSWORD = "StrongPassword123!"
PDF = b"%PDF-1.4\n% test document\n" + b"0" * 200


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
class FakeSocket:
    """Stands in for a browser tab: the test pushes what the browser sends and reads what it got."""

    def __init__(self, headers=None):
        self.headers = headers or {}
        self.sent = []
        self.closed = None
        self._incoming = asyncio.Queue()

    async def accept(self):
        pass

    async def receive(self):
        return await self._incoming.get()

    async def send_json(self, data):
        if self.closed:
            raise RuntimeError("socket closed")
        json.dumps(data)  # what a real socket would do: fail on anything that isn't JSON
        self.sent.append(data)

    async def close(self, code=1000, reason=None):
        self.closed = (code, reason)

    def browser_sends(self, data):
        self._incoming.put_nowait({"type": "websocket.receive", "text": json.dumps(data)})

    def browser_leaves(self):
        self._incoming.put_nowait({"type": "websocket.disconnect", "code": 1001})

    def of_type(self, kind):
        return [m for m in self.sent if m.get("type") == kind]


async def wait_for(condition, timeout=3.0):
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            return False
        await asyncio.sleep(0.02)
    return True


async def open_socket(token):
    """Connect a fake tab, log in with the token and wait for the server's answer."""
    socket = FakeSocket()
    task = asyncio.create_task(ws_routes.notifications_socket(socket))
    socket.browser_sends({"type": "auth", "token": token})
    await wait_for(lambda: socket.sent or socket.closed)
    return socket, task


async def close_socket(socket, task):
    socket.browser_leaves()
    await asyncio.wait_for(task, timeout=3)


async def make_user(client: AsyncClient, email: str, user_type: str = "patient", verified: bool = False) -> dict:
    await client.post(f"{BASE}/auth/register", json={
        "email": email, "password": PASSWORD, "first_name": "Test",
        "last_name": email.split("@")[0].capitalize(), "user_type": "patient" if user_type == "admin" else user_type,
    })
    async with PostgresDB.get_pool().acquire() as conn:
        if user_type == "admin":
            await conn.execute("UPDATE users SET user_type = 'admin' WHERE email = $1", email)
        if verified:
            await conn.execute("UPDATE users SET is_verified = TRUE WHERE email = $1", email)
        user_id = await conn.fetchval("SELECT id FROM users WHERE email = $1", email)
    res = await client.post(f"{BASE}/auth/login", json={"email": email, "password": PASSWORD})
    token = res.json()["access_token"]
    return {"id": str(user_id), "email": email, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


async def notify(user_id, title="Hello", message="Something happened"):
    async with PostgresDB.get_pool().acquire() as conn:
        return await NotificationService(conn).create_notification(
            user_id=user_id, notif_type="system_announcement", title=title, message=message, link="/notifications",
        )


async def notifications_for(user, notif_type):
    async with PostgresDB.get_pool().acquire() as conn:
        return await conn.fetch(
            "SELECT title, message, link FROM notifications WHERE user_id = $1 AND type = $2 ORDER BY created_at",
            user["id"], notif_type,
        )


async def upload_licence(client, user):
    return await client.post(
        f"{BASE}/doctors/verification/upload",
        data={
            "license_number": "MD-12345", "institution": "General Hospital", "country": "Nigeria",
            "specialization": "Cardiology",
            "expiration_date": (date.today() + timedelta(days=365)).isoformat(),
        },
        files={"file": ("licence.pdf", io.BytesIO(PDF), "application/pdf")},
        headers=user["headers"],
    )


@pytest.fixture
async def people(client: AsyncClient, setup_test_db):
    return {
        "patient": await make_user(client, "patient@example.com"),
        "other": await make_user(client, "other@example.com"),
        "doctor": await make_user(client, "doctor@example.com", "hcp"),
        "admin": await make_user(client, "admin@example.com", "admin"),
    }


@pytest.fixture
def sent_emails(monkeypatch):
    emails = []

    async def fake_send(to, subject, text, link=None):
        emails.append({"to": to, "subject": subject, "text": text, "link": link})
        return True

    monkeypatch.setattr(EmailService, "send_message", fake_send)
    return emails


@pytest.fixture(autouse=True)
async def no_listener_left_running():
    yield
    await manager.stop()


# ----------------------------------------------------------------------
# Connecting
# ----------------------------------------------------------------------
async def test_socket_logs_in_with_first_message_and_answers_pings(people):
    socket, task = await open_socket(people["patient"]["token"])
    assert socket.of_type("ready") and socket.closed is None
    assert manager.connection_count(people["patient"]["id"]) == 1

    socket.browser_sends({"type": "ping"})
    assert await wait_for(lambda: socket.of_type("pong"))

    await close_socket(socket, task)
    assert manager.connection_count(people["patient"]["id"]) == 0


async def test_socket_accepts_the_authorization_header(people):
    socket = FakeSocket(headers={"authorization": f"Bearer {people['patient']['token']}"})
    task = asyncio.create_task(ws_routes.notifications_socket(socket))
    assert await wait_for(lambda: socket.of_type("ready"))
    await close_socket(socket, task)


async def test_socket_refuses_a_bad_token(people):
    socket, task = await open_socket("not-a-real-token")
    await asyncio.wait_for(task, timeout=3)
    assert socket.closed[0] == ws_routes.CLOSE_UNAUTHORIZED
    assert not socket.of_type("ready")


async def test_socket_refuses_a_logged_out_token(client, people):
    patient = people["patient"]
    await client.post(f"{BASE}/auth/logout", headers=patient["headers"])
    socket, task = await open_socket(patient["token"])
    await asyncio.wait_for(task, timeout=3)
    assert socket.closed[0] == ws_routes.CLOSE_UNAUTHORIZED


async def test_socket_closes_when_no_login_arrives(people, monkeypatch):
    monkeypatch.setattr(ws_routes, "AUTH_TIMEOUT_SECONDS", 0.05)
    socket = FakeSocket()
    await asyncio.wait_for(ws_routes.notifications_socket(socket), timeout=3)
    assert socket.closed[0] == ws_routes.CLOSE_UNAUTHORIZED


async def test_socket_refuses_a_suspended_account(people):
    patient = people["patient"]
    async with PostgresDB.get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE users SET status = 'suspended', suspended_until = NOW() + INTERVAL '1 day' WHERE id = $1",
            patient["id"],
        )
    socket, task = await open_socket(patient["token"])
    await asyncio.wait_for(task, timeout=3)
    assert socket.closed[0] == ws_routes.CLOSE_SUSPENDED


async def test_socket_closes_when_the_login_expires(people, monkeypatch):
    # The login token runs out 0.2 seconds after connecting
    monkeypatch.setattr(ws_routes, "_token_expiry", lambda token: time.time() + 0.2)
    socket, task = await open_socket(people["patient"]["token"])
    assert socket.of_type("ready")
    await asyncio.wait_for(task, timeout=3)
    assert socket.closed == (ws_routes.CLOSE_UNAUTHORIZED, "Session expired")
    assert manager.connection_count(people["patient"]["id"]) == 0


async def test_socket_closes_when_the_browser_goes_silent(people, monkeypatch):
    monkeypatch.setattr(ws_routes, "IDLE_TIMEOUT_SECONDS", 0.05)
    socket, task = await open_socket(people["patient"]["token"])
    await asyncio.wait_for(task, timeout=3)
    assert socket.closed[0] == ws_routes.CLOSE_IDLE
    assert manager.connection_count(people["patient"]["id"]) == 0


async def test_too_many_tabs_are_refused(people, monkeypatch):
    monkeypatch.setattr(ws_routes, "MAX_SOCKETS_PER_USER", 1)
    first, first_task = await open_socket(people["patient"]["token"])
    second, second_task = await open_socket(people["patient"]["token"])
    await asyncio.wait_for(second_task, timeout=3)
    assert second.closed[0] == ws_routes.CLOSE_TOO_MANY
    await close_socket(first, first_task)


# ----------------------------------------------------------------------
# Delivery
# ----------------------------------------------------------------------
async def test_new_notification_reaches_every_open_tab_of_its_user_only(people, monkeypatch):
    monkeypatch.setattr(redis_db, "redis", None)  # this instance only
    patient, other = people["patient"], people["other"]
    tab1, task1 = await open_socket(patient["token"])
    tab2, task2 = await open_socket(patient["token"])
    stranger, task3 = await open_socket(other["token"])

    saved = await notify(patient["id"], title="Trial update")

    for tab in (tab1, tab2):
        assert await wait_for(lambda: tab.of_type("notification"))
        pushed = tab.of_type("notification")[0]["notification"]
        assert pushed["notification_id"] == str(saved["notification_id"])
        assert pushed["title"] == "Trial update" and pushed["read"] is False
        assert "T" in pushed["created_at"]  # ISO date, readable by the browser
    assert not stranger.of_type("notification")

    for socket, task in ((tab1, task1), (tab2, task2), (stranger, task3)):
        await close_socket(socket, task)


async def test_bulk_notifications_are_pushed_too(people, monkeypatch):
    monkeypatch.setattr(redis_db, "redis", None)
    admin = people["admin"]
    tab, task = await open_socket(admin["token"])
    async with PostgresDB.get_pool().acquire() as conn:
        from app.schemas.notification import NotificationType
        sent = await NotificationService(conn).notify_admins(
            NotificationType.SYSTEM_ANNOUNCEMENT, {"title": "Maintenance tonight", "message": "From 22:00 UTC."}
        )
    assert sent == 1
    assert await wait_for(lambda: tab.of_type("notification"))
    assert tab.of_type("notification")[0]["notification"]["title"] == "Maintenance tonight"
    await close_socket(tab, task)


async def test_notifications_go_through_redis_to_every_instance(people):
    redis = await redis_db.get_redis_client()
    await manager.start()
    assert await manager.wait_until_listening()

    patient = people["patient"]
    tab, task = await open_socket(patient["token"])
    await notify(patient["id"], title="Via Redis")
    assert await wait_for(lambda: tab.of_type("notification"))
    await asyncio.sleep(0.2)
    # Delivered once, by the listener, not a second time directly
    assert len(tab.of_type("notification")) == 1

    # A message published by another backend instance reaches this one's tabs
    await redis.publish(CHANNEL, json.dumps({
        "user_id": patient["id"],
        "message": {"type": "notification", "notification": {"title": "From another instance"}},
    }))
    assert await wait_for(lambda: len(tab.of_type("notification")) == 2)
    assert tab.of_type("notification")[1]["notification"]["title"] == "From another instance"
    await close_socket(tab, task)


async def test_without_redis_messages_are_delivered_directly(monkeypatch):
    local = ConnectionManager()
    monkeypatch.setattr(redis_db, "redis", None)
    tab = FakeSocket()
    local.connect("user-1", tab)
    await local.publish("user-1", {"type": "notification", "notification": {"title": "Local"}})
    assert tab.of_type("notification")[0]["notification"]["title"] == "Local"


async def test_a_dead_tab_is_dropped_and_others_still_get_messages(monkeypatch):
    local = ConnectionManager()
    monkeypatch.setattr(redis_db, "redis", None)
    alive, dead = FakeSocket(), FakeSocket()
    dead.closed = (1006, None)
    local.connect("user-1", alive)
    local.connect("user-1", dead)
    await local.publish("user-1", {"type": "notification", "notification": {"title": "Still here"}})
    assert alive.of_type("notification")
    assert local.connection_count("user-1") == 1


async def test_a_notification_is_saved_even_when_pushing_fails(people, monkeypatch):
    async def broken(*args, **kwargs):
        raise RuntimeError("push failed")

    monkeypatch.setattr(manager, "publish_many", broken)
    saved = await notify(people["patient"]["id"])
    assert saved["notification_id"]
    assert len(await notifications_for(people["patient"], "system_announcement")) == 1


# ----------------------------------------------------------------------
# Names in community notifications
# ----------------------------------------------------------------------
async def test_like_and_reply_notifications_name_the_member(client, people):
    patient, other = people["patient"], people["other"]
    async with PostgresDB.get_pool().acquire() as conn:
        community_id = str(await conn.fetchval("""
            INSERT INTO communities (community_id, name, description, type, moderation_level, is_active)
            VALUES (uuid_generate_v4(), 'General Health', 'A general community', 'general', 'open', TRUE)
            RETURNING community_id
        """))
    post = await client.post(f"{BASE}/community/{community_id}/posts", json={
        "title": "Questions about my treatment", "content": "Has anyone else had this kind of treatment?",
        "post_type": "discussion", "tags": ["treatment"],
    }, headers=patient["headers"])
    post_id = post.json()["data"]["post_id"]

    await client.post(f"{BASE}/community/{community_id}/posts/{post_id}/like", headers=other["headers"])
    reply = await client.post(f"{BASE}/community/{community_id}/posts/{post_id}/replies",
                              json={"content": "Yes, it went well for me."}, headers=other["headers"])
    assert reply.status_code == 201

    likes = await notifications_for(patient, "community_like")
    replies = await notifications_for(patient, "community_reply")
    assert likes[0]["message"] == "Test Other liked your post."
    assert replies[0]["message"].startswith("Test Other replied to your post")


# ----------------------------------------------------------------------
# Licence reviews
# ----------------------------------------------------------------------
async def test_new_licence_alerts_admins(client, people):
    res = await upload_licence(client, people["doctor"])
    assert res.status_code == 201
    alerts = await notifications_for(people["admin"], "verification_update")
    assert [a["title"] for a in alerts] == ["New licence to review"]
    assert "Test Doctor" in alerts[0]["message"]


async def test_approving_a_licence_tells_the_doctor_and_is_audited(client, people, sent_emails):
    doctor, admin = people["doctor"], people["admin"]
    verification_id = (await upload_licence(client, doctor)).json()["verification_id"]
    tab, task = await open_socket(doctor["token"])

    res = await client.patch(f"{BASE}/doctors/verifications/{verification_id}",
                             json={"status": "approved"}, headers=admin["headers"])
    assert res.status_code == 200 and res.json()["status"] == "approved"

    notes = await notifications_for(doctor, "verification_update")
    assert [n["title"] for n in notes] == ["Your licence is verified"]
    assert notes[0]["link"] == "/hcpdashboard"
    assert await wait_for(lambda: tab.of_type("notification"))
    assert sent_emails and sent_emails[0]["to"] == doctor["email"]
    assert sent_emails[0]["link"].endswith("/hcpdashboard")

    async with PostgresDB.get_pool().acquire() as conn:
        audit = await conn.fetchrow(
            "SELECT user_id, target_id, metadata FROM audit_logs WHERE action = 'verification.approved'"
        )
        verified = await conn.fetchval("SELECT is_verified FROM users WHERE id = $1", doctor["id"])
    assert str(audit["user_id"]) == admin["id"] and str(audit["target_id"]) == verification_id
    assert verified is True
    await close_socket(tab, task)


async def test_rejecting_a_licence_needs_a_reason_and_sends_it(client, people, sent_emails):
    doctor, admin = people["doctor"], people["admin"]
    verification_id = (await upload_licence(client, doctor)).json()["verification_id"]
    url = f"{BASE}/doctors/admin/verifications/{verification_id}"

    no_reason = await client.patch(url, json={"status": "rejected"}, headers=admin["headers"])
    assert no_reason.status_code == 422
    still_pending = await client.patch(url, json={"status": "pending"}, headers=admin["headers"])
    assert still_pending.status_code == 422

    res = await client.patch(url, json={"status": "rejected", "rejection_reason": "The photo is blurry."},
                             headers=admin["headers"])
    assert res.status_code == 200
    notes = await notifications_for(doctor, "verification_update")
    assert notes[0]["title"] == "Your licence wasn't approved"
    assert "The photo is blurry." in notes[0]["message"]
    assert "The photo is blurry." in sent_emails[0]["text"]


async def test_a_licence_is_decided_only_once(client, people, sent_emails):
    doctor, admin = people["doctor"], people["admin"]
    verification_id = (await upload_licence(client, doctor)).json()["verification_id"]
    url = f"{BASE}/doctors/verifications/{verification_id}"
    assert (await client.patch(url, json={"status": "approved"}, headers=admin["headers"])).status_code == 200
    again = await client.patch(url, json={"status": "rejected", "rejection_reason": "Changed my mind"},
                               headers=admin["headers"])
    assert again.status_code == 409
    missing = await client.patch(f"{BASE}/doctors/verifications/00000000-0000-0000-0000-000000000000",
                                 json={"status": "approved"}, headers=admin["headers"])
    assert missing.status_code == 404


async def test_pending_licences_list_has_both_paths_and_is_admin_only(client, people):
    doctor, admin = people["doctor"], people["admin"]
    verification_id = (await upload_licence(client, doctor)).json()["verification_id"]
    for path in ("/doctors/verifications/pending", "/doctors/admin/verifications"):
        res = await client.get(f"{BASE}{path}", headers=admin["headers"])
        assert res.status_code == 200
        assert verification_id in [v["verification_id"] for v in res.json()]
        assert (await client.get(f"{BASE}{path}", headers=doctor["headers"])).status_code == 403


# ----------------------------------------------------------------------
# Alerts to admins about new submissions
# ----------------------------------------------------------------------
async def test_new_resource_and_event_alert_admins(client, people):
    doctor, patient, admin = people["doctor"], people["patient"], people["admin"]
    async with PostgresDB.get_pool().acquire() as conn:
        await conn.execute("UPDATE users SET is_verified = TRUE WHERE id = $1", doctor["id"])

    resource = await client.post(f"{BASE}/resources/submit", data={
        "title": "Understanding clinical trial phases",
        "description": "A short guide to what each phase of a clinical trial means for patients.",
        "type": "document", "category": "Clinical Trials", "language": "en",
    }, files={"file": ("guide.pdf", PDF, "application/pdf")}, headers=doctor["headers"])
    assert resource.status_code == 201

    event = await client.post(f"{BASE}/events/", json={
        "title": "Patient voices in cancer research",
        "description": "An online session where patients share how they took part in research.",
        "type": "webinar", "organizer": "Patient Advocacy Network",
        "event_date": (date.today() + timedelta(days=30)).isoformat(), "event_time": "15:00:00",
        "timezone": "Europe/Paris", "virtual_link": "https://meet.example.com/patient-voices",
    }, headers=patient["headers"])
    assert event.status_code == 201

    resource_alerts = await notifications_for(admin, "resource_update")
    event_alerts = await notifications_for(admin, "event_update")
    assert resource_alerts[0]["title"] == "New resource to review"
    assert resource_alerts[0]["link"] == f"/resources/{resource.json()['resource_id']}"
    assert event_alerts[0]["title"] == "New event to review"
    assert "Test Patient" in event_alerts[0]["message"]


async def test_admins_own_event_sends_no_alert(client, people):
    admin = people["admin"]
    res = await client.post(f"{BASE}/events/", json={
        "title": "Platform town hall meeting",
        "description": "Our quarterly meeting with the community about the platform.",
        "type": "roundtable", "organizer": "Voche team",
        "event_date": (date.today() + timedelta(days=10)).isoformat(), "event_time": "17:00:00",
        "timezone": "UTC", "virtual_link": "https://meet.example.com/town-hall",
    }, headers=admin["headers"])
    assert res.status_code == 201 and res.json()["approval_status"] == "approved"
    assert await notifications_for(admin, "event_update") == []
