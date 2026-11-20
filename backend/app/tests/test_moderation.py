"""Content moderation: the automatic filter, what each viewer sees, reports, the queue and decisions."""
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.db.postgres import PostgresDB
from app.services.moderation_service import score_content

BASE = "/api/v1"
PASSWORD = "StrongPassword123!"

CLEAN_TEXT = "I joined a trial last year and wanted to share how the first months went."
QUESTION_TEXT = "Is it true that turmeric cures cancer? My aunt keeps saying so."
HARMFUL_TEXT = "Vaccines cause autism, so stop taking your medication right now."
SELF_HARM_TEXT = "Some days I want to die and I feel there is no reason to live."


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
async def make_user(client: AsyncClient, email: str, user_type: str = "patient") -> dict:
    """Register and log in. Admins are promoted in the database (signup can't create them)."""
    await client.post(f"{BASE}/auth/register", json={
        "email": email,
        "password": PASSWORD,
        "first_name": "Test",
        "last_name": email.split("@")[0],
        "user_type": "patient" if user_type == "admin" else user_type,
    })
    async with PostgresDB.get_pool().acquire() as conn:
        if user_type == "admin":
            await conn.execute("UPDATE users SET user_type = 'admin' WHERE email = $1", email)
        user_id = await conn.fetchval("SELECT id FROM users WHERE email = $1", email)
    res = await client.post(f"{BASE}/auth/login", json={"email": email, "password": PASSWORD})
    token = res.json()["access_token"]
    return {"id": str(user_id), "email": email, "headers": {"Authorization": f"Bearer {token}"}}


async def make_community() -> str:
    community_id = str(uuid.uuid4())
    async with PostgresDB.get_pool().acquire() as conn:
        await conn.execute(
            """
            INSERT INTO communities (community_id, name, description, type, moderation_level, is_active)
            VALUES ($1, $2, 'Test community', 'general', 'open', TRUE)
            """,
            community_id, f"Community {community_id[:8]}",
        )
    return community_id


async def make_post(client, community_id, user, content=CLEAN_TEXT, title="Sharing my experience"):
    res = await client.post(
        f"{BASE}/community/{community_id}/posts",
        json={"title": title, "content": content, "post_type": "discussion", "tags": []},
        headers=user["headers"],
    )
    assert res.status_code == 201, res.text
    return res.json()["data"]


async def make_reply(client, community_id, post_id, user, content="Thanks for sharing this with us."):
    res = await client.post(
        f"{BASE}/community/{community_id}/posts/{post_id}/replies",
        json={"content": content},
        headers=user["headers"],
    )
    assert res.status_code == 201, res.text
    return res.json()


async def report(client, community_id, user, target_id, target_type="post", reason="spam"):
    return await client.post(
        f"{BASE}/community/{community_id}/report",
        json={"target_type": target_type, "target_id": target_id, "reason": reason},
        headers=user["headers"],
    )


async def queue(client, admin, **params):
    res = await client.get(f"{BASE}/moderation/queue", params=params, headers=admin["headers"])
    assert res.status_code == 200, res.text
    return res.json()["data"]


async def decide(client, admin, report_id, **body):
    return await client.post(
        f"{BASE}/moderation/reports/{report_id}/decide", json=body, headers=admin["headers"]
    )


async def fetchrow(sql, *args):
    async with PostgresDB.get_pool().acquire() as conn:
        return await conn.fetchrow(sql, *args)


async def fetch(sql, *args):
    async with PostgresDB.get_pool().acquire() as conn:
        return await conn.fetch(sql, *args)


async def feed_ids(client, user=None):
    res = await client.get(f"{BASE}/community/feed", headers=user["headers"] if user else None)
    assert res.status_code == 200
    return {p["post_id"]: p for p in res.json()["data"]}


async def notifications_for(user, notif_type="moderation_action"):
    return await fetch(
        "SELECT title, message, link FROM notifications WHERE user_id = $1 AND type = $2 ORDER BY created_at",
        user["id"], notif_type,
    )


