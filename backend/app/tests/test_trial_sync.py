import json
from datetime import date

import pytest

from app.core.config import settings
from app.db.postgres import PostgresDB
from app.services import trial_sync_service as sync
from app.services.email import EmailService


def study(nct="NCT90000001", status="RECRUITING", phases=("PHASE2", "PHASE3"), condition="Malaria", country="Kenya"):
    """A ClinicalTrials.gov API v2 study record, trimmed to the fields we read."""
    return {"protocolSection": {
        "identificationModule": {"nctId": nct, "briefTitle": f"{condition} study {nct}"},
        "statusModule": {
            "overallStatus": status,
            "startDateStruct": {"date": "2025-03"},
            "completionDateStruct": {"date": "2027-12-31"},
        },
        "descriptionModule": {"briefSummary": "Tests a new treatment."},
        "conditionsModule": {"conditions": [condition, "Fever"]},
        "designModule": {"phases": list(phases), "enrollmentInfo": {"count": 300}},
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Health Institute"}},
        "eligibilityModule": {
            "eligibilityCriteria": "Inclusion: confirmed infection", "minimumAge": "18 Years",
            "maximumAge": "6 Months", "sex": "ALL",
        },
        "contactsLocationsModule": {"locations": [
            {"facility": "Nairobi Hospital", "city": "Nairobi", "country": country, "status": "RECRUITING"},
            {"facility": "No city here", "country": country},
        ]},
    }}


# ---------------------------------------------------------------- normalization

def test_normalize_maps_api_fields():
    t = sync.normalize(study())
    assert (t["nct_id"], t["status"], t["phase"], t["disease_area"]) == ("NCT90000001", "Recruiting", "Phase 3", "Malaria")
    assert t["start_date"] == date(2025, 3, 1) and t["estimated_completion"] == date(2027, 12, 31)
    assert t["eligibility_rules"] == {"min_age": 18, "max_age": 0, "gender": "all", "conditions": ["Malaria", "Fever"],
                                      "inclusion_list": [], "exclusion_list": []}
    assert t["countries"] == ["Kenya"] and [s["site_name"] for s in t["sites"]] == ["Nairobi Hospital"]
    assert t["metadata"]["source_url"].endswith("NCT90000001")


def test_normalize_skips_records_that_do_not_fit():
    assert sync.normalize(study(phases=("NA",))) is None          # observational, no phase
    assert sync.normalize(study(status="UNKNOWN")) is None
    assert sync.parse_age("N/A") is None and sync.parse_age(None) is None
    assert sync.parse_date("not a date") is None


# ---------------------------------------------------------------- sync runs

def fake_fetch(by_condition):
    async def fetch(condition):
        return by_condition.get(condition, [])
    return fetch


@pytest.fixture
def conditions(monkeypatch):
    monkeypatch.setattr(settings, "trial_sync_conditions", "Malaria, HIV")


@pytest.fixture
def emails(monkeypatch):
    sent = []

    async def fake(email, title, trial_id):
        sent.append(email)
    monkeypatch.setattr(EmailService, "send_trial_alert", staticmethod(fake))
    return sent


async def make_user(conn, email, user_type="patient", condition=None, interests=None):
    uid = await conn.fetchval(
        "INSERT INTO users (email, password_hash, user_type, display_name) VALUES ($1, 'x', $2, $1) RETURNING id",
        email, user_type,
    )
    await conn.execute(
        "INSERT INTO user_profiles (user_id, condition, interests) VALUES ($1, $2, $3::jsonb)",
        uid, condition, json.dumps(interests or []),
    )
    return uid


async def test_sync_inserts_updates_logs_and_notifies_once(client, conditions, emails):
    async with PostgresDB.get_pool().acquire() as conn:
        alert_user = await make_user(conn, "alert_user@example.com")
        await conn.execute(
            "INSERT INTO trial_alerts (user_id, disease_area, location, alert_frequency) VALUES ($1, 'malaria', 'Kenya', 'instant')",
            alert_user,
        )
        weekly_user = await make_user(conn, "weekly_user@example.com")
        await conn.execute("INSERT INTO trial_alerts (user_id, phase, alert_frequency) VALUES ($1, 'Phase 3', 'weekly')", weekly_user)
        profile_user = await make_user(conn, "profile_user@example.com", interests=["HIV"])
        both_user = await make_user(conn, "both_user@example.com", condition="Malaria")
        await conn.execute("INSERT INTO trial_alerts (user_id, disease_area) VALUES ($1, 'Malaria')", both_user)
        await make_user(conn, "unrelated@example.com", condition="Diabetes")

        fetch = fake_fetch({
            "Malaria": [study("NCT90000001"), study("NCT90000002", phases=("NA",))],
            "HIV": [study("NCT90000003", condition="HIV Infections", phases=("PHASE1",), country="Uganda")],
        })
        log = await sync.run_sync(conn, fetch)
        assert (log["status"], log["records_fetched"], log["records_inserted"], log["records_updated"]) == ("success", 3, 2, 0)

        notes = await conn.fetch(
            "SELECT u.email, n.type, n.link FROM notifications n JOIN users u ON u.id = n.user_id ORDER BY u.email, n.link"
        )
        malaria_id = await conn.fetchval("SELECT trial_id FROM clinical_trials WHERE nct_id = 'NCT90000001'")
        hiv_id = await conn.fetchval("SELECT trial_id FROM clinical_trials WHERE nct_id = 'NCT90000003'")
        got = {(n["email"], n["type"], n["link"]) for n in notes}
        assert got == {
            ("alert_user@example.com", "trial_alert", f"/trials/{malaria_id}"),
            ("weekly_user@example.com", "trial_alert", f"/trials/{malaria_id}"),   # Phase 3 alert
            ("both_user@example.com", "trial_alert", f"/trials/{malaria_id}"),     # alert wins over profile match
            ("profile_user@example.com", "trial_match", f"/trials/{hiv_id}"),
        }
        assert emails == ["alert_user@example.com"]  # only instant alerts are emailed
        sites = await conn.fetchval("SELECT count(*) FROM trial_sites WHERE trial_id = $1", malaria_id)
        assert sites == 1

        # Second run: same studies are updates, and nobody is notified again.
        log = await sync.run_sync(conn, fetch)
        assert (log["records_inserted"], log["records_updated"]) == (0, 2)
        assert await conn.fetchval("SELECT count(*) FROM notifications") == len(got)
        assert await conn.fetchval("SELECT count(*) FROM trial_sites WHERE trial_id = $1", malaria_id) == 1
        assert await conn.fetchval("SELECT count(*) FROM trial_sync_logs") == 2


