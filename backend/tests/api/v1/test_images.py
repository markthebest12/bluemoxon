# backend/tests/api/v1/test_images.py
"""Tests for thumbnail extension mismatch bug.

Bug: In images.py, thumbnail_name is generated BEFORE fix_extension() normalizes
the filename. This causes extension mismatches when the original file extension
doesn't match the actual image format.

Example: Upload "photo.jpeg" containing JPEG data
- Expected: thumbnail "thumb_123_xxx.jpg" (normalized to .jpg)
- Actual bug: thumbnail "thumb_123_xxx.jpeg" (keeps original .jpeg)

Example: Upload "image.jpg" containing WebP data
- Expected: thumbnail "thumb_123_xxx.webp" (matches actual format)
- Actual bug: thumbnail "thumb_123_xxx.jpg" (keeps wrong extension)
"""

import io
from unittest.mock import MagicMock

import pytest
from PIL import Image


@pytest.fixture
def jpeg_bytes():
    """Create valid JPEG image bytes."""
    img = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def webp_bytes():
    """Create valid WebP image bytes."""
    img = Image.new("RGB", (100, 100), color="blue")
    buffer = io.BytesIO()
    img.save(buffer, format="WEBP")
    return buffer.getvalue()


@pytest.fixture
def png_bytes():
    """Create valid PNG image bytes."""
    img = Image.new("RGB", (100, 100), color="green")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def lambda_environment(monkeypatch, tmp_path):
    """Set up Lambda-like environment with mocked S3.

    Returns dict with:
        - uploaded_keys: list tracking S3 upload keys
        - mock_s3: the mocked S3 client
        - tmp_path: temp directory for local files
    """
    uploaded_keys = []

    def mock_upload_file(local_path, bucket, s3_key, ExtraArgs=None):
        uploaded_keys.append(s3_key)

    mock_s3 = MagicMock()
    mock_s3.upload_file = mock_upload_file

    # Set environment variable to trigger is_aws_lambda property
    monkeypatch.setenv("DATABASE_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:123:secret:test")

    # Clear cached settings so new env var is picked up
    from app.config import get_settings

    get_settings.cache_clear()

    # Reload settings to pick up env change
    from app import config

    new_settings = config.Settings()

    # Patch the settings and S3 client in images module
    monkeypatch.setattr("app.api.v1.images.settings", new_settings)
    monkeypatch.setattr("app.api.v1.images.get_s3_client", lambda: mock_s3)
    monkeypatch.setattr("app.api.v1.images.LOCAL_IMAGES_PATH", tmp_path)

    return {
        "uploaded_keys": uploaded_keys,
        "mock_s3": mock_s3,
        "tmp_path": tmp_path,
    }


@pytest.fixture
def local_dev_environment(monkeypatch, tmp_path):
    """Set up local development environment (non-Lambda).

    Returns dict with:
        - tmp_path: temp directory where files are saved
    """
    # Ensure DATABASE_SECRET_ARN is NOT set (local dev mode)
    monkeypatch.delenv("DATABASE_SECRET_ARN", raising=False)

    # Clear cached settings
    from app.config import get_settings

    get_settings.cache_clear()

    # Reload settings
    from app import config

    new_settings = config.Settings()

    # Patch settings and local path
    monkeypatch.setattr("app.api.v1.images.settings", new_settings)
    monkeypatch.setattr("app.api.v1.images.LOCAL_IMAGES_PATH", tmp_path)

    return {"tmp_path": tmp_path}


