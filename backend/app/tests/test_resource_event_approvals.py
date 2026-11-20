"""Submitted resources and suggested events: who may submit, uploads, what each viewer sees, and approval."""
import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient

from app.db.postgres import PostgresDB
from app.services import approval_service
from app.services.email import EmailService

BASE = "/api/v1"
PASSWORD = "StrongPassword123!"
PDF = b"%PDF-1.4\n% test document\n" + b"0" * 200
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 200


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
async def make_user(client: AsyncClient, email: str, user_type: str = "patient", verified: bool = False) -> dict:
    await client.post(f"{BASE}/auth/register", json={
        "email": email, "password": PASSWORD, "first_name": "Test",
        "last_name": email.split("@")[0], "user_type": "patient" if user_type == "admin" else user_type,
    })
    async with PostgresDB.get_pool().acquire() as conn:
        if user_type == "admin":
            await conn.execute("UPDATE users SET user_type = 'admin' WHERE email = $1", email)
        if verified:
            await conn.execute("UPDATE users SET is_verified = TRUE WHERE email = $1", email)
        user_id = await conn.fetchval("SELECT id FROM users WHERE email = $1", email)
    res = await client.post(f"{BASE}/auth/login", json={"email": email, "password": PASSWORD})
    token = res.json()["access_token"]
    return {"id": str(user_id), "email": email, "headers": {"Authorization": f"Bearer {token}"}}


async def join_organization(user: dict, status: str = "approved") -> str:
    async with PostgresDB.get_pool().acquire() as conn:
        org_id = await conn.fetchval(
            """
            INSERT INTO organizations (org_name, org_type, country, contact_email, membership_status)
            VALUES ($1, 'advocacy_group', 'USA', 'org@example.com', 'verified') RETURNING org_id
            """,
            f"Org {uuid.uuid4().hex[:8]}",
        )
        await conn.execute(
            "INSERT INTO organization_members (org_id, user_id, role, status) VALUES ($1, $2, 'member', $3)",
            org_id, user["id"], status,
        )
    return str(org_id)


def resource_form(**overrides) -> dict:
    form = {
        "title": "Understanding clinical trial phases",
        "description": "A short guide to what each phase of a clinical trial means for patients.",
        "type": "document",
        "category": "Clinical Trials",
        "language": "en",
        "tags": "trials, #basics",
    }
    form.update(overrides)
    return {k: v for k, v in form.items() if v is not None}


async def submit(client, user, form=None, file=("guide.pdf", PDF, "application/pdf")):
    files = {"file": file} if file else None
    return await client.post(
        f"{BASE}/resources/submit", data=form or resource_form(), files=files, headers=user["headers"]
    )


def event_payload(**overrides) -> dict:
    payload = {
        "title": "Patient voices in cancer research",
        "description": "An online session where patients share how they took part in research.",
        "type": "webinar",
        "organizer": "Patient Advocacy Network",
        "event_date": (date.today() + timedelta(days=30)).isoformat(),
        "event_time": "15:00:00",
        "timezone": "Europe/Paris",
        "virtual_link": "https://meet.example.com/patient-voices",
        "tags": ["research", "patients"],
    }
    payload.update(overrides)
    return payload


async def public_resource_ids(client):
    res = await client.get(f"{BASE}/resources/", params={"limit": 100})
    return {r["resource_id"] for r in res.json()["data"]}


async def public_event_ids(client):
    res = await client.get(f"{BASE}/events/")
    return {e["event_id"] for e in res.json()["data"]}


async def notifications_for(user, notif_type):
    async with PostgresDB.get_pool().acquire() as conn:
        return await conn.fetch(
            "SELECT title, message, link FROM notifications WHERE user_id = $1 AND type = $2",
            user["id"], notif_type,
        )


