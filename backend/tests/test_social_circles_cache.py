"""Tests for social circles cache service."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.social_circles import (
    ConnectionType,
    Era,
    NodeType,
    SocialCircleEdge,
    SocialCircleNode,
    SocialCirclesMeta,
    SocialCirclesResponse,
)
from app.services.social_circles_cache import (
    CACHE_KEY_PREFIX,
    CACHE_TTL_SECONDS,
    MAX_CACHE_SIZE_BYTES,
    _get_cached_graph_sync,
    _invalidate_cache_sync,
    _set_cached_graph_sync,
    get_cache_key,
    get_cached_graph,
    invalidate_cache,
    invalidate_cache_async,
    set_cached_graph,
)


def _create_test_response(num_nodes: int = 2, num_edges: int = 1) -> SocialCirclesResponse:
    """Create a test SocialCirclesResponse with given number of nodes and edges."""
    nodes = [
        SocialCircleNode(
            id=f"author:{i}",
            entity_id=i,
            name=f"Author {i}",
            type=NodeType.author,
            birth_year=1800 + i,
            death_year=1870 + i,
            era=Era.victorian,
            tier="A",
            book_count=i + 1,
            book_ids=[i * 10, i * 10 + 1],
        )
        for i in range(num_nodes)
    ]

    edges = [
        SocialCircleEdge(
            id=f"e:author:{i}:author:{i + 1}",
            source=f"author:{i}",
            target=f"author:{i + 1}",
            type=ConnectionType.shared_publisher,
            strength=5,
            evidence="Shared publisher",
            shared_book_ids=[i * 10],
            start_year=1850,
            end_year=1860,
        )
        for i in range(num_edges)
    ]

    meta = SocialCirclesMeta(
        total_books=10,
        total_authors=num_nodes,
        total_publishers=1,
        total_binders=0,
        date_range=(1800, 1900),
        generated_at=datetime(2024, 1, 15, 12, 0, 0),
        truncated=False,
    )

    return SocialCirclesResponse(nodes=nodes, edges=edges, meta=meta)


class TestGetCacheKey:
    """Tests for get_cache_key() function."""

    def test_generates_deterministic_key(self):
        """Same parameters always produce the same cache key."""
        key1 = get_cache_key(include_binders=True, min_book_count=2, max_books=100)
        key2 = get_cache_key(include_binders=True, min_book_count=2, max_books=100)

        assert key1 == key2

    def test_different_include_binders_produces_different_key(self):
        """Different include_binders value produces different key."""
        key1 = get_cache_key(include_binders=True, min_book_count=2, max_books=100)
        key2 = get_cache_key(include_binders=False, min_book_count=2, max_books=100)

        assert key1 != key2

    def test_different_min_book_count_produces_different_key(self):
        """Different min_book_count value produces different key."""
        key1 = get_cache_key(include_binders=True, min_book_count=2, max_books=100)
        key2 = get_cache_key(include_binders=True, min_book_count=3, max_books=100)

        assert key1 != key2

    def test_different_max_books_produces_different_key(self):
        """Different max_books value produces different key."""
        key1 = get_cache_key(include_binders=True, min_book_count=2, max_books=100)
        key2 = get_cache_key(include_binders=True, min_book_count=2, max_books=200)

        assert key1 != key2

    def test_key_format_has_prefix(self):
        """Cache key starts with the expected prefix."""
        key = get_cache_key(include_binders=True, min_book_count=2, max_books=100)

        assert key.startswith(f"{CACHE_KEY_PREFIX}:")

    def test_key_contains_hash(self):
        """Cache key contains a hash suffix after the prefix."""
        key = get_cache_key(include_binders=True, min_book_count=2, max_books=100)
        parts = key.split(":")

        # Key format: social_circles:graph:{hash}
        assert len(parts) == 3
        assert parts[0] == "social_circles"
        assert parts[1] == "graph"
        # Hash should be 16 characters (truncated SHA256)
        assert len(parts[2]) == 16


class TestGetCachedGraphSync:
    """Tests for _get_cached_graph_sync() function."""

    def test_returns_response_on_cache_hit(self):
        """Returns deserialized response and True on cache hit."""
        mock_client = MagicMock()
        test_response = _create_test_response()
        cached_data = json.dumps(test_response.model_dump(mode="json"), default=str)
        mock_client.get.return_value = cached_data

        result, is_hit = _get_cached_graph_sync(mock_client, "test:key")

        assert is_hit is True
        assert result is not None
        assert isinstance(result, SocialCirclesResponse)
        assert len(result.nodes) == 2
        assert len(result.edges) == 1
        mock_client.get.assert_called_once_with("test:key")

    def test_returns_none_on_cache_miss(self):
        """Returns None and False on cache miss."""
        mock_client = MagicMock()
        mock_client.get.return_value = None

        result, is_hit = _get_cached_graph_sync(mock_client, "test:key")

        assert is_hit is False
        assert result is None
        mock_client.get.assert_called_once_with("test:key")

    def test_returns_none_on_redis_error(self):
        """Returns None and False when Redis GET fails."""
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Connection failed")

        result, is_hit = _get_cached_graph_sync(mock_client, "test:key")

        assert is_hit is False
        assert result is None

    def test_returns_none_on_json_decode_error(self):
        """Returns None and False when cached data is invalid JSON."""
        mock_client = MagicMock()
        mock_client.get.return_value = "not valid json"

        result, is_hit = _get_cached_graph_sync(mock_client, "test:key")

        assert is_hit is False
        assert result is None


class TestGetCachedGraph:
    """Tests for get_cached_graph() async function."""

    @pytest.mark.asyncio
    async def test_returns_none_when_redis_unavailable(self):
        """Returns None and False when Redis client is not available."""
        with patch("app.services.social_circles_cache.get_redis", return_value=None):
            result, is_hit = await get_cached_graph("test:key")

        assert is_hit is False
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_cached_response_on_hit(self):
        """Returns cached response and True on cache hit."""
        mock_client = MagicMock()
        test_response = _create_test_response()
        cached_data = json.dumps(test_response.model_dump(mode="json"), default=str)
        mock_client.get.return_value = cached_data

        with patch("app.services.social_circles_cache.get_redis", return_value=mock_client):
            result, is_hit = await get_cached_graph("test:key")

        assert is_hit is True
        assert result is not None
        assert isinstance(result, SocialCirclesResponse)

    @pytest.mark.asyncio
    async def test_returns_none_on_miss(self):
        """Returns None and False on cache miss."""
        mock_client = MagicMock()
        mock_client.get.return_value = None

        with patch("app.services.social_circles_cache.get_redis", return_value=mock_client):
            result, is_hit = await get_cached_graph("test:key")

        assert is_hit is False
        assert result is None


class TestSetCachedGraphSync:
    """Tests for _set_cached_graph_sync() function."""

    def test_stores_serialized_response(self):
        """Stores serialized response with correct TTL."""
        mock_client = MagicMock()
        test_response = _create_test_response()

        _set_cached_graph_sync(mock_client, "test:key", test_response)

        mock_client.setex.assert_called_once()
        call_args = mock_client.setex.call_args
        assert call_args[0][0] == "test:key"
        assert call_args[0][1] == CACHE_TTL_SECONDS
        # Verify the serialized data is valid JSON
        serialized = call_args[0][2]
        data = json.loads(serialized)
        assert "nodes" in data
        assert "edges" in data
        assert "meta" in data

    def test_skips_caching_oversized_data(self):
        """Skips caching when serialized data exceeds size limit."""
        mock_client = MagicMock()
        # Create a response with many nodes to exceed size limit
        large_response = _create_test_response(num_nodes=100000, num_edges=0)

        _set_cached_graph_sync(mock_client, "test:key", large_response)

        # setex should not be called for oversized data
        mock_client.setex.assert_not_called()

    def test_handles_redis_error_gracefully(self):
        """Does not raise exception when Redis SETEX fails."""
        mock_client = MagicMock()
        mock_client.setex.side_effect = Exception("Connection failed")
        test_response = _create_test_response()

        # Should not raise
        _set_cached_graph_sync(mock_client, "test:key", test_response)

        mock_client.setex.assert_called_once()


class TestSetCachedGraph:
    """Tests for set_cached_graph() async function."""

    @pytest.mark.asyncio
    async def test_skips_when_redis_unavailable(self):
        """Skips caching when Redis client is not available."""
        test_response = _create_test_response()

        with patch("app.services.social_circles_cache.get_redis", return_value=None):
            # Should not raise
            await set_cached_graph("test:key", test_response)

    @pytest.mark.asyncio
    async def test_stores_response_when_redis_available(self):
        """Stores response when Redis is available."""
        mock_client = MagicMock()
        test_response = _create_test_response()

        with patch("app.services.social_circles_cache.get_redis", return_value=mock_client):
            await set_cached_graph("test:key", test_response)

        mock_client.setex.assert_called_once()


class TestInvalidateCacheSync:
    """Tests for _invalidate_cache_sync() function."""

    def test_deletes_matching_keys(self):
        """Deletes all keys matching the cache prefix."""
        mock_client = MagicMock()
        mock_keys = [
            "social_circles:graph:abc123",
            "social_circles:graph:def456",
        ]
        mock_client.scan_iter.return_value = iter(mock_keys)
        mock_client.delete.return_value = 2

        deleted = _invalidate_cache_sync(mock_client)

        assert deleted == 2
        mock_client.scan_iter.assert_called_once_with(match=f"{CACHE_KEY_PREFIX}:*")
        mock_client.delete.assert_called_once_with(*mock_keys)

    def test_returns_zero_when_no_keys_found(self):
        """Returns 0 when no matching keys exist."""
        mock_client = MagicMock()
        mock_client.scan_iter.return_value = iter([])

        deleted = _invalidate_cache_sync(mock_client)

        assert deleted == 0
        mock_client.delete.assert_not_called()

    def test_handles_redis_error_gracefully(self):
        """Returns 0 when Redis operation fails."""
        mock_client = MagicMock()
        mock_client.scan_iter.side_effect = Exception("Connection failed")

        deleted = _invalidate_cache_sync(mock_client)

        assert deleted == 0


class TestInvalidateCache:
    """Tests for invalidate_cache() sync function."""

    def test_returns_zero_when_redis_unavailable(self):
        """Returns 0 when Redis client is not available."""
        with patch("app.services.social_circles_cache.get_redis", return_value=None):
            deleted = invalidate_cache()

        assert deleted == 0

    def test_returns_deleted_count_when_redis_available(self):
        """Returns count of deleted keys when Redis is available."""
        mock_client = MagicMock()
        mock_keys = ["social_circles:graph:abc123"]
        mock_client.scan_iter.return_value = iter(mock_keys)
        mock_client.delete.return_value = 1

        with patch("app.services.social_circles_cache.get_redis", return_value=mock_client):
            deleted = invalidate_cache()

        assert deleted == 1


class TestInvalidateCacheAsync:
    """Tests for invalidate_cache_async() function."""

    @pytest.mark.asyncio
    async def test_returns_zero_when_redis_unavailable(self):
        """Returns 0 when Redis client is not available."""
        with patch("app.services.social_circles_cache.get_redis", return_value=None):
            deleted = await invalidate_cache_async()

        assert deleted == 0

    @pytest.mark.asyncio
    async def test_returns_deleted_count_when_redis_available(self):
        """Returns count of deleted keys when Redis is available."""
        mock_client = MagicMock()
        mock_keys = ["social_circles:graph:abc123", "social_circles:graph:def456"]
        mock_client.scan_iter.return_value = iter(mock_keys)
        mock_client.delete.return_value = 2

        with patch("app.services.social_circles_cache.get_redis", return_value=mock_client):
            deleted = await invalidate_cache_async()

        assert deleted == 2


class TestGracefulDegradation:
    """Tests for graceful degradation when Redis is unavailable."""

    def test_get_cache_key_works_without_redis(self):
        """get_cache_key does not require Redis."""
        # This function is pure computation, should always work
        key = get_cache_key(include_binders=True, min_book_count=2, max_books=100)
        assert key is not None
        assert key.startswith(CACHE_KEY_PREFIX)

    @pytest.mark.asyncio
    async def test_get_cached_graph_returns_miss_without_redis(self):
        """get_cached_graph returns cache miss when Redis unavailable."""
        with patch("app.services.social_circles_cache.get_redis", return_value=None):
            result, is_hit = await get_cached_graph("test:key")

        assert result is None
        assert is_hit is False

    @pytest.mark.asyncio
    async def test_set_cached_graph_silently_fails_without_redis(self):
        """set_cached_graph silently fails when Redis unavailable."""
        test_response = _create_test_response()

        with patch("app.services.social_circles_cache.get_redis", return_value=None):
            # Should not raise
            await set_cached_graph("test:key", test_response)

    def test_invalidate_cache_returns_zero_without_redis(self):
        """invalidate_cache returns 0 when Redis unavailable."""
        with patch("app.services.social_circles_cache.get_redis", return_value=None):
            deleted = invalidate_cache()

        assert deleted == 0

    @pytest.mark.asyncio
    async def test_full_flow_works_without_redis(self):
        """Complete cache flow works gracefully without Redis."""
        test_response = _create_test_response()

        with patch("app.services.social_circles_cache.get_redis", return_value=None):
            # Generate cache key (no Redis needed)
            cache_key = get_cache_key(include_binders=True, min_book_count=2, max_books=100)
            assert cache_key is not None

            # Try to get from cache (returns miss)
            result, is_hit = await get_cached_graph(cache_key)
            assert result is None
            assert is_hit is False

            # Try to store in cache (silently fails)
            await set_cached_graph(cache_key, test_response)

            # Try to invalidate (returns 0)
            deleted = await invalidate_cache_async()
            assert deleted == 0


class TestCacheRoundTrip:
    """Tests for complete cache round-trip (store and retrieve)."""

    def test_sync_roundtrip_preserves_data(self):
        """Data stored and retrieved via sync functions is identical."""
        mock_client = MagicMock()
        test_response = _create_test_response()

        # Store
        _set_cached_graph_sync(mock_client, "test:key", test_response)

        # Get the serialized data that was stored
        stored_data = mock_client.setex.call_args[0][2]

        # Simulate retrieval
        mock_client.get.return_value = stored_data
        retrieved, is_hit = _get_cached_graph_sync(mock_client, "test:key")

        assert is_hit is True
        assert retrieved is not None
        assert len(retrieved.nodes) == len(test_response.nodes)
        assert len(retrieved.edges) == len(test_response.edges)
        assert retrieved.meta.total_books == test_response.meta.total_books

    @pytest.mark.asyncio
    async def test_async_roundtrip_preserves_data(self):
        """Data stored and retrieved via async functions is identical."""
        mock_client = MagicMock()
        test_response = _create_test_response()

        with patch("app.services.social_circles_cache.get_redis", return_value=mock_client):
            # Store
            await set_cached_graph("test:key", test_response)

            # Get the serialized data that was stored
            stored_data = mock_client.setex.call_args[0][2]

            # Simulate retrieval
            mock_client.get.return_value = stored_data
            retrieved, is_hit = await get_cached_graph("test:key")

        assert is_hit is True
        assert retrieved is not None
        assert len(retrieved.nodes) == len(test_response.nodes)
        assert len(retrieved.edges) == len(test_response.edges)


class TestCacheConstants:
    """Tests for cache configuration constants."""

    def test_ttl_is_positive(self):
        """Cache TTL is a positive value."""
        assert CACHE_TTL_SECONDS > 0

    def test_max_size_is_reasonable(self):
        """Max cache size is reasonable (between 1MB and 100MB)."""
        assert 1 * 1024 * 1024 <= MAX_CACHE_SIZE_BYTES <= 100 * 1024 * 1024

    def test_prefix_format(self):
        """Cache key prefix has expected format."""
        assert ":" in CACHE_KEY_PREFIX
        assert CACHE_KEY_PREFIX == "social_circles:graph"
