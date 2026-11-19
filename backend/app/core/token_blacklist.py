"""
Logged-out tokens. Every login token carries a unique id (jti). Logging out stores
that id in Redis until the token would have expired anyway, and the auth middleware
refuses tokens whose id is stored.
"""
import logging
import time

from app.db.redis import get_redis_client

logger = logging.getLogger(__name__)

_PREFIX = "revoked_token:"


async def revoke_token(payload: dict) -> None:
    """Revoke a decoded token. Raises if Redis cannot be reached."""
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or not exp:
        # Tokens issued before logout existed have no id: they simply expire
        return
    seconds_left = int(exp - time.time())
    if seconds_left <= 0:
        return
    redis = await get_redis_client()
    await redis.set(f"{_PREFIX}{jti}", "1", ex=seconds_left)


async def is_token_revoked(payload: dict) -> bool:
    """True if this token was logged out.

    If Redis cannot be reached the token is accepted: an outage must not sign every
    user out. A logged-out token can then work until Redis is back or it expires."""
    jti = payload.get("jti")
    if not jti:
        return False
    try:
        redis = await get_redis_client()
        return bool(await redis.exists(f"{_PREFIX}{jti}"))
    except Exception as e:
        logger.warning(f"Could not check logged-out tokens in Redis: {e}")
        return False
