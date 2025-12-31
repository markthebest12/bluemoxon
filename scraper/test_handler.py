"""Unit tests for scraper handler."""

import io
from unittest.mock import patch, MagicMock

import pytest
from handler import extract_item_id, is_ebay_us_short_url, is_likely_banner, handler
from PIL import Image


class TestHandlerExtractListingsMode:
    """Tests for extract_listings mode in handler."""

    def test_search_url_with_extract_listings_does_not_fail_on_item_id(self):
        """When extract_listings=True, search URLs should not fail trying to extract item ID.

        This is a regression test for the bug where FMV search URLs like
        /sch/i.html?... would fail with "Could not extract eBay item ID".
        """
        search_url = "https://www.ebay.com/sch/i.html?_nkw=christmas+carol&LH_Complete=1&LH_Sold=1"
        event = {
            "url": search_url,
            "fetch_images": False,
            "extract_listings": True,
        }

        # The handler should NOT raise ValueError for search URL in extract_listings mode
        # It will fail for other reasons (Playwright not available in tests),
        # but not with "Could not extract eBay item ID"
        try:
            handler(event, None)
        except ValueError as e:
            if "Could not extract eBay item ID" in str(e):
                pytest.fail(f"Handler should not try to extract item ID for search URLs when extract_listings=True: {e}")
            # Other ValueErrors are fine (e.g., Playwright issues in test env)
        except Exception:
            # Non-ValueError exceptions are expected (Playwright not available)
            pass


class TestExtractItemId:
    """Tests for extract_item_id function."""

    def test_uses_provided_id_when_given(self):
        """Should use provided_id when available, even if URL has different ID."""
        # URL has numeric ID but provided_id should take precedence
        result = extract_item_id(
            "https://www.ebay.com/itm/123456789012",
            provided_id="987654321098"
        )
        assert result == "987654321098"

    def test_uses_provided_id_for_alphanumeric_short_urls(self):
        """Should use provided_id for URLs with alphanumeric IDs that regex can't match."""
        # URL has alphanumeric ID that regex can't extract
        result = extract_item_id(
            "https://www.ebay.com/itm/c492afa0",
            provided_id="316529574873"
        )
        assert result == "316529574873"

    def test_extracts_from_standard_url(self):
        """Should extract numeric ID from standard eBay URL."""
        result = extract_item_id("https://www.ebay.com/itm/316529574873")
        assert result == "316529574873"

    def test_extracts_from_item_param_url(self):
        """Should extract numeric ID from URL with item= parameter."""
        result = extract_item_id("https://www.ebay.com/itm?item=316529574873")
        assert result == "316529574873"

    def test_raises_on_alphanumeric_url_without_provided_id(self):
        """Should raise ValueError for alphanumeric URL when no provided_id given."""
        with pytest.raises(ValueError, match="Could not extract eBay item ID"):
            extract_item_id("https://www.ebay.com/itm/c492afa0")

    def test_raises_on_invalid_url(self):
        """Should raise ValueError for URLs that don't contain valid item ID."""
        with pytest.raises(ValueError, match="Could not extract eBay item ID"):
            extract_item_id("https://www.ebay.com/some/other/path")

    def test_raises_on_empty_url(self):
        """Should raise ValueError for empty URL."""
        with pytest.raises(ValueError, match="Could not extract eBay item ID"):
            extract_item_id("")

    def test_provided_id_empty_string_not_used(self):
        """Empty string provided_id should not be used, should extract from URL."""
        result = extract_item_id(
            "https://www.ebay.com/itm/316529574873",
            provided_id=""
        )
        assert result == "316529574873"

    def test_provided_id_none_extracts_from_url(self):
        """None provided_id should extract from URL."""
        result = extract_item_id(
            "https://www.ebay.com/itm/316529574873",
            provided_id=None
        )
        assert result == "316529574873"


