"""Book API tests."""

from unittest.mock import MagicMock, patch

from app.models import Book, BookImage


class TestListBooks:
    """Tests for GET /api/v1/books."""

    def test_list_books_empty(self, client):
        """Test listing books when database is empty."""
        response = client.get("/api/v1/books")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1

    def test_list_books_pagination(self, client):
        """Test pagination parameters."""
        response = client.get("/api/v1/books?page=1&per_page=10")
        assert response.status_code == 200
        data = response.json()
        assert data["per_page"] == 10


class TestCreateBook:
    """Tests for POST /api/v1/books."""

    def test_create_book_minimal(self, client):
        """Test creating a book with minimal data."""
        response = client.post(
            "/api/v1/books",
            json={"title": "Idylls of the King"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Idylls of the King"
        assert data["id"] is not None
        assert data["inventory_type"] == "PRIMARY"
        assert data["status"] == "ON_HAND"

    def test_create_book_full(self, client):
        """Test creating a book with all fields."""
        response = client.post(
            "/api/v1/books",
            json={
                "title": "In Memoriam",
                "publication_date": "1850",
                "volumes": 1,
                "category": "Victorian Poetry",
                "inventory_type": "PRIMARY",
                "binding_type": "Full morocco",
                "value_low": 200,
                "value_mid": 300,
                "value_high": 400,
                "status": "ON_HAND",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "In Memoriam"
        assert data["category"] == "Victorian Poetry"
        assert float(data["value_mid"]) == 300

    def test_create_book_missing_title(self, client):
        """Test that title is required."""
        response = client.post("/api/v1/books", json={})
        assert response.status_code == 422


class TestGetBook:
    """Tests for GET /api/v1/books/{id}."""

    def test_get_book_not_found(self, client):
        """Test 404 for non-existent book."""
        response = client.get("/api/v1/books/999")
        assert response.status_code == 404

    def test_get_book_exists(self, client):
        """Test getting a book that exists."""
        # Create a book first
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test Book"},
        )
        book_id = create_response.json()["id"]

        # Get it
        response = client.get(f"/api/v1/books/{book_id}")
        assert response.status_code == 200
        assert response.json()["title"] == "Test Book"


class TestUpdateBook:
    """Tests for PUT /api/v1/books/{id}."""

    def test_update_book(self, client):
        """Test updating a book."""
        # Create
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Original Title"},
        )
        book_id = create_response.json()["id"]

        # Update
        response = client.put(
            f"/api/v1/books/{book_id}",
            json={"title": "Updated Title"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    def test_update_book_not_found(self, client):
        """Test 404 when updating non-existent book."""
        response = client.put("/api/v1/books/999", json={"title": "Test"})
        assert response.status_code == 404


class TestDeleteBook:
    """Tests for DELETE /api/v1/books/{id}."""

    def test_delete_book(self, client):
        """Test deleting a book."""
        # Create
        create_response = client.post(
            "/api/v1/books",
            json={"title": "To Delete"},
        )
        book_id = create_response.json()["id"]

        # Delete
        response = client.delete(f"/api/v1/books/{book_id}")
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/api/v1/books/{book_id}")
        assert get_response.status_code == 404


class TestBookStatus:
    """Tests for PATCH /api/v1/books/{id}/status."""

    def test_update_status(self, client):
        """Test updating book status."""
        # Create
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test", "status": "IN_TRANSIT"},
        )
        book_id = create_response.json()["id"]

        # Update status
        response = client.patch(f"/api/v1/books/{book_id}/status?status=ON_HAND")
        assert response.status_code == 200
        assert response.json()["status"] == "ON_HAND"

    def test_update_status_invalid(self, client):
        """Test invalid status value."""
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test"},
        )
        book_id = create_response.json()["id"]

        response = client.patch(f"/api/v1/books/{book_id}/status?status=INVALID")
        assert response.status_code == 400


class TestInventoryType:
    """Tests for PATCH /api/v1/books/{id}/inventory-type."""

    def test_update_inventory_type(self, client):
        """Test moving book between inventory types."""
        # Create in PRIMARY
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test", "inventory_type": "PRIMARY"},
        )
        book_id = create_response.json()["id"]

        # Move to FLAGGED
        response = client.patch(f"/api/v1/books/{book_id}/inventory-type?inventory_type=FLAGGED")
        assert response.status_code == 200
        assert response.json()["old_type"] == "PRIMARY"
        assert response.json()["new_type"] == "FLAGGED"


class TestAddTracking:
    """Tests for PATCH /api/v1/books/{id}/tracking."""

    def test_add_tracking_with_url(self, client):
        """Test adding tracking with direct URL."""
        # Create IN_TRANSIT book
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test Book", "status": "IN_TRANSIT"},
        )
        book_id = create_response.json()["id"]

        # Add tracking
        response = client.patch(
            f"/api/v1/books/{book_id}/tracking",
            json={
                "tracking_number": "12345",
                "tracking_carrier": "Custom",
                "tracking_url": "https://custom-tracker.com/12345",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tracking_number"] == "12345"
        assert data["tracking_carrier"] == "Custom"
        assert data["tracking_url"] == "https://custom-tracker.com/12345"

    def test_add_tracking_auto_detect_ups(self, client):
        """Test auto-detecting UPS carrier from tracking number."""
        # Create IN_TRANSIT book
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test Book", "status": "IN_TRANSIT"},
        )
        book_id = create_response.json()["id"]

        # Add tracking (UPS format)
        response = client.patch(
            f"/api/v1/books/{book_id}/tracking",
            json={"tracking_number": "1Z999AA10123456784"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tracking_number"] == "1Z999AA10123456784"
        assert data["tracking_carrier"] == "UPS"
        assert "ups.com" in data["tracking_url"]

    def test_add_tracking_auto_detect_usps(self, client):
        """Test auto-detecting USPS carrier from tracking number."""
        # Create IN_TRANSIT book
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test Book", "status": "IN_TRANSIT"},
        )
        book_id = create_response.json()["id"]

        # Add tracking (USPS format)
        response = client.patch(
            f"/api/v1/books/{book_id}/tracking",
            json={"tracking_number": "9400111899223100001234"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tracking_carrier"] == "USPS"
        assert "usps.com" in data["tracking_url"]

    def test_add_tracking_requires_in_transit(self, client):
        """Test that tracking can only be added to IN_TRANSIT books."""
        # Create ON_HAND book
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test Book", "status": "ON_HAND"},
        )
        book_id = create_response.json()["id"]

        # Try to add tracking
        response = client.patch(
            f"/api/v1/books/{book_id}/tracking",
            json={"tracking_url": "https://example.com/track"},
        )
        assert response.status_code == 400
        assert "IN_TRANSIT" in response.json()["detail"]

    def test_add_tracking_unknown_carrier_error(self, client):
        """Test error when carrier cannot be detected."""
        # Create IN_TRANSIT book
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test Book", "status": "IN_TRANSIT"},
        )
        book_id = create_response.json()["id"]

        # Try to add tracking with unknown format
        response = client.patch(
            f"/api/v1/books/{book_id}/tracking",
            json={"tracking_number": "INVALID123"},
        )
        assert response.status_code == 400
        assert "Could not detect carrier" in response.json()["detail"]

    def test_add_tracking_not_found(self, client):
        """Test 404 when book doesn't exist."""
        response = client.patch(
            "/api/v1/books/999/tracking",
            json={"tracking_url": "https://example.com/track"},
        )
        assert response.status_code == 404

    def test_add_tracking_empty_request(self, client):
        """Test that empty tracking request is rejected."""
        # Create IN_TRANSIT book
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test Book", "status": "IN_TRANSIT"},
        )
        book_id = create_response.json()["id"]

        # Try empty tracking
        response = client.patch(
            f"/api/v1/books/{book_id}/tracking",
            json={},
        )
        assert response.status_code == 400
        assert "tracking_number or tracking_url" in response.json()["detail"]

    def test_add_tracking_normalizes_number(self, client):
        """Test that tracking number is normalized (uppercase, no spaces)."""
        # Create IN_TRANSIT book
        create_response = client.post(
            "/api/v1/books",
            json={"title": "Test Book", "status": "IN_TRANSIT"},
        )
        book_id = create_response.json()["id"]

        # Add tracking with messy number
        response = client.patch(
            f"/api/v1/books/{book_id}/tracking",
            json={"tracking_number": "1z 999 aa1-0123-4567-84"},
        )
        assert response.status_code == 200
        data = response.json()
        # Should be normalized
        assert data["tracking_number"] == "1Z999AA10123456784"


class TestCopyListingImagesToBook:
    """Tests for _copy_listing_images_to_book function."""

    @patch("app.api.v1.books.boto3")
    @patch("app.api.v1.books.settings")
    def test_copies_images_and_creates_records(self, mock_settings, mock_boto3, db):
        """Test happy path: images are copied and BookImage records created."""
        from app.api.v1.books import _copy_listing_images_to_book

        # Setup
        mock_settings.images_bucket = "test-bucket"
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3

        # Create a book to associate images with
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        listing_keys = ["listings/item123/image_0.jpg", "listings/item123/image_1.png"]

        # Mock thumbnail generation to return success
        with patch("app.api.v1.images.generate_thumbnail") as mock_thumb:
            mock_thumb.return_value = (True, None)

            _copy_listing_images_to_book(book.id, listing_keys, db)

        # Verify S3 copy calls
        assert mock_s3.copy_object.call_count == 2
        mock_s3.copy_object.assert_any_call(
            Bucket="test-bucket",
            CopySource={"Bucket": "test-bucket", "Key": "listings/item123/image_0.jpg"},
            Key=f"books/{book.id}/image_00.jpg",
        )
        mock_s3.copy_object.assert_any_call(
            Bucket="test-bucket",
            CopySource={"Bucket": "test-bucket", "Key": "listings/item123/image_1.png"},
            Key=f"books/{book.id}/image_01.png",
        )

        # Verify BookImage records created
        images = db.query(BookImage).filter(BookImage.book_id == book.id).all()
        assert len(images) == 2
        assert images[0].s3_key == f"{book.id}/image_00.jpg"
        assert images[0].is_primary is True
        assert images[0].display_order == 0
        assert images[1].s3_key == f"{book.id}/image_01.png"
        assert images[1].is_primary is False
        assert images[1].display_order == 1

    @patch("app.api.v1.books.settings")
    def test_returns_early_if_bucket_not_configured(self, mock_settings, db):
        """Test that function returns early when images_bucket is not set."""
        from app.api.v1.books import _copy_listing_images_to_book

        mock_settings.images_bucket = ""

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        # Should not raise, just return early
        _copy_listing_images_to_book(book.id, ["listings/item/img.jpg"], db)

        # No images should be created
        images = db.query(BookImage).filter(BookImage.book_id == book.id).all()
        assert len(images) == 0

    @patch("app.api.v1.books.boto3")
    @patch("app.api.v1.books.settings")
    def test_returns_early_if_no_listing_keys(self, mock_settings, mock_boto3, db):
        """Test that function returns early when listing_s3_keys is empty."""
        from app.api.v1.books import _copy_listing_images_to_book

        mock_settings.images_bucket = "test-bucket"
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        _copy_listing_images_to_book(book.id, [], db)

        # S3 should not be called
        mock_s3.copy_object.assert_not_called()

        # No images should be created
        images = db.query(BookImage).filter(BookImage.book_id == book.id).all()
        assert len(images) == 0

    @patch("app.api.v1.books.boto3")
    @patch("app.api.v1.books.settings")
    def test_continues_on_s3_copy_failure(self, mock_settings, mock_boto3, db):
        """Test that function continues with other images when one S3 copy fails."""
        from app.api.v1.books import _copy_listing_images_to_book

        mock_settings.images_bucket = "test-bucket"
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3

        # First copy fails, second succeeds
        mock_s3.copy_object.side_effect = [Exception("S3 error"), None]

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        listing_keys = ["listings/item/fail.jpg", "listings/item/success.jpg"]

        with patch("app.api.v1.images.generate_thumbnail") as mock_thumb:
            mock_thumb.return_value = (True, None)
            _copy_listing_images_to_book(book.id, listing_keys, db)

        # Only second image should be created (first failed)
        images = db.query(BookImage).filter(BookImage.book_id == book.id).all()
        assert len(images) == 1
        assert images[0].s3_key == f"{book.id}/image_01.jpg"

    @patch("app.api.v1.books.boto3")
    @patch("app.api.v1.books.settings")
    def test_continues_on_thumbnail_failure(self, mock_settings, mock_boto3, db):
        """Test that function continues when thumbnail generation fails."""
        from app.api.v1.books import _copy_listing_images_to_book

        mock_settings.images_bucket = "test-bucket"
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        listing_keys = ["listings/item/image.jpg"]

        with patch("app.api.v1.images.generate_thumbnail") as mock_thumb:
            # Thumbnail fails but copy succeeds
            mock_thumb.return_value = (False, "Thumbnail error")
            _copy_listing_images_to_book(book.id, listing_keys, db)

        # Image record should still be created even if thumbnail failed
        images = db.query(BookImage).filter(BookImage.book_id == book.id).all()
        assert len(images) == 1
        assert images[0].s3_key == f"{book.id}/image_00.jpg"

        # Thumbnail upload should not have been called
        mock_s3.upload_file.assert_not_called()
