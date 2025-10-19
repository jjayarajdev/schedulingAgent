"""
Redis connection and session state management.

Provides:
- Async Redis client
- Session state management (short-term memory)
- Intent caching
- Rate limiting support
"""

import json
from typing import Any

from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


# ============================================================================
# Redis Client Creation
# ============================================================================


def create_redis_client(url: str | None = None, max_connections: int | None = None) -> Redis:
    """
    Create async Redis client with connection pooling.

    Args:
        url: Redis URL (defaults to settings.redis_url)
        max_connections: Max connections in pool (defaults to settings.redis_max_connections)

    Returns:
        Redis: Async Redis client
    """
    url = url or settings.redis_url
    max_connections = max_connections or settings.redis_max_connections

    logger.info(
        "creating_redis_client",
        url=url.split("@")[0] if "@" in url else url.split("/")[0],
        max_connections=max_connections,
    )

    # Create connection pool
    pool = ConnectionPool.from_url(
        url,
        max_connections=max_connections,
        decode_responses=True,  # Auto-decode bytes to strings
        encoding="utf-8",
    )

    return Redis(connection_pool=pool)


# Global Redis client
redis_client: Redis = create_redis_client()


# ============================================================================
# Session State Management
# ============================================================================


class SessionManager:
    """
    Manage session state in Redis.

    Session state is stored as JSON with TTL (Time To Live).
    This provides short-term memory for the agent.
    """

    def __init__(self, client: Redis | None = None, ttl: int | None = None):
        """
        Initialize session manager.

        Args:
            client: Redis client (defaults to global redis_client)
            ttl: Session TTL in seconds (defaults to settings.session_ttl_seconds)
        """
        self.client = client or redis_client
        self.ttl = ttl or settings.session_ttl_seconds

    def _get_key(self, session_id: str) -> str:
        """Get Redis key for session."""
        return f"session:{session_id}"

    async def set(
        self,
        session_id: str,
        data: dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """
        Store session state in Redis.

        Args:
            session_id: Session ID
            data: Session data to store
            ttl: TTL in seconds (defaults to self.ttl)

        Returns:
            bool: True if successful, False otherwise
        """
        ttl = ttl or self.ttl
        key = self._get_key(session_id)

        try:
            await self.client.setex(
                key,
                ttl,
                json.dumps(data, default=str),  # default=str for datetime serialization
            )
            logger.debug("session_state_stored", session_id=session_id, ttl=ttl)
            return True
        except RedisError as e:
            logger.error("session_state_store_failed", session_id=session_id, error=str(e))
            return False

    async def get(self, session_id: str) -> dict[str, Any] | None:
        """
        Retrieve session state from Redis.

        Args:
            session_id: Session ID

        Returns:
            dict | None: Session data or None if not found
        """
        key = self._get_key(session_id)

        try:
            data = await self.client.get(key)
            if data is None:
                logger.debug("session_state_not_found", session_id=session_id)
                return None

            session_data = json.loads(data)
            logger.debug("session_state_retrieved", session_id=session_id)
            return session_data
        except (RedisError, json.JSONDecodeError) as e:
            logger.error("session_state_retrieve_failed", session_id=session_id, error=str(e))
            return None

    async def delete(self, session_id: str) -> bool:
        """
        Delete session state from Redis.

        Args:
            session_id: Session ID

        Returns:
            bool: True if deleted, False otherwise
        """
        key = self._get_key(session_id)

        try:
            deleted = await self.client.delete(key)
            logger.debug("session_state_deleted", session_id=session_id, deleted=bool(deleted))
            return bool(deleted)
        except RedisError as e:
            logger.error("session_state_delete_failed", session_id=session_id, error=str(e))
            return False

    async def update(self, session_id: str, updates: dict[str, Any]) -> bool:
        """
        Update session state (merge updates with existing data).

        Args:
            session_id: Session ID
            updates: Updates to merge

        Returns:
            bool: True if successful, False otherwise
        """
        # Get existing session
        session = await self.get(session_id)
        if session is None:
            # Create new session if doesn't exist
            return await self.set(session_id, updates)

        # Merge updates
        session.update(updates)

        # Save back
        return await self.set(session_id, session)

    async def exists(self, session_id: str) -> bool:
        """
        Check if session exists.

        Args:
            session_id: Session ID

        Returns:
            bool: True if session exists, False otherwise
        """
        key = self._get_key(session_id)
        try:
            return bool(await self.client.exists(key))
        except RedisError:
            return False

    async def get_ttl(self, session_id: str) -> int:
        """
        Get remaining TTL for session.

        Args:
            session_id: Session ID

        Returns:
            int: TTL in seconds, -1 if no expiry, -2 if doesn't exist
        """
        key = self._get_key(session_id)
        try:
            return await self.client.ttl(key)
        except RedisError:
            return -2


# Global session manager
session_manager = SessionManager()


# ============================================================================
# Intent Caching
# ============================================================================


class IntentCache:
    """
    Cache intent classification results to avoid redundant LLM calls.

    Uses Redis with short TTL (5 minutes) to cache recent classifications.
    """

    def __init__(self, client: Redis | None = None, ttl: int = 300):
        """
        Initialize intent cache.

        Args:
            client: Redis client (defaults to global redis_client)
            ttl: Cache TTL in seconds (default: 300 = 5 minutes)
        """
        self.client = client or redis_client
        self.ttl = ttl

    def _get_key(self, message: str, session_id: str) -> str:
        """Get Redis key for intent cache."""
        # Use hash of message for consistent key
        import hashlib

        message_hash = hashlib.md5(message.encode()).hexdigest()
        return f"intent_cache:{session_id}:{message_hash}"

    async def set(
        self,
        message: str,
        session_id: str,
        intent: str,
        confidence: float,
    ) -> bool:
        """
        Cache intent classification result.

        Args:
            message: User message
            session_id: Session ID
            intent: Classified intent
            confidence: Confidence score

        Returns:
            bool: True if successful, False otherwise
        """
        if not settings.enable_intent_caching:
            return False

        key = self._get_key(message, session_id)
        data = {"intent": intent, "confidence": confidence, "message": message}

        try:
            await self.client.setex(key, self.ttl, json.dumps(data))
            logger.debug("intent_cached", session_id=session_id, intent=intent)
            return True
        except RedisError as e:
            logger.error("intent_cache_failed", error=str(e))
            return False

    async def get(
        self, message: str, session_id: str
    ) -> tuple[str, float] | None:
        """
        Retrieve cached intent classification.

        Args:
            message: User message
            session_id: Session ID

        Returns:
            tuple[str, float] | None: (intent, confidence) or None if not cached
        """
        if not settings.enable_intent_caching:
            return None

        key = self._get_key(message, session_id)

        try:
            data = await self.client.get(key)
            if data is None:
                return None

            cached = json.loads(data)
            logger.debug("intent_cache_hit", session_id=session_id, intent=cached["intent"])
            return cached["intent"], cached["confidence"]
        except (RedisError, json.JSONDecodeError, KeyError) as e:
            logger.error("intent_cache_retrieve_failed", error=str(e))
            return None


# Global intent cache
intent_cache = IntentCache()


# ============================================================================
# Health Check
# ============================================================================


async def check_redis_health() -> bool:
    """
    Check Redis connection health.

    Returns:
        bool: True if Redis is accessible, False otherwise
    """
    try:
        await redis_client.ping()
        logger.info("redis_health_check", status="healthy")
        return True
    except RedisError as e:
        logger.error("redis_health_check", status="unhealthy", error=str(e))
        return False


# ============================================================================
# Lifecycle Management
# ============================================================================


async def close_redis() -> None:
    """
    Close Redis connections.

    Should be called on application shutdown.
    """
    logger.info("closing_redis_connections")
    await redis_client.close()
    logger.info("redis_connections_closed")