@pytest.fixture
async def setup(client: AsyncClient, setup_test_db):
    community_id = await make_community()
    author = await make_user(client, "author@example.com")
    other = await make_user(client, "other@example.com")
    admin = await make_user(client, "admin@example.com", "admin")
    return {"community_id": community_id, "author": author, "other": other, "admin": admin}


# ----------------------------------------------------------------------
# The automatic filter (no database)
# ----------------------------------------------------------------------
def test_filter_passes_ordinary_posts():
    result = score_content("My first week in the trial", CLEAN_TEXT)
    assert result.score == 0
    assert not result.needs_review and not result.held


def test_filter_queues_a_patient_question_without_holding_it():
    result = score_content(QUESTION_TEXT)
    assert result.needs_review
    assert not result.held
    assert result.category == "misinformation"
    assert result.priority == "normal"


def test_filter_holds_harmful_claims():
    result = score_content(HARMFUL_TEXT)
    assert result.held
    assert result.category == "misinformation"
    assert result.priority == "high"
    assert "vaccines cause autism" in result.reason


def test_filter_never_holds_self_harm_alone_but_makes_it_critical():
    result = score_content(SELF_HARM_TEXT + " I keep thinking about suicide.")
    assert result.needs_review
    assert not result.held
    assert result.category == "self_harm"
    assert result.priority == "critical"


def test_filter_spam_links_and_markdown():
    links = " ".join(f"https://shop{i}.example.com" for i in range(6))
    assert score_content(f"Great deals here {links}").held
    assert score_content("Results\n----------\nAll good ..........").score == 0


# ----------------------------------------------------------------------
# New posts and replies
# ----------------------------------------------------------------------
async def test_clean_post_is_published_without_a_report(client, setup):
    post = await make_post(client, setup["community_id"], setup["author"])
    assert post["moderation_status"] == "approved"
    assert await queue(client, setup["admin"]) == []


async def test_borderline_post_is_published_and_queued(client, setup):
    post = await make_post(client, setup["community_id"], setup["author"], QUESTION_TEXT)
    assert post["moderation_status"] == "approved"
    assert post["post_id"] in await feed_ids(client, setup["other"])

    items = await queue(client, setup["admin"])
    assert len(items) == 1
    item = items[0]
    assert item["source"] == "auto_filter"
    assert item["reporter_id"] is None
    assert item["priority"] == "normal"
    assert item["reason"] == "misinformation"
    assert item["post_id"] == post["post_id"]
    assert item["author_id"] == setup["author"]["id"]

    row = await fetchrow("SELECT moderation_score, flagged_reason FROM forum_posts WHERE post_id = $1", post["post_id"])
    assert row["moderation_score"] >= 0.3
    assert row["flagged_reason"].startswith("Automatic filter")


async def test_held_post_is_only_visible_to_its_author_and_admins(client, setup):
    community_id = setup["community_id"]
    post = await make_post(client, community_id, setup["author"], HARMFUL_TEXT)
    post_id = post["post_id"]
    assert post["moderation_status"] == "pending"

    # Feed: hidden from others and anonymous visitors, shown to the author with its status
    assert post_id not in await feed_ids(client, setup["other"])
    assert post_id not in await feed_ids(client)
    mine = await feed_ids(client, setup["author"])
    assert mine[post_id]["moderation_status"] == "pending"

    url = f"{BASE}/community/{community_id}/posts/{post_id}"
    assert (await client.get(url, headers=setup["other"]["headers"])).status_code == 404
    assert (await client.get(url)).status_code == 404
    assert (await client.get(url, headers=setup["author"]["headers"])).status_code == 200
    assert (await client.get(url, headers=setup["admin"]["headers"])).status_code == 200

    # Others can't reply to it either
    res = await client.post(f"{url}/replies", json={"content": "hello"}, headers=setup["other"]["headers"])
    assert res.status_code == 404

    items = await queue(client, setup["admin"])
    assert items[0]["priority"] == "high"
    assert items[0]["content_status"] == "pending"


