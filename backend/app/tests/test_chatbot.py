import uuid

import httpx
import pytest

from app.core.config import settings
from app.db.postgres import PostgresDB
from app.services import ai_service

API = "/api/v1/ai"


@pytest.fixture(autouse=True)
def offline_ai(monkeypatch):
    # Never call the real provider from tests.
    monkeypatch.setattr(settings, "gemini_api_key", "")


async def login(client, email):
    pwd = "StrongPassword123!"
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": pwd, "first_name": "Chat", "last_name": "User", "user_type": "patient",
    })
    res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def new_conversation(client, headers, **body):
    res = await client.post(f"{API}/conversations", json=body, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()["id"]


async def test_conversation_flow_persists_messages_and_cites_trials(client):
    headers = await login(client, "chat_flow@example.com")
    trial_id = str(uuid.uuid4())
    async with PostgresDB.get_pool().acquire() as conn:
        await conn.execute("""
            INSERT INTO clinical_trials (trial_id, title, disease_area, phase, status, sponsor, summary)
            VALUES ($1, 'Malaria Vaccine Study', 'Malaria', 'Phase 2', 'Recruiting', 'Health Org', 'Tests a vaccine')
        """, trial_id)

    conv_id = await new_conversation(client, headers)
    res = await client.post(f"{API}/conversations/{conv_id}/messages",
                            json={"content": "Are there malaria vaccine trials?"}, headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["user_message"]["sender_role"] == "user"
    reply = body["assistant_message"]
    assert reply["sender_role"] == "assistant"
    assert {"type": "trial", "id": trial_id, "title": "Malaria Vaccine Study"} in reply["citations"]
    assert ai_service.DISCLAIMER in reply["content"]
    assert reply["safety_flagged"] is False

    detail = (await client.get(f"{API}/conversations/{conv_id}", headers=headers)).json()
    assert [m["sender_role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["title"] == "Are there malaria vaccine trials?"  # first message becomes the title

    listed = (await client.get(f"{API}/conversations", headers=headers)).json()
    assert [c["id"] for c in listed] == [conv_id]


async def test_emergency_message_is_flagged_and_not_sent_to_ai(client, monkeypatch):
    headers = await login(client, "chat_emergency@example.com")
    conv_id = await new_conversation(client, headers)

    async def fail(*args, **kwargs):
        raise AssertionError("provider must not be called for emergencies")
    monkeypatch.setattr(settings, "gemini_api_key", "set")
    monkeypatch.setattr(ai_service, "call_gemini", fail)

    res = await client.post(f"{API}/conversations/{conv_id}/messages",
                            json={"content": "I have severe chest pain right now"}, headers=headers)
    reply = res.json()["assistant_message"]
    assert reply["safety_flagged"] is True
    assert reply["content"] == ai_service.EMERGENCY_REPLY
    assert reply["citations"] == []


async def test_provider_reply_gets_disclaimer_and_errors_save_nothing(client, monkeypatch):
    headers = await login(client, "chat_provider@example.com")
    conv_id = await new_conversation(client, headers)
    monkeypatch.setattr(settings, "gemini_api_key", "set")

    async def ok(history, text, context):
        return {"text": "Informed consent means you agree after learning the risks.", "token_count": 42}
    monkeypatch.setattr(ai_service, "call_gemini", ok)
    reply = (await client.post(f"{API}/conversations/{conv_id}/messages",
                               json={"content": "What is consent?"}, headers=headers)).json()["assistant_message"]
    assert reply["content"].startswith("Informed consent means")
    assert ai_service.DISCLAIMER in reply["content"]

    async def down(history, text, context):
        raise httpx.ConnectError("provider down")
    monkeypatch.setattr(ai_service, "call_gemini", down)
    res = await client.post(f"{API}/conversations/{conv_id}/messages",
                            json={"content": "Second question"}, headers=headers)
    assert res.status_code == 502
    messages = (await client.get(f"{API}/conversations/{conv_id}", headers=headers)).json()["messages"]
    assert len(messages) == 2  # only the first exchange was saved


async def test_feedback_upserts_and_only_on_own_assistant_messages(client):
    headers = await login(client, "chat_feedback@example.com")
    conv_id = await new_conversation(client, headers)
    body = (await client.post(f"{API}/conversations/{conv_id}/messages",
                              json={"content": "hello there"}, headers=headers)).json()
    reply_id, user_msg_id = body["assistant_message"]["id"], body["user_message"]["id"]

    assert (await client.post(f"{API}/messages/{reply_id}/feedback", json={"rating": 1}, headers=headers)).status_code == 201
    assert (await client.post(f"{API}/messages/{reply_id}/feedback", json={"rating": -1, "comment": "unclear"}, headers=headers)).status_code == 201
    async with PostgresDB.get_pool().acquire() as conn:
        rows = await conn.fetch("SELECT rating, comment FROM chat_feedback WHERE message_id = $1", uuid.UUID(reply_id))
    assert [(r["rating"], r["comment"]) for r in rows] == [(-1, "unclear")]

    assert (await client.post(f"{API}/messages/{reply_id}/feedback", json={"rating": 0}, headers=headers)).status_code == 422
    assert (await client.post(f"{API}/messages/{user_msg_id}/feedback", json={"rating": 1}, headers=headers)).status_code == 404


async def test_other_users_cannot_touch_a_conversation(client):
    owner = await login(client, "chat_owner@example.com")
    other = await login(client, "chat_other@example.com")
    conv_id = await new_conversation(client, owner)
    reply_id = (await client.post(f"{API}/conversations/{conv_id}/messages",
                                  json={"content": "hello"}, headers=owner)).json()["assistant_message"]["id"]

    assert (await client.get(f"{API}/conversations/{conv_id}", headers=other)).status_code == 404
    assert (await client.post(f"{API}/conversations/{conv_id}/messages", json={"content": "hi"}, headers=other)).status_code == 404
    assert (await client.post(f"{API}/messages/{reply_id}/feedback", json={"rating": 1}, headers=other)).status_code == 404
    assert (await client.delete(f"{API}/conversations/{conv_id}", headers=other)).status_code == 404
    assert (await client.get(f"{API}/conversations", headers=other)).json() == []

    assert (await client.delete(f"{API}/conversations/{conv_id}", headers=owner)).status_code == 204
    assert (await client.get(f"{API}/conversations/{conv_id}", headers=owner)).status_code == 404


async def test_requires_login_and_validates_input(client):
    assert (await client.get(f"{API}/conversations")).status_code in (401, 403)
    headers = await login(client, "chat_validate@example.com")
    assert (await client.post(f"{API}/conversations", json={"context_type": "diagnosis"}, headers=headers)).status_code == 422
    conv_id = await new_conversation(client, headers)
    assert (await client.post(f"{API}/conversations/{conv_id}/messages", json={"content": "   "}, headers=headers)).status_code == 422


def test_keywords_keep_short_disease_names():
    assert ai_service.keywords("Are there any HIV or TB trials for kids?") == ["tb", "hiv", "kids"]
