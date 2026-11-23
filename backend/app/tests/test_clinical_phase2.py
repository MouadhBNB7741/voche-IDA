import json
import uuid

import pytest

from app.db.postgres import PostgresDB
from app.services import eligibility_service
from app.services.email import EmailService

RULES = {
    "min_age": 18, "max_age": 70, "gender": "female", "conditions": ["Breast Cancer"],
    "inclusion_list": ["Confirmed diagnosis"], "exclusion_list": ["Chemotherapy in the last 30 days"],
}


# ---------------------------------------------------------------- screener logic

def test_screen_all_criteria_met_is_eligible():
    out = eligibility_service.screen(RULES, {
        "age": 45, "gender": "female", "conditions": ["breast cancer"],
        "inclusion_answers": {"Confirmed diagnosis": True},
        "exclusion_answers": {"Chemotherapy in the last 30 days": False},
    })
    assert out["result"] == "eligible" and out["score"] == 100
    assert all(c["status"] == "met" for c in out["breakdown"])


def test_screen_one_failure_is_not_eligible():
    out = eligibility_service.screen(RULES, {
        "age": 75, "gender": "female", "conditions": ["Breast Cancer"],
        "inclusion_answers": {"Confirmed diagnosis": True},
        "exclusion_answers": {"Chemotherapy in the last 30 days": True},
    })
    assert out["result"] == "not_eligible"
    failed = {c["criterion"] for c in out["breakdown"] if c["status"] == "not_met"}
    assert failed == {"Maximum age", "Chemotherapy in the last 30 days"}


def test_screen_unanswered_is_possibly_eligible():
    out = eligibility_service.screen(RULES, {"age": 30})
    assert out["result"] == "possibly_eligible"
    assert out["score"] == 33  # 2 of 6 checks met (both age limits)


def test_screen_condition_matches_partial_names_and_no_rules_means_eligible():
    assert eligibility_service.screen({"conditions": ["Type 2 Diabetes"]}, {"conditions": ["diabetes"]})["result"] == "eligible"
    assert eligibility_service.screen({"conditions": ["Malaria"]}, {"conditions": ["HIV"]})["result"] == "not_eligible"
    assert eligibility_service.screen({}, {}) == {"result": "eligible", "score": 100, "breakdown": []}


# ---------------------------------------------------------------- helpers

async def user(client, email, user_type="patient", verified=False, condition=None, country=None):
    pwd = "StrongPassword123!"
    reg_type = "patient" if user_type == "admin" else user_type
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": pwd, "first_name": "T", "last_name": email.split("@")[0], "user_type": reg_type,
    })
    async with PostgresDB.get_pool().acquire() as conn:
        uid = await conn.fetchval(
            "UPDATE users SET user_type = $2, is_verified = $3, country = $4 WHERE email = $1 RETURNING id",
            email, user_type, verified, country,
        )
        if condition:
            await conn.execute("UPDATE user_profiles SET condition = $2 WHERE user_id = $1", uid, condition)
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}, uid


async def trial(title, status="Recruiting", disease="Malaria", countries=("Kenya",), rules=None):
    async with PostgresDB.get_pool().acquire() as conn:
        return str(await conn.fetchval(
            """
            INSERT INTO clinical_trials (title, disease_area, phase, status, sponsor, countries, eligibility_rules)
            VALUES ($1, $2, 'Phase 2', $3, 'Test Sponsor', $4::jsonb, $5::jsonb) RETURNING trial_id
            """,
            title, disease, status, json.dumps(list(countries)), json.dumps(rules or {}),
        ))


@pytest.fixture
def sent_emails(monkeypatch):
    sent = []

    async def fake_send(email, doctor_name, trial_title, trial_id, has_account):
        sent.append({"email": email, "has_account": has_account})
    monkeypatch.setattr(EmailService, "send_trial_referral", staticmethod(fake_send))
    return sent


# ---------------------------------------------------------------- search & drafts

async def test_drafts_hidden_from_public_but_visible_to_admin(client):
    draft_id = await trial("Hidden Draft Trial", status="Draft")
    live_id = await trial("Visible Trial")

    public = (await client.get("/api/v1/trials")).json()
    ids = [t["trial_id"] for t in public["items"]]
    assert live_id in ids and draft_id not in ids
    assert public["total"] == len(public["items"])  # count uses the same filters as the list
    assert (await client.get(f"/api/v1/trials/{draft_id}")).status_code == 404

    admin, _ = await user(client, "admin_drafts@example.com", "admin")
    ids = [t["trial_id"] for t in (await client.get("/api/v1/trials", headers=admin)).json()["items"]]
    assert draft_id in ids
    assert (await client.get(f"/api/v1/trials/{draft_id}", headers=admin)).status_code == 200