async def test_posts_in_a_premoderated_community_reach_the_queue(client, setup):
    community_id = await make_community()
    async with PostgresDB.get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE communities SET moderation_level = 'pre_moderated' WHERE community_id = $1", community_id
        )
    post = await make_post(client, community_id, setup["author"])
    assert post["moderation_status"] == "pending"

    items = await queue(client, setup["admin"])
    assert len(items) == 1
    assert items[0]["post_id"] == post["post_id"]
    assert items[0]["description"].startswith("Waiting for approval")

    res = await decide(client, setup["admin"], items[0]["report_id"], action="approve_content")
    assert res.status_code == 200
    assert post["post_id"] in await feed_ids(client, setup["other"])
    assert (await notifications_for(setup["author"]))[0]["title"] == "Your post is now visible"


async def test_held_reply_is_not_counted_or_announced(client, setup):
    community_id = setup["community_id"]
    post = await make_post(client, community_id, setup["author"])
    reply = await make_reply(client, community_id, post["post_id"], setup["other"], "You are an idiot, shut up")
    assert reply["moderation_status"] == "pending"

    row = await fetchrow("SELECT replies_count FROM forum_posts WHERE post_id = $1", post["post_id"])
    assert row["replies_count"] == 0
    assert await notifications_for(setup["author"], "community_reply") == []

    replies_url = f"{BASE}/community/{community_id}/posts/{post['post_id']}/replies"
    seen_by_post_author = (await client.get(replies_url, headers=setup["author"]["headers"])).json()
    seen_by_reply_author = (await client.get(replies_url, headers=setup["other"]["headers"])).json()
    assert seen_by_post_author == []
    assert [r["comment_id"] for r in seen_by_reply_author] == [reply["comment_id"]]


async def test_an_edit_can_hold_a_post_and_refreshes_its_auto_report(client, setup):
    community_id = setup["community_id"]
    post = await make_post(client, community_id, setup["author"])
    url = f"{BASE}/community/{community_id}/posts/{post['post_id']}"

    res = await client.patch(url, json={"content": QUESTION_TEXT}, headers=setup["author"]["headers"])
    assert res.status_code == 200
    assert res.json()["data"]["moderation_status"] == "approved"

    res = await client.patch(url, json={"content": HARMFUL_TEXT}, headers=setup["author"]["headers"])
    assert res.json()["data"]["moderation_status"] == "pending"

    row = await fetchrow("SELECT edited_at FROM forum_posts WHERE post_id = $1", post["post_id"])
    assert row["edited_at"] is not None
    items = await queue(client, setup["admin"])
    assert len(items) == 1  # one open automatic report per post, refreshed by each edit
    assert items[0]["priority"] == "high"
    assert items[0]["reported_content"] == HARMFUL_TEXT


# ----------------------------------------------------------------------
# User reports
# ----------------------------------------------------------------------
async def test_report_reasons_priority_and_target_checks(client, setup):
    community_id = setup["community_id"]
    post = await make_post(client, community_id, setup["author"])

    res = await report(client, community_id, setup["other"], post["post_id"], reason="self_harm")
    assert res.status_code == 201
    assert res.json()["priority"] == "critical"

    res = await report(client, community_id, setup["admin"], post["post_id"], reason="inappropriate_content")
    assert res.status_code == 201
    assert res.json()["priority"] == "normal"

    # Unknown content, or content from another community
    assert (await report(client, community_id, setup["other"], str(uuid.uuid4()))).status_code == 404
    other_community = await make_community()
    assert (await report(client, other_community, setup["author"], post["post_id"])).status_code == 404


async def test_three_reports_hide_a_post_from_everyone_but_its_author(client, setup):
    community_id = setup["community_id"]
    post = await make_post(client, community_id, setup["author"])
    for i in range(3):
        reporter = await make_user(client, f"reporter{i}@example.com")
        assert (await report(client, community_id, reporter, post["post_id"])).status_code == 201

    assert post["post_id"] not in await feed_ids(client, setup["other"])
    assert (await feed_ids(client, setup["author"]))[post["post_id"]]["moderation_status"] == "flagged"
    row = await fetchrow("SELECT flagged_reason FROM forum_posts WHERE post_id = $1", post["post_id"])
    assert row["flagged_reason"] == "Reported by 3 users"
    assert {i["priority"] for i in await queue(client, setup["admin"])} == {"high"}


