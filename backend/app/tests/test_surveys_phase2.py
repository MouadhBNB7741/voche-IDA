import json
import uuid
from datetime import date, datetime, timedelta, timezone

from app.core.cron_manager import survey_reminders
from app.db.postgres import PostgresDB
from app.models.survey_model import answer_error, answer_path

Q1, Q2, Q3 = "q1", "q2", "q3"
QUESTIONS = [
    {"question_id": Q1, "branching_rules": [
        {"condition": "equals", "value": "no", "next_question_id": Q2},
        {"condition": "equals", "value": "yes", "next_question_id": Q3},
    ]},
    {"question_id": Q2, "branching_rules": []},
    {"question_id": Q3, "branching_rules": []},
]


# ---------------------------------------------------------------- pure logic

def test_answer_path_follows_branching_rules():
    assert answer_path(QUESTIONS, {Q1: "yes"}) == [Q1, Q3]
    assert answer_path(QUESTIONS, {Q1: "No"}) == [Q1, Q2, Q3]
    assert answer_path(QUESTIONS, {Q1: True}) == [Q1, Q3]           # booleans count as yes/no
    assert answer_path(QUESTIONS, {}) == [Q1, Q2, Q3]               # unanswered: no jump
    looping = [{"question_id": "a", "branching_rules": []},
               {"question_id": "b", "branching_rules": [{"condition": "equals", "value": "x", "next_question_id": "a"}]}]
    assert answer_path(looping, {"b": "x"}) == ["a", "b"]           # a jump backwards ends the path


def test_answer_error_per_type():
    assert answer_error("number", None, "12.5") is None
    assert answer_error("number", None, "twelve") and answer_error("scale", None, True)
    assert answer_error("date", None, "2026-11-20") is None and answer_error("date", None, "20/11/2026")
    assert answer_error("single_choice", ["A", "B"], "A") is None
    assert answer_error("single_choice", ["A", "B"], ["A", "B"]) and answer_error("single_choice", ["A"], "C")
    assert answer_error("multiple_choice", ["A", "B"], ["A", "B"]) is None and answer_error("multiple_choice", ["A"], ["Z"])


# ---------------------------------------------------------------- helpers

async def account(client, email, user_type="patient", verified=False):
    pwd = "StrongPassword123!"
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": pwd, "first_name": "T", "last_name": "U", "user_type": "patient"})
    async with PostgresDB.get_pool().acquire() as conn:
        uid = await conn.fetchval("UPDATE users SET user_type = $2, is_verified = $3 WHERE email = $1 RETURNING id",
                                  email, user_type, verified)
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}, uid


async def branching_survey(status="active"):
    """Q1 yes/no: 'no' -> Q2 (what went wrong, required), 'yes' -> Q3 (score). Q4 optional single choice."""
    sid = uuid.uuid4()
    q = [uuid.uuid4() for _ in range(4)]
    async with PostgresDB.get_pool().acquire() as conn:
        await conn.execute("INSERT INTO surveys (survey_id, title, description, status) VALUES ($1, 'Care survey', 'd', $2)", sid, status)
        rows = [
            (q[0], "Happy with your care?", "yes_no", 1, True, None),
            (q[1], "What went wrong?", "open_text", 2, True, None),
            (q[2], "Score your visit", "scale", 3, True, None),
            (q[3], "Clinic", "single_choice", 4, False, json.dumps(["North", "South"])),
        ]
        for qid, text, qtype, pos, req, opts in rows:
            await conn.execute(
                "INSERT INTO survey_questions (question_id, survey_id, question_text, question_type, order_position, required, options) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7)", qid, sid, text, qtype, pos, req, opts)
        await conn.execute("UPDATE survey_questions SET branching_rules = $2::jsonb WHERE question_id = $1", q[0], json.dumps([
            {"condition": "equals", "value": "no", "next_question_id": str(q[1])},
            {"condition": "equals", "value": "yes", "next_question_id": str(q[2])},
        ]))
    return str(sid), [str(x) for x in q]


def answers(**by_id):
    return {"consent_given": True, "anonymous": False,
            "responses": [{"question_id": k, "answer": v} for k, v in by_id.items()]}


# ---------------------------------------------------------------- branching submit

