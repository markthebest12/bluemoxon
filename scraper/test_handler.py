"""Unit tests for scraper handler."""

import io

import pytest
from handler import extract_item_id, is_likely_banner
from PIL import Image


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