# ----------------------------------------------------------------------
# The queue
# ----------------------------------------------------------------------
async def test_queue_is_for_admins_only(client, setup):
    assert (await client.get(f"{BASE}/moderation/queue")).status_code == 401
    res = await client.get(f"{BASE}/moderation/queue", headers=setup["other"]["headers"])
    assert res.status_code == 403
    res = await client.post(
        f"{BASE}/moderation/reports/{uuid.uuid4()}/decide",
        json={"action": "hide_content"},
        headers=setup["other"]["headers"],
    )
    assert res.status_code == 403


async def test_queue_puts_urgent_reports_first_and_shows_author_history(client, setup):
    community_id = setup["community_id"]
    normal = await make_post(client, community_id, setup["author"], title="Normal one")
    await report(client, community_id, setup["other"], normal["post_id"], reason="spam")
    held = await make_post(client, community_id, setup["author"], HARMFUL_TEXT, title="Held one")
    critical = await make_post(client, community_id, setup["other"], title="Critical one")
    await report(client, community_id, setup["admin"], critical["post_id"], reason="self_harm")

    items = await queue(client, setup["admin"])
    assert [i["priority"] for i in items] == ["critical", "high", "normal"]
    assert [i["post_id"] for i in items] == [critical["post_id"], held["post_id"], normal["post_id"]]

    history = items[2]["author_history"]
    assert history["reports_received"] == 2  # the spam report and the held post's automatic report
    assert history["warnings"] == 0

    assert len(await queue(client, setup["admin"], priority="critical")) == 1
    assert await queue(client, setup["admin"], status="closed") == []


# ----------------------------------------------------------------------
# Decisions
# ----------------------------------------------------------------------
async def test_approving_a_held_post_publishes_it_and_tells_the_author(client, setup):
    community_id = setup["community_id"]
    post = await make_post(client, community_id, setup["author"], HARMFUL_TEXT)
    report_id = (await queue(client, setup["admin"]))[0]["report_id"]

    res = await decide(client, setup["admin"], report_id, action="approve_content")
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["report_status"] == "dismissed"
    assert data["content_status"] == "approved"

    assert post["post_id"] in await feed_ids(client, setup["other"])
    notes = await notifications_for(setup["author"])
    assert len(notes) == 1
    assert notes[0]["title"] == "Your post is now visible"
    assert notes[0]["link"] == f"/community/{community_id}/posts/{post['post_id']}"


async def test_dismissing_a_report_on_a_visible_post_tells_nobody(client, setup):
    community_id = setup["community_id"]
    post = await make_post(client, community_id, setup["author"])
    report_id = (await report(client, community_id, setup["other"], post["post_id"])).json()["report_id"]

    res = await decide(client, setup["admin"], report_id, action="approve_content")
    assert res.status_code == 200
    assert await notifications_for(setup["author"]) == []


async def test_hiding_a_post_closes_every_report_and_is_recorded(client, setup):
    community_id = setup["community_id"]
    post = await make_post(client, community_id, setup["author"])
    first = (await report(client, community_id, setup["other"], post["post_id"])).json()["report_id"]
    await report(client, community_id, setup["admin"], post["post_id"], reason="harassment")

    res = await decide(client, setup["admin"], first, action="hide_content", reason="Off-topic advertising")
    assert res.status_code == 200
    assert res.json()["data"]["reports_closed"] == 2

    assert await queue(client, setup["admin"]) == []
    closed = await queue(client, setup["admin"], status="closed")
    assert len(closed) == 2
    assert {i["status"] for i in closed} == {"actioned"}
    assert {i["moderator_id"] for i in closed} == {setup["admin"]["id"]}

    row = await fetchrow("SELECT moderation_status FROM forum_posts WHERE post_id = $1", post["post_id"])
    assert row["moderation_status"] == "hidden"
    assert post["post_id"] not in await feed_ids(client, setup["author"])

    actions = await fetch("SELECT action_type, target_user_id, reason FROM moderation_actions")
    assert [(a["action_type"], str(a["target_user_id"]), a["reason"]) for a in actions] == [
        ("hide_content", setup["author"]["id"], "Off-topic advertising")
    ]
    audit = await fetchrow("SELECT user_id, metadata FROM audit_logs WHERE action = 'moderation.hide_content'")
    assert str(audit["user_id"]) == setup["admin"]["id"]
    metadata = audit["metadata"] if isinstance(audit["metadata"], dict) else json.loads(audit["metadata"])
    assert metadata["content_status"] == {"before": "approved", "after": "hidden"}

    notes = await notifications_for(setup["author"])
    assert notes[0]["title"] == "Your post was hidden"
    assert "Off-topic advertising" in notes[0]["message"]

    # The author can't edit it back
    res = await client.patch(
        f"{BASE}/community/{community_id}/posts/{post['post_id']}",
        json={"content": "Edited after it was hidden by a moderator."},
        headers=setup["author"]["headers"],
    )
    assert res.status_code == 403


