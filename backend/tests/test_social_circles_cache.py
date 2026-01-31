# backend/tests/test_social_circles_cache.py

"""Tests for social circles graph caching."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.social_circles_cache import (
    CACHE_KEY_PREFIX,
    CACHE_TTL_SECONDS,
    MAX_CACHE_SIZE_BYTES,
    get_cache_key,
)


class TestGetCacheKey:
    """Tests for cache key generation."""

    def test_generates_deterministic_key(self):
        """Same parameters produce the same cache key."""
        key1 = get_cache_key(include_binders=True, min_book_count=1, max_books=5000)
        key2 = get_cache_key(include_binders=True, min_book_count=1, max_books=5000)
        assert key1 == key2

    def test_different_params_different_keys(self):
        """Different parameters produce different cache keys."""
        key1 = get_cache_key(include_binders=True, min_book_count=1, max_books=5000)
        key2 = get_cache_key(include_binders=False, min_book_count=1, max_books=5000)
        assert key1 != key2

    def test_key_starts_with_prefix(self):
        """Cache key starts with the expected prefix."""
        key = get_cache_key(include_binders=True, min_book_count=1, max_books=5000)
        assert key.startswith(f"{CACHE_KEY_PREFIX}:")


class TestGetCachedGraphSync:
    """Tests for synchronous cache get."""

    def test_cache_hit_returns_response(self):
        """Cache hit deserializes and returns SocialCirclesResponse."""
        from app.services.social_circles_cache import _get_cached_graph_sync

        cached_data = {
            "nodes": [],
            "edges": [],
            "meta": {
                "total_books": 0,
                "total_authors": 0,
                "total_publishers": 0,
                "total_binders": 0,
                "date_range": [1800, 1900],
                "truncated": False,
                "generated_at": "2026-01-01T00:00:00",
            },
        }
        client = MagicMock()
        client.get.return_value = json.dumps(cached_data)

        result, is_hit = _get_cached_graph_sync(client, "test:key")
        assert is_hit is True
        assert result is not None

    def test_cache_miss_returns_none(self):
        """Cache miss returns (None, False)."""
        from app.services.social_circles_cache import _get_cached_graph_sync

        client = MagicMock()
        client.get.return_value = None

        result, is_hit = _get_cached_graph_sync(client, "test:key")
        assert is_hit is False
        assert result is None

    def test_redis_error_returns_none(self):
        """Redis error returns (None, False) gracefully."""
        from app.services.social_circles_cache import _get_cached_graph_sync

        client = MagicMock()
        client.get.side_effect = Exception("Connection refused")

        result, is_hit = _get_cached_graph_sync(client, "test:key")
        assert is_hit is False
        assert result is None


class TestSetCachedGraphSync:
    """Tests for synchronous cache set."""

    def test_sets_with_ttl(self):
        """Caches serialized response with TTL."""
        from app.services.social_circles_cache import _set_cached_graph_sync

        client = MagicMock()
        response = MagicMock()
        response.model_dump.return_value = {"nodes": [], "edges": [], "meta": {}}

        _set_cached_graph_sync(client, "test:key", response)

        client.setex.assert_called_once()
        args = client.setex.call_args[0]
        assert args[0] == "test:key"
        assert args[1] == CACHE_TTL_SECONDS

    def test_skips_oversized_data(self):
        """Data exceeding MAX_CACHE_SIZE_BYTES is not cached."""
        from app.services.social_circles_cache import _set_cached_graph_sync

        client = MagicMock()
        response = MagicMock()
        # Create response that will serialize to > MAX_CACHE_SIZE_BYTES
        response.model_dump.return_value = {"data": "x" * (MAX_CACHE_SIZE_BYTES + 1)}

        _set_cached_graph_sync(client, "test:key", response)

        client.setex.assert_not_called()

    def test_redis_error_handled_gracefully(self):
        """Redis error during set does not raise."""
        from app.services.social_circles_cache import _set_cached_graph_sync

        client = MagicMock()
        client.setex.side_effect = Exception("Connection refused")
        response = MagicMock()
        response.model_dump.return_value = {"nodes": [], "edges": [], "meta": {}}

        # Should not raise
        _set_cached_graph_sync(client, "test:key", response)


class TestGetCachedGraphAsync:
    """Tests for async cache get."""

    @pytest.mark.asyncio
    @patch("app.services.social_circles_cache.get_redis")
    async def test_no_redis_returns_miss(self, mock_redis):
        """No Redis client returns (None, False)."""
        from app.services.social_circles_cache import get_cached_graph

        mock_redis.return_value = None
        result, is_hit = await get_cached_graph("test:key")
        assert is_hit is False
        assert result is None


class TestSetCachedGraphAsync:
    """Tests for async cache set."""

    @pytest.mark.asyncio
    @patch("app.services.social_circles_cache.get_redis")
    async def test_no_redis_skips(self, mock_redis):
        """No Redis client skips caching silently."""
        from app.services.social_circles_cache import set_cached_graph

        mock_redis.return_value = None
        response = MagicMock()
        # Should not raise
        await set_cached_graph("test:key", response)


class TestInvalidateCache:
    """Tests for cache invalidation."""

    @patch("app.services.social_circles_cache.get_redis")
    def test_no_redis_returns_zero(self, mock_redis):
        """No Redis client returns 0."""
        from app.services.social_circles_cache import invalidate_cache

        mock_redis.return_value = None
        assert invalidate_cache() == 0


class TestGetOrBuildGraph:
    """Tests for sync cache wrapper (#1549)."""

    @patch("app.services.social_circles_cache.get_redis")
    @patch("app.services.social_circles.build_social_circles_graph")
    def test_returns_cached_graph_on_hit(self, mock_build, mock_redis):
        """Cache hit returns cached graph without calling build."""
        from app.services.social_circles_cache import get_or_build_graph

        client = MagicMock()
        client.get.return_value = json.dumps(
            {
                "nodes": [],
                "edges": [],
                "meta": {
                    "total_books": 0,
                    "total_authors": 0,
                    "total_publishers": 0,
                    "total_binders": 0,
                    "date_range": [1800, 1900],
                    "truncated": False,
                    "generated_at": "2026-01-01T00:00:00",
                },
            }
        )
        mock_redis.return_value = client

        db = MagicMock()
        result = get_or_build_graph(db)

        mock_build.assert_not_called()
        assert result is not None

    @patch("app.services.social_circles_cache.get_redis")
    @patch("app.services.social_circles.build_social_circles_graph")
    def test_builds_and_caches_on_miss(self, mock_build, mock_redis):
        """Cache miss builds graph and caches it."""
        from app.services.social_circles_cache import get_or_build_graph

        client = MagicMock()
        client.get.return_value = None  # Cache miss
        mock_redis.return_value = client
        mock_build.return_value = MagicMock()
        mock_build.return_value.model_dump.return_value = {"nodes": [], "edges": [], "meta": {}}

        db = MagicMock()
        result = get_or_build_graph(db)

        mock_build.assert_called_once_with(db)
        assert result == mock_build.return_value

    @patch("app.services.social_circles_cache.get_redis")
    @patch("app.services.social_circles.build_social_circles_graph")
    def test_builds_without_caching_when_no_redis(self, mock_build, mock_redis):
        """No Redis client: build graph, skip caching."""
        from app.services.social_circles_cache import get_or_build_graph

        mock_redis.return_value = None
        mock_build.return_value = MagicMock()

        db = MagicMock()
        result = get_or_build_graph(db)

        mock_build.assert_called_once_with(db)
        assert result == mock_build.return_value
