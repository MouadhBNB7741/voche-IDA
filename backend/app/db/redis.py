from redis.asyncio import Redis
from app.core.config import settings

redis: Redis | None = None

# redis-cli CONFIG SET notify-keyspace-events Ex
async def get_redis_client():
    """Helper to ensure redis is connected and typed correctly."""
    if redis is None:
        raise RuntimeError(
            "Redis is not initialized. Did you call connect_redis()?")
    return redis


async def connect_redis():
    global redis
    redis = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        # Adds resilience for production
        retry_on_timeout=True,
        health_check_interval=30
    )
    # 'Ex' means Expired events for (x)Generic keys
    await redis.config_set("notify-keyspace-events", "Ex")


async def disconnect_redis():
    if redis:
        await redis.close()
