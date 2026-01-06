"""Tests for listings extraction API."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.auth import CurrentUser, require_editor
from app.main import app


def get_mock_editor():
    """Return a mock editor user for tests."""
    return CurrentUser(
        cognito_sub="test-user-123",
        email="test@example.com",
        role="editor",
        db_user=None,
    )


@pytest.fixture
def client():
    """Client with auth overrides for editor access."""
    app.dependency_overrides[require_editor] = get_mock_editor
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def unauthenticated_client():
    """Client WITHOUT auth overrides - for security tests."""
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client


class TestExtractListingEndpoint:
    """Tests for POST /api/v1/listings/extract endpoint."""

    @patch("app.api.v1.listings.match_publisher")
    @patch("app.api.v1.listings.match_binder")
    @patch("app.api.v1.listings.match_author")
    @patch("app.api.v1.listings.scrape_ebay_listing")
    def test_extracts_listing_data(
        self, mock_scrape, mock_author, mock_binder, mock_publisher, client
    ):
        mock_scrape.return_value = {
            "listing_data": {
                "title": "The Queen of the Air",
                "author": "John Ruskin",
                "binder": "Zaehnsdorf",
                "price": 165.00,
                "currency": "USD",
                "volumes": 1,
            },
            "images": [
                {
                    "s3_key": "listings/123456/image_00.jpg",
                    "presigned_url": "https://s3.amazonaws.com/bucket/listings/123456/image_00.jpg?signed",
                }
            ],
            "image_urls": ["https://i.ebayimg.com/img1.jpg"],
            "item_id": "123456",
        }
        mock_author.return_value = None
        mock_binder.return_value = None
        mock_publisher.return_value = None

        response = client.post(
            "/api/v1/listings/extract",
            json={"url": "https://www.ebay.com/itm/123456"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["listing_data"]["title"] == "The Queen of the Air"
        assert data["listing_data"]["author"] == "John Ruskin"
        assert len(data["images"]) == 1

    @patch("app.api.v1.listings.match_publisher")
    @patch("app.api.v1.listings.match_binder")
    @patch("app.api.v1.listings.match_author")
    @patch("app.api.v1.listings.scrape_ebay_listing")
    def test_returns_image_previews(
        self, mock_scrape, mock_author, mock_binder, mock_publisher, client
    ):
        # Images now use S3 presigned URLs instead of base64
        mock_scrape.return_value = {
            "listing_data": {"title": "Test Book", "volumes": 1, "currency": "USD"},
            "images": [
                {
                    "s3_key": "listings/123456/image_00.jpg",
                    "presigned_url": "https://s3.amazonaws.com/bucket/listings/123456/image_00.jpg?signed",
                }
            ],
            "image_urls": ["https://i.ebayimg.com/img1.jpg"],
            "item_id": "123456",
        }
        mock_author.return_value = None
        mock_binder.return_value = None
        mock_publisher.return_value = None

        response = client.post(
            "/api/v1/listings/extract",
            json={"url": "https://www.ebay.com/itm/123456"},
        )

        assert response.status_code == 200
        data = response.json()
        # Images should have S3 key and presigned URL
        assert "s3_key" in data["images"][0]
        assert "presigned_url" in data["images"][0]
        assert data["images"][0]["s3_key"].startswith("listings/")

    def test_validates_ebay_url(self, client):
        response = client.post(
            "/api/v1/listings/extract",
            json={"url": "https://example.com/not-ebay"},
        )

        assert response.status_code == 400
        assert "Invalid eBay URL" in response.json()["detail"]

    def test_validates_url_required(self, client):
        response = client.post("/api/v1/listings/extract", json={})

        assert response.status_code == 422

    @patch("app.api.v1.listings.scrape_ebay_listing")
    def test_handles_rate_limit_error(self, mock_scrape, client):
        from app.services.scraper import ScraperRateLimitError

        mock_scrape.side_effect = ScraperRateLimitError("Rate limited by eBay")

        response = client.post(
            "/api/v1/listings/extract",
            json={"url": "https://www.ebay.com/itm/123456"},
        )

        assert response.status_code == 429
        assert "Rate limit" in response.json()["detail"]

    @patch("app.api.v1.listings.scrape_ebay_listing")
    def test_handles_scraper_error(self, mock_scrape, client):
        from app.services.scraper import ScraperError

        mock_scrape.side_effect = ScraperError("Navigation timeout")

        response = client.post(
            "/api/v1/listings/extract",
            json={"url": "https://www.ebay.com/itm/123456"},
        )

        assert response.status_code == 502
        assert "Scraping failed" in response.json()["detail"]

    @patch("app.api.v1.listings.scrape_ebay_listing")
    def test_handles_extraction_error(self, mock_scrape, client):
        mock_scrape.side_effect = ValueError("Failed to parse listing data")

        response = client.post(
            "/api/v1/listings/extract",
            json={"url": "https://www.ebay.com/itm/123456"},
        )

        assert response.status_code == 422
        assert "extract" in response.json()["detail"].lower()

    @patch("app.api.v1.listings.scrape_ebay_listing")
    @patch("app.api.v1.listings.match_author")
    @patch("app.api.v1.listings.match_binder")
    def test_matches_references(self, mock_binder, mock_author, mock_scrape, client):
        mock_scrape.return_value = {
            "listing_data": {
                "title": "Test Book",
                "author": "John Ruskin",
                "binder": "Zaehnsdorf",
                "volumes": 1,
                "currency": "USD",
            },
            "images": [],
            "image_urls": [],
            "item_id": "123456",
        }
        mock_author.return_value = {"id": 5, "name": "John Ruskin", "similarity": 1.0}
        mock_binder.return_value = {"id": 3, "name": "Zaehnsdorf", "similarity": 1.0}

        response = client.post(
            "/api/v1/listings/extract",
            json={"url": "https://www.ebay.com/itm/123456"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["matches"]["author"]["id"] == 5
        assert data["matches"]["binder"]["id"] == 3

    @patch("app.api.v1.listings.match_publisher")
    @patch("app.api.v1.listings.match_binder")
    @patch("app.api.v1.listings.match_author")
    @patch("app.api.v1.listings.scrape_ebay_listing")
    def test_returns_normalized_url_and_item_id(
        self, mock_scrape, mock_author, mock_binder, mock_publisher, client
    ):
        mock_scrape.return_value = {
            "listing_data": {"title": "Test", "volumes": 1, "currency": "USD"},
            "images": [],
            "image_urls": [],
            "item_id": "123456789",
        }
        mock_author.return_value = None
        mock_binder.return_value = None
        mock_publisher.return_value = None

        response = client.post(
            "/api/v1/listings/extract",
            json={"url": "https://www.ebay.com/itm/some-title/123456789?hash=abc"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ebay_url"] == "https://www.ebay.com/itm/123456789"
        assert data["ebay_item_id"] == "123456789"


class TestListingsEndpointsSecurity:
    """Security tests for listings endpoints (issue #808).

    These POST endpoints trigger external resources (Playwright, Bedrock, S3)
    and MUST require authentication to prevent DoS attacks.
    """

    def test_extract_requires_auth(self, unauthenticated_client):
        """POST /listings/extract requires authentication."""
        response = unauthenticated_client.post(
            "/api/v1/listings/extract",
            json={"url": "https://www.ebay.com/itm/123456"},
        )
        assert response.status_code == 401, (
            f"Expected 401 Unauthorized, got {response.status_code}. "
            "Endpoint must require authentication (issue #808)"
        )

    def test_extract_async_requires_auth(self, unauthenticated_client):
        """POST /listings/extract-async requires authentication."""
        response = unauthenticated_client.post(
            "/api/v1/listings/extract-async",
            json={"url": "https://www.ebay.com/itm/123456"},
        )
        assert response.status_code == 401, (
            f"Expected 401 Unauthorized, got {response.status_code}. "
            "Endpoint must require authentication (issue #808)"
        )
