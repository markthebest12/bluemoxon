"""Unit tests for scraper handler banner detection."""

import io
import pytest
from PIL import Image

from handler import is_likely_banner, BANNER_ASPECT_RATIO_THRESHOLD, BANNER_POSITION_WINDOW


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