class TestIsEbayUsShortUrl:
    """Tests for is_ebay_us_short_url function."""

    def test_ebay_us_short_url_detected(self):
        """Should detect ebay.us short URLs."""
        assert is_ebay_us_short_url("https://ebay.us/m/egMUqO") is True

    def test_ebay_us_with_www_detected(self):
        """Should detect www.ebay.us short URLs."""
        assert is_ebay_us_short_url("https://www.ebay.us/m/xyz123") is True

    def test_ebay_us_http_detected(self):
        """Should detect http ebay.us URLs."""
        assert is_ebay_us_short_url("http://ebay.us/m/abc") is True

    def test_standard_ebay_com_not_short_url(self):
        """Standard ebay.com URLs should not be detected as short URLs."""
        assert is_ebay_us_short_url("https://www.ebay.com/itm/123456789") is False

    def test_mobile_ebay_not_short_url(self):
        """Mobile ebay.com URLs should not be detected as short URLs."""
        assert is_ebay_us_short_url("https://m.ebay.com/itm/123456789") is False

    def test_empty_url_not_short_url(self):
        """Empty URL should not be detected as short URL."""
        assert is_ebay_us_short_url("") is False

    def test_invalid_url_not_short_url(self):
        """Invalid URL should not be detected as short URL."""
        assert is_ebay_us_short_url("not a url") is False


def create_test_image(width: int, height: int) -> bytes:
    """Create a test image with given dimensions."""
    img = Image.new("RGB", (width, height), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


class TestIsLikelyBanner:
    """Tests for is_likely_banner function."""

    def test_wide_image_at_end_is_banner(self):
        """Wide image (3:1 ratio) in last position should be detected as banner."""
        image_data = create_test_image(1200, 300)  # 4:1 ratio
        assert is_likely_banner(image_data, position=17, total_images=18) is True

    def test_portrait_image_at_end_not_banner(self):
        """Portrait image (2:3 ratio) in last position should NOT be detected as banner."""
        image_data = create_test_image(800, 1200)  # 0.67:1 ratio
        assert is_likely_banner(image_data, position=17, total_images=18) is False

    def test_wide_image_at_start_not_banner(self):
        """Wide image at start of carousel should NOT be detected (position filter)."""
        image_data = create_test_image(1200, 300)  # 4:1 ratio
        assert is_likely_banner(image_data, position=0, total_images=18) is False

    def test_wide_image_in_middle_not_banner(self):
        """Wide image in middle of carousel should NOT be detected."""
        image_data = create_test_image(1200, 300)  # 4:1 ratio
        assert is_likely_banner(image_data, position=10, total_images=18) is False

    def test_square_image_at_end_not_banner(self):
        """Square image at end should NOT be detected (aspect ratio filter)."""
        image_data = create_test_image(800, 800)  # 1:1 ratio
        assert is_likely_banner(image_data, position=17, total_images=18) is False

    def test_single_image_listing_not_filtered(self):
        """Single image listings should never be filtered."""
        image_data = create_test_image(1200, 300)  # 4:1 ratio
        assert is_likely_banner(image_data, position=0, total_images=1) is False

    def test_boundary_aspect_ratio(self):
        """Image exactly at threshold should be detected."""
        # 2.01:1 ratio (just over threshold of 2.0)
        image_data = create_test_image(1005, 500)
        assert is_likely_banner(image_data, position=17, total_images=18) is True

    def test_boundary_position(self):
        """Image at boundary of position window should be detected."""
        image_data = create_test_image(1200, 300)
        # Position 15 in 18 images = index 15, total-3 = 15, so 15 >= 15 = True
        assert is_likely_banner(image_data, position=15, total_images=18) is True
        # Position 14 should NOT be detected (14 < 15)
        assert is_likely_banner(image_data, position=14, total_images=18) is False

    def test_invalid_image_data_fails_open(self):
        """Invalid image data should fail open (not filter)."""
        assert is_likely_banner(b"not an image", position=17, total_images=18) is False

    def test_empty_image_data_fails_open(self):
        """Empty image data should fail open."""
        assert is_likely_banner(b"", position=17, total_images=18) is False