async def test_eligible_for_me_matches_condition_and_country(client):
    match_id = await trial("Malaria in Kenya", disease="Malaria", countries=("Kenya",))
    await trial("Malaria in Peru", disease="Malaria", countries=("Peru",))
    await trial("Diabetes in Kenya", disease="Diabetes", countries=("Kenya",))

    headers, _ = await user(client, "eligible_me@example.com", condition="Malaria", country="Kenya")
    res = (await client.get("/api/v1/trials", params={"eligible_for_me": "true"}, headers=headers)).json()
    assert [t["trial_id"] for t in res["items"]] == [match_id]
    assert res["total"] == 1

    assert (await client.get("/api/v1/trials", params={"eligible_for_me": "true"})).status_code == 401
    empty, _ = await user(client, "empty_profile@example.com")
    assert (await client.get("/api/v1/trials", params={"eligible_for_me": "true"}, headers=empty)).status_code == 400


# ---------------------------------------------------------------- lifecycle

async def test_status_transitions_are_enforced_and_audited(client):
    trial_id = await trial("Lifecycle Trial", status="Draft")
    admin, admin_id = await user(client, "admin_life@example.com", "admin")
    patient, _ = await user(client, "patient_life@example.com")
    url = f"/api/v1/trials/{trial_id}/status"

    assert (await client.patch(url, json={"status": "Recruiting"}, headers=patient)).status_code == 403
    res = await client.patch(url, json={"status": "Recruiting"}, headers=admin)
    assert res.status_code == 200 and res.json() == {"trial_id": trial_id, "previous_status": "Draft", "status": "Recruiting"}

    assert (await client.patch(url, json={"status": "Draft"}, headers=admin)).status_code == 409
    assert (await client.patch(url, json={"status": "Completed"}, headers=admin)).status_code == 200
    assert (await client.patch(url, json={"status": "Recruiting"}, headers=admin)).status_code == 409  # final
    assert (await client.patch(url, json={"status": "Paused"}, headers=admin)).status_code == 422

    async with PostgresDB.get_pool().acquire() as conn:
        rows = await conn.fetch(
            "SELECT metadata FROM audit_logs WHERE action = 'trial_status_changed' AND user_id = $1 ORDER BY created_at",
            admin_id,
        )
    changes = [json.loads(r["metadata"]) if isinstance(r["metadata"], str) else r["metadata"] for r in rows]
    assert changes == [{"from": "Draft", "to": "Recruiting"}, {"from": "Recruiting", "to": "Completed"}]


# ---------------------------------------------------------------- screener endpoint

async def test_screen_endpoint(client):
    trial_id = await trial("Screen Trial", rules=RULES)
    res = await client.post(f"/api/v1/trials/{trial_id}/screen", json={"age": 30, "gender": "female"})
    assert res.status_code == 200
    body = res.json()
    assert body["result"] == "possibly_eligible" and "pre-screen" in body["disclaimer"]

    draft_id = await trial("Draft Screen", status="Draft", rules=RULES)
    assert (await client.post(f"/api/v1/trials/{draft_id}/screen", json={})).status_code == 404
    assert (await client.post(f"/api/v1/trials/{trial_id}/screen", json={"age": -1})).status_code == 422


# ---------------------------------------------------------------- referrals

async def test_referral_flow_for_existing_patient(client, sent_emails):
    trial_id = await trial("Referral Trial")
    hcp, _ = await user(client, "doc_ok@example.com", "hcp", verified=True)
    unverified, _ = await user(client, "doc_new@example.com", "hcp", verified=False)
    patient, patient_id = await user(client, "pat_ref@example.com")
    other, _ = await user(client, "pat_other@example.com")
    body = {"patient_email": "Pat_Ref@example.com", "clinical_notes": "Meets age criteria"}

    assert (await client.post(f"/api/v1/trials/{trial_id}/refer", json=body, headers=unverified)).status_code == 403
    assert (await client.post(f"/api/v1/trials/{trial_id}/refer", json=body, headers=patient)).status_code == 403

    res = await client.post(f"/api/v1/trials/{trial_id}/refer", json=body, headers=hcp)
    assert res.status_code == 201, res.text
    ref = res.json()
    assert ref["status"] == "sent" and ref["patient_user_id"] == str(patient_id)
    assert sent_emails == [{"email": "pat_ref@example.com", "has_account": True}]
    async with PostgresDB.get_pool().acquire() as conn:
        note = await conn.fetchval("SELECT title FROM notifications WHERE user_id = $1", patient_id)
    assert note == "Your doctor referred you to a trial"

    received = (await client.get("/api/v1/referrals/received", headers=patient)).json()
    assert [r["id"] for r in received] == [ref["id"]] and received[0]["status"] == "viewed"
    assert (await client.get("/api/v1/referrals/received", headers=other)).json() == []

    respond = f"/api/v1/referrals/{ref['id']}/respond"
    assert (await client.patch(respond, json={"action": "accept"}, headers=other)).status_code == 404
    res = await client.patch(respond, json={"action": "accept"}, headers=patient)
    assert res.status_code == 200 and res.json()["status"] == "consent_pending"
    assert (await client.patch(respond, json={"action": "decline"}, headers=patient)).status_code == 409

    sent = (await client.get("/api/v1/referrals/sent", headers=hcp)).json()
    assert [(r["id"], r["status"]) for r in sent] == [(ref["id"], "consent_pending")]
    assert (await client.get("/api/v1/referrals/sent", headers=patient)).status_code == 403


