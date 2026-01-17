"""Tests for image processor Lambda worker."""

import sys
from unittest.mock import MagicMock

# Mock rembg before importing handler (Lambda dependency not in backend env)
sys.modules["rembg"] = MagicMock()


class TestQualityValidation:
    """Tests for image quality validation."""

    def test_area_check_passes_when_sufficient(self):
        """Should pass when subject area >= 50% of original."""
        from lambdas.image_processor.handler import validate_image_quality

        result = validate_image_quality(
            original_width=100,
            original_height=100,
            subject_width=80,
            subject_height=80,
        )
        assert result["passed"] is True

    def test_area_check_fails_when_insufficient(self):
        """Should fail when subject area < 50% of original."""
        from lambdas.image_processor.handler import validate_image_quality

        result = validate_image_quality(
            original_width=100,
            original_height=100,
            subject_width=50,
            subject_height=50,
        )
        assert result["passed"] is False
        assert result["reason"] == "area_too_small"

    def test_aspect_ratio_check_passes_when_similar(self):
        """Should pass when aspect ratio within +-20%."""
        from lambdas.image_processor.handler import validate_image_quality

        result = validate_image_quality(
            original_width=100,
            original_height=150,
            subject_width=90,
            subject_height=130,
        )
        assert result["passed"] is True

    def test_aspect_ratio_check_fails_when_different(self):
        """Should fail when aspect ratio differs by >20%."""
        from lambdas.image_processor.handler import validate_image_quality

        result = validate_image_quality(
            original_width=100,
            original_height=100,
            subject_width=100,
            subject_height=50,
        )
        assert result["passed"] is False
        assert result["reason"] == "aspect_ratio_mismatch"


class TestRetryStrategy:
    """Tests for retry strategy with model fallback."""

    def test_first_attempt_uses_u2net_alpha(self):
        """First attempt should use u2net with alpha matting."""
        from lambdas.image_processor.handler import get_processing_config

        config = get_processing_config(attempt=1)
        assert config["model"] == "u2net"
        assert config["alpha_matting"] is True
        assert config["model_name"] == "u2net-alpha"

    def test_second_attempt_uses_u2net_alpha(self):
        """Second attempt should retry u2net with alpha matting."""
        from lambdas.image_processor.handler import get_processing_config

        config = get_processing_config(attempt=2)
        assert config["model"] == "u2net"
        assert config["alpha_matting"] is True

    def test_third_attempt_uses_isnet(self):
        """Third attempt should fall back to isnet-general-use."""
        from lambdas.image_processor.handler import get_processing_config

        config = get_processing_config(attempt=3)
        assert config["model"] == "isnet-general-use"
        assert config["alpha_matting"] is False
        assert config["model_name"] == "isnet-general-use"


class TestBrightnessCalculation:
    """Tests for brightness-based background color selection."""

    def test_dark_book_gets_black_background(self):
        """Book with brightness < 128 should get black background."""
        from lambdas.image_processor.handler import select_background_color

        assert select_background_color(brightness=100) == "black"
        assert select_background_color(brightness=0) == "black"
        assert select_background_color(brightness=127) == "black"

    def test_light_book_gets_white_background(self):
        """Book with brightness >= 128 should get white background."""
        from lambdas.image_processor.handler import select_background_color

        assert select_background_color(brightness=128) == "white"
        assert select_background_color(brightness=200) == "white"
        assert select_background_color(brightness=255) == "white"
