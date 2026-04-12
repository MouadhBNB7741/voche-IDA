"""
Test suite for System API — /api/v1/system, /api/v1/health

Covers:
  - Health check (public)
  - System status (public)
  - Metadata endpoint (public, cached)
  - Feedback submission (auth required)
  - Edge cases (invalid feedback, unauthorized)
"""
import pytest
import secrets
from httpx import AsyncClient

pytestmark = pytest.mark.anyio

BASE = "/api/v1"


# ── HELPERS ──────────────────────────────────────────────────────────────────

async def register_user(client: AsyncClient, email: str = None, user_type: str = "patient"):
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
    import jwt
    payload = jwt.decode(data["access_token"], options={"verify_signature": False})
    return data["access_token"], payload["sub"]


def auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


# ── HEALTH CHECK ─────────────────────────────────────────────────────────────

class TestHealthCheck:

    async def test_health_endpoint_public(self, client: AsyncClient):
        """Health check should be accessible without authentication."""
        resp = await client.get(f"{BASE}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")
        assert "version" in data
        assert "database" in data
        assert "timestamp" in data

    async def test_health_check_db_connected(self, client: AsyncClient):
        """Health check should report connected DB."""
        resp = await client.get(f"{BASE}/health")
        assert resp.status_code == 200
        assert resp.json()["database"] == "connected"


# ── SYSTEM STATUS ────────────────────────────────────────────────────────────

