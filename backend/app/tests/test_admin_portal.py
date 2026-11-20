"""What the admin portal reads: overview, audit log, pending licences, and urgent report alerts."""
import pytest
from httpx import AsyncClient

from app.db.postgres import PostgresDB
from app.tests.test_live_notifications import make_user, notifications_for, sent_emails, upload_licence  # noqa: F401

BASE = "/api/v1"


@pytest.fixture
async def people(client: AsyncClient, setup_test_db):
    return {
        "patient": await make_user(client, "patient@example.com"),
        "other": await make_user(client, "other@example.com"),
        "doctor": await make_user(client, "doctor@example.com", "hcp"),
        "admin": await make_user(client, "admin@example.com", "admin"),
    }


async def make_community() -> str:
    async with PostgresDB.get_pool().acquire() as conn:
        return str(await conn.fetchval("""
            INSERT INTO communities (community_id, name, description, type, moderation_level, is_active)
            VALUES (uuid_generate_v4(), 'General Health', 'A general community', 'general', 'open', TRUE)
            RETURNING community_id
        """))


async def make_post(client, community_id, user, content="Has anyone else had this kind of treatment?"):
    res = await client.post(f"{BASE}/community/{community_id}/posts", json={
        "title": "Questions about my treatment", "content": content, "post_type": "discussion", "tags": ["treatment"],
    }, headers=user["headers"])
    assert res.status_code == 201, res.text
    return res.json()["data"]["post_id"]


# ----------------------------------------------------------------------
# Overview
# ----------------------------------------------------------------------
async def test_overview_is_for_admins_only(client, people):
    url = f"{BASE}/system/admin/overview"
    assert (await client.get(url)).status_code in (401, 403)
    assert (await client.get(url, headers=people["patient"]["headers"])).status_code == 403
    assert (await client.get(url, headers=people["admin"]["headers"])).status_code == 200


async def test_overview_counts_what_waits_for_review(client, people):
    admin = people["admin"]
    await upload_licence(client, people["doctor"])
    community_id = await make_community()
    post_id = await make_post(client, community_id, people["patient"])
    await client.post(f"{BASE}/community/{community_id}/report", json={
        "target_type": "post", "target_id": post_id, "reason": "spam",
    }, headers=people["other"]["headers"])

    res = await client.get(f"{BASE}/system/admin/overview", headers=admin["headers"])
    body = res.json()
    assert body["queues"] == {
        "open_reports": 1, "critical_reports": 0, "pending_licences": 1,
        "pending_resources": 0, "pending_events": 0,
    }
    assert body["users"]["total"] == 4
    assert body["users"]["by_type"]["admin"] == 1
    assert body["users"]["new_last_7_days"] == 4
    assert body["activity"]["posts_last_7_days"] == 1
    assert body["health"]["database"] == "connected"
    assert isinstance(body["health"]["live_connections"], int)


# ----------------------------------------------------------------------
# Audit log
# ----------------------------------------------------------------------
async def test_audit_log_lists_decisions_with_the_admin_and_filters_by_category(client, people, sent_emails):
    admin, doctor = people["admin"], people["doctor"]
    verification_id = (await upload_licence(client, doctor)).json()["verification_id"]
    await client.patch(f"{BASE}/doctors/verifications/{verification_id}",
                       json={"status": "rejected", "rejection_reason": "The photo is blurry."}, headers=admin["headers"])

    community_id = await make_community()
    post_id = await make_post(client, community_id, people["patient"])
    report = await client.post(f"{BASE}/community/{community_id}/report", json={
        "target_type": "post", "target_id": post_id, "reason": "spam",
    }, headers=people["other"]["headers"])
    await client.post(f"{BASE}/moderation/reports/{report.json()['report_id']}/decide",
                      json={"action": "approve_content"}, headers=admin["headers"])

    url = f"{BASE}/system/audit-logs"
    assert (await client.get(url, headers=doctor["headers"])).status_code == 403

    everything = (await client.get(url, headers=admin["headers"])).json()
    assert everything["meta"]["total"] == 2
    assert [e["action"] for e in everything["data"]] == ["moderation.approve_content", "verification.rejected"]
    assert everything["data"][1]["actor_name"] == "Test Admin"
    assert everything["data"][1]["metadata"]["reason"] == "The photo is blurry."
    assert "ip_address" not in everything["data"][0]

    licences = (await client.get(url, params={"category": "verification"}, headers=admin["headers"])).json()
    assert [e["action"] for e in licences["data"]] == ["verification.rejected"]
    assert (await client.get(url, params={"category": "nonsense"}, headers=admin["headers"])).status_code == 422


# ----------------------------------------------------------------------
# Pending licences show who sent them
# ----------------------------------------------------------------------
async def test_pending_licences_include_the_doctor(client, people):
    await upload_licence(client, people["doctor"])
    res = await client.get(f"{BASE}/doctors/verifications/pending", headers=people["admin"]["headers"])
    item = res.json()[0]
    assert item["display_name"] == "Test Doctor"
    assert item["email"] == "doctor@example.com"
    assert item["has_document"] is True


# ----------------------------------------------------------------------
# Urgent reports alert admins straight away
# ----------------------------------------------------------------------
async def test_a_self_harm_report_alerts_admins_once(client, people):
    community_id = await make_community()
    post_id = await make_post(client, community_id, people["patient"])

    for reporter in (people["other"], people["doctor"]):
        res = await client.post(f"{BASE}/community/{community_id}/report", json={
            "target_type": "post", "target_id": post_id, "reason": "self_harm",
        }, headers=reporter["headers"])
        assert res.status_code in (200, 201), res.text

    alerts = await notifications_for(people["admin"], "moderation_action")
    assert [a["title"] for a in alerts] == ["Urgent report: possible self-harm"]
    assert alerts[0]["link"] == "/admin?tab=moderation"


async def test_a_post_the_filter_flags_for_self_harm_alerts_admins(client, people):
    community_id = await make_community()
    await make_post(client, community_id, people["patient"],
                    content="Some days I feel like I want to die, and I do not know who to talk to.")
    alerts = await notifications_for(people["admin"], "moderation_action")
    assert [a["title"] for a in alerts] == ["Urgent report: possible self-harm"]


async def test_ordinary_reports_do_not_alert_admins(client, people):
    community_id = await make_community()
    post_id = await make_post(client, community_id, people["patient"])
    await client.post(f"{BASE}/community/{community_id}/report", json={
        "target_type": "post", "target_id": post_id, "reason": "spam",
    }, headers=people["other"]["headers"])
    assert await notifications_for(people["admin"], "moderation_action") == []
