"""Tests for Wayback archive service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestArchiveUrl:
    """Tests for archive_url function."""

    @pytest.mark.asyncio
    async def test_archive_url_success(self):
        """Test successful archive returns archived URL."""
        from app.services.archive import archive_url

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Location": "/web/20251212120000/https://www.ebay.com/itm/123"
        }
        mock_response.url = "https://web.archive.org/web/20251212120000/https://www.ebay.com/itm/123"

        with patch("app.services.archive.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await archive_url("https://www.ebay.com/itm/123")

            assert result["status"] == "success"
            assert "web.archive.org" in result["archived_url"]

    @pytest.mark.asyncio
    async def test_archive_url_failure(self):
        """Test failed archive returns failed status."""
        from app.services.archive import archive_url

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service unavailable"

        with patch("app.services.archive.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await archive_url("https://www.ebay.com/itm/123")

            assert result["status"] == "failed"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_archive_url_timeout(self):
        """Test timeout returns failed status."""
        import httpx

        from app.services.archive import archive_url

        with patch("app.services.archive.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.TimeoutException("Timeout")
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await archive_url("https://www.ebay.com/itm/123")

            assert result["status"] == "failed"
            assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_archive_url_no_url(self):
        """Test empty URL returns failed status."""
        from app.services.archive import archive_url

        result = await archive_url("")

        assert result["status"] == "failed"
        assert "No URL" in result["error"]
