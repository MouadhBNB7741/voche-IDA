"""
Tests for Events & Webinars API Module.

Covers:
- List Events (success, filter by type, filter by date range)
- Event Details (valid id, invalid id)
- Register for Event (success, duplicate, event full)
- Cancel Registration (success, not registered)
- My Events (success, pagination)
"""

import pytest
import uuid
import json
from datetime import date, time as time_type, timedelta, datetime, timezone
from httpx import AsyncClient
from app.db.postgres import PostgresDB


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def create_user(
    client: AsyncClient, email: str = "events_test@example.com"
) -> tuple[str, str]:
    """Register and login a user, return (user_id, JWT token)."""
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
    token = login_res.json()["access_token"]
    me_res = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    user_id = me_res.json()["id"]
    return user_id, token


async def seed_events() -> list[str]:
    """Insert test events directly into the DB, return their IDs."""
    pool = PostgresDB.get_pool()
    ids = [str(uuid.uuid4()) for _ in range(5)]

    tomorrow = date.today() + timedelta(days=1)
    next_week = date.today() + timedelta(days=7)
    last_week = date.today() - timedelta(days=7)
    next_month = date.today() + timedelta(days=30)
    future_deadline = datetime.now(timezone.utc) + timedelta(days=5)
    past_deadline = datetime.now(timezone.utc) - timedelta(days=1)

    async with pool.acquire() as conn:
        # Event 0: upcoming webinar (tomorrow, 200 cap, 10 registered)
        await conn.execute("""
            INSERT INTO events (
                event_id, title, description, type, organizer,
                event_date, event_time, timezone, location, virtual_link,
                participants, max_participants, registration_deadline,
                status, tags
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        """,
            ids[0], "Global TB Webinar", "A webinar about TB", "webinar", "WHO",
            tomorrow, time_type(14, 0), "UTC", "Virtual", "https://zoom.us/tb-webinar",
            10, 200, future_deadline,
            "upcoming", json.dumps(["research", "tb"]),
        )

        # Event 1: upcoming conference (next_week, 2 cap, 1 registered — almost full)
        await conn.execute("""
            INSERT INTO events (
                event_id, title, description, type, organizer,
                event_date, event_time, timezone, location,
                participants, max_participants, registration_deadline,
                status, tags
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        """,
            ids[1], "HIV Conference", "Annual HIV conference", "conference", "UNAIDS",
            next_week, time_type(9, 0), "CET", "Geneva",
            1, 2, future_deadline,
            "upcoming", json.dumps(["hiv"]),
        )

        # Event 2: past event (last_week, completed)
        await conn.execute("""
            INSERT INTO events (
                event_id, title, description, type, organizer,
                event_date, event_time, timezone, location,
                participants, max_participants,
                status, tags
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        """,
            ids[2], "Past Training", "Completed training session", "training", "MSF",
            last_week, time_type(10, 0), "UTC", "Paris",
            50, 100,
            "completed", json.dumps(["training"]),
        )

        # Event 3: upcoming roundtable (next_month, deadline passed)
        await conn.execute("""
            INSERT INTO events (
                event_id, title, description, type, organizer,
                event_date, event_time, timezone, location,
                participants, max_participants, registration_deadline,
                status, tags
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        """,
            ids[3], "Policy Roundtable", "Discuss policy", "roundtable", "WHO",
            next_month, time_type(16, 0), "UTC", "Virtual",
            5, 50, past_deadline,
            "upcoming", json.dumps(["policy"]),
        )

        # Event 4: cancelled event
        await conn.execute("""
            INSERT INTO events (
                event_id, title, description, type, organizer,
                event_date, event_time, timezone, location,
                participants, max_participants,
                status, tags
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        """,
            ids[4], "Cancelled Seminar", "This was cancelled", "webinar", "Org",
            next_week, time_type(11, 0), "UTC", "Virtual",
            0, 100,
            "cancelled", json.dumps([]),
        )

    return ids


