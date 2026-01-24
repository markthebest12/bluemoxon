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

from PIL import Image


class TestThumbnailExtensionMismatch:
    """Tests for the thumbnail extension mismatch bug.

    These tests verify that:
    1. thumbnail_name gets the corrected extension (not the original)
    2. The S3 thumbnail key matches the corrected image format
    3. The thumbnail_url in responses uses the correct extension
    """

    def _create_jpeg_bytes(self, size: tuple[int, int] = (100, 100)) -> bytes:
        """Create valid JPEG image bytes."""
        img = Image.new("RGB", size, color="red")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        return buffer.getvalue()

    def _create_webp_bytes(self, size: tuple[int, int] = (100, 100)) -> bytes:
        """Create valid WebP image bytes."""
        img = Image.new("RGB", size, color="blue")
        buffer = io.BytesIO()
        img.save(buffer, format="WEBP")
        return buffer.getvalue()

    def _create_png_bytes(self, size: tuple[int, int] = (100, 100)) -> bytes:
        """Create valid PNG image bytes."""
        img = Image.new("RGB", size, color="green")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_jpeg_extension_normalized_in_thumbnail(self, client, monkeypatch, tmp_path):
        """Upload .jpeg file with JPEG data should create thumbnail with .jpg extension.

        The fix_extension() function normalizes .jpeg to .jpg for consistency.
        The thumbnail filename must also use .jpg, not the original .jpeg.
        """
        # Create a book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Create JPEG image data
        jpeg_bytes = self._create_jpeg_bytes()

        # Track what S3 keys are used for upload
        uploaded_keys = []

        def mock_upload_file(local_path, bucket, s3_key, ExtraArgs=None):
            uploaded_keys.append(s3_key)

        # Mock S3 client and settings to simulate Lambda environment
        mock_s3 = MagicMock()
        mock_s3.upload_file = mock_upload_file

        # Set environment variable to trigger is_aws_lambda property
        monkeypatch.setenv("DATABASE_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:123:secret:test")

        # Clear the cached settings so new env var is picked up
        from app.config import get_settings
        get_settings.cache_clear()

        # Reload settings module to pick up env change
        from app import config
        new_settings = config.Settings()

        # Patch the settings object used in images module
        monkeypatch.setattr("app.api.v1.images.settings", new_settings)
        monkeypatch.setattr("app.api.v1.images.get_s3_client", lambda: mock_s3)

        # Use temp path for local images during test
        monkeypatch.setattr("app.api.v1.images.LOCAL_IMAGES_PATH", tmp_path)

        # Upload with .jpeg extension (should be normalized to .jpg)
        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("photo.jpeg", io.BytesIO(jpeg_bytes), "image/jpeg")},
        )

        assert response.status_code == 201

        # Find the thumbnail key that was uploaded
        thumbnail_keys = [k for k in uploaded_keys if k.startswith("books/thumb_")]

        assert len(thumbnail_keys) == 1, f"Expected 1 thumbnail upload, got: {uploaded_keys}"
        thumbnail_key = thumbnail_keys[0]

        # BUG: Currently thumbnail_key ends with .jpeg (wrong)
        # FIX: Should end with .jpg (normalized)
        assert thumbnail_key.endswith(".jpg"), (
            f"Thumbnail key should end with .jpg (normalized), "
            f"but got: {thumbnail_key}"
        )

    def test_wrong_extension_corrected_in_thumbnail(self, client, monkeypatch, tmp_path):
        """Upload .jpg file containing WebP data should create thumbnail with .webp extension.

        When file content doesn't match extension, fix_extension() corrects it.
        The thumbnail must use the corrected extension based on actual content.
        """
        # Create a book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Create WebP image data (but we'll upload it with .jpg extension)
        webp_bytes = self._create_webp_bytes()

        # Track what S3 keys are used for upload
        uploaded_keys = []

        def mock_upload_file(local_path, bucket, s3_key, ExtraArgs=None):
            uploaded_keys.append(s3_key)

        # Mock S3 client and settings to simulate Lambda environment
        mock_s3 = MagicMock()
        mock_s3.upload_file = mock_upload_file

        # Set environment variable to trigger is_aws_lambda property
        monkeypatch.setenv("DATABASE_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:123:secret:test")

        # Clear the cached settings so new env var is picked up
        from app.config import get_settings
        get_settings.cache_clear()

        # Reload settings module to pick up env change
        from app import config
        new_settings = config.Settings()

        # Patch the settings object used in images module
        monkeypatch.setattr("app.api.v1.images.settings", new_settings)
        monkeypatch.setattr("app.api.v1.images.get_s3_client", lambda: mock_s3)

        # Use temp path for local images during test
        monkeypatch.setattr("app.api.v1.images.LOCAL_IMAGES_PATH", tmp_path)

        # Upload WebP data with wrong .jpg extension
        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("image.jpg", io.BytesIO(webp_bytes), "image/webp")},
        )

        assert response.status_code == 201

        # Find the thumbnail and main image keys
        main_keys = [k for k in uploaded_keys if "thumb_" not in k]
        thumbnail_keys = [k for k in uploaded_keys if "thumb_" in k]

        assert len(main_keys) == 1, f"Expected 1 main image upload, got: {uploaded_keys}"
        assert len(thumbnail_keys) == 1, f"Expected 1 thumbnail upload, got: {uploaded_keys}"

        main_key = main_keys[0]
        thumbnail_key = thumbnail_keys[0]

        # Main image should be corrected to .webp
        assert main_key.endswith(".webp"), (
            f"Main image key should end with .webp (corrected from .jpg), "
            f"but got: {main_key}"
        )

        # BUG: Currently thumbnail_key ends with .jpg (original wrong extension)
        # FIX: Should end with .webp (matching corrected main image)
        assert thumbnail_key.endswith(".webp"), (
            f"Thumbnail key should end with .webp (matching main image), "
            f"but got: {thumbnail_key}"
        )

    def test_thumbnail_url_matches_corrected_extension(self, client, monkeypatch, tmp_path):
        """Verify thumbnail_url in response uses the corrected extension.

        When listing images, the thumbnail_url should reflect the actual
        thumbnail key (with corrected extension), not the original filename.
        """
        # Create a book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Create JPEG data, upload with .jpeg extension
        jpeg_bytes = self._create_jpeg_bytes()

        # Track uploads
        uploaded_keys = []

        def mock_upload_file(local_path, bucket, s3_key, ExtraArgs=None):
            uploaded_keys.append(s3_key)

        mock_s3 = MagicMock()
        mock_s3.upload_file = mock_upload_file

        # Set environment variable to trigger is_aws_lambda property
        monkeypatch.setenv("DATABASE_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:123:secret:test")

        # Clear the cached settings so new env var is picked up
        from app.config import get_settings
        get_settings.cache_clear()

        # Reload settings module to pick up env change
        from app import config
        new_settings = config.Settings()

        monkeypatch.setattr("app.api.v1.images.settings", new_settings)
        monkeypatch.setattr("app.api.v1.images.get_s3_client", lambda: mock_s3)
        monkeypatch.setattr("app.api.v1.images.LOCAL_IMAGES_PATH", tmp_path)

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
        # BUG: Currently s3_key might have .jpeg
        # FIX: Should have .jpg (normalized)
        assert image["s3_key"].endswith(".jpg"), (
            f"s3_key should end with .jpg (normalized), "
            f"but got: {image['s3_key']}"
        )

        # thumbnail_url should derive from corrected s3_key
        # get_thumbnail_key prepends "thumb_" to s3_key
        expected_thumbnail_suffix = f"thumb_{image['s3_key']}"
        assert expected_thumbnail_suffix.endswith(".jpg"), (
            f"Expected thumbnail to end with .jpg, got: {expected_thumbnail_suffix}"
        )


