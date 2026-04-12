"""
Tests for Surveys & Research API Module.
"""

import pytest
import uuid
import json
from httpx import AsyncClient
from app.db.postgres import PostgresDB
from datetime import date, timedelta


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def create_user(
    client: AsyncClient, email: str = "surveys_test@example.com"
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


async def seed_surveys() -> dict:
    """Insert test surveys directly into the DB, return their IDs and Questions."""
    pool = PostgresDB.get_pool()
    survey_ids = [str(uuid.uuid4()) for _ in range(4)]
    question_ids = [str(uuid.uuid4()) for _ in range(3)]
    
    tomorrow = date.today() + timedelta(days=1)
    last_week = date.today() - timedelta(days=7)

    async with pool.acquire() as conn:
        # Survey 0: Active
        await conn.execute("""
            INSERT INTO surveys (
                survey_id, title, description, consent_text,
                target_audience, estimated_time, status, incentive,
                published_date, closing_date
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
            survey_ids[0], "Patient Experience Survey", "Help us improve", "I consent.",
            json.dumps(["patient"]), "10 minutes", "active", "10 points",
            last_week, tomorrow
        )
        
        # Survey 1: Draft
        await conn.execute("""
            INSERT INTO surveys (
                survey_id, title, description,
                target_audience, estimated_time, status
            ) VALUES ($1, $2, $3, $4, $5, $6)
        """,
            survey_ids[1], "Draft Survey", "Draft",
            json.dumps(["patient"]), "5 mins", "draft"
        )
        
        # Survey 2: Completed (closed)
        await conn.execute("""
            INSERT INTO surveys (
                survey_id, title, description,
                target_audience, status
            ) VALUES ($1, $2, $3, $4, $5)
        """,
            survey_ids[2], "Old Survey", "Old",
            json.dumps([]), "closed"
        )
        
        # Survey 3: Active but expired (closing_date in past)
        yesterday = date.today() - timedelta(days=1)
        await conn.execute("""
            INSERT INTO surveys (
                survey_id, title, description,
                target_audience, status, closing_date
            ) VALUES ($1, $2, $3, $4, $5, $6)
        """,
            survey_ids[3], "Expired Survey", "Expired",
            json.dumps([]), "active", yesterday
        )
        
        # Questions for Survey 0
        await conn.execute("""
            INSERT INTO survey_questions (question_id, survey_id, question_text, question_type, order_position, required, options)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, question_ids[0], survey_ids[0], "How old are you?", "open_text", 1, True, None)
        
        await conn.execute("""
            INSERT INTO survey_questions (question_id, survey_id, question_text, question_type, order_position, required, options)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, question_ids[1], survey_ids[0], "Are you happy?", "yes_no", 2, True, None)

        await conn.execute("""
            INSERT INTO survey_questions (question_id, survey_id, question_text, question_type, order_position, required, options)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, question_ids[2], survey_ids[0], "Rate us", "scale", 3, False, None)

    return {"surveys": survey_ids, "questions": question_ids}


# ──────────────────────────────────────────────────────────────────────────────
# 1. List Surveys
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_surveys_success(client: AsyncClient, setup_test_db, auth_headers):
    """Test listing active surveys the user is eligible for."""
    await seed_surveys()
    _, token = await create_user(client, "list1@example.com")

    res = await client.get("/api/v1/surveys/", headers=auth_headers(token))
    
    assert res.status_code == 200
    data = res.json()
    assert len(data["data"]) >= 1
    # By default, should only list active
    for item in data["data"]:
        assert item["status"] == "active"

@pytest.mark.asyncio
async def test_list_surveys_filter_by_status(client: AsyncClient, setup_test_db, auth_headers):
    """Test listing surveys filtered by status."""
    await seed_surveys()
    _, token = await create_user(client, "list2@example.com")

    res = await client.get("/api/v1/surveys/?status=closed", headers=auth_headers(token))
    
    assert res.status_code == 200
    data = res.json()
    for item in data["data"]:
        assert item["status"] == "closed"
        
@pytest.mark.asyncio
async def test_list_surveys_pagination(client: AsyncClient, setup_test_db, auth_headers):
    """Test listing surveys with pagination."""
    await seed_surveys()
    _, token = await create_user(client, "list3@example.com")

    res = await client.get("/api/v1/surveys/?page=1&limit=1", headers=auth_headers(token))
    
    assert res.status_code == 200
    data = res.json()
    assert len(data["data"]) == 1
    assert data["meta"]["page"] == 1
    assert data["meta"]["limit"] == 1


# ──────────────────────────────────────────────────────────────────────────────
# 2. Survey Details
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_survey_details_valid(client: AsyncClient, setup_test_db, auth_headers):
    """Test survey details for valid ID includes questions."""
    seeded = await seed_surveys()
    _, token = await create_user(client, "detail1@example.com")

    res = await client.get(f"/api/v1/surveys/{seeded['surveys'][0]}", headers=auth_headers(token))
    
    assert res.status_code == 200
    data = res.json()
    assert data["survey_id"] == seeded['surveys'][0]
    assert data["title"] == "Patient Experience Survey"
    assert len(data["questions"]) == 3
    assert data["questions"][0]["text"] == "How old are you?"
    assert data["questions"][0]["required"] is True

@pytest.mark.asyncio
async def test_get_survey_details_invalid(client: AsyncClient, setup_test_db, auth_headers):
    """Test survey details for invalid ID returns 404."""
    _, token = await create_user(client, "detail2@example.com")

    res = await client.get(f"/api/v1/surveys/{uuid.uuid4()}", headers=auth_headers(token))
    
    assert res.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# 3. Submit Responses
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_response_success(client: AsyncClient, setup_test_db, auth_headers):
    """Test successful response submission."""
    seeded = await seed_surveys()
    _, token = await create_user(client, "submit1@example.com")
    
    survey_id = seeded['surveys'][0]
    q_ids = seeded['questions']

    payload = {
        "consent_given": True,
        "anonymous": False,
        "responses": [
            {"question_id": q_ids[0], "answer": "30"},
            {"question_id": q_ids[1], "answer": "Yes"}
        ]
    }

    res = await client.post(f"/api/v1/surveys/{survey_id}/responses", headers=auth_headers(token), json=payload)
    
    assert res.status_code == 200
    assert res.json()["message"] == "Thank you for your feedback!"
    assert "completion_id" in res.json()

@pytest.mark.asyncio
async def test_submit_response_missing_consent(client: AsyncClient, setup_test_db, auth_headers):
    """Test failed submission due to missing consent."""
    seeded = await seed_surveys()
    _, token = await create_user(client, "submit2@example.com")
    
    survey_id = seeded['surveys'][0]

    payload = {
        "consent_given": False,
        "anonymous": False,
        "responses": []
    }

    res = await client.post(f"/api/v1/surveys/{survey_id}/responses", headers=auth_headers(token), json=payload)
    
    assert res.status_code == 400
    assert "Consent is required" in res.json()["detail"]

@pytest.mark.asyncio
async def test_submit_response_missing_required(client: AsyncClient, setup_test_db, auth_headers):
    """Test failed submission due to missing required answer."""
    seeded = await seed_surveys()
    _, token = await create_user(client, "submit3@example.com")
    
    survey_id = seeded['surveys'][0]
    q_ids = seeded['questions']

    payload = {
        "consent_given": True,
        "anonymous": False,
        "responses": [
            {"question_id": q_ids[0], "answer": "30"} # missing q_ids[1] which is required
        ]
    }

    res = await client.post(f"/api/v1/surveys/{survey_id}/responses", headers=auth_headers(token), json=payload)
    
    assert res.status_code == 400
    assert "missing" in res.json()["detail"].lower()

@pytest.mark.asyncio
async def test_submit_response_invalid_question(client: AsyncClient, setup_test_db, auth_headers):
    """Test failed submission due to invalid question."""
    seeded = await seed_surveys()
    _, token = await create_user(client, "submit4@example.com")
    
    survey_id = seeded['surveys'][0]
    q_ids = seeded['questions']

    payload = {
        "consent_given": True,
        "anonymous": False,
        "responses": [
            {"question_id": q_ids[0], "answer": "30"},
            {"question_id": q_ids[1], "answer": "Yes"},
            {"question_id": str(uuid.uuid4()), "answer": "Invalid Q"} 
        ]
    }

    res = await client.post(f"/api/v1/surveys/{survey_id}/responses", headers=auth_headers(token), json=payload)
    
    assert res.status_code == 400
    assert "does not belong" in res.json()["detail"].lower()

@pytest.mark.asyncio
async def test_submit_duplicate_response(client: AsyncClient, setup_test_db, auth_headers):
    """Test failed submission due to duplicate response."""
    seeded = await seed_surveys()
    _, token = await create_user(client, "submit5@example.com")
    
    survey_id = seeded['surveys'][0]
    q_ids = seeded['questions']

    payload = {
        "consent_given": True,
        "anonymous": False,
        "responses": [
            {"question_id": q_ids[0], "answer": "30"},
            {"question_id": q_ids[1], "answer": "Yes"}
        ]
    }

    # First submission
    res1 = await client.post(f"/api/v1/surveys/{survey_id}/responses", headers=auth_headers(token), json=payload)
    assert res1.status_code == 200

    # Second submission
    res2 = await client.post(f"/api/v1/surveys/{survey_id}/responses", headers=auth_headers(token), json=payload)
    assert res2.status_code == 400
    assert "already submitted" in res2.json()["detail"].lower()

@pytest.mark.asyncio
async def test_submit_closed_survey(client: AsyncClient, setup_test_db, auth_headers):
    """Test failed submission due to closed survey."""
    seeded = await seed_surveys()
    _, token = await create_user(client, "submit6@example.com")
    
    survey_id = seeded['surveys'][2] # closed survey

    payload = {
        "consent_given": True,
        "anonymous": False,
        "responses": []
    }

    res = await client.post(f"/api/v1/surveys/{survey_id}/responses", headers=auth_headers(token), json=payload)
    assert res.status_code == 400
    assert "no longer active" in res.json()["detail"].lower()

@pytest.mark.asyncio
async def test_submit_anonymous(client: AsyncClient, setup_test_db, auth_headers):
    """Test successful anonymous submission and duplicate bypass."""
    seeded = await seed_surveys()
    _, token = await create_user(client, "submit7@example.com")
    
    survey_id = seeded['surveys'][0]
    q_ids = seeded['questions']

    payload = {
        "consent_given": True,
        "anonymous": True,
        "responses": [
            {"question_id": q_ids[0], "answer": "30"},
            {"question_id": q_ids[1], "answer": "Yes"}
        ]
    }

    res = await client.post(f"/api/v1/surveys/{survey_id}/responses", headers=auth_headers(token), json=payload)
    assert res.status_code == 200

@pytest.mark.asyncio
async def test_submit_invalid_answer_type(client: AsyncClient, setup_test_db, auth_headers):
    """Test failed submission due to invalid answer type for yes_no question."""
    seeded = await seed_surveys()
    _, token = await create_user(client, "submit8@example.com")
    
    survey_id = seeded['surveys'][0]
    q_ids = seeded['questions']

    payload = {
        "consent_given": True,
        "anonymous": False,
        "responses": [
            {"question_id": q_ids[0], "answer": "30"},
            {"question_id": q_ids[1], "answer": "Maybe"} # Invalid yes_no answer
        ]
    }

    res = await client.post(f"/api/v1/surveys/{survey_id}/responses", headers=auth_headers(token), json=payload)
    assert res.status_code == 400
    assert "requires a yes/no answer" in res.json()["detail"].lower()

@pytest.mark.asyncio
async def test_submit_expired_survey(client: AsyncClient, setup_test_db, auth_headers):
    """Test failed submission due to expired closing date."""
    seeded = await seed_surveys()
    _, token = await create_user(client, "submit9@example.com")
    
    survey_id = seeded['surveys'][3] # expired survey

    payload = {
        "consent_given": True,
        "anonymous": False,
        "responses": []
    }

    res = await client.post(f"/api/v1/surveys/{survey_id}/responses", headers=auth_headers(token), json=payload)
    assert res.status_code == 400
    assert "already closed" in res.json()["detail"].lower()


# ──────────────────────────────────────────────────────────────────────────────
# 4. Completed Surveys
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_completed_surveys(client: AsyncClient, setup_test_db, auth_headers):
    """Test listing surveys the user has completed."""
    seeded = await seed_surveys()
    _, token = await create_user(client, "comp1@example.com")
    
    survey_id = seeded['surveys'][0]
    q_ids = seeded['questions']

    # Submit a response first
    payload = {
        "consent_given": True,
        "anonymous": False,
        "responses": [
            {"question_id": q_ids[0], "answer": "30"},
            {"question_id": q_ids[1], "answer": "Yes"}
        ]
    }
    await client.post(f"/api/v1/surveys/{survey_id}/responses", headers=auth_headers(token), json=payload)

    # List completed
    res = await client.get("/api/v1/surveys/completed", headers=auth_headers(token))
    assert res.status_code == 200
    data = res.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["survey_id"] == survey_id
    assert data["data"][0]["title"] == "Patient Experience Survey"

@pytest.mark.asyncio
async def test_get_completion_details_success(client: AsyncClient, setup_test_db, auth_headers):
    """Test retrieving details of a specific completion."""
    seeded = await seed_surveys()
    _, token = await create_user(client, "comp2@example.com")
    
    survey_id = seeded['surveys'][0]
    q_ids = seeded['questions']

    # Submit
    payload = {
        "consent_given": True,
        "anonymous": False,
        "responses": [
            {"question_id": q_ids[0], "answer": "30"},
            {"question_id": q_ids[1], "answer": "Yes"}
        ]
    }
    sub_res = await client.post(f"/api/v1/surveys/{survey_id}/responses", headers=auth_headers(token), json=payload)
    completion_id = sub_res.json()["completion_id"]

    # Get details
    res = await client.get(f"/api/v1/surveys/completed/{completion_id}", headers=auth_headers(token))
    assert res.status_code == 200
    data = res.json()
    assert data["completion_id"] == completion_id
    assert data["survey_id"] == survey_id
    assert len(data["responses"]) == 2
    assert data["responses"][0]["question_text"] == "How old are you?"
    assert data["responses"][0]["answer"] == "30"

@pytest.mark.asyncio
async def test_get_completion_details_not_found(client: AsyncClient, setup_test_db, auth_headers):
    """Test 404 for invalid completion ID or unauthorized access."""
    _, token = await create_user(client, "comp3@example.com")
    
    res = await client.get(f"/api/v1/surveys/completed/{uuid.uuid4()}", headers=auth_headers(token))
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_get_completion_details_unauthorized(client: AsyncClient, setup_test_db, auth_headers):
    """Test that a user cannot see someone else's completion."""
    seeded = await seed_surveys()
    _, token1 = await create_user(client, "user1@example.com")
    _, token2 = await create_user(client, "user2@example.com")
    
    survey_id = seeded['surveys'][0]
    q_ids = seeded['questions']

    # User 1 submits
    payload = {
        "consent_given": True,
        "anonymous": False,
        "responses": [{"question_id": q_ids[0], "answer": "30"}, {"question_id": q_ids[1], "answer": "Yes"}]
    }
    sub_res = await client.post(f"/api/v1/surveys/{survey_id}/responses", headers=auth_headers(token1), json=payload)
    completion_id = sub_res.json()["completion_id"]

    # User 2 tries to access
    res = await client.get(f"/api/v1/surveys/completed/{completion_id}", headers=auth_headers(token2))
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_get_completion_details_anonymous(client: AsyncClient, setup_test_db, auth_headers):
    """Test that anonymous completions cannot be retrieved by user."""
    seeded = await seed_surveys()
    _, token = await create_user(client, "anon@example.com")
    
    survey_id = seeded['surveys'][0]
    q_ids = seeded['questions']

    # Submit anonymously
    payload = {
        "consent_given": True,
        "anonymous": True,
        "responses": [{"question_id": q_ids[0], "answer": "30"}, {"question_id": q_ids[1], "answer": "Yes"}]
    }
    sub_res = await client.post(f"/api/v1/surveys/{survey_id}/responses", headers=auth_headers(token), json=payload)
    completion_id = sub_res.json()["completion_id"]

    # Try to access
    res = await client.get(f"/api/v1/surveys/completed/{completion_id}", headers=auth_headers(token))
    assert res.status_code == 404