# ──────────────────────────────────────────────────────────────────────────────
# 1. List Events
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_events_success(client: AsyncClient, setup_test_db):
    """Test listing events returns all seeded events."""
    await seed_events()

    res = await client.get("/api/v1/events/")
    assert res.status_code == 200
    data = res.json()
    assert len(data["data"]) >= 5
    assert data["meta"]["total"] >= 5


@pytest.mark.asyncio
async def test_list_events_filter_by_type(client: AsyncClient, setup_test_db):
    """Test filtering events by type."""
    await seed_events()

    res = await client.get("/api/v1/events/?type=webinar")
    assert res.status_code == 200
    data = res.json()
    for event in data["data"]:
        assert event["type"] == "webinar"


@pytest.mark.asyncio
async def test_list_events_filter_by_date_range(client: AsyncClient, setup_test_db):
    """Test filtering events by date range."""
    await seed_events()

    today = date.today().isoformat()
    next_week = (date.today() + timedelta(days=7)).isoformat()

    res = await client.get(f"/api/v1/events/?date_from={today}&date_to={next_week}")
    assert res.status_code == 200
    data = res.json()
    # Should include tomorrow and next_week events, but not last_week or next_month
    for event in data["data"]:
        event_date = event["event_date"]
        assert event_date >= today
        assert event_date <= next_week


@pytest.mark.asyncio
async def test_list_events_sorting(client: AsyncClient, setup_test_db):
    """Test that upcoming events appear before past events."""
    await seed_events()

    res = await client.get("/api/v1/events/")
    assert res.status_code == 200
    data = res.json()
    events = data["data"]

    # Find indices of upcoming vs past events
    today_str = date.today().isoformat()
    upcoming_indices = [
        i for i, e in enumerate(events) if e["event_date"] >= today_str
    ]
    past_indices = [
        i for i, e in enumerate(events) if e["event_date"] < today_str
    ]
    # All upcoming events should appear before past events
    if upcoming_indices and past_indices:
        assert max(upcoming_indices) < min(past_indices)


@pytest.mark.asyncio
async def test_list_events_pagination(client: AsyncClient, setup_test_db):
    """Test pagination works correctly."""
    await seed_events()

    res = await client.get("/api/v1/events/?page=1&limit=2")
    assert res.status_code == 200
    data = res.json()
    assert len(data["data"]) == 2
    assert data["meta"]["page"] == 1
    assert data["meta"]["limit"] == 2
    assert data["meta"]["total"] >= 5


# ──────────────────────────────────────────────────────────────────────────────
# 2. Event Details
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_event_details_valid(client: AsyncClient, setup_test_db):
    """Test getting details for a valid event."""
    ids = await seed_events()

    res = await client.get(f"/api/v1/events/{ids[0]}")
    assert res.status_code == 200
    data = res.json()
    assert data["event_id"] == ids[0]
    assert data["title"] == "Global TB Webinar"
    assert data["description"] == "A webinar about TB"
    assert data["type"] == "webinar"
    assert data["organizer"] == "WHO"
    assert "tags" in data
    assert isinstance(data["tags"], list)
    assert "research" in data["tags"]
    assert data["max_participants"] == 200
    assert data["virtual_link"] == "https://zoom.us/tb-webinar"