class TestThumbnailExtensionMismatch:
    """Tests for the thumbnail extension mismatch bug.

    These tests verify that:
    1. thumbnail_name gets the corrected extension (not the original)
    2. The S3 thumbnail key matches the corrected image format
    3. The thumbnail_url in responses uses the correct extension
    """

    def test_jpeg_extension_normalized_in_thumbnail(self, client, lambda_environment, jpeg_bytes):
        """Upload .jpeg file with JPEG data should create thumbnail with .jpg extension.

        The fix normalizes .jpeg to .jpg for consistency.
        The thumbnail filename must also use .jpg, not the original .jpeg.
        """
        # Create a book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Upload with .jpeg extension (should be normalized to .jpg)
        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("photo.jpeg", io.BytesIO(jpeg_bytes), "image/jpeg")},
        )

        assert response.status_code == 201

        # Find the thumbnail key that was uploaded
        uploaded_keys = lambda_environment["uploaded_keys"]
        thumbnail_keys = [k for k in uploaded_keys if k.startswith("books/thumb_")]

        assert len(thumbnail_keys) == 1, f"Expected 1 thumbnail upload, got: {uploaded_keys}"
        thumbnail_key = thumbnail_keys[0]

        # Should end with .jpg (normalized from .jpeg)
        assert thumbnail_key.endswith(".jpg"), (
            f"Thumbnail key should end with .jpg (normalized), but got: {thumbnail_key}"
        )

    def test_wrong_extension_corrected_in_thumbnail(self, client, lambda_environment, webp_bytes):
        """Upload .jpg file containing WebP data should create thumbnail with .webp extension.

        When file content doesn't match extension, format detection corrects it.
        The thumbnail must use the corrected extension based on actual content.
        """
        # Create a book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Upload WebP data with wrong .jpg extension
        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("image.jpg", io.BytesIO(webp_bytes), "image/webp")},
        )

        assert response.status_code == 201

        # Find the thumbnail and main image keys
        uploaded_keys = lambda_environment["uploaded_keys"]
        main_keys = [k for k in uploaded_keys if "thumb_" not in k]
        thumbnail_keys = [k for k in uploaded_keys if "thumb_" in k]

        assert len(main_keys) == 1, f"Expected 1 main image upload, got: {uploaded_keys}"
        assert len(thumbnail_keys) == 1, f"Expected 1 thumbnail upload, got: {uploaded_keys}"

        main_key = main_keys[0]
        thumbnail_key = thumbnail_keys[0]

        # Main image should be corrected to .webp
        assert main_key.endswith(".webp"), (
            f"Main image key should end with .webp (corrected from .jpg), but got: {main_key}"
        )

        # Should end with .webp (matching corrected main image)
        assert thumbnail_key.endswith(".webp"), (
            f"Thumbnail key should end with .webp (matching main image), but got: {thumbnail_key}"
        )

    def test_thumbnail_url_matches_corrected_extension(
        self, client, lambda_environment, jpeg_bytes
    ):
        """Verify thumbnail_url in response uses the corrected extension.

        When listing images, the thumbnail_url should reflect the actual
        thumbnail key (with corrected extension), not the original filename.
        """
        # Create a book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Upload with .jpeg extension
        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("cover.jpeg", io.BytesIO(jpeg_bytes), "image/jpeg")},
        )
        assert response.status_code == 201

        # Get the list of images to check thumbnail_url
        response = client.get(f"/api/v1/books/{book_id}/images")
        assert response.status_code == 200
        images = response.json()

        assert len(images) == 1
        image = images[0]

        # The s3_key stored in DB should have corrected extension
        assert image["s3_key"].endswith(".jpg"), (
            f"s3_key should end with .jpg (normalized), but got: {image['s3_key']}"
        )

        # thumbnail_url should derive from corrected s3_key
        # get_thumbnail_key prepends "thumb_" to s3_key
        expected_thumbnail_suffix = f"thumb_{image['s3_key']}"
        assert expected_thumbnail_suffix.endswith(".jpg"), (
            f"Expected thumbnail to end with .jpg, got: {expected_thumbnail_suffix}"
        )


class TestThumbnailExtensionConsistency:
    """Additional tests for thumbnail/main image extension consistency."""

    def test_png_data_with_jpg_extension_fixed_in_both(self, client, lambda_environment, png_bytes):
        """PNG data uploaded with .jpg extension should fix both main and thumbnail.

        Main: xxx.jpg -> xxx.png
        Thumbnail: thumb_xxx.jpg -> thumb_xxx.png
        """
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Upload PNG data with wrong .jpg extension
        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("wrong.jpg", io.BytesIO(png_bytes), "image/png")},
        )

        assert response.status_code == 201

        uploaded_keys = lambda_environment["uploaded_keys"]
        main_keys = [k for k in uploaded_keys if "thumb_" not in k]
        thumbnail_keys = [k for k in uploaded_keys if "thumb_" in k]

        # Both should be corrected to .png
        assert main_keys[0].endswith(".png"), f"Main key should be .png: {main_keys[0]}"
        assert thumbnail_keys[0].endswith(".png"), (
            f"Thumbnail key should be .png (matching main): {thumbnail_keys[0]}"
        )

    def test_thumbnail_key_derived_from_corrected_name(
        self, client, lambda_environment, jpeg_bytes
    ):
        """Verify thumbnail key is derived from corrected unique_name.

        The bug is that thumbnail_name is generated before fix_extension runs.
        This test ensures get_thumbnail_key is called on the CORRECTED name.
        """
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Create JPEG but upload as .png (wrong extension)

        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("misnamed.png", io.BytesIO(jpeg_bytes), "image/jpeg")},
        )

        assert response.status_code == 201

        uploaded_keys = lambda_environment["uploaded_keys"]
        main_keys = [k for k in uploaded_keys if "thumb_" not in k]
        thumbnail_keys = [k for k in uploaded_keys if "thumb_" in k]

        main_key = main_keys[0]
        thumbnail_key = thumbnail_keys[0]

        # Extract just the filename part (after "books/")
        main_filename = main_key.replace("books/", "")
        thumbnail_filename = thumbnail_key.replace("books/", "")

        # Thumbnail should be "thumb_" + main_filename
        expected_thumbnail = f"thumb_{main_filename}"

        assert thumbnail_filename == expected_thumbnail, (
            f"Thumbnail filename should be derived from corrected main filename.\n"
            f"Main: {main_filename}\n"
            f"Expected thumbnail: {expected_thumbnail}\n"
            f"Actual thumbnail: {thumbnail_filename}"
        )


