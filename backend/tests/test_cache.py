"""Tests for cache module."""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestCachedDecorator:
    """Tests for the @cached decorator."""

    def test_cache_miss_calls_function_and_stores_result(self):
        """On cache miss, function is called and result is stored."""
        from app.cache import cached

        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # Cache miss

        with patch("app.cache.get_redis", return_value=mock_redis):

            @cached(key="test:key", ttl=300)
            def my_func():
                return {"data": "value"}

            result = my_func()

        assert result == {"data": "value"}
        mock_redis.get.assert_called_once_with("test:key")
        mock_redis.setex.assert_called_once()
        # Verify TTL and serialized value
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "test:key"
        assert call_args[0][1] == 300
        assert json.loads(call_args[0][2]) == {"data": "value"}

    def test_cache_hit_returns_cached_value(self):
        """On cache hit, cached value is returned without calling function."""
        from app.cache import cached

        mock_redis = MagicMock()
        mock_redis.get.return_value = '{"cached": true}'  # Cache hit

        call_count = 0

        with patch("app.cache.get_redis", return_value=mock_redis):

            @cached(key="test:key", ttl=300)
            def my_func():
                nonlocal call_count
                call_count += 1
                return {"cached": False}

            result = my_func()

        assert result == {"cached": True}
        assert call_count == 0  # Function was NOT called
        mock_redis.setex.assert_not_called()

    def test_graceful_degradation_when_redis_unavailable(self):
        """Function works normally when Redis is not available."""
        from app.cache import cached

        with patch("app.cache.get_redis", return_value=None):

            @cached(key="test:key", ttl=300)
            def my_func():
                return {"data": "value"}

            result = my_func()

        assert result == {"data": "value"}

    def test_graceful_degradation_on_redis_get_error(self):
        """Function works normally when Redis GET fails."""
        from app.cache import cached

        mock_redis = MagicMock()
        mock_redis.get.side_effect = Exception("Connection failed")

        with patch("app.cache.get_redis", return_value=mock_redis):

            @cached(key="test:key", ttl=300)
            def my_func():
                return {"data": "value"}

            result = my_func()

        assert result == {"data": "value"}

    def test_graceful_degradation_on_redis_set_error(self):
        """Function works normally when Redis SET fails."""
        from app.cache import cached

        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # Cache miss
        mock_redis.setex.side_effect = Exception("Connection failed")

        with patch("app.cache.get_redis", return_value=mock_redis):

            @cached(key="test:key", ttl=300)
            def my_func():
                return {"data": "value"}

            result = my_func()

        # Should still return result despite SET failing
        assert result == {"data": "value"}


class TestGetRedis:
    """Tests for get_redis function."""

    def test_returns_none_when_redis_url_empty(self):
        """Returns None when REDIS_URL is not configured."""
        from app.cache import _reset_client, get_redis

        _reset_client()  # Reset singleton

        with patch("app.cache.get_settings") as mock_settings:
            mock_settings.return_value.redis_url = ""
            client = get_redis()

        assert client is None

    def test_returns_client_when_redis_url_configured(self):
        """Returns Redis client when REDIS_URL is configured."""
        from app.cache import _reset_client, get_redis

        _reset_client()  # Reset singleton

        with patch("app.cache.get_settings") as mock_settings:
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            with patch("app.cache.redis.from_url") as mock_from_url:
                mock_client = MagicMock()
                mock_from_url.return_value = mock_client

                client = get_redis()

        assert client == mock_client
        mock_from_url.assert_called_once()

    def test_caches_client_instance(self):
        """Client instance is cached (singleton pattern)."""
        from app.cache import _reset_client, get_redis

        _reset_client()

        with patch("app.cache.get_settings") as mock_settings:
            mock_settings.return_value.redis_url = "redis://localhost:6379"
            with patch("app.cache.redis.from_url") as mock_from_url:
                mock_client = MagicMock()
                mock_from_url.return_value = mock_client

                client1 = get_redis()
                client2 = get_redis()

        # from_url only called once
        assert mock_from_url.call_count == 1
        assert client1 is client2