@pytest.mark.asyncio
async def test_event_details_invalid(client: AsyncClient, setup_test_db):
    """Test getting details for a non-existent event returns 404."""
    res = await client.get(f"/api/v1/events/{uuid.uuid4()}")
    assert res.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# 3. Register for Event
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_event_success(client: AsyncClient, setup_test_db, auth_headers):
    """Test successful event registration."""
    ids = await seed_events()
    _, token = await create_user(client, "register@example.com")

    res = await client.post(
        f"/api/v1/events/{ids[0]}/register",
        headers=auth_headers(token),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "registered"
    assert "successfully" in data["message"].lower()

    # Verify participants incremented
    event_res = await client.get(f"/api/v1/events/{ids[0]}")
    assert event_res.json()["participants"] == 11  # was 10


@pytest.mark.asyncio
async def test_register_event_duplicate(client: AsyncClient, setup_test_db, auth_headers):
    """Test duplicate registration is rejected."""
    ids = await seed_events()
    _, token = await create_user(client, "dup@example.com")

    # First registration
    res1 = await client.post(
        f"/api/v1/events/{ids[0]}/register",
        headers=auth_headers(token),
    )
    assert res1.status_code == 200

    # Duplicate registration
    res2 = await client.post(
        f"/api/v1/events/{ids[0]}/register",
        headers=auth_headers(token),
    )
    assert res2.status_code == 409


@pytest.mark.asyncio
async def test_register_event_full(client: AsyncClient, setup_test_db, auth_headers):
    """Test registration fails when event is full."""
    ids = await seed_events()

    # Event 1 has max_participants=2 and participants=1
    # Register first user to fill it
    _, token1 = await create_user(client, "fill1@example.com")
    res1 = await client.post(
        f"/api/v1/events/{ids[1]}/register",
        headers=auth_headers(token1),
    )
    assert res1.status_code == 200

    # Now event is at capacity (2/2)
    _, token2 = await create_user(client, "fill2@example.com")
    res2 = await client.post(
        f"/api/v1/events/{ids[1]}/register",
        headers=auth_headers(token2),
    )
    assert res2.status_code == 409


@pytest.mark.asyncio
async def test_register_event_not_found(client: AsyncClient, setup_test_db, auth_headers):
    """Test registration for non-existent event returns 404."""
    _, token = await create_user(client, "notfound@example.com")

    res = await client.post(
        f"/api/v1/events/{uuid.uuid4()}/register",
        headers=auth_headers(token),
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_register_event_deadline_passed(client: AsyncClient, setup_test_db, auth_headers):
    """Test registration fails when deadline has passed."""
    ids = await seed_events()
    _, token = await create_user(client, "deadline@example.com")

    # Event 3 has past deadline
    res = await client.post(
        f"/api/v1/events/{ids[3]}/register",
        headers=auth_headers(token),
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_register_requires_auth(client: AsyncClient, setup_test_db):
    """Test registration without auth fails."""
    ids = await seed_events()

    res = await client.post(f"/api/v1/events/{ids[0]}/register")
    assert res.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# 4. Cancel Registration
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancel_registration_success(client: AsyncClient, setup_test_db, auth_headers):
    """Test successful cancellation."""
    ids = await seed_events()
    _, token = await create_user(client, "cancel@example.com")

    # Register first
    await client.post(
        f"/api/v1/events/{ids[0]}/register",
        headers=auth_headers(token),
    )

    # Cancel
    res = await client.delete(
        f"/api/v1/events/{ids[0]}/register",
        headers=auth_headers(token),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "cancelled"

    # Verify participants decremented
    event_res = await client.get(f"/api/v1/events/{ids[0]}")
    assert event_res.json()["participants"] == 10  # back to original


@pytest.mark.asyncio
async def test_cancel_registration_not_registered(client: AsyncClient, setup_test_db, auth_headers):
    """Test cancellation when not registered returns 404."""
    ids = await seed_events()
    _, token = await create_user(client, "notreg@example.com")

    res = await client.delete(
        f"/api/v1/events/{ids[0]}/register",
        headers=auth_headers(token),
    )
    assert res.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# 5. My Events
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_my_events_success(client: AsyncClient, setup_test_db, auth_headers):
    """Test getting user's registered events."""
    ids = await seed_events()
    _, token = await create_user(client, "myevents@example.com")

    # Register for two events
    await client.post(
        f"/api/v1/events/{ids[0]}/register",
        headers=auth_headers(token),
    )
    await client.post(
        f"/api/v1/events/{ids[1]}/register",
        headers=auth_headers(token),
    )

    res = await client.get(
        "/api/v1/users/me/events",
        headers=auth_headers(token),
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["data"]) == 2
    assert data["meta"]["total"] == 2


@pytest.mark.asyncio
async def test_my_events_excludes_cancelled(client: AsyncClient, setup_test_db, auth_headers):
    """Test that cancelled registrations are not included in my events."""
    ids = await seed_events()
    _, token = await create_user(client, "excludecancel@example.com")

    # Register and cancel
    await client.post(
        f"/api/v1/events/{ids[0]}/register",
        headers=auth_headers(token),
    )
    await client.delete(
        f"/api/v1/events/{ids[0]}/register",
        headers=auth_headers(token),
    )

    res = await client.get(
        "/api/v1/users/me/events",
        headers=auth_headers(token),
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["data"]) == 0


@pytest.mark.asyncio
async def test_my_events_pagination(client: AsyncClient, setup_test_db, auth_headers):
    """Test pagination on my events."""
    ids = await seed_events()
    _, token = await create_user(client, "mypaged@example.com")

    # Register for 3 events
    await client.post(f"/api/v1/events/{ids[0]}/register", headers=auth_headers(token))
    await client.post(f"/api/v1/events/{ids[1]}/register", headers=auth_headers(token))

    res = await client.get(
        "/api/v1/users/me/events?page=1&limit=1",
        headers=auth_headers(token),
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["data"]) == 1
    assert data["meta"]["total"] == 2
    assert data["meta"]["page"] == 1
    assert data["meta"]["limit"] == 1
    assert data["meta"]["pages"] == 2


@pytest.mark.asyncio
async def test_my_events_requires_auth(client: AsyncClient, setup_test_db):
    """Test my events without auth fails."""
    res = await client.get("/api/v1/users/me/events")
    assert res.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
# 6. Registration Status in List (Authenticated)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_events_with_registration_status(client: AsyncClient, setup_test_db, auth_headers):
    """Test that registration_status appears for authenticated users."""
    ids = await seed_events()
    _, token = await create_user(client, "regstatus@example.com")

    # Register for one event
    await client.post(
        f"/api/v1/events/{ids[0]}/register",
        headers=auth_headers(token),
    )

    # List events with auth
    res = await client.get(
        "/api/v1/events/",
        headers=auth_headers(token),
    )
    assert res.status_code == 200
    data = res.json()

    # Find the registered event
    registered_event = next(
        (e for e in data["data"] if e["event_id"] == ids[0]), None
    )
    assert registered_event is not None
    assert registered_event["registration_status"] == "registered"

    # Other events should have no registration_status
    other_event = next(
        (e for e in data["data"] if e["event_id"] == ids[1]), None
    )
    assert other_event is not None
    assert other_event["registration_status"] is None


@pytest.mark.asyncio
async def test_event_details_with_registration_status(client: AsyncClient, setup_test_db, auth_headers):
    """Test that event details include registration_status for authenticated users."""
    ids = await seed_events()
    _, token = await create_user(client, "detailreg@example.com")

    # Register
    await client.post(
        f"/api/v1/events/{ids[0]}/register",
        headers=auth_headers(token),
    )

    # Get details with auth
    res = await client.get(
        f"/api/v1/events/{ids[0]}",
        headers=auth_headers(token),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["registration_status"] == "registered"


@pytest.mark.asyncio
async def test_re_register_after_cancel(client: AsyncClient, setup_test_db, auth_headers):
    """Test re-registration after cancelling works correctly."""
    ids = await seed_events()
    _, token = await create_user(client, "rereg@example.com")

    # Register → cancel → re-register
    await client.post(f"/api/v1/events/{ids[0]}/register", headers=auth_headers(token))
    await client.delete(f"/api/v1/events/{ids[0]}/register", headers=auth_headers(token))

    res = await client.post(
        f"/api/v1/events/{ids[0]}/register",
        headers=auth_headers(token),
    )
    assert res.status_code == 200
    assert res.json()["status"] == "registered"
