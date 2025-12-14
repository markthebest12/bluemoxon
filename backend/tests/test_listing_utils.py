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