class TestSystemStatus:

    async def test_system_status_public(self, client: AsyncClient):
        """System status should be accessible without authentication."""
        resp = await client.get(f"{BASE}/system/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["api_version"] == "v1"
        assert data["status"] in ("operational", "degraded")
        assert "uptime_seconds" in data
        assert "database" in data
        assert "features" in data

    async def test_system_status_features(self, client: AsyncClient):
        """System status should include feature flags."""
        resp = await client.get(f"{BASE}/system/status")
        features = resp.json()["features"]
        assert features["forums"] is True
        assert features["events"] is True
        assert features["notifications"] is True

    async def test_system_status_uptime(self, client: AsyncClient):
        """Uptime should be a positive number."""
        resp = await client.get(f"{BASE}/system/status")
        assert resp.json()["uptime_seconds"] > 0


# ── METADATA ─────────────────────────────────────────────────────────────────

class TestMetadata:

    async def test_metadata_public(self, client: AsyncClient):
        """Metadata should be accessible without authentication."""
        resp = await client.get(f"{BASE}/system/metadata")
        assert resp.status_code == 200

    async def test_metadata_contains_all_enums(self, client: AsyncClient):
        """Metadata should contain all expected enum categories."""
        resp = await client.get(f"{BASE}/system/metadata")
        data = resp.json()
        expected_keys = [
            "countries", "disease_areas", "languages", "trial_phases",
            "trial_statuses", "roles", "community_types", "event_types",
            "resource_types", "feedback_categories",
        ]
        for key in expected_keys:
            assert key in data, f"Missing metadata key: {key}"
            assert len(data[key]) > 0, f"Empty metadata for: {key}"

    async def test_metadata_countries_populated(self, client: AsyncClient):
        resp = await client.get(f"{BASE}/system/metadata")
        countries = resp.json()["countries"]
        assert "Kenya" in countries
        assert "Nigeria" in countries
        assert "South Africa" in countries

    async def test_metadata_trial_phases(self, client: AsyncClient):
        resp = await client.get(f"{BASE}/system/metadata")
        phases = resp.json()["trial_phases"]
        assert "Phase 1" in phases
        assert "Phase 3" in phases

    async def test_metadata_languages_structure(self, client: AsyncClient):
        """Each language should have code and name."""
        resp = await client.get(f"{BASE}/system/metadata")
        languages = resp.json()["languages"]
        for lang in languages:
            assert "code" in lang
            assert "name" in lang

    async def test_metadata_cached(self, client: AsyncClient):
        """Calling metadata twice should return identical results."""
        resp1 = await client.get(f"{BASE}/system/metadata")
        resp2 = await client.get(f"{BASE}/system/metadata")
        assert resp1.json() == resp2.json()


# ── FEEDBACK ─────────────────────────────────────────────────────────────────

class TestFeedback:

    async def test_submit_feedback_unauthorized(self, client: AsyncClient):
        """Feedback submission requires authentication."""
        resp = await client.post(f"{BASE}/system/feedback", json={
            "category": "platform",
            "message": "The search is slow on the trials page.",
            "rating": 4,
        })
        assert resp.status_code in (401, 403)

    async def test_submit_feedback_success(self, client: AsyncClient):
        """Authenticated user can submit feedback with star rating."""
        token, user_id = await register_user(client)
        resp = await client.post(
            f"{BASE}/system/feedback",
            json={
                "category": "platform",
                "message": "The search is slow on the trials page, please fix it.",
                "rating": 4,
            },
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "ticket_id" in data
        assert data["message"] == "Feedback submitted successfully"
        assert data["rating"] == 4

    async def test_submit_feedback_5_stars(self, client: AsyncClient):
        """5-star rating should be accepted."""
        token, _ = await register_user(client)
        resp = await client.post(
            f"{BASE}/system/feedback",
            json={
                "category": "feature",
                "message": "Loving the new trial matching feature! Works perfectly.",
                "rating": 5,
            },
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.json()["rating"] == 5

    async def test_submit_feedback_1_star(self, client: AsyncClient):
        """1-star rating should be accepted."""
        token, _ = await register_user(client)
        resp = await client.post(
            f"{BASE}/system/feedback",
            json={
                "category": "bug",
                "message": "The application keeps crashing when I search for trials.",
                "rating": 1,
            },
            headers=auth_header(token),
        )
        assert resp.status_code == 200
        assert resp.json()["rating"] == 1

    async def test_submit_feedback_rating_too_high(self, client: AsyncClient):
        """Rating > 5 should be rejected."""
        token, _ = await register_user(client)
        resp = await client.post(
            f"{BASE}/system/feedback",
            json={
                "category": "platform",
                "message": "This should fail rating validation check.",
                "rating": 6,
            },
            headers=auth_header(token),
        )
        assert resp.status_code == 422

    async def test_submit_feedback_rating_too_low(self, client: AsyncClient):
        """Rating < 1 should be rejected."""
        token, _ = await register_user(client)
        resp = await client.post(
            f"{BASE}/system/feedback",
            json={
                "category": "platform",
                "message": "This should fail rating validation check.",
                "rating": 0,
            },
            headers=auth_header(token),
        )
        assert resp.status_code == 422

    async def test_submit_feedback_missing_rating(self, client: AsyncClient):
        """Missing rating should be rejected."""
        token, _ = await register_user(client)
        resp = await client.post(
            f"{BASE}/system/feedback",
            json={
                "category": "platform",
                "message": "This should fail because rating is missing.",
            },
            headers=auth_header(token),
        )
        assert resp.status_code == 422

    async def test_submit_feedback_invalid_category(self, client: AsyncClient):
        """Invalid category should be rejected."""
        token, _ = await register_user(client)
        resp = await client.post(
            f"{BASE}/system/feedback",
            json={
                "category": "invalid_category",
                "message": "This should fail validation.",
                "rating": 3,
            },
            headers=auth_header(token),
        )
        assert resp.status_code == 422  # Validation error

    async def test_submit_feedback_too_short(self, client: AsyncClient):
        """Message too short should be rejected."""
        token, _ = await register_user(client)
        resp = await client.post(
            f"{BASE}/system/feedback",
            json={
                "category": "platform",
                "message": "Short",  # Less than 10 chars
                "rating": 3,
            },
            headers=auth_header(token),
        )
        assert resp.status_code == 422

    async def test_submit_feedback_missing_fields(self, client: AsyncClient):
        """Missing required fields should be rejected."""
        token, _ = await register_user(client)
        resp = await client.post(
            f"{BASE}/system/feedback",
            json={"category": "platform"},  # Missing message and rating
            headers=auth_header(token),
        )
        assert resp.status_code == 422

    async def test_all_feedback_categories(self, client: AsyncClient):
        """All valid categories should be accepted with rating."""
        token, _ = await register_user(client)
        for i, category in enumerate(["platform", "trial", "patient", "feature", "bug", "other"]):
            rating = (i % 5) + 1  # Cycles 1-5
            resp = await client.post(
                f"{BASE}/system/feedback",
                json={
                    "category": category,
                    "message": f"Testing feedback for {category} category works correctly.",
                    "rating": rating,
                },
                headers=auth_header(token),
            )
            assert resp.status_code == 200, f"Category '{category}' failed: {resp.text}"