async def test_deleting_a_reply_updates_the_reply_count(client, setup):
    community_id = setup["community_id"]
    post = await make_post(client, community_id, setup["author"])
    reply = await make_reply(client, community_id, post["post_id"], setup["other"])
    report_id = (await report(
        client, community_id, setup["author"], reply["comment_id"], target_type="comment", reason="harassment"
    )).json()["report_id"]

    res = await decide(client, setup["admin"], report_id, action="delete_content", reason="Rude reply")
    assert res.status_code == 200
    row = await fetchrow("SELECT replies_count FROM forum_posts WHERE post_id = $1", post["post_id"])
    assert row["replies_count"] == 0
    assert (await notifications_for(setup["other"]))[0]["title"] == "Your comment was removed"


async def test_warning_can_also_remove_the_content(client, setup):
    community_id = setup["community_id"]
    post = await make_post(client, community_id, setup["author"])
    report_id = (await report(client, community_id, setup["other"], post["post_id"])).json()["report_id"]

    res = await decide(
        client, setup["admin"], report_id, action="warn_user", reason="Please don't advertise", remove_content=True
    )
    assert res.status_code == 200
    assert res.json()["data"]["content_status"] == "removed"

    actions = await fetch("SELECT action_type FROM moderation_actions ORDER BY created_at")
    assert sorted(a["action_type"] for a in actions) == ["delete_content", "warn_user"]
    note = (await notifications_for(setup["author"]))[0]
    assert note["title"] == "Warning from the moderators"
    assert "Your post was also removed." in note["message"]

    # The author's history now shows the warning and the removal
    other_post = await make_post(client, community_id, setup["author"], title="Another post here")
    await report(client, community_id, setup["other"], other_post["post_id"])
    history = (await queue(client, setup["admin"]))[0]["author_history"]
    assert history["warnings"] == 1
    assert history["content_removed"] == 1
    assert history["reports_upheld"] == 1