@pytest.fixture
async def people(client: AsyncClient, setup_test_db):
    return {
        "patient": await make_user(client, "patient@example.com"),
        "doctor": await make_user(client, "doctor@example.com", "hcp", verified=True),
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


# ----------------------------------------------------------------------
# Rows that existed before the migration
# ----------------------------------------------------------------------
async def test_existing_resources_and_events_stay_public(client, setup_test_db):
    async with PostgresDB.get_pool().acquire() as conn:
        resource_id = await conn.fetchval(
            """
            INSERT INTO resources (title, type, category, description)
            VALUES ('Old guide', 'document', 'General', 'Added before approvals existed') RETURNING resource_id
            """
        )
        event_id = await conn.fetchval(
            """
            INSERT INTO events (title, description, type, organizer, event_date, event_time)
            VALUES ('Old event', 'Added before approvals existed', 'webinar', 'IDA', CURRENT_DATE + 7, '10:00')
            RETURNING event_id
            """
        )
    assert str(resource_id) in await public_resource_ids(client)
    assert str(event_id) in await public_event_ids(client)


# ----------------------------------------------------------------------
# Who may share resources (Q36)
# ----------------------------------------------------------------------
async def test_who_can_submit_resources(client, people):
    async def access(user=None):
        res = await client.get(f"{BASE}/resources/can-submit", headers=user["headers"] if user else None)
        return res.json()

    assert (await access())["can_submit"] is False
    assert (await access(people["patient"]))["can_submit"] is False
    assert (await access(people["doctor"]))["can_submit"] is True
    assert (await access(people["admin"]))["can_submit"] is True

    unverified = await make_user(client, "newdoc@example.com", "hcp")
    result = await access(unverified)
    assert result["can_submit"] is False
    assert "Verify your medical license" in result["reason"]

    member = await make_user(client, "member@example.com", "org_member")
    await join_organization(member, status="pending")
    assert (await access(member))["can_submit"] is False
    await join_organization(member, status="approved")
    assert (await access(member))["can_submit"] is True

    res = await submit(client, people["patient"])
    assert res.status_code == 403


# ----------------------------------------------------------------------
# Submitting resources
# ----------------------------------------------------------------------
async def test_doctor_submission_waits_for_review(client, people):
    doctor, patient, admin = people["doctor"], people["patient"], people["admin"]
    res = await submit(client, doctor)
    assert res.status_code == 201, res.text
    resource = res.json()
    rid = resource["resource_id"]
    assert resource["approval_status"] == "pending"
    assert resource["has_file"] is True
    assert resource["file_name"] == "guide.pdf"
    assert resource["file_type"] == "application/pdf"
    assert resource["tags"] == ["trials", "basics"]
    assert resource["author"]  # defaults to the submitter's name

    assert rid not in await public_resource_ids(client)
    url = f"{BASE}/resources/{rid}"
    assert (await client.get(url)).status_code == 404
    assert (await client.get(url, headers=patient["headers"])).status_code == 404
    assert (await client.get(url, headers=doctor["headers"])).status_code == 200
    assert (await client.get(url, headers=admin["headers"])).status_code == 200

    file_url = f"{url}/file"
    assert (await client.get(file_url, headers=patient["headers"])).status_code == 404
    res = await client.get(file_url, headers=doctor["headers"])
    assert res.status_code == 200
    assert res.content == PDF
    assert res.headers["content-type"] == "application/pdf"

    mine = (await client.get(f"{BASE}/resources/mine", headers=doctor["headers"])).json()["data"]
    assert [r["resource_id"] for r in mine] == [rid]

    pending = (await client.get(f"{BASE}/resources/pending", headers=admin["headers"])).json()["data"]
    assert pending[0]["resource_id"] == rid
    assert pending[0]["submitter_email"] == doctor["email"]
    assert pending[0]["submitter_type"] == "hcp"
    assert (await client.get(f"{BASE}/resources/pending", headers=doctor["headers"])).status_code == 403


async def test_organization_member_submission_is_linked_to_their_organization(client, people):
    member = await make_user(client, "member@example.com", "org_member")
    org_id = await join_organization(member)
    res = await submit(client, member, file=None, form=resource_form(url="https://example.org/guide"))
    assert res.status_code == 201
    async with PostgresDB.get_pool().acquire() as conn:
        row = await conn.fetchrow(
            "SELECT organization_id, approval_status FROM resources WHERE resource_id = $1",
            res.json()["resource_id"],
        )
    assert str(row["organization_id"]) == org_id
    assert row["approval_status"] == "pending"


async def test_admin_resource_is_published_straight_away(client, people):
    link = "https://www.youtube.com/watch?v=abc123"
    res = await submit(client, people["admin"], file=None, form=resource_form(type="video", url=link))
    assert res.status_code == 201
    resource = res.json()
    assert resource["approval_status"] == "approved"
    assert resource["published_date"] is not None
    assert resource["resource_id"] in await public_resource_ids(client)

    res = await client.get(f"{BASE}/resources/{resource['resource_id']}/download")
    assert res.json() == {"success": True, "has_file": False, "download_url": link}


async def test_submission_checks(client, people, monkeypatch):
    doctor = people["doctor"]
    assert (await submit(client, doctor, file=None)).status_code == 422  # no file and no link
    assert (await submit(client, doctor, file=None, form=resource_form(url="ftp://example.org/x"))).status_code == 422
    assert (await submit(client, doctor, form=resource_form(title="Hi"))).status_code == 422
    assert (await submit(client, doctor, form=resource_form(description="Too short"))).status_code == 422

    fake = await submit(client, doctor, file=("notes.pdf", b"just some text, not a pdf", "application/pdf"))
    assert fake.status_code == 400
    assert "PDF" in fake.json()["detail"]

    wrong_kind = await submit(client, doctor, file=("clip.mp4", MP4, "video/mp4"))
    assert wrong_kind.status_code == 400
    assert wrong_kind.json()["detail"] == "A document needs a PDF."
    assert (await submit(client, doctor, form=resource_form(type="video"), file=("clip.mp4", MP4, "video/mp4"))).status_code == 201

    monkeypatch.setitem(approval_service.RESOURCE_FILE_LIMITS, "pdf", 100)
    too_big = await submit(client, doctor)
    assert too_big.status_code == 400
    assert "at most" in too_big.json()["detail"]

    async with PostgresDB.get_pool().acquire() as conn:
        assert await conn.fetchval("SELECT COUNT(*) FROM resources") == 1


# ----------------------------------------------------------------------
# Deciding on resources
# ----------------------------------------------------------------------
async def test_approving_a_resource_publishes_it_and_tells_the_submitter(client, people, sent_emails):
    doctor, admin = people["doctor"], people["admin"]
    rid = (await submit(client, doctor)).json()["resource_id"]

    res = await client.patch(f"{BASE}/resources/{rid}/approval", json={"decision": "approve"}, headers=admin["headers"])
    assert res.status_code == 200, res.text
    assert res.json()["approval_status"] == "approved"

    assert rid in await public_resource_ids(client)
    details = (await client.get(f"{BASE}/resources/{rid}")).json()
    assert details["published_date"] is not None
    file_res = await client.get(f"{BASE}/resources/{rid}/file")
    assert file_res.status_code == 200 and file_res.content == PDF

    download = (await client.get(f"{BASE}/resources/{rid}/download")).json()
    assert download["has_file"] is True
    assert download["download_url"] == f"/api/v1/resources/{rid}/file"
    assert (await client.get(f"{BASE}/resources/{rid}")).json()["downloads"] == 1

    notes = await notifications_for(doctor, "resource_update")
    assert notes[0]["title"] == "Your resource is published"
    assert notes[0]["link"] == f"/resources/{rid}"
    assert sent_emails[0]["to"] == doctor["email"]
    assert sent_emails[0]["subject"] == "Your resource is published"
    assert sent_emails[0]["link"].endswith(f"/resources/{rid}")

    async with PostgresDB.get_pool().acquire() as conn:
        audit = await conn.fetchrow("SELECT user_id FROM audit_logs WHERE action = 'resource.approved'")
    assert str(audit["user_id"]) == admin["id"]

    # Already decided
    res = await client.patch(f"{BASE}/resources/{rid}/approval", json={"decision": "reject", "reason": "x"}, headers=admin["headers"])
    assert res.status_code == 409


async def test_rejecting_a_resource_needs_a_reason_and_explains_it(client, people, sent_emails):
    doctor, admin = people["doctor"], people["admin"]
    rid = (await submit(client, doctor)).json()["resource_id"]
    url = f"{BASE}/resources/{rid}/approval"

    assert (await client.patch(url, json={"decision": "reject"}, headers=admin["headers"])).status_code == 422
    assert (await client.patch(url, json={"decision": "approve"}, headers=doctor["headers"])).status_code == 403
    missing = await client.patch(f"{BASE}/resources/{uuid.uuid4()}/approval", json={"decision": "approve"}, headers=admin["headers"])
    assert missing.status_code == 404

    res = await client.patch(url, json={"decision": "reject", "reason": "Please add your sources."}, headers=admin["headers"])
    assert res.status_code == 200
    assert res.json()["rejection_reason"] == "Please add your sources."

    assert rid not in await public_resource_ids(client)
    mine = (await client.get(f"{BASE}/resources/mine", headers=doctor["headers"])).json()["data"]
    assert mine[0]["approval_status"] == "rejected"
    assert mine[0]["rejection_reason"] == "Please add your sources."
    note = (await notifications_for(doctor, "resource_update"))[0]
    assert "Please add your sources." in note["message"]
    assert "Please add your sources." in sent_emails[0]["text"]


# ----------------------------------------------------------------------
# Suggested events (Q38)
# ----------------------------------------------------------------------
async def test_member_suggestion_waits_for_review(client, people):
    patient, doctor, admin = people["patient"], people["doctor"], people["admin"]
    assert (await client.post(f"{BASE}/events/", json=event_payload())).status_code == 401

    res = await client.post(f"{BASE}/events/", json=event_payload(), headers=patient["headers"])
    assert res.status_code == 201, res.text
    event = res.json()
    eid = event["event_id"]
    assert event["approval_status"] == "pending"
    assert event["status"] == "upcoming"
    assert event["created_by"] == patient["id"]

    assert eid not in await public_event_ids(client)
    url = f"{BASE}/events/{eid}"
    assert (await client.get(url, headers=doctor["headers"])).status_code == 404
    assert (await client.get(url, headers=patient["headers"])).status_code == 200
    assert (await client.post(f"{url}/register", headers=doctor["headers"])).status_code == 404

    mine = (await client.get(f"{BASE}/events/my-suggestions", headers=patient["headers"])).json()["data"]
    assert [e["event_id"] for e in mine] == [eid]
    pending = (await client.get(f"{BASE}/events/pending", headers=admin["headers"])).json()["data"]
    assert pending[0]["suggester_email"] == patient["email"]
    assert (await client.get(f"{BASE}/events/pending", headers=patient["headers"])).status_code == 403


async def test_event_suggestion_checks(client, people):
    headers = people["patient"]["headers"]
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    for bad in (
        event_payload(event_date=yesterday),
        event_payload(virtual_link=None, location=None),
        event_payload(virtual_link="meet.example.com/no-scheme"),
        event_payload(description="Too short"),
        event_payload(type="party"),
        event_payload(registration_deadline=(date.today() + timedelta(days=60)).isoformat() + "T00:00:00Z"),
    ):
        res = await client.post(f"{BASE}/events/", json=bad, headers=headers)
        assert res.status_code == 422, bad

    in_person = event_payload(virtual_link="", location="Geneva, Switzerland")
    assert (await client.post(f"{BASE}/events/", json=in_person, headers=headers)).status_code == 201


async def test_admin_event_goes_live_straight_away(client, people):
    res = await client.post(f"{BASE}/events/", json=event_payload(), headers=people["admin"]["headers"])
    assert res.json()["approval_status"] == "approved"
    assert res.json()["event_id"] in await public_event_ids(client)


async def test_approving_and_rejecting_events(client, people, sent_emails):
    patient, doctor, admin = people["patient"], people["doctor"], people["admin"]
    first = (await client.post(f"{BASE}/events/", json=event_payload(), headers=patient["headers"])).json()["event_id"]
    second = (await client.post(
        f"{BASE}/events/", json=event_payload(title="Another suggested event"), headers=patient["headers"]
    )).json()["event_id"]

    res = await client.patch(f"{BASE}/events/{first}/approval", json={"decision": "approve"}, headers=admin["headers"])
    assert res.status_code == 200
    assert first in await public_event_ids(client)
    assert (await client.post(f"{BASE}/events/{first}/register", headers=doctor["headers"])).status_code == 200

    res = await client.patch(
        f"{BASE}/events/{second}/approval",
        json={"decision": "reject", "reason": "This event is already listed."},
        headers=admin["headers"],
    )
    assert res.json()["approval_status"] == "rejected"
    assert second not in await public_event_ids(client)

    notes = await notifications_for(patient, "event_update")
    assert {n["title"] for n in notes} == {"Your event is published", "Your event suggestion wasn't approved"}
    assert any("This event is already listed." in n["message"] for n in notes)
    assert [e["to"] for e in sent_emails] == [patient["email"], patient["email"]]

    assert (await client.patch(f"{BASE}/events/{second}/approval", json={"decision": "approve"}, headers=admin["headers"])).status_code == 409
