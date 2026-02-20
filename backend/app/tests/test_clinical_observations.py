import pytest
from httpx import AsyncClient
from app.db.postgres import PostgresDB

@pytest.mark.asyncio
async def test_clinical_observations_flow(client: AsyncClient, unique_email, auth_headers):
    # 1. Setup Data - Create Trial
    pool = PostgresDB.get_pool()
    async with pool.acquire() as conn:
        # Ensure we have a trial
        # phase enum ('Phase 1', etc) or text? Standardize.
        # schema.sql: clinical_trials.phase (VARCHAR)
        trial_id = await conn.fetchval("""
            INSERT INTO clinical_trials (title, status, phase, disease_area, sponsor) 
            VALUES ('Test Trial', 'Recruiting', 'Phase 1', 'Cardiology', 'Test Sponsor') 
            RETURNING trial_id
        """)
        trial_id = str(trial_id)
    
    # 2. Register Patient
    resp = await client.post("/api/v1/auth/register", json={
        "email": unique_email, "password": "password123", 
        "first_name": "Patient", "last_name": "User", "user_type": "patient"
    })
    assert resp.status_code == 201
    
    # Login Patient
    resp = await client.post("/api/v1/auth/login", json={"email": unique_email, "password": "password123"})
    token = resp.json()["access_token"]
    headers = auth_headers(token)
    
    # 3. Try to submit (Should Fail)
    payload = {
        "trial_id": trial_id,
        "summary": "Observation Attempt",
        "severity_level": "low"
    }
    resp = await client.post("/api/v1/clinical-observations/", json=payload, headers=headers)
    assert resp.status_code == 403
    
    # 4. Promote to HCP
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET user_type = 'hcp', is_verified = TRUE WHERE email = $1", unique_email)
        
    # 5. Submit Success
    resp = await client.post("/api/v1/clinical-observations/", json=payload, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["flagged"] is False
    
    # 6. Critical Observation (Flagged)
    payload["severity_level"] = "critical"
    resp = await client.post("/api/v1/clinical-observations/", json=payload, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["flagged"] is True
    
    # 7. List Observations (As HCP - Allowed)
    resp = await client.get(f"/api/v1/clinical-observations/trial/{trial_id}", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2
