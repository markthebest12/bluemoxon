import pytest

from app.services.listing import is_valid_ebay_url, normalize_ebay_url


class TestEbayUrlParsing:
    def test_standard_url(self):
        url = "https://www.ebay.com/itm/317495720025"
        normalized, item_id = normalize_ebay_url(url)
        assert normalized == "https://www.ebay.com/itm/317495720025"
        assert item_id == "317495720025"

    def test_mobile_url(self):
        url = "https://m.ebay.com/itm/317495720025"
        normalized, item_id = normalize_ebay_url(url)
        assert normalized == "https://www.ebay.com/itm/317495720025"
        assert item_id == "317495720025"

    def test_url_without_www(self):
        url = "https://ebay.com/itm/317495720025"
        normalized, item_id = normalize_ebay_url(url)
        assert normalized == "https://www.ebay.com/itm/317495720025"

    def test_url_with_slug(self):
        url = "https://www.ebay.com/itm/Antique-Book-Title/317495720025"
        normalized, item_id = normalize_ebay_url(url)
        assert normalized == "https://www.ebay.com/itm/317495720025"
        assert item_id == "317495720025"

    def test_url_with_tracking_params(self):
        url = "https://www.ebay.com/itm/317495720025?hash=item49f&mkcid=1"
        normalized, item_id = normalize_ebay_url(url)
        assert normalized == "https://www.ebay.com/itm/317495720025"

    def test_invalid_url(self):
        with pytest.raises(ValueError, match="Invalid eBay URL"):
            normalize_ebay_url("https://amazon.com/item/123")

    def test_is_valid_ebay_url(self):
        assert is_valid_ebay_url("https://www.ebay.com/itm/123") is True
        assert is_valid_ebay_url("https://m.ebay.com/itm/123") is True
        assert is_valid_ebay_url("https://amazon.com/item/123") is False
        assert is_valid_ebay_url("not a url") is False

    def test_ebay_co_uk_url_validation(self):
        """Test that ebay.co.uk URLs are recognized as valid."""
        assert is_valid_ebay_url("https://www.ebay.co.uk/itm/123456789") is True
        assert is_valid_ebay_url("https://ebay.co.uk/itm/123456789") is True
        assert is_valid_ebay_url("https://m.ebay.co.uk/itm/123456789") is True
        assert is_valid_ebay_url("https://www.ebay.co.uk/itm/Book-Title/123456789") is True

    def test_ebay_co_uk_url_normalization(self):
        """Test that ebay.co.uk URLs normalize correctly."""
        url = "https://www.ebay.co.uk/itm/Antique-Book/317495720025?hash=abc"
        normalized, item_id = normalize_ebay_url(url)
        assert normalized == "https://www.ebay.com/itm/317495720025"
        assert item_id == "317495720025"

    def test_ebay_us_short_url_validation(self):
        """Test that ebay.us short URLs are recognized as valid."""
        assert is_valid_ebay_url("https://ebay.us/m/9R8Zfd") is True
        assert is_valid_ebay_url("https://www.ebay.us/m/9R8Zfd") is True
        assert is_valid_ebay_url("https://ebay.us/") is False  # No path

    @pytest.mark.skip(reason="Requires valid ebay.us short URL - test manually with fresh URL")
    def test_ebay_us_short_url_normalization(self):
        """Test that ebay.us short URLs resolve to canonical URLs.

        This test makes a real HTTP request to follow the redirect.
        Skipped by default since ebay.us short URLs can expire.
        To test manually, find a fresh short URL and run:
            pytest tests/test_listing_utils.py::TestEbayUrlParsing::test_ebay_us_short_url_normalization -v --runxfail
        """
        url = "https://ebay.us/m/9R8Zfd"
        normalized, item_id = normalize_ebay_url(url)

        # Should resolve to the canonical eBay URL
        assert normalized.startswith("https://www.ebay.com/itm/")
        assert item_id.isdigit()
        assert len(item_id) > 5  # eBay item IDs are long numbers

    def test_ebay_us_expired_url_error_message(self):
        """Test that expired ebay.us URLs give a clear error message."""
        from unittest.mock import MagicMock, patch

        # Mock httpx to simulate an expired URL redirect to error page
        mock_response = MagicMock()
        mock_response.url = "https://www.ebay.com/n/error?statuscode=500"

        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.get.return_value = mock_response
            mock_client.return_value = mock_instance

            with pytest.raises(ValueError, match="Short URL has expired or is invalid"):
                normalize_ebay_url("https://ebay.us/m/expired123")

    def test_ebay_us_too_many_redirects_error(self):
        """Test that redirect loops give a clear error message."""
        from unittest.mock import MagicMock, patch

        import httpx

        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.get.side_effect = httpx.TooManyRedirects("Too many redirects")
            mock_client.return_value = mock_instance

            with pytest.raises(ValueError, match="Short URL has expired or is invalid"):
                normalize_ebay_url("https://ebay.us/m/looping123")

    def test_mobile_ebay_com_short_url_validation(self):
        """Test that mobile eBay URLs with alphanumeric short IDs are recognized as valid."""
        # Mobile eBay URLs can have alphanumeric short IDs instead of numeric item IDs
        assert is_valid_ebay_url("https://www.ebay.com/itm/946e590b") is True
        assert is_valid_ebay_url("https://m.ebay.com/itm/abc123def") is True
        assert is_valid_ebay_url("https://ebay.com/itm/946e590b") is True

    def test_mobile_ebay_com_short_url_normalization(self):
        """Test that mobile eBay URLs with alphanumeric short IDs resolve to canonical URLs.

        Mobile eBay often generates short alphanumeric IDs (e.g., 946e590b) instead of
        the full numeric item ID. These need to be resolved by following redirects.
        """
        from unittest.mock import MagicMock, patch

        # Mock httpx to simulate the redirect from short ID to full item ID
        mock_response = MagicMock()
        mock_response.url = "https://www.ebay.com/itm/287023271679"

        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.get.return_value = mock_response
            mock_client.return_value = mock_instance

            url = "https://www.ebay.com/itm/946e590b"
            normalized, item_id = normalize_ebay_url(url)

            # Should resolve to the canonical eBay URL with full numeric item ID
            assert normalized == "https://www.ebay.com/itm/287023271679"
            assert item_id == "287023271679"
            assert item_id.isdigit()
            assert len(item_id) > 5
