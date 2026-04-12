import pytest
import uuid
from httpx import AsyncClient
from app.db.postgres import PostgresDB


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
async def create_user(client: AsyncClient, email: str = "community_test@example.com") -> str:
    """Register and login a user, return JWT token."""
    pwd = "StrongPassword123!"
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": pwd,
        "first_name": "Test",
        "last_name": "User",
        "user_type": "patient",
    })
    login_res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": pwd,
    })
    return login_res.json()["access_token"]


async def create_admin_user(client: AsyncClient, email: str = "admin_test@example.com") -> str:
    """Register and login an admin user, return JWT token."""
    pwd = "StrongPassword123!"
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": pwd,
        "first_name": "Admin",
        "last_name": "User",
        "user_type": "admin",
    })
    login_res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": pwd,
    })
    return login_res.json()["access_token"]


async def seed_community() -> str:
    """Insert a test community, return community_id."""
    pool = PostgresDB.get_pool()
    community_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO communities (
                community_id, name, description, type, moderation_level,
                member_count, post_count, is_active
            ) VALUES (
                $1, 'General Health', 'A general community', 'general', 'open',
                10, 0, TRUE
            )
        """, community_id)
    return community_id


async def seed_premod_community() -> str:
    """Insert a pre-moderated community."""
    pool = PostgresDB.get_pool()
    community_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO communities (
                community_id, name, description, type, moderation_level,
                member_count, post_count, is_active
            ) VALUES (
                $1, 'Moderated Forum', 'A pre-moderated community', 'disease_specific', 'pre_moderated',
                5, 0, TRUE
            )
        """, community_id)
    return community_id


# Helper: create a post inside a community and return post_id
async def create_post_in_community(
    client: AsyncClient, community_id: str, headers: dict, title: str = "Test Post Title Here"
) -> str:
    """Create a post in a community and return post_id."""
    res = await client.post(
        f"/api/v1/community/{community_id}/posts",
        json={
            "title": title,
            "content": "This is test content that is long enough.",
            "post_type": "discussion",
            "tags": ["test"],
        },
        headers=headers,
    )
    assert res.status_code == 201, f"Create post failed: {res.json()}"
    return res.json()["data"]["post_id"]


# ----------------------------------------------------------------------
# Tests: Communities
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_communities(client: AsyncClient, setup_test_db):
    """Test listing active communities."""
    community_id = await seed_community()

    res = await client.get("/api/v1/community/")
    assert res.status_code == 200
    data = res.json()
    assert data["meta"]["total"] >= 1
    assert len(data["data"]) >= 1
    names = [c["name"] for c in data["data"]]
    assert "General Health" in names


@pytest.mark.asyncio
async def test_list_communities_with_pagination(client: AsyncClient, setup_test_db):
    """Test communities pagination and sorting."""
    await seed_community()

    res = await client.get("/api/v1/community/?page=1&limit=5&sort=newest")
    assert res.status_code == 200
    data = res.json()
    assert data["meta"]["page"] == 1
    assert data["meta"]["limit"] == 5