class TestThumbnailExtensionConsistency:
    """Additional tests for thumbnail/main image extension consistency."""

    def _create_png_bytes(self) -> bytes:
        """Create valid PNG image bytes."""
        img = Image.new("RGB", (100, 100), color="green")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_png_data_with_jpg_extension_fixed_in_both(self, client, monkeypatch, tmp_path):
        """PNG data uploaded with .jpg extension should fix both main and thumbnail.

        Main: xxx.jpg -> xxx.png
        Thumbnail: thumb_xxx.jpg -> thumb_xxx.png
        """
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        png_bytes = self._create_png_bytes()

        uploaded_keys = []

        def mock_upload_file(local_path, bucket, s3_key, ExtraArgs=None):
            uploaded_keys.append(s3_key)

        mock_s3 = MagicMock()
        mock_s3.upload_file = mock_upload_file

        # Set environment variable to trigger is_aws_lambda property
        monkeypatch.setenv("DATABASE_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:123:secret:test")

        # Clear the cached settings so new env var is picked up
        from app.config import get_settings
        get_settings.cache_clear()

        # Reload settings module to pick up env change
        from app import config
        new_settings = config.Settings()

        monkeypatch.setattr("app.api.v1.images.settings", new_settings)
        monkeypatch.setattr("app.api.v1.images.get_s3_client", lambda: mock_s3)
        monkeypatch.setattr("app.api.v1.images.LOCAL_IMAGES_PATH", tmp_path)

        # Upload PNG data with wrong .jpg extension
        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("wrong.jpg", io.BytesIO(png_bytes), "image/png")},
        )

        assert response.status_code == 201

        main_keys = [k for k in uploaded_keys if "thumb_" not in k]
        thumbnail_keys = [k for k in uploaded_keys if "thumb_" in k]

        # Both should be corrected to .png
        assert main_keys[0].endswith(".png"), f"Main key should be .png: {main_keys[0]}"
        assert thumbnail_keys[0].endswith(".png"), (
            f"Thumbnail key should be .png (matching main): {thumbnail_keys[0]}"
        )

    def test_thumbnail_key_derived_from_corrected_name(self, client, monkeypatch, tmp_path):
        """Verify thumbnail key is derived from corrected unique_name.

        The bug is that thumbnail_name is generated before fix_extension runs.
        This test ensures get_thumbnail_key is called on the CORRECTED name.
        """
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Create JPEG but upload as .png (wrong extension)
        img = Image.new("RGB", (100, 100), color="red")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        jpeg_bytes = buffer.getvalue()

        uploaded_keys = []

        def mock_upload_file(local_path, bucket, s3_key, ExtraArgs=None):
            uploaded_keys.append(s3_key)

        mock_s3 = MagicMock()
        mock_s3.upload_file = mock_upload_file

        # Set environment variable to trigger is_aws_lambda property
        monkeypatch.setenv("DATABASE_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:123:secret:test")

        # Clear the cached settings so new env var is picked up
        from app.config import get_settings
        get_settings.cache_clear()

        # Reload settings module to pick up env change
        from app import config
        new_settings = config.Settings()

        monkeypatch.setattr("app.api.v1.images.settings", new_settings)
        monkeypatch.setattr("app.api.v1.images.get_s3_client", lambda: mock_s3)
        monkeypatch.setattr("app.api.v1.images.LOCAL_IMAGES_PATH", tmp_path)

        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("misnamed.png", io.BytesIO(jpeg_bytes), "image/jpeg")},
        )

        assert response.status_code == 201

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
