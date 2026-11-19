"""
Google sign-in (POST /auth/google), logout (POST /auth/logout) and the login token
itself (length from ACCESS_TOKEN_EXPIRE_MINUTES, a unique id per token).

Google is replaced by a local RSA key: tokens are signed with it, and the check that
normally fetches Google's public keys gets this key instead. Everything else (signature,
audience, issuer, expiry, email_verified) runs the real checks.
"""
import secrets
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import AsyncClient

from app.core.config import settings
from app.core.security import decode_jwt
from app.db.postgres import PostgresDB
from app.services import google_auth

BASE = "/api/v1"
PASSWORD = "StrongPassword123!"
CLIENT_ID = "test-client.apps.googleusercontent.com"

GOOGLE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _FakeSigningKey:
    key = GOOGLE_KEY.public_key()


class _FakeGoogleKeys:
    def get_signing_key_from_jwt(self, token):
        return _FakeSigningKey()


class _UnreachableGoogleKeys:
    def get_signing_key_from_jwt(self, token):
        raise jwt.PyJWKClientConnectionError("network down")


@pytest.fixture(autouse=True)
def fake_google(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", CLIENT_ID)
    monkeypatch.setattr(google_auth, "_google_keys", lambda: _FakeGoogleKeys())


# ── Helpers ──────────────────────────────────────────────────────────────────

def google_token(key=GOOGLE_KEY, **overrides) -> str:
    """An ID token like the one Google Identity Services gives the browser."""
    now = int(time.time())
    claims = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "sub": "google-user-1",
        "email": "ada@example.com",
        "email_verified": True,
        "given_name": "Ada",
        "family_name": "Obi",
        "name": "Ada Obi",
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "test-key"})


async def google_sign_in(client: AsyncClient, **overrides):
    return await client.post(f"{BASE}/auth/google", json={"credential": google_token(**overrides)})


def unique(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(4)}"


async def register(client: AsyncClient, email: str, user_type: str = "patient") -> str:
    res = await client.post(f"{BASE}/auth/register", json={
        "email": email, "password": PASSWORD,
        "first_name": "Pass", "last_name": "Word", "user_type": user_type,
    })
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


async def db_value(query: str, *args):
    async with PostgresDB.get_pool().acquire() as conn:
        return await conn.fetchval(query, *args)


async def db_row(query: str, *args):
    async with PostgresDB.get_pool().acquire() as conn:
        return await conn.fetchrow(query, *args)


async def db_execute(query: str, *args):
    async with PostgresDB.get_pool().acquire() as conn:
        return await conn.execute(query, *args)


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── New Google users ─────────────────────────────────────────────────────────

async def test_new_google_user_is_created_in_onboarding(client: AsyncClient):
    email = f"{unique('new')}@gmail.com"
    res = await google_sign_in(client, sub=unique("g"), email=email)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["is_new_user"] is True
    assert body["user_type"] is None

    user = await db_row("SELECT * FROM users WHERE email = $1", email)
    assert user["status"] == "onboarding"
    assert user["user_type"] is None
    assert user["password_hash"] is None
    assert user["first_name"] == "Ada" and user["last_name"] == "Obi"
    assert user["display_name"] == "Ada Obi"
    assert await db_value("SELECT COUNT(*) FROM user_profiles WHERE user_id = $1", user["id"]) == 1
    link = await db_row("SELECT * FROM user_oauth_accounts WHERE user_id = $1", user["id"])
    assert link["provider"] == "google" and link["provider_email"] == email


