"""
Live notification connections.

Every browser tab that opens /api/v1/notifications/ws is registered here under its
user. One user can have several tabs open, so a user maps to a set of sockets.

With more than one backend instance, a notification can be created on one instance
while the user's socket is open on another. New notifications therefore go through
Redis Pub/Sub: every instance listens on the same channel and forwards each message
to the sockets it holds. Without Redis (local development, or Redis down) messages
go straight to the sockets of this instance, and the frontend's 10-second refresh
covers the rest.
"""
import asyncio
import json
import logging
from typing import Any, Dict, Iterable, List, Set, Tuple

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder

from app.db import redis as redis_db

logger = logging.getLogger(__name__)

CHANNEL = "voche:notifications"


class ConnectionManager:
    def __init__(self):
        self._sockets: Dict[str, Set[WebSocket]] = {}
        self._locks: Dict[WebSocket, asyncio.Lock] = {}
        self._listener: asyncio.Task | None = None
        self._listening = False

    # ── Sockets on this instance ───────────────────────────────────────

    def connect(self, user_id: str, websocket: WebSocket) -> None:
        self._sockets.setdefault(str(user_id), set()).add(websocket)
        self._locks[websocket] = asyncio.Lock()

    def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        sockets = self._sockets.get(str(user_id))
        if sockets is not None:
            sockets.discard(websocket)
            if not sockets:
                del self._sockets[str(user_id)]
        self._locks.pop(websocket, None)

    def connection_count(self, user_id: str | None = None) -> int:
        if user_id is not None:
            return len(self._sockets.get(str(user_id), ()))
        return sum(len(s) for s in self._sockets.values())

    async def send(self, websocket: WebSocket, message: Dict[str, Any]) -> bool:
        """Send one message to one socket. Sends to the same socket never overlap."""
        lock = self._locks.get(websocket)
        if lock is None:
            return False
        try:
            async with lock:
                await websocket.send_json(message)
            return True
        except Exception:
            return False

    async def send_local(self, user_id: str, message: Dict[str, Any]) -> int:
        """Send to every socket this instance holds for the user. Returns how many got it."""
        delivered = 0
        for websocket in list(self._sockets.get(str(user_id), ())):
            if await self.send(websocket, message):
                delivered += 1
            else:
                # The tab is gone: its handler will also notice, but stop sending to it now
                self.disconnect(user_id, websocket)
        return delivered

    # ── Delivery across instances ──────────────────────────────────────

    async def publish(self, user_id: str, message: Dict[str, Any]) -> None:
        await self.publish_many([(str(user_id), message)])

    async def publish_many(self, items: Iterable[Tuple[str, Dict[str, Any]]]) -> None:
        """Deliver messages to users wherever their sockets are. Never raises."""
        items = [(str(user_id), jsonable_encoder(message)) for user_id, message in items]
        if not items:
            return

        published = await self._publish_to_redis(items)
        # While this instance listens on Redis, its own sockets get the message from there
        if published and self._listening:
            return
        for user_id, message in items:
            try:
                await self.send_local(user_id, message)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Could not send a live notification to user {user_id}: {e}")

    async def _publish_to_redis(self, items: List[Tuple[str, Dict[str, Any]]]) -> bool:
        redis = redis_db.redis
        if redis is None:
            return False
        try:
            async with redis.pipeline(transaction=False) as pipe:
                for user_id, message in items:
                    pipe.publish(CHANNEL, json.dumps({"user_id": user_id, "message": message}))
                await pipe.execute()
            return True
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Could not publish live notifications to Redis: {e}")
            return False

    # ── Redis listener ─────────────────────────────────────────────────

    def is_listening(self) -> bool:
        return self._listening

    async def start(self) -> None:
        """Listen on Redis for messages published by any instance. Does nothing without Redis."""
        if redis_db.redis is None:
            logger.info("Live notifications: Redis is not connected, delivering on this instance only.")
            return
        if self._listener is None or self._listener.done():
            self._listener = asyncio.create_task(self._listen())

    async def stop(self) -> None:
        task, self._listener = self._listener, None
        self._listening = False
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    async def wait_until_listening(self, timeout: float = 5.0) -> bool:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while not self._listening and loop.time() < deadline:
            await asyncio.sleep(0.02)
        return self._listening

    async def _listen(self) -> None:
        delay = 1
        while True:
            redis = redis_db.redis
            if redis is None:
                return
            pubsub = redis.pubsub()
            try:
                await pubsub.subscribe(CHANNEL)
                self._listening = True
                delay = 1
                logger.info("Live notifications: listening on Redis.")
                async for item in pubsub.listen():
                    if item.get("type") == "message":
                        await self._deliver(item.get("data"))
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Live notifications: Redis listener stopped ({e}), retrying in {delay}s.")
            finally:
                self._listening = False
                try:
                    await pubsub.aclose()
                except Exception:
                    pass
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)

    async def _deliver(self, raw: Any) -> None:
        try:
            envelope = json.loads(raw)
            await self.send_local(envelope["user_id"], envelope["message"])
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Live notifications: could not deliver a message from Redis: {e}")


manager = ConnectionManager()