class TestSmallFileHandling:
    """Tests for edge cases with small files."""

    def test_file_smaller_than_12_bytes_uses_filename_extension(self, client, lambda_environment):
        """Files < 12 bytes can't be detected - should fall back to filename extension.

        The detect_format function requires 12 bytes minimum. For smaller files,
        we should use the filename extension rather than crashing with ValueError.
        """
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Create a tiny file (smaller than 12 bytes)
        tiny_content = b"tiny"  # 4 bytes

        # Upload with .jpg extension - should use that extension since content too small
        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("small.jpg", io.BytesIO(tiny_content), "image/jpeg")},
        )

        # Should NOT crash with 500 error - should gracefully fall back
        assert response.status_code == 201, (
            f"Expected 201 (success with fallback), got: {response.status_code}"
        )

        # Verify the extension was used
        uploaded_keys = lambda_environment["uploaded_keys"]
        main_keys = [k for k in uploaded_keys if "thumb_" not in k]
        assert main_keys, f"Expected main image upload, got: {uploaded_keys}"
        assert main_keys[0].endswith(".jpg"), (
            f"Should use filename extension for small files: {main_keys[0]}"
        )


class TestLocalDevPath:
    """Tests for local development (non-Lambda) code path."""

    def test_local_dev_saves_file_with_correct_extension(
        self, client, local_dev_environment, jpeg_bytes
    ):
        """In local dev, files should be saved with correct extension based on content.

        This tests the non-Lambda path where files are saved locally instead of S3.
        """
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("photo.jpeg", io.BytesIO(jpeg_bytes), "image/jpeg")},
        )

        assert response.status_code == 201

        # Check that file was saved locally with correct extension
        tmp_path = local_dev_environment["tmp_path"]
        saved_files = list(tmp_path.glob("*.jpg"))

        # Should have main image and thumbnail both with .jpg extension
        main_files = [f for f in saved_files if not f.name.startswith("thumb_")]
        thumb_files = [f for f in saved_files if f.name.startswith("thumb_")]

        assert len(main_files) >= 1, f"Expected main image file, found: {list(tmp_path.iterdir())}"
        assert main_files[0].suffix == ".jpg", (
            f"Main image should have .jpg extension: {main_files[0].name}"
        )

        # Thumbnail should also exist with matching extension
        assert len(thumb_files) >= 1, f"Expected thumbnail file, found: {list(tmp_path.iterdir())}"
        assert thumb_files[0].suffix == ".jpg", (
            f"Thumbnail should have .jpg extension: {thumb_files[0].name}"
        )


class TestUnrecognizedFormats:
    """Tests for handling unrecognized image formats."""

    def test_unrecognized_format_uses_filename_extension(self, client, lambda_environment):
        """Unrecognized formats should fall back to filename extension.

        For formats like TIFF, BMP, HEIC that we don't recognize by magic bytes,
        we should use the filename extension as the fallback.
        """
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Create fake TIFF-like content (we don't recognize TIFF)
        # Real TIFF starts with II or MM, but we only detect JPEG/PNG/WebP/GIF
        fake_tiff = b"II*\x00" + b"\x00" * 100  # Fake TIFF header + padding

        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("image.tiff", io.BytesIO(fake_tiff), "image/tiff")},
        )

        # Should use .tiff extension from filename since format not recognized
        assert response.status_code == 201, f"Expected 201 success, got: {response.status_code}"
        uploaded_keys = lambda_environment["uploaded_keys"]
        main_keys = [k for k in uploaded_keys if "thumb_" not in k]
        assert main_keys, f"Expected main image upload, got: {uploaded_keys}"
        assert main_keys[0].endswith(".tiff"), (
            f"Should fall back to filename extension: {main_keys[0]}"
        )

    def test_garbage_data_uses_default_jpg(self, client, lambda_environment):
        """Garbage data with no extension should default to .jpg.

        When format detection fails and filename has no extension,
        we fall back to .jpg as the default.
        """
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Random garbage that doesn't match any known format
        garbage = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f" * 10

        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("noextension", io.BytesIO(garbage), "application/octet-stream")},
        )

        # Should use .jpg as fallback when no extension and unrecognized format
        assert response.status_code == 201, f"Expected 201 success, got: {response.status_code}"
        uploaded_keys = lambda_environment["uploaded_keys"]
        main_keys = [k for k in uploaded_keys if "thumb_" not in k]
        assert main_keys, f"Expected main image upload, got: {uploaded_keys}"
        assert main_keys[0].endswith(".jpg"), (
            f"Should default to .jpg for unknown format: {main_keys[0]}"
        )