async def test_failed_fetch_is_logged(client, conditions):
    async def broken(condition):
        raise RuntimeError("ClinicalTrials.gov unreachable")
    async with PostgresDB.get_pool().acquire() as conn:
        log = await sync.run_sync(conn, broken)
    assert log["status"] == "failed" and "unreachable" in log["error_details"]
    assert log["sync_completed_at"] is not None


async def test_scheduled_sync_is_off_by_default(client, monkeypatch):
    called = []

    async def spy(*args, **kwargs):
        called.append(1)
    monkeypatch.setattr(sync, "run_sync", spy)
    await sync.scheduled_sync()
    assert called == []


# ---------------------------------------------------------------- hooks & endpoints

async def login(client, email, user_type):
    pwd = "StrongPassword123!"
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": pwd, "first_name": "T", "last_name": "U", "user_type": "patient"})
    async with PostgresDB.get_pool().acquire() as conn:
        await conn.execute("UPDATE users SET user_type = $2 WHERE email = $1", email, user_type)
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def test_trial_becoming_recruiting_notifies_alerts(client, emails):
    admin = await login(client, "admin_sync@example.com", "admin")
    async with PostgresDB.get_pool().acquire() as conn:
        user = await make_user(conn, "watcher@example.com")
        trial_id = await conn.fetchval(
            "INSERT INTO clinical_trials (title, disease_area, phase, status, sponsor) "
            "VALUES ('TB Vaccine', 'Tuberculosis', 'Phase 2', 'Not yet recruiting', 'X') RETURNING trial_id"
        )
        await conn.execute("INSERT INTO trial_alerts (user_id, trial_id, alert_frequency) VALUES ($1, $2, 'instant')", user, trial_id)

    res = await client.patch(f"/api/v1/trials/{trial_id}/status", json={"status": "Recruiting"}, headers=admin)
    assert res.status_code == 200
    async with PostgresDB.get_pool().acquire() as conn:
        assert await conn.fetchval("SELECT type FROM notifications WHERE user_id = $1", user) == "trial_alert"
    assert emails == ["watcher@example.com"]


async def test_admin_sync_trigger_and_logs(client, conditions, monkeypatch):
    async def fetch(condition):
        return [study("NCT90000009")] if condition == "Malaria" else []
    monkeypatch.setattr(sync, "fetch_from_clinicaltrials_gov", fetch)

    admin = await login(client, "admin_trigger@example.com", "admin")
    patient = await login(client, "patient_trigger@example.com", "patient")
    assert (await client.post("/api/v1/trials/sync", headers=patient)).status_code == 403
    assert (await client.get("/api/v1/trials/sync/logs", headers=patient)).status_code == 403

    res = await client.post("/api/v1/trials/sync", headers=admin)
    assert res.status_code == 202 and res.json()["status"] == "running"
    logs = (await client.get("/api/v1/trials/sync/logs", headers=admin)).json()
    assert logs[0]["id"] == res.json()["sync_id"]
    assert (logs[0]["status"], logs[0]["records_inserted"]) == ("success", 1)  # background task ran after the response


async def test_each_user_hears_about_a_trial_once(client):
    async with PostgresDB.get_pool().acquire() as conn:
        user = await make_user(conn, "two_alerts@example.com")
        await conn.execute("INSERT INTO trial_alerts (user_id, disease_area) VALUES ($1, 'HIV'), ($1, NULL)", user)
        trial_id = await conn.fetchval(
            "INSERT INTO clinical_trials (title, disease_area, phase, status, sponsor) "
            "VALUES ('HIV PrEP', 'HIV', 'Phase 3', 'Recruiting', 'X') RETURNING trial_id"
        )
        assert await sync.notify_matches(conn, trial_id) == 1
        assert await sync.notify_matches(conn, trial_id) == 0
        assert await conn.fetchval("SELECT count(*) FROM notifications WHERE user_id = $1", user) == 1
