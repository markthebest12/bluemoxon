"""Image API tests."""

import io

from app.api.v1.images import get_thumbnail_key


class TestGetThumbnailKey:
    """Tests for get_thumbnail_key function.

    This function generates S3 keys for thumbnails from original image keys.
    It preserves the full path structure and original extension for backwards
    compatibility with existing thumbnails.
    """

    def test_simple_filename(self):
        """Simple filename without directory."""
        assert get_thumbnail_key("638_abc.jpg") == "thumb_638_abc.jpg"

    def test_preserves_directory_path(self):
        """Directory paths must be preserved."""
        assert get_thumbnail_key("639/image_01.webp") == "thumb_639/image_01.webp"

    def test_preserves_png_extension(self):
        """PNG extension preserved for backwards compatibility."""
        assert get_thumbnail_key("638_processed_xxx.png") == "thumb_638_processed_xxx.png"

    def test_preserves_webp_extension(self):
        """WebP extension preserved for backwards compatibility."""
        assert get_thumbnail_key("639/image_05.webp") == "thumb_639/image_05.webp"

    def test_nested_directory_path(self):
        """Nested directories must be preserved."""
        assert get_thumbnail_key("books/639/cover.jpg") == "thumb_books/639/cover.jpg"


class TestListImages:
    """Tests for GET /api/v1/books/{id}/images."""

    def test_list_images_empty(self, client):
        """Test listing images for a book with no images."""
        # Create a book first
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # List images
        response = client.get(f"/api/v1/books/{book_id}/images")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_images_book_not_found(self, client):
        """Test 404 when book doesn't exist."""
        response = client.get("/api/v1/books/999/images")
        assert response.status_code == 404


class TestPrimaryImage:
    """Tests for GET /api/v1/books/{id}/images/primary."""

    def test_primary_image_placeholder(self, client):
        """Test placeholder returned when no images exist."""
        # Create a book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Get primary image
        response = client.get(f"/api/v1/books/{book_id}/images/primary")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] is None
        assert data["image_type"] == "placeholder"
        assert "placeholder" in data["url"]

    def test_primary_image_book_not_found(self, client):
        """Test 404 when book doesn't exist."""
        response = client.get("/api/v1/books/999/images/primary")
        assert response.status_code == 404


class TestUploadImage:
    """Tests for POST /api/v1/books/{id}/images."""

    def test_upload_image(self, client):
        """Test uploading an image."""
        # Create a book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Create a simple test image (1x1 PNG)
        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        # Upload
        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("test.png", io.BytesIO(png_data), "image/png")},
            params={"image_type": "cover", "is_primary": True, "caption": "Test cover"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] is not None
        assert data["image_type"] == "cover"
        assert data["is_primary"] is True

    def test_upload_image_book_not_found(self, client):
        """Test 404 when book doesn't exist."""
        png_data = b"\x89PNG\r\n\x1a\n"  # Minimal PNG header
        response = client.post(
            "/api/v1/books/999/images",
            files={"file": ("test.png", io.BytesIO(png_data), "image/png")},
        )
        assert response.status_code == 404


class TestUpdateImage:
    """Tests for PUT /api/v1/books/{id}/images/{img_id}."""

    def test_update_image_metadata(self, client):
        """Test updating image metadata."""
        # Create book and upload image
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        upload_response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("test.png", io.BytesIO(png_data), "image/png")},
        )
        image_id = upload_response.json()["id"]

        # Update
        response = client.put(
            f"/api/v1/books/{book_id}/images/{image_id}",
            params={"caption": "Updated caption", "image_type": "spine"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Image updated"


class TestDeleteImage:
    """Tests for DELETE /api/v1/books/{id}/images/{img_id}."""

    def test_delete_image(self, client):
        """Test deleting an image."""
        # Create book and upload image
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        upload_response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("test.png", io.BytesIO(png_data), "image/png")},
        )
        image_id = upload_response.json()["id"]

        # Delete
        response = client.delete(f"/api/v1/books/{book_id}/images/{image_id}")
        assert response.status_code == 204

        # Verify deleted
        response = client.get(f"/api/v1/books/{book_id}/images")
        assert response.json() == []

    def test_delete_image_not_found(self, client):
        """Test 404 when image doesn't exist."""
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        response = client.delete(f"/api/v1/books/{book_id}/images/999")
        assert response.status_code == 404


class TestPlaceholder:
    """Tests for GET /api/v1/images/placeholder."""

    def test_get_placeholder(self, client):
        """Test placeholder image returns SVG."""
        response = client.get("/api/v1/images/placeholder")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"
        assert b"<svg" in response.content