async def test_required_questions_follow_the_branch_taken(client):
    sid, q = await branching_survey()
    yes_user, _ = await account(client, "branch_yes@example.com")
    no_user, _ = await account(client, "branch_no@example.com")
    url = f"/api/v1/surveys/{sid}/responses"

    # "yes" skips the required Q2; an answer sent for Q2 anyway is not stored
    res = await client.post(url, json=answers(**{q[0]: "yes", q[1]: "stale answer", q[2]: 4}), headers=yes_user)
    assert res.status_code == 200, res.text
    async with PostgresDB.get_pool().acquire() as conn:
        stored = await conn.fetchval("SELECT count(*) FROM survey_responses WHERE question_id = $1", uuid.UUID(q[1]))
    assert stored == 0

    # "no" makes Q2 required, and an empty answer does not count
    assert (await client.post(url, json=answers(**{q[0]: "no", q[2]: 2}), headers=no_user)).status_code == 400
    assert (await client.post(url, json=answers(**{q[0]: "no", q[1]: "  ", q[2]: 2}), headers=no_user)).status_code == 400
    assert (await client.post(url, json=answers(**{q[0]: "no", q[1]: "Long wait", q[2]: 2, q[3]: "East"}), headers=no_user)).status_code == 400
    assert (await client.post(url, json=answers(**{q[0]: "no", q[1]: "Long wait", q[2]: 2, q[3]: "North"}), headers=no_user)).status_code == 200


async def test_questions_expose_branching_rules(client):
    sid, q = await branching_survey()
    body = (await client.get(f"/api/v1/surveys/{sid}")).json()
    assert [r["next_question_id"] for r in body["questions"][0]["branching_rules"]] == [q[1], q[2]]
    assert body["draft_answers"] is None


# ---------------------------------------------------------------- drafts

async def test_draft_save_resume_and_clear_on_submit(client):
    sid, q = await branching_survey()
    user, uid = await account(client, "drafter@example.com")
    draft_url = f"/api/v1/surveys/{sid}/draft"

    res = await client.patch(draft_url, json={"answers": {q[0]: "no"}}, headers=user)
    assert res.status_code == 200 and res.json()["status"] == "in_progress"
    await client.patch(draft_url, json={"answers": {q[0]: "no", q[1]: "Long wait"}}, headers=user)
    resumed = (await client.get(f"/api/v1/surveys/{sid}", headers=user)).json()
    assert resumed["draft_answers"] == {q[0]: "no", q[1]: "Long wait"}

    assert (await client.patch(draft_url, json={"answers": {str(uuid.uuid4()): 1}}, headers=user)).status_code == 400
    assert (await client.patch(draft_url, json={"answers": {}})).status_code in (401, 403)

    assert (await client.post(f"/api/v1/surveys/{sid}/responses",
                              json=answers(**{q[0]: "no", q[1]: "Long wait", q[2]: 3}), headers=user)).status_code == 200
    async with PostgresDB.get_pool().acquire() as conn:
        row = await conn.fetchrow("SELECT status, draft_answers, completed_at FROM survey_assignments WHERE patient_user_id = $1", uid)
    assert row["status"] == "completed" and json.loads(row["draft_answers"]) == {} and row["completed_at"]
    assert (await client.patch(draft_url, json={"answers": {q[0]: "yes"}}, headers=user)).status_code == 409


# ---------------------------------------------------------------- assignments & reminders

