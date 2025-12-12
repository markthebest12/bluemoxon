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
        mock_response.url = (
            "https://web.archive.org/web/20251212120000/https://www.ebay.com/itm/123"
        )

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


class TestArchiveEndpoint:
    """Tests for POST /books/{id}/archive-source endpoint."""

    def test_archive_source_no_url_returns_error(self, client, db):
        """Test archive endpoint returns error when no source_url."""
        from app.models.book import Book

        book = Book(title="Test Book", status="EVALUATING")
        db.add(book)
        db.commit()
        db.refresh(book)

        response = client.post(f"/api/v1/books/{book.id}/archive-source")

        assert response.status_code == 400
        assert "source_url" in response.json()["detail"].lower()

    def test_archive_source_already_archived_returns_existing(self, client, db):
        """Test archive endpoint returns existing URL if already archived."""
        from app.models.book import Book

        book = Book(
            title="Test Book",
            source_url="https://www.ebay.com/itm/123456",
            source_archived_url="https://web.archive.org/web/123/https://ebay.com/itm/123456",
            archive_status="success",
            status="EVALUATING",
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        response = client.post(f"/api/v1/books/{book.id}/archive-source")

        assert response.status_code == 200
        data = response.json()
        assert data["archive_status"] == "success"
        assert "web.archive.org" in data["source_archived_url"]

    def test_archive_source_book_not_found(self, client, db):
        """Test archive endpoint returns 404 for nonexistent book."""
        response = client.post("/api/v1/books/99999/archive-source")
        assert response.status_code == 404