async def test_referral_by_email_is_claimed_after_signup_and_closed_trials_refused(client, sent_emails):
    trial_id = await trial("Email Referral Trial")
    closed_id = await trial("Closed Trial", status="Completed")
    hcp, _ = await user(client, "doc_mail@example.com", "hcp", verified=True)

    body = {"patient_email": "future_patient@example.com"}
    assert (await client.post(f"/api/v1/trials/{closed_id}/refer", json=body, headers=hcp)).status_code == 409
    assert (await client.post(f"/api/v1/trials/{trial_id}/refer", json={"patient_email": "doc_mail@example.com"}, headers=hcp)).status_code == 400
    res = await client.post(f"/api/v1/trials/{trial_id}/refer", json=body, headers=hcp)
    assert res.status_code == 201 and res.json()["patient_user_id"] is None
    assert sent_emails[-1] == {"email": "future_patient@example.com", "has_account": False}

    patient, patient_id = await user(client, "future_patient@example.com")
    received = (await client.get("/api/v1/referrals/received", headers=patient)).json()
    assert len(received) == 1 and received[0]["patient_user_id"] == str(patient_id)
    res = await client.patch(f"/api/v1/referrals/{received[0]['id']}/respond", json={"action": "decline"}, headers=patient)
    assert res.json()["status"] == "declined"


async def test_referral_survives_email_failure(client, monkeypatch):
    async def broken(*args, **kwargs):
        raise Exception("SMTP down")
    monkeypatch.setattr(EmailService, "send_trial_referral", staticmethod(broken))
    trial_id = await trial("Mail Outage Trial")
    hcp, _ = await user(client, "doc_outage@example.com", "hcp", verified=True)
    res = await client.post(f"/api/v1/trials/{trial_id}/refer", json={"patient_email": "x@example.com"}, headers=hcp)
    assert res.status_code == 201


async def test_unverified_hcp_cannot_submit_observations(client):
    trial_id = await trial("Observation Trial")
    unverified, _ = await user(client, "doc_obs@example.com", "hcp", verified=False)
    res = await client.post("/api/v1/clinical-observations/", headers=unverified, json={
        "trial_id": trial_id, "summary": "Observed improvement in symptoms", "feedback_data": {}, "severity": "low",
    })
    assert res.status_code == 403


# ---------------------------------------------------------------- consent

async def test_consent_signs_once_after_accepting_and_enrolls(client, sent_emails):
    trial_id = await trial("Consent Trial")
    hcp, _ = await user(client, "doc_consent@example.com", "hcp", verified=True)
    patient, patient_id = await user(client, "pat_consent@example.com")
    other, _ = await user(client, "pat_consent_other@example.com")
    ref = (await client.post(f"/api/v1/trials/{trial_id}/refer",
                             json={"patient_email": "pat_consent@example.com"}, headers=hcp)).json()
    url = f"/api/v1/referrals/{ref['id']}/consent"

    form = (await client.get(url, headers=patient)).json()
    assert form["version"] == "v1" and "withdraw" in form["text"] and form["signed_at"] is None
    assert (await client.get(url, headers=other)).status_code == 404

    body = {"version": "v1", "signed_name": "Pat Consent", "agreed": True}
    assert (await client.post(url, json=body, headers=patient)).status_code == 409  # not accepted yet
    await client.patch(f"/api/v1/referrals/{ref['id']}/respond", json={"action": "accept"}, headers=patient)

    assert (await client.post(url, json={**body, "agreed": False}, headers=patient)).status_code == 422
    assert (await client.post(url, json={**body, "version": "v0"}, headers=patient)).status_code == 409
    assert (await client.post(url, json=body, headers=other)).status_code == 404
    res = await client.post(url, json=body, headers=patient)
    assert res.status_code == 200 and res.json()["status"] == "enrolled"
    assert (await client.post(url, json=body, headers=patient)).status_code == 409  # already signed

    signed = (await client.get(url, headers=patient)).json()
    assert signed["signed_name"] == "Pat Consent" and signed["signed_at"]
    async with PostgresDB.get_pool().acquire() as conn:
        row = await conn.fetchrow("SELECT user_id, consent_version, consent_text FROM trial_consents WHERE referral_id = $1",
                                  uuid.UUID(ref["id"]))
    assert row["user_id"] == patient_id and row["consent_version"] == "v1" and row["consent_text"] == form["text"]
    sent = (await client.get("/api/v1/referrals/sent", headers=hcp)).json()
    assert sent[0]["status"] == "enrolled"
