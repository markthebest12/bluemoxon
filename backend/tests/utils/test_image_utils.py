# backend/tests/utils/test_image_utils.py
"""Tests for image format detection utilities."""

import pytest

from app.utils.image_utils import (
    MIN_DETECTION_BYTES,
    ImageFormat,
    detect_content_type,
    detect_format,
    fix_extension,
    get_content_type,
    get_extension,
    validate_format_match,
)


class TestDetectFormat:
    """Tests for detect_format function."""

    def test_detect_jpeg_standard(self):
        """JPEG with standard APP0 marker."""
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 8
        assert detect_format(data) == ImageFormat.JPEG

    def test_detect_jpeg_exif(self):
        """JPEG with EXIF marker (from cameras)."""
        data = b"\xff\xd8\xff\xe1" + b"\x00" * 8
        assert detect_format(data) == ImageFormat.JPEG

    def test_detect_jpeg_minimal(self):
        """JPEG detection only needs first 2 bytes."""
        data = b"\xff\xd8\xff\xdb" + b"\x00" * 8
        assert detect_format(data) == ImageFormat.JPEG

    def test_detect_png(self):
        """PNG 8-byte signature."""
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 4
        assert detect_format(data) == ImageFormat.PNG

    def test_detect_webp(self):
        """WebP RIFF container."""
        data = b"RIFF\x00\x00\x00\x00WEBP"
        assert detect_format(data) == ImageFormat.WEBP

    def test_detect_gif87a(self):
        """GIF87a format."""
        data = b"GIF87a" + b"\x00" * 6
        assert detect_format(data) == ImageFormat.GIF

    def test_detect_gif89a(self):
        """GIF89a format."""
        data = b"GIF89a" + b"\x00" * 6
        assert detect_format(data) == ImageFormat.GIF

    def test_detect_unknown(self):
        """Unknown format returns UNKNOWN."""
        data = b"\x00" * 12
        assert detect_format(data) == ImageFormat.UNKNOWN

    def test_detect_unknown_strict_raises(self):
        """Unknown format with strict=True raises ValueError."""
        data = b"\x00" * 12
        with pytest.raises(ValueError, match="Unknown image format"):
            detect_format(data, strict=True)

    def test_insufficient_data_raises(self):
        """Data shorter than MIN_DETECTION_BYTES raises ValueError."""
        data = b"\xff\xd8"  # Valid JPEG start but too short
        with pytest.raises(ValueError, match="Insufficient data"):
            detect_format(data)

    def test_minimum_bytes_constant(self):
        """MIN_DETECTION_BYTES is 12 (for WebP check)."""
        assert MIN_DETECTION_BYTES == 12


class TestGetContentType:
    """Tests for get_content_type function."""

    def test_jpeg_content_type(self):
        assert get_content_type(ImageFormat.JPEG) == "image/jpeg"

    def test_png_content_type(self):
        assert get_content_type(ImageFormat.PNG) == "image/png"

    def test_webp_content_type(self):
        assert get_content_type(ImageFormat.WEBP) == "image/webp"

    def test_gif_content_type(self):
        assert get_content_type(ImageFormat.GIF) == "image/gif"

    def test_unknown_content_type(self):
        assert get_content_type(ImageFormat.UNKNOWN) == "application/octet-stream"


class TestGetExtension:
    """Tests for get_extension function."""

    def test_jpeg_extension(self):
        assert get_extension(ImageFormat.JPEG) == ".jpg"

    def test_png_extension(self):
        assert get_extension(ImageFormat.PNG) == ".png"

    def test_webp_extension(self):
        assert get_extension(ImageFormat.WEBP) == ".webp"

    def test_gif_extension(self):
        assert get_extension(ImageFormat.GIF) == ".gif"

    def test_unknown_extension(self):
        assert get_extension(ImageFormat.UNKNOWN) == ""


class TestDetectContentType:
    """Tests for detect_content_type convenience function."""

    def test_detects_jpeg(self):
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 8
        assert detect_content_type(data) == "image/jpeg"

    def test_detects_png(self):
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 4
        assert detect_content_type(data) == "image/png"


class TestValidateFormatMatch:
    """Tests for validate_format_match function."""

    def test_matching_jpg(self):
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 8
        assert validate_format_match("photo.jpg", data) is True

    def test_matching_jpeg(self):
        """Both .jpg and .jpeg are valid for JPEG."""
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 8
        assert validate_format_match("photo.jpeg", data) is True

    def test_matching_png(self):
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 4
        assert validate_format_match("image.png", data) is True

    def test_mismatched_extension(self):
        """PNG data with .jpg extension."""
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 4
        assert validate_format_match("image.jpg", data) is False

    def test_unknown_format(self):
        data = b"\x00" * 12
        assert validate_format_match("file.bin", data) is False

    def test_case_insensitive(self):
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 8
        assert validate_format_match("PHOTO.JPG", data) is True


class TestFixExtension:
    """Tests for fix_extension function."""

    def test_fix_png_to_jpg(self):
        """PNG extension on JPEG data gets fixed."""
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 8
        assert fix_extension("photo.png", data) == "photo.jpg"

    def test_fix_jpg_to_png(self):
        """JPG extension on PNG data gets fixed."""
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 4
        assert fix_extension("image.jpg", data) == "image.png"

    def test_already_correct(self):
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 8
        assert fix_extension("photo.jpg", data) == "photo.jpg"

    def test_unknown_format_unchanged(self):
        data = b"\x00" * 12
        assert fix_extension("file.bin", data) == "file.bin"

    def test_no_extension(self):
        data = b"\xff\xd8\xff\xe0" + b"\x00" * 8
        assert fix_extension("photo", data) == "photo.jpg"

    def test_preserves_path(self):
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 4
        assert fix_extension("books/638_processed.jpg", data) == "books/638_processed.png"