@pytest.mark.asyncio
async def test_get_single_community(client: AsyncClient, setup_test_db):
    """Test getting a single community by ID."""
    community_id = await seed_community()

    res = await client.get(f"/api/v1/community/{community_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["community_id"] == community_id
    assert data["name"] == "General Health"


@pytest.mark.asyncio
async def test_get_community_not_found(client: AsyncClient, setup_test_db):
    """Test 404 for non-existent community."""
    fake_id = str(uuid.uuid4())
    res = await client.get(f"/api/v1/community/{fake_id}")
    assert res.status_code == 404


# ----------------------------------------------------------------------
# Tests: Posts CRUD
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_post(client: AsyncClient, setup_test_db, auth_headers):
    """Test creating a forum post."""
    community_id = await seed_community()
    token = await create_user(client)
    headers = auth_headers(token)

    payload = {
        "title": "How to manage chronic pain",
        "content": "I've been dealing with this condition for years and need advice.",
        "post_type": "question",
        "tags": ["pain", "chronic"],
    }
    res = await client.post(
        f"/api/v1/community/{community_id}/posts", json=payload, headers=headers
    )
    assert res.status_code == 201
    data = res.json()
    assert data["success"] is True
    assert data["data"]["title"] == "How to manage chronic pain"
    assert data["data"]["moderation_status"] == "approved"


@pytest.mark.asyncio
async def test_create_post_requires_auth(client: AsyncClient, setup_test_db):
    """Test that creating a post requires authentication."""
    community_id = await seed_community()
    payload = {
        "title": "Test Post Title",
        "content": "Test content body long enough",
    }
    res = await client.post(f"/api/v1/community/{community_id}/posts", json=payload)
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_post_premoderated(client: AsyncClient, setup_test_db, auth_headers):
    """Test create post in pre_moderated community -> status = pending."""
    community_id = await seed_premod_community()
    token = await create_user(client)
    headers = auth_headers(token)

    payload = {
        "title": "My experience with the disease",
        "content": "Let me share my story with this condition and how I cope.",
    }
    res = await client.post(
        f"/api/v1/community/{community_id}/posts", json=payload, headers=headers
    )
    assert res.status_code == 201
    data = res.json()
    assert data["data"]["moderation_status"] == "pending"


@pytest.mark.asyncio
async def test_edit_post(client: AsyncClient, setup_test_db, auth_headers):
    """Test editing a post by its author."""
    community_id = await seed_community()
    token = await create_user(client)
    headers = auth_headers(token)

    post_id = await create_post_in_community(client, community_id, headers, "Original Title Here")

    # Edit post
    edit_res = await client.patch(
        f"/api/v1/community/{community_id}/posts/{post_id}",
        json={"title": "Updated Title Here"},
        headers=headers,
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["data"]["title"] == "Updated Title Here"


@pytest.mark.asyncio
async def test_edit_post_reject_non_author(client: AsyncClient, setup_test_db, auth_headers):
    """Test that non-author cannot edit a post."""
    community_id = await seed_community()
    token_author = await create_user(client, "author@example.com")
    token_other = await create_user(client, "other@example.com")

    post_id = await create_post_in_community(
        client, community_id, auth_headers(token_author), "Author Only Post Title"
    )

    # Try to edit as other user
    edit_res = await client.patch(
        f"/api/v1/community/{community_id}/posts/{post_id}",
        json={"title": "Hacked Title From Other"},
        headers=auth_headers(token_other),
    )
    assert edit_res.status_code == 403


@pytest.mark.asyncio
async def test_delete_post(client: AsyncClient, setup_test_db, auth_headers):
    """Test soft deleting a post."""
    community_id = await seed_community()
    token = await create_user(client)
    headers = auth_headers(token)

    post_id = await create_post_in_community(client, community_id, headers, "Post To Be Deleted")

    del_res = await client.delete(
        f"/api/v1/community/{community_id}/posts/{post_id}", headers=headers
    )
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Verify it's gone from listing
    get_res = await client.get(
        f"/api/v1/community/{community_id}/posts/{post_id}", headers=headers
    )
    assert get_res.status_code == 404


# ----------------------------------------------------------------------
# Tests: Comments / Replies
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_reply_to_post(client: AsyncClient, setup_test_db, auth_headers):
    """Test replying to a post."""
    community_id = await seed_community()
    token = await create_user(client)
    headers = auth_headers(token)

    post_id = await create_post_in_community(
        client, community_id, headers, "Discussion About Treatment"
    )

    # Reply
    reply_res = await client.post(
        f"/api/v1/community/{community_id}/posts/{post_id}/replies",
        json={"content": "Great post! I have similar experiences."},
        headers=headers,
    )
    assert reply_res.status_code == 201
    assert reply_res.json()["content"] == "Great post! I have similar experiences."

    # Verify replies in post details
    detail_res = await client.get(
        f"/api/v1/community/{community_id}/posts/{post_id}", headers=headers
    )
    assert detail_res.status_code == 200
    assert len(detail_res.json()["replies"]) == 1


@pytest.mark.asyncio
async def test_edit_reply(client: AsyncClient, setup_test_db, auth_headers):
    """Test editing a reply."""
    community_id = await seed_community()
    token = await create_user(client)
    headers = auth_headers(token)

    post_id = await create_post_in_community(
        client, community_id, headers, "Post for editing reply"
    )

    # Reply
    reply_res = await client.post(
        f"/api/v1/community/{community_id}/posts/{post_id}/replies",
        json={"content": "Original reply content here."},
        headers=headers,
    )
    comment_id = reply_res.json()["comment_id"]

    # Edit reply
    edit_res = await client.patch(
        f"/api/v1/community/{community_id}/replies/{comment_id}",
        json={"content": "Updated reply content here instead."},
        headers=headers,
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["content"] == "Updated reply content here instead."


@pytest.mark.asyncio
async def test_delete_reply(client: AsyncClient, setup_test_db, auth_headers):
    """Test soft deleting a reply."""
    community_id = await seed_community()
    token = await create_user(client)
    headers = auth_headers(token)

    post_id = await create_post_in_community(
        client, community_id, headers, "Post for deleting reply"
    )

    # Reply
    reply_res = await client.post(
        f"/api/v1/community/{community_id}/posts/{post_id}/replies",
        json={"content": "Reply to be deleted soon."},
        headers=headers,
    )
    comment_id = reply_res.json()["comment_id"]

    # Delete reply
    del_res = await client.delete(
        f"/api/v1/community/{community_id}/replies/{comment_id}",
        headers=headers,
    )
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True


# ----------------------------------------------------------------------
# Tests: Community-Scoped Posts
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_community_posts(client: AsyncClient, setup_test_db, auth_headers):
    """Test listing posts scoped to a specific community."""
    community_id = await seed_community()
    token = await create_user(client)
    headers = auth_headers(token)

    # Create two posts in the community
    for i in range(2):
        await create_post_in_community(
            client, community_id, headers, f"Community Post {i+1} Title"
        )

    res = await client.get(
        f"/api/v1/community/{community_id}/posts", headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["meta"]["total"] >= 2


# ----------------------------------------------------------------------
# Tests: Likes
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_like_post(client: AsyncClient, setup_test_db, auth_headers):
    """Test liking a post."""
    community_id = await seed_community()
    token = await create_user(client)
    headers = auth_headers(token)

    post_id = await create_post_in_community(
        client, community_id, headers, "Like This Post Please"
    )

    # Like
    like_res = await client.post(
        f"/api/v1/community/{community_id}/posts/{post_id}/like", headers=headers
    )
    assert like_res.status_code == 200
    assert like_res.json()["data"]["likes_count"] == 1


@pytest.mark.asyncio
async def test_like_reply(client: AsyncClient, setup_test_db, auth_headers):
    """Test liking a reply/comment."""
    community_id = await seed_community()
    token = await create_user(client)
    headers = auth_headers(token)

    post_id = await create_post_in_community(
        client, community_id, headers, "Post For Liking Reply"
    )

    # Reply
    reply_res = await client.post(
        f"/api/v1/community/{community_id}/posts/{post_id}/replies",
        json={"content": "A reply to be liked."},
        headers=headers,
    )
    comment_id = reply_res.json()["comment_id"]

    # Like reply
    like_res = await client.post(
        f"/api/v1/community/{community_id}/replies/{comment_id}/like", headers=headers
    )
    assert like_res.status_code == 200
    assert like_res.json()["data"]["likes_count"] == 1


# ----------------------------------------------------------------------
# Tests: Reports
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_report_post(client: AsyncClient, setup_test_db, auth_headers):
    """Test reporting a post."""
    community_id = await seed_community()
    token = await create_user(client)
    headers = auth_headers(token)

    post_id = await create_post_in_community(
        client, community_id, headers, "Potentially Harmful Post Content"
    )

    # Report
    report_payload = {
        "target_type": "post",
        "target_id": post_id,
        "reason": "misinformation",
        "description": "Contains unverified medical claims",
    }
    report_res = await client.post(
        f"/api/v1/community/{community_id}/report",
        json=report_payload,
        headers=headers,
    )
    assert report_res.status_code == 201
    assert report_res.json()["reason"] == "misinformation"
    assert report_res.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_auto_flag_after_10_reports(client: AsyncClient, setup_test_db, auth_headers):
    """Test that content is auto-flagged after 10 reports."""
    community_id = await seed_community()

    # Create 10 reporter users
    reporters = []
    for i in range(10):
        t = await create_user(client, f"reporter{i}@example.com")
        reporters.append(t)

    # Create post as reporter 0
    post_id = await create_post_in_community(
        client, community_id, auth_headers(reporters[0]),
        "Flaggable Post Content Here"
    )

    report_payload = {
        "target_type": "post",
        "target_id": post_id,
        "reason": "spam",
    }

    # 10 reports from different users
    for t in reporters:
        await client.post(
            f"/api/v1/community/{community_id}/report",
            json=report_payload,
            headers=auth_headers(t),
        )

    # Verify post is now flagged
    pool = PostgresDB.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT moderation_status FROM forum_posts WHERE post_id = $1", post_id
        )
        assert row["moderation_status"] == "flagged"


@pytest.mark.asyncio
async def test_report_requires_auth(client: AsyncClient, setup_test_db):
    """Test that reporting requires authentication."""
    community_id = await seed_community()
    report_payload = {
        "target_type": "post",
        "target_id": str(uuid.uuid4()),
        "reason": "spam",
    }
    res = await client.post(
        f"/api/v1/community/{community_id}/report", json=report_payload
    )
    assert res.status_code in (401, 403)


# ----------------------------------------------------------------------
# Tests: Admin Report Management (global)
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_list_reports(client: AsyncClient, setup_test_db, auth_headers):
    """Test admin listing reports with pagination."""
    community_id = await seed_community()
    token = await create_user(client, "report_user@example.com")
    admin_token = await create_admin_user(client, "report_admin@example.com")
    headers = auth_headers(token)
    admin_headers = auth_headers(admin_token)

    # Create post and report it
    post_id = await create_post_in_community(
        client, community_id, headers, "Reported Post For Admin"
    )

    await client.post(
        f"/api/v1/community/{community_id}/report",
        json={
            "target_type": "post",
            "target_id": post_id,
            "reason": "spam",
        },
        headers=headers,
    )

    # Admin lists reports (global — no community_id in path)
    res = await client.get(
        "/api/v1/community/admin/reports?page=1&limit=10", headers=admin_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert len(data["reports"]) >= 1


@pytest.mark.asyncio
async def test_admin_list_reports_filter_status(client: AsyncClient, setup_test_db, auth_headers):
    """Test admin filtering reports by status."""
    admin_token = await create_admin_user(client, "filter_admin@example.com")
    admin_headers = auth_headers(admin_token)

    # Filter by pending
    res = await client.get(
        "/api/v1/community/admin/reports?report_status=pending",
        headers=admin_headers,
    )
    assert res.status_code == 200

    # Filter by resolved
    res2 = await client.get(
        "/api/v1/community/admin/reports?report_status=resolved",
        headers=admin_headers,
    )
    assert res2.status_code == 200


@pytest.mark.asyncio
async def test_admin_resolve_report(client: AsyncClient, setup_test_db, auth_headers):
    """Test admin resolving a report."""
    community_id = await seed_community()
    token = await create_user(client, "resolve_user@example.com")
    admin_token = await create_admin_user(client, "resolve_admin@example.com")
    headers = auth_headers(token)
    admin_headers = auth_headers(admin_token)

    # Create post and report
    post_id = await create_post_in_community(
        client, community_id, headers, "Post To Be Resolved By Admin"
    )

    report_res = await client.post(
        f"/api/v1/community/{community_id}/report",
        json={
            "target_type": "post",
            "target_id": post_id,
            "reason": "harassment",
        },
        headers=headers,
    )
    report_id = report_res.json()["report_id"]

    # Admin resolves report
    resolve_res = await client.patch(
        f"/api/v1/community/admin/reports/{report_id}",
        json={
            "status": "resolved",
            "action_taken": "removed",
            "resolution_notes": "Content violates community guidelines",
        },
        headers=admin_headers,
    )
    assert resolve_res.status_code == 200
    data = resolve_res.json()["data"]
    assert data["status"] == "resolved"
    assert data["action_taken"] == "removed"
    assert data["resolution_notes"] == "Content violates community guidelines"


@pytest.mark.asyncio
async def test_admin_delete_report(client: AsyncClient, setup_test_db, auth_headers):
    """Test admin deleting a report."""
    community_id = await seed_community()
    token = await create_user(client, "delreport_user@example.com")
    admin_token = await create_admin_user(client, "delreport_admin@example.com")
    headers = auth_headers(token)
    admin_headers = auth_headers(admin_token)

    # Create post and report
    post_id = await create_post_in_community(
        client, community_id, headers, "Post For Report Deletion"
    )

    report_res = await client.post(
        f"/api/v1/community/{community_id}/report",
        json={
            "target_type": "post",
            "target_id": post_id,
            "reason": "spam",
        },
        headers=headers,
    )
    report_id = report_res.json()["report_id"]

    # Admin deletes report
    del_res = await client.delete(
        f"/api/v1/community/admin/reports/{report_id}",
        headers=admin_headers,
    )
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True


@pytest.mark.asyncio
async def test_admin_reports_requires_admin(client: AsyncClient, setup_test_db, auth_headers):
    """Test that report admin endpoints reject non-admin users."""
    token = await create_user(client, "nonadmin@example.com")
    headers = auth_headers(token)

    # List reports
    res = await client.get("/api/v1/community/admin/reports", headers=headers)
    assert res.status_code == 403

    # Resolve report
    fake_id = str(uuid.uuid4())
    res2 = await client.patch(
        f"/api/v1/community/admin/reports/{fake_id}",
        json={"status": "resolved"},
        headers=headers,
    )
    assert res2.status_code == 403

    # Delete report
    res3 = await client.delete(
        f"/api/v1/community/admin/reports/{fake_id}",
        headers=headers,
    )
    assert res3.status_code == 403