async def test_assign_permissions_results_and_notifications(client):
    sid, _ = await branching_survey()
    closed_sid, _ = await branching_survey(status="closed")
    doctor, _ = await account(client, "assigner@example.com", "hcp", verified=True)
    unverified, _ = await account(client, "assigner_new@example.com", "hcp", verified=False)
    patient, patient_id = await account(client, "assignee@example.com")
    url = f"/api/v1/surveys/{sid}/assign"
    body = {"patient_emails": ["Assignee@example.com", "nobody@example.com", "assigner@example.com"],
            "due_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()}

    assert (await client.post(url, json=body, headers=patient)).status_code == 403
    assert (await client.post(url, json=body, headers=unverified)).status_code == 403

    res = await client.post(url, json=body, headers=doctor)
    assert res.status_code == 200, res.text
    assert res.json() == {"assigned": ["assignee@example.com"], "already_assigned": [],
                          "not_found": ["nobody@example.com", "assigner@example.com"]}  # HCPs are not patients
    again = (await client.post(url, json=body, headers=doctor)).json()
    assert again["assigned"] == [] and again["already_assigned"] == ["assignee@example.com"]

    async with PostgresDB.get_pool().acquire() as conn:
        assert await conn.fetchval("SELECT count(*) FROM notifications WHERE user_id = $1 AND type = 'survey_available'", patient_id) == 1

    past = {**body, "due_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}
    assert (await client.post(url, json=past, headers=doctor)).status_code == 400
    assert (await client.post(f"/api/v1/surveys/{closed_sid}/assign", json=body, headers=doctor)).status_code == 400


async def test_reminders_once_and_expiry(client):
    sid, _ = await branching_survey()
    _, soon_id = await account(client, "due_soon@example.com")
    _, late_id = await account(client, "overdue@example.com")
    _, later_id = await account(client, "due_later@example.com")
    async with PostgresDB.get_pool().acquire() as conn:
        for uid, due in [(soon_id, "1 day"), (late_id, "-1 day"), (later_id, "10 days")]:
            await conn.execute(
                f"INSERT INTO survey_assignments (survey_id, patient_user_id, due_date) VALUES ($1, $2, NOW() + INTERVAL '{due}')",
                uuid.UUID(sid), uid)

    await survey_reminders()
    await survey_reminders()  # running twice must not remind twice

    async with PostgresDB.get_pool().acquire() as conn:
        reminded = await conn.fetch("SELECT user_id FROM notifications WHERE title = 'Survey due soon'")
        statuses = dict(await conn.fetch("SELECT patient_user_id, status FROM survey_assignments"))
    assert [r["user_id"] for r in reminded] == [soon_id]
    assert statuses == {soon_id: "pending", late_id: "expired", later_id: "pending"}


# ---------------------------------------------------------------- analytics

async def test_analytics(client):
    sid, q = await branching_survey()
    admin, _ = await account(client, "survey_admin@example.com", "admin")
    patient, _ = await account(client, "analytics_patient@example.com")
    _, assigned_only = await account(client, "assigned_only@example.com")
    respondents = []
    for i, (happy, score, clinic) in enumerate([("yes", 5, "North"), ("yes", 3, None), ("no", 1, "North")]):
        headers, _ = await account(client, f"respondent{i}@example.com")
        respondents.append(headers)
        await client.patch(f"/api/v1/surveys/{sid}/draft", json={"answers": {}}, headers=headers)  # creates an assignment
        resp = {q[0]: happy, q[2]: score, **({q[1]: "Slow"} if happy == "no" else {}), **({q[3]: clinic} if clinic else {})}
        assert (await client.post(f"/api/v1/surveys/{sid}/responses", json=answers(**resp), headers=headers)).status_code == 200
    async with PostgresDB.get_pool().acquire() as conn:
        await conn.execute("INSERT INTO survey_assignments (survey_id, patient_user_id) VALUES ($1, $2)", uuid.UUID(sid), assigned_only)

    assert (await client.get(f"/api/v1/surveys/{sid}/analytics", headers=patient)).status_code == 403
    data = (await client.get(f"/api/v1/surveys/{sid}/analytics", headers=admin)).json()
    assert (data["total_responses"], data["assigned"], data["completed_assignments"], data["completion_rate"]) == (3, 4, 3, 75.0)
    assert data["avg_completion_hours"] is not None
    by_text = {x["question_text"]: x for x in data["questions"]}
    assert by_text["Happy with your care?"]["distribution"] == {"yes": 2, "no": 1}
    assert (by_text["Score your visit"]["average"], by_text["Score your visit"]["min"], by_text["Score your visit"]["max"]) == (3.0, 1.0, 5.0)
    assert by_text["Clinic"]["distribution"] == {"North": 2, "South": 0}
    wrong = by_text["What went wrong?"]
    assert wrong["answered"] == 1 and wrong["distribution"] is None  # free text is counted, not exposed
    assert (await client.get(f"/api/v1/surveys/{uuid.uuid4()}/analytics", headers=admin)).status_code == 404


# ---------------------------------------------------------------- builder & hub

def builder_body(**overrides):
    body = {
        "title": "Side effects check", "description": "Two-minute check-in", "status": "draft",
        "questions": [
            {"text": "Any side effects?", "type": "yes_no", "required": True,
             "branching": [{"value": "no", "next": 2}]},
            {"text": "Which ones?", "type": "multiple_choice", "required": True, "options": ["Fever", "Nausea"]},
            {"text": "Rate your week", "type": "scale", "required": True},
        ],
    }
    return {**body, **overrides}


async def test_create_publish_take_and_close_a_survey(client):
    admin, _ = await account(client, "builder_admin@example.com", "admin")
    patient, _ = await account(client, "builder_patient@example.com")

    assert (await client.post("/api/v1/surveys/", json=builder_body(), headers=patient)).status_code == 403
    res = await client.post("/api/v1/surveys/", json=builder_body(), headers=admin)
    assert res.status_code == 201, res.text
    sid = res.json()["survey_id"]

    managed = (await client.get("/api/v1/surveys/manage", headers=admin)).json()
    mine = next(m for m in managed if m["survey_id"] == sid)
    assert (mine["status"], mine["question_count"], mine["responses"]) == ("draft", 3, 0)
    assert (await client.get("/api/v1/surveys/manage", headers=patient)).status_code == 403

    detail = (await client.get(f"/api/v1/surveys/{sid}")).json()
    q = [x["question_id"] for x in detail["questions"]]
    assert detail["questions"][0]["branching_rules"] == [{"condition": "equals", "value": "no", "next_question_id": q[2]}]

    # Drafts cannot be answered; publishing opens it
    assert (await client.post(f"/api/v1/surveys/{sid}/responses", json=answers(**{q[0]: "no", q[2]: 3}), headers=patient)).status_code == 400
    res = await client.patch(f"/api/v1/surveys/{sid}/status", json={"status": "active"}, headers=admin)
    assert res.json()["previous_status"] == "draft"
    assert (await client.post(f"/api/v1/surveys/{sid}/responses", json=answers(**{q[0]: "no", q[2]: 3}), headers=patient)).status_code == 200

    assert (await client.patch(f"/api/v1/surveys/{sid}/status", json={"status": "draft"}, headers=admin)).status_code == 409
    assert (await client.patch(f"/api/v1/surveys/{sid}/status", json={"status": "closed"}, headers=admin)).status_code == 200
    assert (await client.patch(f"/api/v1/surveys/{uuid.uuid4()}/status", json={"status": "closed"}, headers=admin)).status_code == 404


async def test_builder_rejects_bad_questions(client):
    admin, _ = await account(client, "builder_admin2@example.com", "admin")
    q = builder_body()["questions"]
    bad = [
        [{**q[0], "branching": [{"value": "no", "next": 0}]}, q[1], q[2]],            # jumps backwards
        [{**q[0], "branching": [{"value": "maybe", "next": 2}]}, q[1], q[2]],         # not an answer
        [q[0], {**q[1], "options": ["Only one"]}, q[2]],                              # too few options
        [q[0], q[1], {**q[2], "branching": [{"value": "3", "next": 2}]}],             # scale cannot branch
    ]
    for questions in bad:
        res = await client.post("/api/v1/surveys/", json=builder_body(questions=questions), headers=admin)
        assert res.status_code == 400, questions
    assert (await client.post("/api/v1/surveys/", json=builder_body(questions=[]), headers=admin)).status_code == 422


async def test_assigned_list_shows_status_and_draft(client):
    sid, q = await branching_survey()
    patient, uid = await account(client, "hub_patient@example.com")
    assert (await client.get("/api/v1/surveys/assigned", headers=patient)).json() == []
    async with PostgresDB.get_pool().acquire() as conn:
        await conn.execute("INSERT INTO survey_assignments (survey_id, patient_user_id, due_date) VALUES ($1, $2, NOW() + INTERVAL '3 days')",
                           uuid.UUID(sid), uid)
    item = (await client.get("/api/v1/surveys/assigned", headers=patient)).json()[0]
    assert (item["survey_id"], item["status"], item["has_draft"]) == (sid, "pending", False)
    await client.patch(f"/api/v1/surveys/{sid}/draft", json={"answers": {q[0]: "yes"}}, headers=patient)
    item = (await client.get("/api/v1/surveys/assigned", headers=patient)).json()[0]
    assert (item["status"], item["has_draft"]) == ("in_progress", True)
    async with PostgresDB.get_pool().acquire() as conn:
        await conn.execute("UPDATE surveys SET status = 'closed' WHERE survey_id = $1", uuid.UUID(sid))
    assert (await client.get("/api/v1/surveys/assigned", headers=patient)).json() == []
