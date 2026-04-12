import pytest
import uuid
from httpx import AsyncClient
from app.db.postgres import PostgresDB
from app.main import app
from app.services.email import EmailService

# ----------------------------------------------------------------------
# Mocks & Helpers
# ----------------------------------------------------------------------
class MockEmailService:
    async def send_trial_interest_notification(self, *args, **kwargs):
        return True
    async def send_interest_confirmation(self, *args, **kwargs):
        return True

@pytest.fixture
def mock_email_service():
    app.dependency_overrides[EmailService] = lambda: MockEmailService()
    yield
    app.dependency_overrides = {}

async def create_user(client, email="test@example.com"):
    pwd = "StrongPassword123!"
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": pwd,
        "first_name": "Test",
        "last_name": "User",
        "user_type": "patient"
    })
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    return login_res.json()["access_token"]

async def seed_trials():
    pool = PostgresDB.get_pool()
    trial_id_1 = str(uuid.uuid4())
    trial_id_2 = str(uuid.uuid4())
    
    async with pool.acquire() as conn:
        # Trial 1
        await conn.execute("""
            INSERT INTO clinical_trials (
                trial_id, title, disease_area, phase, status, 
                sponsor, countries, summary, enrollment
            ) VALUES (
                $1, 'Safety Study of X', 'HIV', 'Phase 1', 'Recruiting',
                'Pharma Inc', '["Kenya", "Uganda"]', 'Summary 1', 100
            )
        """, trial_id_1)
        
        # Trial 2
        await conn.execute("""
            INSERT INTO clinical_trials (
                trial_id, title, disease_area, phase, status, 
                sponsor, countries, summary, enrollment
            ) VALUES (
                $1, 'Efficacy Study of Y', 'Malaria', 'Phase 3', 'Completed',
                'Health Org', '["Kenya"]', 'Summary 2', 500
            )
        """, trial_id_2)
        
        # Site for Trial 1
        await conn.execute("""
            INSERT INTO trial_sites (
                site_id, trial_id, site_name, country, city, is_recruiting
            ) VALUES (
                $1, $2, 'Nairobi Hospital', 'Kenya', 'Nairobi', TRUE
            )
        """, str(uuid.uuid4()), trial_id_1)
        
    return [trial_id_1, trial_id_2]

# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_search_trials(client: AsyncClient, setup_test_db):
    ids = await seed_trials()
    
    # 1. No filter
    res = await client.get("/api/v1/trials")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    
    # 2. Filter by Keyword
    res = await client.get("/api/v1/trials?keyword=Safety")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Safety Study of X"
    
    # 3. Filter by Phase (List)
    res = await client.get("/api/v1/trials", params={"phases": ["Phase 3"]})
    assert res.status_code == 200
    assert res.json()["total"] == 1
    assert res.json()["items"][0]["phase"] == "Phase 3"
    
    # 4. Filter by Status (List)
    res = await client.get("/api/v1/trials", params={"statuses": ["Recruiting"]})
    assert res.json()["total"] == 1
    
    # 5. Invalid Filter (should return nothing)
    res = await client.get("/api/v1/trials?disease_areas=Cancer")
    assert res.json()["total"] == 0

@pytest.mark.asyncio
async def test_get_trial_detail(client: AsyncClient, setup_test_db):
    ids = await seed_trials()
    trial_id = ids[0]
    
    # 1. Valid ID
    res = await client.get(f"/api/v1/trials/{trial_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["trial_id"] == trial_id
    assert data["sites"][0]["city"] == "Nairobi"
    assert data["is_saved"] is False  # Anonymous
    
    # 2. Invalid ID
    random_id = str(uuid.uuid4())
    res = await client.get(f"/api/v1/trials/{random_id}")
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_save_and_saved_trials(client: AsyncClient, setup_test_db, auth_headers):
    ids = await seed_trials()
    trial_id = ids[0]
    token = await create_user(client)
    headers = auth_headers(token)
    
    # 1. Save Trial
    res = await client.post(f"/api/v1/trials/{trial_id}/save", headers=headers, json={"notes": "My note"})
    assert res.status_code == 201
    assert res.json()["message"] == "Trial saved successfully"
    
    # 2. Duplicate Save
    res = await client.post(f"/api/v1/trials/{trial_id}/save", headers=headers, json={})
    assert res.status_code == 409
    
    # 3. Get Saved Trials
    res = await client.get("/api/v1/users/me/saved-trials", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["trial_id"] == trial_id
    
    # 4. Detail View Authenticated (is_saved check)
    res = await client.get(f"/api/v1/trials/{trial_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_saved"] is True
    
    # 5. Unsave
    res = await client.delete(f"/api/v1/trials/{trial_id}/save", headers=headers)
    assert res.status_code == 200
    
    # 6. Verify Unsave
    res = await client.get("/api/v1/users/me/saved-trials", headers=headers)
    assert len(res.json()) == 0

@pytest.mark.asyncio
async def test_alerts(client: AsyncClient, setup_test_db, auth_headers):
    token = await create_user(client)
    headers = auth_headers(token)
    
    # 1. Create Alert
    payload = {
        "disease_area": "HIV",
        "alert_frequency": "weekly"
    }
    res = await client.post("/api/v1/alerts/trials", json=payload, headers=headers)
    assert res.status_code == 201
    alert_id = res.json()["alert_id"]
    
    # 2. List Alerts
    res = await client.get("/api/v1/alerts/trials", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["alert_id"] == alert_id
    
    # 3. Patch Alert
    res = await client.patch(f"/api/v1/alerts/trials/{alert_id}", json={"alert_frequency": "daily"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["alert_frequency"] == "daily"
    
    # 4. Delete Alert
    res = await client.delete(f"/api/v1/alerts/trials/{alert_id}", headers=headers)
    assert res.status_code == 204
    
    # 5. Verify Delete
    res = await client.get("/api/v1/alerts/trials", headers=headers)
    assert len(res.json()) == 0

@pytest.mark.asyncio
async def test_express_interest(client: AsyncClient, setup_test_db, auth_headers, mock_email_service):
    ids = await seed_trials()
    trial_id = ids[0]
    token = await create_user(client)
    headers = auth_headers(token)
    
    payload = {"message": "I am interested"}
    res = await client.post(f"/api/v1/trials/{trial_id}/interest", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["trial_id"] == trial_id
