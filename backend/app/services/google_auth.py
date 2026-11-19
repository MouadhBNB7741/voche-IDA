"""
Google sign-in with Google Identity Services: the "Sign in with Google" button gives
the browser an ID token, a JWT signed by Google. The backend checks it here, then signs
the user in with our usual login token. Google's own tokens are never stored.
"""
import asyncio
import logging
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

import asyncpg
import jwt
from fastapi import HTTPException

from app.core.config import settings
from app.models.user_model import UserModel

logger = logging.getLogger(__name__)

PROVIDER = "google"
GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")

UNVERIFIED_EMAIL = (
    "Google has not verified the email address of this Google account. "
    "Verify it with Google, or sign up with your email and a password."
)


@lru_cache
def _google_keys() -> jwt.PyJWKClient:
    # Google rotates its signing keys: they are cached for an hour, and fetched again
    # straight away when a token is signed with a key that is not in the cache.
    return jwt.PyJWKClient(GOOGLE_CERTS_URL, cache_keys=True, lifespan=3600, timeout=10)


def _decode(credential: str) -> Dict[str, Any]:
    signing_key = _google_keys().get_signing_key_from_jwt(credential)
    return jwt.decode(
        credential,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings.google_client_id,
        issuer=GOOGLE_ISSUERS,
        leeway=30,  # allow small clock differences with Google
        options={"require": ["exp", "iat", "iss", "aud", "sub"]},
    )


async def verify_google_credential(credential: str) -> Dict[str, Any]:
    """Check the ID token's signature, audience, issuer and expiry. Returns its claims."""
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google sign-in is not available right now.")
    try:
        # Fetching Google's keys is a blocking HTTP call: keep it off the event loop
        claims = await asyncio.to_thread(_decode, credential)
    except jwt.PyJWKClientConnectionError as e:
        logger.error(f"Could not fetch Google's signing keys: {e}")
        raise HTTPException(status_code=503, detail="Could not reach Google. Please try again.")
    except jwt.PyJWTError as e:
        logger.info(f"Rejected Google credential: {e}")
        raise HTTPException(status_code=401, detail="Google sign-in failed. Please try again.")

    if not claims.get("email"):
        raise HTTPException(status_code=400, detail="Your Google account did not share an email address.")
    return claims


def _names_from(claims: Dict[str, Any]) -> Tuple[str, str, str]:
    """First name, last name and display name, from the Google profile."""
    first = (claims.get("given_name") or "").strip()
    last = (claims.get("family_name") or "").strip()
    full = (claims.get("name") or "").strip()
    if not first and full:
        first, _, rest = full.partition(" ")
        last = last or rest.strip()
    display = full or f"{first} {last}".strip() or claims["email"].split("@")[0]
    return first[:100], last[:100], display[:100]


async def _find_or_create_user(conn, claims: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], bool]:
    """Find the user for this Google account, linking or creating one if needed.
    Returns (user, created)."""
    model = UserModel(conn)
    google_id = claims["sub"]
    email = claims["email"]
    email_verified = claims.get("email_verified") is True

    async with conn.transaction():
        user = await model.get_by_oauth_account(PROVIDER, google_id)
        if user:
            await model.update_oauth_email(PROVIDER, google_id, email)
            return user, False

        # Linking or creating an account trusts the email: only if Google verified it
        if not email_verified:
            raise HTTPException(status_code=403, detail=UNVERIFIED_EMAIL)

        user = await model.get_by_email_any_case(email)
        if user:
            await model.link_oauth_account(user["id"], PROVIDER, google_id, email)
            return user, False

        first, last, display = _names_from(claims)
        created = await model.create_user(
            email=email, password_hash=None, user_type=None,
            first_name=first, last_name=last, display_name=display,
            status="onboarding",
        )
        await model.link_oauth_account(created["id"], PROVIDER, google_id, email)
        return await model.get_by_email(email), True


async def sign_in_with_google(conn, claims: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    """Returns (user, created). The caller still checks the account's state."""
    try:
        return await _find_or_create_user(conn, claims)
    except asyncpg.UniqueViolationError:
        # Two sign-ins with the same new Google account at once: the other one created
        # or linked the account first, so looking it up again finds it.
        return await _find_or_create_user(conn, claims)