async def test_new_google_user_can_finish_onboarding(client: AsyncClient):
    res = await google_sign_in(client, sub=unique("g"), email=f"{unique('wizard')}@gmail.com")
    headers = bearer(res.json()["access_token"])

    me = await client.get(f"{BASE}/users/me", headers=headers)
    assert me.status_code == 200, me.text
    assert me.json()["status"] == "onboarding"

    done = await client.post(f"{BASE}/users/onboarding/complete", json={"user_type": "caregiver"}, headers=headers)
    assert done.status_code == 200, done.text
    me = await client.get(f"{BASE}/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    assert me.json()["user_type"] == "caregiver"
    assert me.json()["status"] == "active"


async def test_same_google_account_signs_in_to_the_same_user(client: AsyncClient):
    sub, email = unique("g"), f"{unique('again')}@gmail.com"
    first = await google_sign_in(client, sub=sub, email=email)
    second = await google_sign_in(client, sub=sub, email=email)
    assert second.status_code == 200, second.text
    assert second.json()["is_new_user"] is False
    assert decode_jwt(first.json()["access_token"])["sub"] == decode_jwt(second.json()["access_token"])["sub"]
    assert await db_value("SELECT COUNT(*) FROM users WHERE email = $1", email) == 1
    assert await db_value("SELECT COUNT(*) FROM user_oauth_accounts WHERE provider_user_id = $1", sub) == 1


async def test_google_account_is_found_by_its_id_after_an_email_change(client: AsyncClient):
    sub = unique("g")
    old_email, new_email = f"{unique('old')}@gmail.com", f"{unique('new')}@gmail.com"
    await google_sign_in(client, sub=sub, email=old_email)
    res = await google_sign_in(client, sub=sub, email=new_email)
    assert res.json()["is_new_user"] is False
    assert await db_value("SELECT provider_email FROM user_oauth_accounts WHERE provider_user_id = $1", sub) == new_email


async def test_google_profile_without_given_name_uses_full_name(client: AsyncClient):
    email = f"{unique('names')}@gmail.com"
    await google_sign_in(client, sub=unique("g"), email=email, given_name=None, family_name=None, name="Chinwe Ada Eze")
    user = await db_row("SELECT first_name, last_name, display_name FROM users WHERE email = $1", email)
    assert (user["first_name"], user["last_name"], user["display_name"]) == ("Chinwe", "Ada Eze", "Chinwe Ada Eze")


# ── Linking to an existing password account (Q15) ────────────────────────────

async def test_verified_google_email_links_to_existing_account(client: AsyncClient):
    email = f"{unique('linked')}@example.com"
    await register(client, email, user_type="hcp")

    # Google sends the email in its own case: the accounts still match
    res = await google_sign_in(client, sub=unique("g"), email=email.upper())
    assert res.status_code == 200, res.text
    assert res.json()["is_new_user"] is False
    assert res.json()["user_type"] == "hcp"

    user_id = await db_value("SELECT id FROM users WHERE email = $1", email)
    assert await db_value("SELECT COUNT(*) FROM users WHERE LOWER(email) = LOWER($1)", email) == 1
    assert await db_value("SELECT COUNT(*) FROM user_oauth_accounts WHERE user_id = $1", user_id) == 1

    # The password still works too
    login = await client.post(f"{BASE}/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200


async def test_unverified_google_email_is_not_linked(client: AsyncClient):
    email = f"{unique('unverified')}@example.com"
    await register(client, email)

    res = await google_sign_in(client, sub=unique("g"), email=email, email_verified=False)
    assert res.status_code == 403
    assert "not verified" in res.json()["detail"]
    assert await db_value("SELECT COUNT(*) FROM user_oauth_accounts") == 0


async def test_unverified_google_email_does_not_create_an_account(client: AsyncClient):
    email = f"{unique('nobody')}@example.com"
    res = await google_sign_in(client, sub=unique("g"), email=email, email_verified=False)
    assert res.status_code == 403
    assert await db_value("SELECT COUNT(*) FROM users WHERE email = $1", email) == 0


async def test_email_signup_is_refused_for_an_email_used_with_google(client: AsyncClient):
    email = f"{unique('taken')}@gmail.com"
    await google_sign_in(client, sub=unique("g"), email=email)
    res = await client.post(f"{BASE}/auth/register", json={
        "email": email, "password": PASSWORD, "first_name": "A", "last_name": "B", "user_type": "patient",
    })
    assert res.status_code == 409


# ── Tokens Google did not issue for us ───────────────────────────────────────

@pytest.mark.parametrize("overrides", [
    {"aud": "someone-elses-app.apps.googleusercontent.com"},
    {"iss": "https://evil.example.com"},
    {"exp": int(time.time()) - 600, "iat": int(time.time()) - 4200},
    {"key": OTHER_KEY},
    {"sub": None},
], ids=["other-app", "other-issuer", "expired", "wrong-signature", "no-user-id"])
async def test_invalid_google_tokens_are_rejected(client: AsyncClient, overrides):
    res = await google_sign_in(client, **overrides)
    assert res.status_code == 401, res.text
    assert await db_value("SELECT COUNT(*) FROM users") == 0


async def test_garbage_credential_is_rejected(client: AsyncClient):
    res = await client.post(f"{BASE}/auth/google", json={"credential": "not-a-token"})
    assert res.status_code == 401


async def test_google_sign_in_is_off_without_a_client_id(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "")
    res = await google_sign_in(client)
    assert res.status_code == 503


async def test_google_unreachable_returns_503(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(google_auth, "_google_keys", lambda: _UnreachableGoogleKeys())
    res = await google_sign_in(client)
    assert res.status_code == 503


# ── Account states apply to Google sign-in too ───────────────────────────────

async def test_suspended_user_cannot_sign_in_with_google(client: AsyncClient):
    email = f"{unique('suspended')}@example.com"
    await register(client, email)
    await db_execute(
        "UPDATE users SET status = 'suspended', suspended_until = NOW() + INTERVAL '2 days', suspended_reason = 'Spam' WHERE email = $1",
        email,
    )
    res = await google_sign_in(client, sub=unique("g"), email=email)
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "account_suspended"
    assert res.json()["detail"]["suspended_reason"] == "Spam"


async def test_google_sign_in_cancels_scheduled_deletion(client: AsyncClient):
    sub, email = unique("g"), f"{unique('leaving')}@gmail.com"
    await google_sign_in(client, sub=sub, email=email)
    await db_execute("UPDATE users SET deletion_scheduled_at = NOW() + INTERVAL '3 days' WHERE email = $1", email)

    res = await google_sign_in(client, sub=sub, email=email)
    assert res.status_code == 200
    assert "annulled" in res.json()["message"]
    assert await db_value("SELECT deletion_scheduled_at FROM users WHERE email = $1", email) is None


async def test_google_user_who_set_a_password_can_log_in_during_onboarding(client: AsyncClient):
    """A Google user can set a password with "Forgot password?" before finishing onboarding."""
    from app.core.security import hash_password
    email = f"{unique('both')}@gmail.com"
    await google_sign_in(client, sub=unique("g"), email=email)
    await db_execute("UPDATE users SET password_hash = $2 WHERE email = $1", email, hash_password(PASSWORD))

    res = await client.post(f"{BASE}/auth/login", json={"email": email, "password": PASSWORD})
    assert res.status_code == 200, res.text
    assert res.json()["user_type"] is None


async def test_password_login_fails_for_google_only_account(client: AsyncClient):
    email = f"{unique('nopass')}@gmail.com"
    await google_sign_in(client, sub=unique("g"), email=email)
    res = await client.post(f"{BASE}/auth/login", json={"email": email, "password": PASSWORD})
    assert res.status_code == 401


async def test_google_only_user_is_told_how_to_set_a_password(client: AsyncClient):
    res = await google_sign_in(client, sub=unique("g"), email=f"{unique('change')}@gmail.com")
    headers = bearer(res.json()["access_token"])
    await client.post(f"{BASE}/users/onboarding/complete", json={"user_type": "patient"}, headers=headers)

    res = await client.put(f"{BASE}/auth/update-password", json={
        "current_password": "anything", "new_password": "NewPassword123!",
    }, headers=headers)
    assert res.status_code == 400
    assert "Forgot password" in res.json()["detail"]


# ── Login tokens and logout (Q16) ────────────────────────────────────────────

async def test_token_length_comes_from_settings(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "access_token_expire_minutes", 5)
    token = await register(client, f"{unique('short')}@example.com")
    payload = decode_jwt(token)
    assert payload["exp"] - payload["iat"] == 5 * 60


async def test_every_token_has_its_own_id(client: AsyncClient):
    email = f"{unique('ids')}@example.com"
    first = await register(client, email)
    second = (await client.post(f"{BASE}/auth/login", json={"email": email, "password": PASSWORD})).json()["access_token"]
    assert decode_jwt(first)["jti"] != decode_jwt(second)["jti"]


async def test_logout_revokes_only_that_token(client: AsyncClient):
    email = f"{unique('logout')}@example.com"
    phone = await register(client, email)
    laptop = (await client.post(f"{BASE}/auth/login", json={"email": email, "password": PASSWORD})).json()["access_token"]

    res = await client.post(f"{BASE}/auth/logout", headers=bearer(phone))
    assert res.status_code == 200

    assert (await client.get(f"{BASE}/auth/me", headers=bearer(phone))).status_code == 401
    assert (await client.get(f"{BASE}/auth/me", headers=bearer(laptop))).status_code == 200


async def test_logout_without_a_valid_token_still_succeeds(client: AsyncClient):
    assert (await client.post(f"{BASE}/auth/logout")).status_code == 200
    assert (await client.post(f"{BASE}/auth/logout", headers=bearer("not-a-token"))).status_code == 200


async def test_revoked_token_expires_from_redis_with_the_token(client: AsyncClient):
    from app.db.redis import get_redis_client
    token = await register(client, f"{unique('ttl')}@example.com")
    payload = decode_jwt(token)
    await client.post(f"{BASE}/auth/logout", headers=bearer(token))

    ttl = await (await get_redis_client()).ttl(f"revoked_token:{payload['jti']}")
    assert 0 < ttl <= payload["exp"] - int(time.time()) + 1
