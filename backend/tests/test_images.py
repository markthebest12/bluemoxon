"""Image API tests."""

import io


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
