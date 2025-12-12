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