class TestThumbnailGeneration:
    """Tests for thumbnail generation status in upload response (Issue #866)."""

    def test_upload_image_returns_thumbnail_status_field(self, client):
        """Test that upload response includes thumbnail_status field."""
        # Create a book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Create a simple test image (1x1 PNG)
        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        # Upload
        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("test.png", io.BytesIO(png_data), "image/png")},
        )
        assert response.status_code == 201
        data = response.json()

        # Issue #866: Response MUST include thumbnail_status field
        assert "thumbnail_status" in data, "Response missing 'thumbnail_status' field (Issue #866)"
        assert data["thumbnail_status"] in ("generated", "failed", "skipped")

    def test_upload_image_thumbnail_status_generated_on_success(self, client):
        """Test thumbnail_status is 'generated' when thumbnail generation succeeds."""
        # Create a book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Create a valid 100x100 RGB JPEG (realistic for thumbnail gen)
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        buffer.seek(0)

        # Upload
        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("test.jpg", buffer, "image/jpeg")},
        )
        assert response.status_code == 201
        data = response.json()

        # Should succeed with valid image
        assert data["thumbnail_status"] == "generated"
        assert data.get("thumbnail_error") is None

    def test_upload_image_thumbnail_status_failed_with_error(self, client, monkeypatch):
        """Test thumbnail_status is 'failed' with error message when generation fails."""
        # Mock generate_thumbnail to fail
        monkeypatch.setattr(
            "app.api.v1.images.generate_thumbnail",
            lambda *args, **kwargs: (False, "Simulated failure"),
        )

        # Create a book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Create a simple test image
        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        # Upload
        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("test.png", io.BytesIO(png_data), "image/png")},
        )
        assert response.status_code == 201
        data = response.json()

        # Issue #866: Should report thumbnail failure with error detail
        assert data["thumbnail_status"] == "failed"
        assert data["thumbnail_error"] == "Simulated failure"

    def test_upload_duplicate_image_thumbnail_status_skipped(self, client):
        """Test thumbnail_status is 'skipped' for duplicate image uploads."""
        # Create a book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Create a valid image
        from PIL import Image

        img = Image.new("RGB", (50, 50), color="blue")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()

        # First upload
        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("test.jpg", io.BytesIO(image_bytes), "image/jpeg")},
        )
        assert response.status_code == 201
        first_data = response.json()
        assert first_data["thumbnail_status"] == "generated"

        # Second upload (duplicate)
        response = client.post(
            f"/api/v1/books/{book_id}/images",
            files={"file": ("test2.jpg", io.BytesIO(image_bytes), "image/jpeg")},
        )
        assert response.status_code == 201
        data = response.json()

        # Duplicate should have thumbnail_status: skipped
        assert data["duplicate"] is True
        assert data["thumbnail_status"] == "skipped"
        assert data.get("thumbnail_error") is None


class TestImageProcessingTrigger:
    """Tests for auto-triggering image processing on primary change."""

    def test_upload_as_primary_queues_processing(self, client, db):
        """Uploading an image as primary should queue processing."""
        from unittest.mock import patch

        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        with patch("app.api.v1.images.queue_image_processing") as mock_queue:
            response = client.post(
                f"/api/v1/books/{book_id}/images",
                files={"file": ("test.png", io.BytesIO(png_data), "image/png")},
                params={"is_primary": True},
            )
            assert response.status_code == 201
            mock_queue.assert_called_once()

    def test_upload_not_primary_skips_processing(self, client, db):
        """Uploading a non-primary image should not queue processing."""
        from unittest.mock import patch

        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        with patch("app.api.v1.images.queue_image_processing") as mock_queue:
            client.post(
                f"/api/v1/books/{book_id}/images",
                files={"file": ("test1.png", io.BytesIO(png_data), "image/png")},
                params={"is_primary": True},
            )
            mock_queue.reset_mock()

            response = client.post(
                f"/api/v1/books/{book_id}/images",
                files={"file": ("test2.png", io.BytesIO(png_data), "image/png")},
            )
            assert response.status_code == 201
            mock_queue.assert_not_called()

    def test_reorder_to_primary_queues_processing(self, client, db):
        """Reordering an image to primary position should queue processing."""
        from unittest.mock import patch

        from PIL import Image

        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Create two distinct images to avoid duplicate detection
        img1 = Image.new("RGB", (10, 10), color="red")
        buffer1 = io.BytesIO()
        img1.save(buffer1, format="JPEG")
        img1_bytes = buffer1.getvalue()

        img2 = Image.new("RGB", (10, 10), color="blue")
        buffer2 = io.BytesIO()
        img2.save(buffer2, format="JPEG")
        img2_bytes = buffer2.getvalue()

        with patch("app.api.v1.images.queue_image_processing"):
            client.post(
                f"/api/v1/books/{book_id}/images",
                files={"file": ("test1.jpg", io.BytesIO(img1_bytes), "image/jpeg")},
                params={"is_primary": True},
            )
            client.post(
                f"/api/v1/books/{book_id}/images",
                files={"file": ("test2.jpg", io.BytesIO(img2_bytes), "image/jpeg")},
            )

        response = client.get(f"/api/v1/books/{book_id}/images")
        images = response.json()
        image_ids = [img["id"] for img in images]

        with patch("app.api.v1.images.queue_image_processing") as mock_queue:
            new_order = [image_ids[1], image_ids[0]]
            response = client.put(
                f"/api/v1/books/{book_id}/images/reorder",
                json=new_order,
            )
            assert response.status_code == 200
            mock_queue.assert_called_once()
