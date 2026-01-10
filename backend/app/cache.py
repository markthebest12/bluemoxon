"""Redis caching utilities for dashboard stats.

Provides a simple caching decorator with graceful degradation.
When Redis is unavailable, functions execute normally without caching.
"""

import json
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

import redis

from app.config import get_settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


def _reset_client() -> None:
    """Reset the cached client (for testing)."""
    global _redis_client
    _redis_client = None


def get_redis() -> redis.Redis | None:
    """Get Redis client, or None if not configured.

    Returns:
        Redis client instance, or None if REDIS_URL is empty.
        Client is cached as a singleton.
    """
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        if settings.redis_url:
            try:
                _redis_client = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                logger.info("Redis client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis client: {e}")
    return _redis_client


def cached(key: str, ttl: int = 300) -> Callable:
    """Cache decorator with TTL and graceful degradation.

    Args:
        key: Redis key for caching
        ttl: Time-to-live in seconds (default 5 minutes)

    Returns:
        Decorator that caches function results.

    Example:
        @cached(key="dashboard:stats", ttl=300)
        def get_expensive_data():
            return {"data": "value"}
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            client = get_redis()

            # Try cache hit
            if client:
                try:
                    cached_value = client.get(key)
                    if cached_value:
                        logger.debug(f"Cache HIT: {key}")
                        return json.loads(cached_value)
                except Exception as e:
                    logger.warning(f"Redis GET failed for {key}: {e}")

            # Cache miss - execute function
            logger.debug(f"Cache MISS: {key}")
            result = func(*args, **kwargs)

            # Store in cache
            if client and result is not None:
                try:
                    serialized = json.dumps(result, default=str)
                    client.setex(key, ttl, serialized)
                    logger.debug(f"Cached {key} with TTL {ttl}s")
                except Exception as e:
                    logger.warning(f"Redis SETEX failed for {key}: {e}")

            return result

        return wrapper

    return decorator