async def test_suspending_an_author_blocks_their_account(client, setup):
    community_id = setup["community_id"]
    post = await make_post(client, community_id, setup["author"])
    report_id = (await report(client, community_id, setup["other"], post["post_id"])).json()["report_id"]

    res = await decide(
        client, setup["admin"], report_id, action="suspend_user", reason="Repeated spam", duration_hours=24
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["author_status"] == "suspended"

    row = await fetchrow(
        "SELECT status, suspended_until, suspended_reason FROM users WHERE id = $1", setup["author"]["id"]
    )
    assert row["status"] == "suspended"
    assert row["suspended_reason"] == "Repeated spam"
    expected = datetime.now(timezone.utc) + timedelta(hours=24)
    assert abs((row["suspended_until"] - expected).total_seconds()) < 60

    # Their existing login stops working, and they can't log in again
    res = await client.get(f"{BASE}/users/me", headers=setup["author"]["headers"])
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "account_suspended"
    res = await client.post(f"{BASE}/auth/login", json={"email": setup["author"]["email"], "password": PASSWORD})
    assert res.status_code == 403


async def test_ban_has_no_end_date(client, setup):
    community_id = setup["community_id"]
    post = await make_post(client, community_id, setup["author"])
    report_id = (await report(client, community_id, setup["other"], post["post_id"])).json()["report_id"]

    res = await decide(client, setup["admin"], report_id, action="ban_user", reason="Threats against members")
    assert res.status_code == 200
    row = await fetchrow("SELECT status, suspended_until FROM users WHERE id = $1", setup["author"]["id"])
    assert row["status"] == "suspended"
    assert row["suspended_until"] is None


async def test_moderation_notifications_ignore_notification_settings(client, setup):
    community_id = setup["community_id"]
    prefs = {"emailAlerts": False, "pushNotifications": False, "frequency": "instant",
             "notificationTypes": {"community_reply": False, "system_announcement": False}}
    async with PostgresDB.get_pool().acquire() as conn:
        await conn.execute(
            "UPDATE users SET notification_preferences = $2::jsonb WHERE id = $1",
            setup["author"]["id"], json.dumps(prefs),
        )
    post = await make_post(client, community_id, setup["author"])
    report_id = (await report(client, community_id, setup["other"], post["post_id"])).json()["report_id"]
    await decide(client, setup["admin"], report_id, action="warn_user", reason="Be kind")
    assert len(await notifications_for(setup["author"])) == 1


async def test_decision_checks(client, setup):
    community_id = setup["community_id"]
    admin = setup["admin"]
    post = await make_post(client, community_id, setup["author"])
    report_id = (await report(client, community_id, setup["other"], post["post_id"])).json()["report_id"]

    # Missing or misplaced details
    assert (await decide(client, admin, report_id, action="suspend_user", reason="x")).status_code == 422
    assert (await decide(client, admin, report_id, action="warn_user")).status_code == 422
    assert (await decide(client, admin, report_id, action="hide_content", remove_content=True)).status_code == 422
    assert (await decide(client, admin, report_id, action="hide_content", duration_hours=5)).status_code == 422
    assert (await decide(client, admin, report_id, action="explode")).status_code == 422
    assert (await decide(client, admin, str(uuid.uuid4()), action="hide_content")).status_code == 404

    # A decided report can't be decided again
    assert (await decide(client, admin, report_id, action="approve_content")).status_code == 200
    res = await decide(client, admin, report_id, action="hide_content")
    assert res.status_code == 409


async def test_admins_cant_be_warned_suspended_or_banned(client, setup):
    community_id = setup["community_id"]
    other_admin = await make_user(client, "admin2@example.com", "admin")
    post = await make_post(client, community_id, other_admin)
    report_id = (await report(client, community_id, setup["other"], post["post_id"])).json()["report_id"]

    res = await decide(client, setup["admin"], report_id, action="ban_user", reason="Testing")
    assert res.status_code == 400
    assert res.json()["detail"]["error"]["code"] == "ADMIN_ACCOUNT"
    # Their content can still be hidden
    assert (await decide(client, setup["admin"], report_id, action="hide_content")).status_code == 200


async def test_old_admin_report_list_still_works_with_automatic_reports(client, setup):
    await make_post(client, setup["community_id"], setup["author"], HARMFUL_TEXT)
    res = await client.get(f"{BASE}/community/admin/reports", headers=setup["admin"]["headers"])
    assert res.status_code == 200
    reports = res.json()["reports"]
    assert reports[0]["reporter_id"] is None
    assert reports[0]["source"] == "auto_filter"


async def test_verified_doctors_are_marked(client, setup):
    community_id = setup["community_id"]
    doctor = await make_user(client, "doctor@example.com", "hcp")
    async with PostgresDB.get_pool().acquire() as conn:
        await conn.execute("UPDATE users SET is_verified = TRUE WHERE id = $1", doctor["id"])
    post = await make_post(client, community_id, doctor)
    reply = await make_reply(client, community_id, post["post_id"], setup["author"])

    feed = await feed_ids(client)
    assert feed[post["post_id"]]["author_is_verified_hcp"] is True
    details = (await client.get(f"{BASE}/community/{community_id}/posts/{post['post_id']}")).json()
    assert details["post"]["author_is_verified_hcp"] is True
    assert details["replies"][0]["author_is_verified_hcp"] is False
    assert reply["author_is_verified_hcp"] is False
