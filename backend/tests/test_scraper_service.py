"""Tests for scraper invocation service."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.scraper import (
    ScraperError,
    ScraperRateLimitError,
    invoke_scraper,
    scrape_ebay_listing,
)


class TestInvokeScraper:
    """Tests for the low-level Lambda invocation."""

    @patch("app.services.scraper.get_lambda_client")
    def test_invokes_scraper_lambda(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock successful response with S3 keys
        response_payload = {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "html": "<html>test</html>",
                    "image_urls": ["https://i.ebayimg.com/test.jpg"],
                    "s3_keys": ["listings/123456/image_00.jpg"],
                    "item_id": "123456",
                }
            ),
        }
        mock_client.invoke.return_value = {
            "StatusCode": 200,
            "Payload": MagicMock(
                read=MagicMock(return_value=json.dumps(response_payload).encode())
            ),
        }

        invoke_scraper("https://www.ebay.com/itm/123456")

        mock_client.invoke.assert_called_once()
        call_kwargs = mock_client.invoke.call_args[1]
        assert "bluemoxon" in call_kwargs["FunctionName"]
        assert "scraper" in call_kwargs["FunctionName"]

        payload = json.loads(call_kwargs["Payload"])
        assert payload["url"] == "https://www.ebay.com/itm/123456"

    @patch("app.services.scraper.get_lambda_client")
    def test_returns_html_and_s3_keys(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        response_payload = {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "html": "<html><title>Test Book</title></html>",
                    "image_urls": [
                        "https://i.ebayimg.com/img1.jpg",
                        "https://i.ebayimg.com/img2.jpg",
                    ],
                    "s3_keys": [
                        "listings/123456/image_00.jpg",
                        "listings/123456/image_01.jpg",
                    ],
                    "item_id": "123456",
                }
            ),
        }
        mock_client.invoke.return_value = {
            "StatusCode": 200,
            "Payload": MagicMock(
                read=MagicMock(return_value=json.dumps(response_payload).encode())
            ),
        }

        result = invoke_scraper("https://www.ebay.com/itm/123456")

        assert result["html"] == "<html><title>Test Book</title></html>"
        assert len(result["image_urls"]) == 2
        assert len(result["s3_keys"]) == 2
        assert result["s3_keys"][0] == "listings/123456/image_00.jpg"

    @patch("app.services.scraper.get_lambda_client")
    def test_raises_on_rate_limit(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        response_payload = {
            "statusCode": 429,
            "body": json.dumps({"error": "Rate limited", "html": "<html>blocked</html>"}),
        }
        mock_client.invoke.return_value = {
            "StatusCode": 200,  # Lambda itself succeeded
            "Payload": MagicMock(
                read=MagicMock(return_value=json.dumps(response_payload).encode())
            ),
        }

        with pytest.raises(ScraperRateLimitError, match="Rate limited"):
            invoke_scraper("https://www.ebay.com/itm/123456")

    @patch("app.services.scraper.get_lambda_client")
    def test_raises_on_scraper_error(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        response_payload = {
            "statusCode": 500,
            "body": json.dumps({"error": "Navigation timeout"}),
        }
        mock_client.invoke.return_value = {
            "StatusCode": 200,
            "Payload": MagicMock(
                read=MagicMock(return_value=json.dumps(response_payload).encode())
            ),
        }

        with pytest.raises(ScraperError, match="Navigation timeout"):
            invoke_scraper("https://www.ebay.com/itm/123456")

    @patch("app.services.scraper.get_lambda_client")
    def test_raises_on_lambda_error(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_client.invoke.return_value = {
            "StatusCode": 500,
            "FunctionError": "Unhandled",
            "Payload": MagicMock(read=MagicMock(return_value=b'{"errorMessage": "Out of memory"}')),
        }

        with pytest.raises(ScraperError, match="Lambda execution failed"):
            invoke_scraper("https://www.ebay.com/itm/123456")

    @patch("app.services.scraper.get_lambda_client")
    def test_passes_fetch_images_flag(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        response_payload = {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "html": "<html/>",
                    "image_urls": [],
                    "s3_keys": [],
                    "item_id": "123456",
                }
            ),
        }
        mock_client.invoke.return_value = {
            "StatusCode": 200,
            "Payload": MagicMock(
                read=MagicMock(return_value=json.dumps(response_payload).encode())
            ),
        }

        invoke_scraper("https://www.ebay.com/itm/123456", fetch_images=False)

        call_kwargs = mock_client.invoke.call_args[1]
        payload = json.loads(call_kwargs["Payload"])
        assert payload["fetch_images"] is False


class TestScrapeEbayListing:
    """Tests for the high-level scraping function."""

    @patch("app.services.scraper.generate_presigned_url")
    @patch("app.services.scraper.invoke_scraper")
    @patch("app.services.scraper.extract_listing_data")
    @patch.dict("os.environ", {"IMAGES_BUCKET": "test-bucket"})
    def test_scrapes_and_extracts_data(self, mock_extract, mock_invoke, mock_presign):
        mock_invoke.return_value = {
            "html": "<html><title>The Queen of the Air</title></html>",
            "image_urls": ["https://i.ebayimg.com/img1.jpg"],
            "s3_keys": ["listings/123456/image_00.jpg"],
            "item_id": "123456",
        }
        mock_extract.return_value = {
            "title": "The Queen of the Air",
            "author": "John Ruskin",
            "price": 165.00,
            "currency": "USD",
            "volumes": 1,
        }
        mock_presign.return_value = "https://s3.amazonaws.com/signed-url"

        result = scrape_ebay_listing("https://www.ebay.com/itm/123456")

        assert result["listing_data"]["title"] == "The Queen of the Air"
        assert result["listing_data"]["author"] == "John Ruskin"
        assert len(result["images"]) == 1
        assert result["images"][0]["s3_key"] == "listings/123456/image_00.jpg"
        assert result["images"][0]["presigned_url"] == "https://s3.amazonaws.com/signed-url"
        assert result["image_urls"] == ["https://i.ebayimg.com/img1.jpg"]

    @patch("app.services.scraper.invoke_scraper")
    @patch("app.services.scraper.extract_listing_data")
    def test_handles_no_images(self, mock_extract, mock_invoke):
        mock_invoke.return_value = {
            "html": "<html>test</html>",
            "image_urls": [],
            "s3_keys": [],
            "item_id": "123456",
        }
        mock_extract.return_value = {
            "title": "Test Book",
            "author": "Author",
            "price": 50.00,
            "currency": "USD",
            "volumes": 1,
        }

        result = scrape_ebay_listing("https://www.ebay.com/itm/123456")

        assert result["images"] == []
        assert result["image_urls"] == []

    @patch("app.services.scraper.generate_presigned_url")
    @patch("app.services.scraper.invoke_scraper")
    @patch("app.services.scraper.extract_listing_data")
    @patch("app.services.scraper.get_settings")
    def test_generates_presigned_urls_for_s3_images(
        self, mock_get_settings, mock_extract, mock_invoke, mock_presign
    ):
        # Mock get_settings to return test bucket name
        mock_settings = MagicMock()
        mock_settings.images_bucket = "test-bucket"
        mock_get_settings.return_value = mock_settings

        mock_invoke.return_value = {
            "html": "<html/>",
            "image_urls": ["https://i.ebayimg.com/img1.jpg"],
            "s3_keys": ["listings/123456/image_00.jpg"],
            "item_id": "123456",
        }
        mock_extract.return_value = {"title": "Book", "volumes": 1, "currency": "USD"}
        mock_presign.return_value = (
            "https://s3.amazonaws.com/bucket/listings/123456/image_00.jpg?signed"
        )

        result = scrape_ebay_listing("https://www.ebay.com/itm/123456")

        # Images should have S3 keys and presigned URLs
        assert result["images"][0]["s3_key"] == "listings/123456/image_00.jpg"
        assert "presigned_url" in result["images"][0]
        mock_presign.assert_called_once_with("test-bucket", "listings/123456/image_00.jpg")

    @patch("app.services.scraper.invoke_scraper")
    def test_propagates_scraper_errors(self, mock_invoke):
        mock_invoke.side_effect = ScraperRateLimitError("Rate limited by eBay")

        with pytest.raises(ScraperRateLimitError):
            scrape_ebay_listing("https://www.ebay.com/itm/123456")

    @patch("app.services.scraper.invoke_scraper")
    @patch("app.services.scraper.extract_listing_data")
    def test_propagates_extraction_errors(self, mock_extract, mock_invoke):
        mock_invoke.return_value = {
            "html": "<html>malformed</html>",
            "image_urls": [],
            "s3_keys": [],
            "item_id": "123456",
        }
        mock_extract.side_effect = ValueError("Failed to parse listing data")

        with pytest.raises(ValueError, match="Failed to parse"):
            scrape_ebay_listing("https://www.ebay.com/itm/123456")

    @patch("app.services.scraper.generate_presigned_url")
    @patch("app.services.scraper.invoke_scraper")
    @patch("app.services.scraper.extract_listing_data")
    @patch("app.services.scraper.get_settings")
    def test_uses_passed_item_id_over_scraper_result(
        self, mock_get_settings, mock_extract, mock_invoke, mock_presign
    ):
        """Should use the item_id passed to the function, not the scraper result."""
        mock_settings = MagicMock()
        mock_settings.images_bucket = "test-bucket"
        mock_get_settings.return_value = mock_settings

        mock_invoke.return_value = {
            "html": "<html/>",
            "image_urls": [],
            "s3_keys": [],
            "item_id": "scraper_item_id",  # Scraper returns different ID
        }
        mock_extract.return_value = {"title": "Book", "volumes": 1, "currency": "USD"}

        # Pass specific item_id to function
        result = scrape_ebay_listing("https://www.ebay.com/itm/c492afa0", item_id="316529574873")

        # Should use the passed item_id, not the scraper's
        assert result["item_id"] == "316529574873"

    @patch("app.services.scraper.invoke_scraper")
    @patch("app.services.scraper.extract_listing_data")
    def test_raises_when_no_valid_item_id(self, mock_extract, mock_invoke):
        """Should raise ValueError when neither item_id is passed nor scraper returns one."""
        mock_invoke.return_value = {
            "html": "<html/>",
            "image_urls": [],
            "s3_keys": [],
            "item_id": "",  # Scraper returns empty item_id
        }
        mock_extract.return_value = {"title": "Book", "volumes": 1, "currency": "USD"}

        # No item_id passed and scraper returns empty
        with pytest.raises(ValueError, match="Scraper did not return a valid item ID"):
            scrape_ebay_listing("https://www.ebay.com/itm/c492afa0")


class TestInvokeScraperItemIdParameter:
    """Tests for item_id parameter handling in invoke_scraper."""

    @patch("app.services.scraper.get_lambda_client")
    def test_passes_item_id_in_payload(self, mock_get_client):
        """Should include item_id in Lambda payload when provided."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        response_payload = {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "html": "<html/>",
                    "image_urls": [],
                    "s3_keys": [],
                    "item_id": "316529574873",
                }
            ),
        }
        mock_client.invoke.return_value = {
            "StatusCode": 200,
            "Payload": MagicMock(
                read=MagicMock(return_value=json.dumps(response_payload).encode())
            ),
        }

        invoke_scraper("https://www.ebay.com/itm/c492afa0", item_id="316529574873")

        call_kwargs = mock_client.invoke.call_args[1]
        payload = json.loads(call_kwargs["Payload"])
        assert payload["item_id"] == "316529574873"

    @patch("app.services.scraper.get_lambda_client")
    def test_omits_item_id_when_not_provided(self, mock_get_client):
        """Should not include item_id in payload when not provided."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        response_payload = {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "html": "<html/>",
                    "image_urls": [],
                    "s3_keys": [],
                    "item_id": "123456",
                }
            ),
        }
        mock_client.invoke.return_value = {
            "StatusCode": 200,
            "Payload": MagicMock(
                read=MagicMock(return_value=json.dumps(response_payload).encode())
            ),
        }

        invoke_scraper("https://www.ebay.com/itm/123456")

        call_kwargs = mock_client.invoke.call_args[1]
        payload = json.loads(call_kwargs["Payload"])
        assert "item_id" not in payload
