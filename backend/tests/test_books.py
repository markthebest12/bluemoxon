"""Book API tests."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.models import Book, BookImage
from app.models.analysis import BookAnalysis


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

    def test_create_book_with_near_fine_condition(self, client):
        """Test creating and updating a book with NEAR_FINE condition grade.

        Issue #1223: NEAR_FINE was in the database (from migrations) and frontend
        but missing from the backend ConditionGrade enum, causing API validation
        failures when editing books with this condition.
        """
        # Create book with NEAR_FINE condition
        response = client.post(
            "/api/v1/books",
            json={
                "title": "The Princess",
                "condition_grade": "NEAR_FINE",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["condition_grade"] == "NEAR_FINE"
        book_id = data["id"]

        # Verify it roundtrips correctly on GET
        response = client.get(f"/api/v1/books/{book_id}")
        assert response.status_code == 200
        assert response.json()["condition_grade"] == "NEAR_FINE"

        # Verify PUT works with NEAR_FINE (API uses PUT for updates)
        response = client.put(
            f"/api/v1/books/{book_id}",
            json={"title": "The Princess", "condition_grade": "NEAR_FINE"},
        )
        assert response.status_code == 200
        assert response.json()["condition_grade"] == "NEAR_FINE"


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
            MetadataDirective="COPY",
        )
        mock_s3.copy_object.assert_any_call(
            Bucket="test-bucket",
            CopySource={"Bucket": "test-bucket", "Key": "listings/item123/image_1.png"},
            Key=f"books/{book.id}/image_01.png",
            MetadataDirective="COPY",
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

    @patch("app.api.v1.books.queue_image_processing")
    @patch("app.api.v1.books.boto3")
    @patch("app.api.v1.books.settings")
    def test_queues_image_processing_for_primary_image(
        self, mock_settings, mock_boto3, mock_queue_processing, db
    ):
        """Test that queue_image_processing is called for primary image (idx==0)."""
        from app.api.v1.books import _copy_listing_images_to_book

        mock_settings.images_bucket = "test-bucket"
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        listing_keys = ["listings/item123/image_0.jpg", "listings/item123/image_1.png"]

        with patch("app.api.v1.images.generate_thumbnail") as mock_thumb:
            mock_thumb.return_value = (True, None)
            _copy_listing_images_to_book(book.id, listing_keys, db)

        # Verify queue_image_processing was called once for primary image
        mock_queue_processing.assert_called_once()
        call_args = mock_queue_processing.call_args
        # Should be called with (db, book_id, image_id) where image is primary
        assert call_args[0][1] == book.id  # book_id
        # Verify it was called with the primary image (first image, display_order=0)
        primary_image = (
            db.query(BookImage)
            .filter(BookImage.book_id == book.id, BookImage.is_primary.is_(True))
            .first()
        )
        assert primary_image is not None
        assert call_args[0][2] == primary_image.id  # image_id

    @patch("app.services.aws_clients.boto3")
    @patch("app.services.aws_clients.get_settings")
    @patch("app.services.image_processing.get_settings")
    @patch("app.api.v1.books.boto3")
    @patch("app.api.v1.books.settings")
    def test_image_processing_job_created_integration(
        self,
        mock_books_settings,
        mock_books_boto3,
        mock_ip_settings,
        mock_aws_settings,
        mock_aws_boto3,
        db,
    ):
        """Integration test: verify ImageProcessingJob is actually created in database.

        This test does NOT mock queue_image_processing - it tests the real function
        and only mocks the boto3 clients to avoid actual AWS calls.
        """
        import app.services.image_processing as ip_module
        from app.api.v1.books import _copy_listing_images_to_book
        from app.models import ImageProcessingJob
        from app.services.aws_clients import get_sqs_client

        # Clear cached SQS client so mock takes effect
        get_sqs_client.cache_clear()
        # Clear cached queue URL
        ip_module._queue_url_cache = None

        mock_books_settings.images_bucket = "test-bucket"

        mock_ip_settings.return_value.image_processing_queue_name = "test-queue"
        mock_aws_settings.return_value.aws_region = "us-east-1"

        mock_s3 = MagicMock()
        mock_books_boto3.client.return_value = mock_s3

        mock_sqs = MagicMock()
        mock_sqs.send_message.return_value = {"MessageId": "test-message-id"}
        mock_sqs.get_queue_url.return_value = {
            "QueueUrl": "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
        }

        mock_aws_boto3.client.return_value = mock_sqs

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        listing_keys = ["listings/item123/image_0.jpg"]

        with patch("app.api.v1.images.generate_thumbnail") as mock_thumb:
            mock_thumb.return_value = (True, None)
            _copy_listing_images_to_book(book.id, listing_keys, db)

        primary_image = (
            db.query(BookImage)
            .filter(BookImage.book_id == book.id, BookImage.is_primary.is_(True))
            .first()
        )
        assert primary_image is not None

        job = db.query(ImageProcessingJob).filter(ImageProcessingJob.book_id == book.id).first()
        assert job is not None, "ImageProcessingJob should be created in database"
        assert job.book_id == book.id
        assert job.source_image_id == primary_image.id
        assert job.status == "pending"

        mock_sqs.send_message.assert_called_once()


class TestGetAnalysisIssues:
    """Tests for _get_analysis_issues helper function."""

    def test_no_analysis_returns_none(self, db):
        """Book with no analysis returns None."""
        from app.api.v1.books import _get_analysis_issues

        book = Book(title="Test Book")
        db.add(book)
        db.commit()
        assert _get_analysis_issues(book) is None

    def test_complete_analysis_returns_none(self, db):
        """Book with all analysis fields present returns None."""
        from app.api.v1.books import _get_analysis_issues

        book = Book(title="Test Book")
        db.add(book)
        db.flush()
        analysis = BookAnalysis(
            book_id=book.id,
            recommendations="Buy this book",
            condition_assessment={"grade": "VG"},
            market_analysis={"demand": "high"},
            extraction_status="success",
        )
        db.add(analysis)
        db.commit()
        db.refresh(book)
        assert _get_analysis_issues(book) is None

    def test_truncated_recommendations(self, db):
        """Book with recommendations=None returns ['truncated']."""
        from app.api.v1.books import _get_analysis_issues

        book = Book(title="Test Book")
        db.add(book)
        db.flush()
        analysis = BookAnalysis(
            book_id=book.id,
            recommendations=None,
            condition_assessment={"grade": "VG"},
            market_analysis={"demand": "high"},
        )
        db.add(analysis)
        db.commit()
        db.refresh(book)
        issues = _get_analysis_issues(book)
        assert issues == ["truncated"]

    def test_degraded_extraction(self, db):
        """Book with extraction_status='degraded' returns ['degraded']."""
        from app.api.v1.books import _get_analysis_issues

        book = Book(title="Test Book")
        db.add(book)
        db.flush()
        analysis = BookAnalysis(
            book_id=book.id,
            recommendations="Buy",
            condition_assessment={"grade": "VG"},
            market_analysis={"demand": "high"},
            extraction_status="degraded",
        )
        db.add(analysis)
        db.commit()
        db.refresh(book)
        issues = _get_analysis_issues(book)
        assert issues == ["degraded"]

    def test_missing_condition_assessment(self, db):
        """Book with condition_assessment=None returns ['missing_condition']."""
        from app.api.v1.books import _get_analysis_issues

        book = Book(title="Test Book")
        db.add(book)
        db.flush()
        analysis = BookAnalysis(
            book_id=book.id,
            recommendations="Buy",
            condition_assessment=None,
            market_analysis={"demand": "high"},
        )
        db.add(analysis)
        db.commit()
        db.refresh(book)
        issues = _get_analysis_issues(book)
        assert issues == ["missing_condition"]

    def test_missing_market_analysis(self, db):
        """Book with market_analysis=None returns ['missing_market']."""
        from app.api.v1.books import _get_analysis_issues

        book = Book(title="Test Book")
        db.add(book)
        db.flush()
        analysis = BookAnalysis(
            book_id=book.id,
            recommendations="Buy",
            condition_assessment={"grade": "VG"},
            market_analysis=None,
        )
        db.add(analysis)
        db.commit()
        db.refresh(book)
        issues = _get_analysis_issues(book)
        assert issues == ["missing_market"]

    def test_multiple_issues(self, db):
        """Book with multiple issues returns all of them."""
        from app.api.v1.books import _get_analysis_issues

        book = Book(title="Test Book")
        db.add(book)
        db.flush()
        analysis = BookAnalysis(
            book_id=book.id,
            recommendations=None,
            condition_assessment=None,
            market_analysis=None,
            extraction_status="degraded",
        )
        db.add(analysis)
        db.commit()
        db.refresh(book)
        issues = _get_analysis_issues(book)
        assert "truncated" in issues
        assert "degraded" in issues
        assert "missing_condition" in issues
        assert "missing_market" in issues
        assert len(issues) == 4


class TestApplyExtractedDataToBook:
    """Tests for _apply_extracted_data_to_book helper function."""

    def test_applies_valuation_fields(self, db):
        """Test that valuation_low, valuation_mid, valuation_high are applied."""
        from decimal import Decimal

        from app.api.v1.books import _apply_extracted_data_to_book

        book = Book(title="Test Book")
        db.add(book)
        db.flush()

        extracted_data = {
            "valuation_low": 100,
            "valuation_mid": 150,
            "valuation_high": 200,
        }
        fields_updated = _apply_extracted_data_to_book(book, extracted_data)

        assert book.value_low == Decimal("100")
        assert book.value_mid == Decimal("150")
        assert book.value_high == Decimal("200")
        assert "value_low" in fields_updated
        assert "value_mid" in fields_updated
        assert "value_high" in fields_updated

    def test_calculates_mid_when_missing(self, db):
        """Test that value_mid is auto-calculated when low and high are present but mid is not."""
        from decimal import Decimal

        from app.api.v1.books import _apply_extracted_data_to_book

        book = Book(title="Test Book")
        db.add(book)
        db.flush()

        extracted_data = {
            "valuation_low": 100,
            "valuation_high": 200,
        }
        fields_updated = _apply_extracted_data_to_book(book, extracted_data)

        assert book.value_low == Decimal("100")
        assert book.value_high == Decimal("200")
        assert book.value_mid == Decimal("150")
        assert "value_mid" in fields_updated

    def test_applies_condition_and_binding(self, db):
        """Test that condition_grade and binding_type are applied."""
        from app.api.v1.books import _apply_extracted_data_to_book

        book = Book(title="Test Book")
        db.add(book)
        db.flush()

        extracted_data = {
            "condition_grade": "VG+",
            "binding_type": "Full morocco",
        }
        fields_updated = _apply_extracted_data_to_book(book, extracted_data)

        assert book.condition_grade == "VG+"
        assert book.binding_type == "Full morocco"
        assert "condition_grade" in fields_updated
        assert "binding_type" in fields_updated

    def test_applies_provenance_fields(self, db):
        """Test that provenance fields are applied correctly."""
        from app.api.v1.books import _apply_extracted_data_to_book

        book = Book(title="Test Book")
        db.add(book)
        db.flush()

        extracted_data = {
            "has_provenance": True,
            "provenance_tier": "notable",
            "provenance_description": "From the library of Lord Byron",
        }
        fields_updated = _apply_extracted_data_to_book(book, extracted_data)

        assert book.has_provenance is True
        assert book.provenance_tier == "notable"
        assert book.provenance == "From the library of Lord Byron"
        assert "has_provenance" in fields_updated
        assert "provenance_tier" in fields_updated
        assert "provenance" in fields_updated

    def test_applies_is_first_edition(self, db):
        """Test that is_first_edition is applied (including False values)."""
        from app.api.v1.books import _apply_extracted_data_to_book

        book = Book(title="Test Book")
        db.add(book)
        db.flush()

        extracted_data = {"is_first_edition": False}
        fields_updated = _apply_extracted_data_to_book(book, extracted_data)

        assert book.is_first_edition is False
        assert "is_first_edition" in fields_updated

    def test_empty_extracted_data(self, db):
        """Test that empty extracted_data returns empty list."""
        from app.api.v1.books import _apply_extracted_data_to_book

        book = Book(title="Test Book")
        db.add(book)
        db.flush()

        fields_updated = _apply_extracted_data_to_book(book, {})

        assert fields_updated == []

    def test_zero_values_applied(self, db):
        """Test that zero values are applied (not ignored as falsy).

        Regression test: Using 'if value:' would skip zero values.
        A book worth $0 (damaged, worthless reprint) should have its value updated.
        """
        from decimal import Decimal

        from app.api.v1.books import _apply_extracted_data_to_book

        book = Book(title="Test Book", value_low=Decimal("100"), value_mid=Decimal("150"))
        db.add(book)
        db.flush()

        extracted_data = {"valuation_low": 0, "valuation_mid": 0}
        fields_updated = _apply_extracted_data_to_book(book, extracted_data)

        assert book.value_low == Decimal("0")
        assert book.value_mid == Decimal("0")
        assert "value_low" in fields_updated
        assert "value_mid" in fields_updated

    def test_has_provenance_false_applied(self, db):
        """Test that has_provenance=False is applied (explicit False clears the flag)."""
        from app.api.v1.books import _apply_extracted_data_to_book

        book = Book(title="Test Book", has_provenance=True)
        db.add(book)
        db.flush()

        extracted_data = {"has_provenance": False}
        fields_updated = _apply_extracted_data_to_book(book, extracted_data)

        assert book.has_provenance is False
        assert "has_provenance" in fields_updated


class TestGenerateAnalysisDefaults:
    """Tests for analysis generation default values."""

    def test_sync_endpoint_defaults_to_opus(self):
        """Test that sync analysis generation defaults to opus model."""
        from app.api.v1.books import GenerateAnalysisRequest

        request = GenerateAnalysisRequest()
        assert request.model == "opus"

    def test_async_endpoint_defaults_to_opus(self):
        """Test that async analysis generation defaults to opus model."""
        from app.api.v1.books import GenerateAnalysisAsyncRequest

        request = GenerateAnalysisAsyncRequest()
        assert request.model == "opus"

    def test_analysis_job_create_defaults_to_opus(self):
        """Test that AnalysisJobCreate schema defaults to opus model."""
        from app.schemas.analysis_job import AnalysisJobCreate

        job_create = AnalysisJobCreate()
        assert job_create.model == "opus"


class TestStaleJobAutoCleanup:
    """Tests for stale job auto-cleanup on re-trigger."""

    def test_stale_running_job_auto_failed_on_retrigger(self, client, db):
        """Test that stale running jobs are auto-failed when re-triggering analysis."""
        from app.models import AnalysisJob, Book

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        stale_time = datetime.now(UTC) - timedelta(minutes=20)
        stale_job = AnalysisJob(
            id=uuid4(),
            book_id=book.id,
            status="running",
            model="opus",
            created_at=stale_time,
            updated_at=stale_time,
        )
        db.add(stale_job)
        db.commit()

        with patch("app.api.v1.books.send_analysis_job"):
            response = client.post(f"/api/v1/books/{book.id}/analysis/generate-async")

        assert response.status_code == 202
        db.refresh(stale_job)
        assert stale_job.status == "failed"
        assert "timed out" in stale_job.error_message.lower()

    def test_fresh_running_job_blocks_retrigger(self, client, db):
        """Test that fresh running jobs still block re-triggering."""
        from app.models import AnalysisJob, Book

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        fresh_time = datetime.now(UTC) - timedelta(minutes=5)
        fresh_job = AnalysisJob(
            id=uuid4(),
            book_id=book.id,
            status="running",
            model="opus",
            created_at=fresh_time,
            updated_at=fresh_time,
        )
        db.add(fresh_job)
        db.commit()

        response = client.post(f"/api/v1/books/{book.id}/analysis/generate-async")
        assert response.status_code == 409
        assert "already in progress" in response.json()["detail"].lower()

    def test_stale_pending_job_auto_failed_on_retrigger(self, client, db):
        """Test that stale pending jobs are also auto-failed when re-triggering analysis."""
        from app.models import AnalysisJob, Book

        book = Book(title="Test Book Pending")
        db.add(book)
        db.commit()

        stale_time = datetime.now(UTC) - timedelta(minutes=20)
        stale_job = AnalysisJob(
            id=uuid4(),
            book_id=book.id,
            status="pending",  # Test pending status
            model="opus",
            created_at=stale_time,
            updated_at=stale_time,
        )
        db.add(stale_job)
        db.commit()

        with patch("app.api.v1.books.send_analysis_job"):
            response = client.post(f"/api/v1/books/{book.id}/analysis/generate-async")

        assert response.status_code == 202
        db.refresh(stale_job)
        assert stale_job.status == "failed"
        assert "timed out" in stale_job.error_message.lower()


class TestBuildBookResponse:
    """Tests for _build_book_response helper function."""

    def test_builds_response_with_basic_fields(self, db):
        """Test that _build_book_response returns BookResponse with computed fields."""
        from app.api.v1.books import _build_book_response
        from app.models import Book

        book = Book(title="Test Book")
        db.add(book)
        db.commit()
        db.refresh(book)

        response = _build_book_response(book, db)

        assert response.id == book.id
        assert response.title == "Test Book"
        assert response.has_analysis is False
        assert response.has_eval_runbook is False
        assert response.eval_runbook_job_status is None
        assert response.analysis_job_status is None
        assert response.image_count == 0
        assert response.primary_image_url is None

    def test_builds_response_with_analysis(self, db):
        """Test has_analysis is True when book has analysis."""
        from app.api.v1.books import _build_book_response
        from app.models import Book
        from app.models.analysis import BookAnalysis

        book = Book(title="Test Book With Analysis")
        db.add(book)
        db.commit()

        analysis = BookAnalysis(book_id=book.id, recommendations="Buy it")
        db.add(analysis)
        db.commit()
        db.refresh(book)

        response = _build_book_response(book, db)

        assert response.has_analysis is True

    def test_builds_response_with_images(self, db):
        """Test primary_image_url and image_count with images."""
        from unittest.mock import PropertyMock, patch

        from app.api.v1.books import _build_book_response
        from app.config import Settings
        from app.models import Book, BookImage

        book = Book(title="Test Book With Images")
        db.add(book)
        db.commit()

        img1 = BookImage(
            book_id=book.id,
            s3_key="images/img1.jpg",
            display_order=1,
            is_primary=False,
        )
        img2 = BookImage(
            book_id=book.id,
            s3_key="images/img2.jpg",
            display_order=2,
            is_primary=True,
        )
        db.add_all([img1, img2])
        db.commit()
        db.refresh(book)

        with (
            patch.object(Settings, "is_aws_lambda", new_callable=PropertyMock, return_value=True),
            patch(
                "app.api.v1.books.get_cloudfront_url",
                return_value="https://cdn.example.com/images/img2.jpg",
            ),
        ):
            response = _build_book_response(book, db)

        assert response.image_count == 2
        assert response.primary_image_url == "https://cdn.example.com/images/img2.jpg"

    def test_builds_response_with_first_image_as_primary_fallback(self, db):
        """Test primary image falls back to first by display_order when none marked primary."""
        from unittest.mock import PropertyMock, patch

        from app.api.v1.books import _build_book_response
        from app.config import Settings
        from app.models import Book, BookImage

        book = Book(title="Test Book Fallback Primary")
        db.add(book)
        db.commit()

        img1 = BookImage(
            book_id=book.id,
            s3_key="images/first.jpg",
            display_order=5,
            is_primary=False,
        )
        img2 = BookImage(
            book_id=book.id,
            s3_key="images/second.jpg",
            display_order=1,
            is_primary=False,
        )
        db.add_all([img1, img2])
        db.commit()
        db.refresh(book)

        with (
            patch.object(Settings, "is_aws_lambda", new_callable=PropertyMock, return_value=True),
            patch("app.api.v1.books.get_cloudfront_url") as mock_cdn,
        ):
            mock_cdn.return_value = "https://cdn.example.com/images/second.jpg"
            response = _build_book_response(book, db)
            mock_cdn.assert_called_once_with("images/second.jpg")

        assert response.primary_image_url == "https://cdn.example.com/images/second.jpg"

    def test_builds_response_with_analysis_issues(self, db):
        """Test analysis_issues populated when analysis has problems."""
        from app.api.v1.books import _build_book_response
        from app.models import Book
        from app.models.analysis import BookAnalysis

        book = Book(title="Test Book Truncated Analysis")
        db.add(book)
        db.commit()

        analysis = BookAnalysis(
            book_id=book.id,
            recommendations=None,  # Missing = truncated
            condition_assessment=None,  # Missing condition
        )
        db.add(analysis)
        db.commit()
        db.refresh(book)

        response = _build_book_response(book, db)

        assert response.analysis_issues is not None
        assert "truncated" in response.analysis_issues
        assert "missing_condition" in response.analysis_issues

    def test_builds_response_with_active_job_status(self, db):
        """Test job statuses populated when active jobs exist."""
        from uuid import uuid4

        from app.api.v1.books import _build_book_response
        from app.models import AnalysisJob, Book, EvalRunbookJob

        book = Book(title="Test Book With Jobs")
        db.add(book)
        db.commit()

        analysis_job = AnalysisJob(
            id=uuid4(),
            book_id=book.id,
            status="running",
            model="opus",
        )
        eval_job = EvalRunbookJob(
            id=uuid4(),
            book_id=book.id,
            status="pending",
        )
        db.add_all([analysis_job, eval_job])
        db.commit()
        db.refresh(book)

        response = _build_book_response(book, db)

        assert response.analysis_job_status == "running"
        assert response.eval_runbook_job_status == "pending"

    def test_builds_response_with_legacy_enum_values(self, db):
        """Test BookResponse accepts legacy DB values that don't match enums.

        The database has free-form values like:
        - condition_grade: "VG", "VG+", "Good+", "Fair to Good"
        - provenance_tier: "Tier 3" (vs enum "TIER_3")

        BookResponse must serialize these without 500 errors.
        """
        from app.api.v1.books import _build_book_response
        from app.models import Book

        # Create book with legacy values that don't match enums
        book = Book(
            title="Book With Legacy Values",
            condition_grade="VG+",  # Not in ConditionGrade enum
            provenance_tier="Tier 3",  # Not in Tier enum (expects TIER_3)
            status="ON_HAND",  # Matches enum
            inventory_type="PRIMARY",  # Matches enum
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        # Should not raise ValidationError
        response = _build_book_response(book, db)

        # Legacy values should serialize as-is
        assert response.condition_grade == "VG+"
        assert response.provenance_tier == "Tier 3"
        assert response.status == "ON_HAND"
        assert response.inventory_type == "PRIMARY"


class TestFilterByDateAcquired:
    """Tests for filtering books by date_acquired (purchase_date)."""

    def test_filter_by_date_acquired(self, client, db):
        """Test filtering books by acquisition date."""
        from datetime import date

        from app.models import Book

        # Create a book with a specific purchase/acquisition date
        book = Book(title="Test Book", purchase_date=date(2026, 1, 5))
        db.add(book)
        db.commit()

        # Filter by that date using date_acquired param
        response = client.get("/api/v1/books", params={"date_acquired": "2026-01-05"})
        assert response.status_code == 200
        data = response.json()

        # Should find the book
        assert data["total"] >= 1
        book_ids = [b["id"] for b in data["items"]]
        assert book.id in book_ids

    def test_filter_by_date_acquired_no_match(self, client, db):
        """Test date_acquired filter returns empty when no match."""
        from datetime import date

        from app.models import Book

        # Create a book with a specific purchase/acquisition date
        book = Book(title="Test Book", purchase_date=date(2026, 1, 5))
        db.add(book)
        db.commit()

        # Filter by different date
        response = client.get("/api/v1/books", params={"date_acquired": "2026-01-10"})
        assert response.status_code == 200
        data = response.json()

        # Should not find the book
        book_ids = [b["id"] for b in data["items"]]
        assert book.id not in book_ids


class TestIsNullFiltering:
    """Tests for __isnull filtering (uncategorized/ungraded books)."""

    def test_filter_category__isnull_true(self, client, db):
        """Test filtering books where category IS NULL."""
        from app.models import Book

        # Create books with and without category
        book_with_category = Book(title="Categorized Book", category="Victorian Poetry")
        book_without_category = Book(title="Uncategorized Book", category=None)
        db.add_all([book_with_category, book_without_category])
        db.commit()

        # Filter for books where category is null
        response = client.get("/api/v1/books", params={"category__isnull": "true"})
        assert response.status_code == 200
        data = response.json()

        # Should only find the book without category
        book_ids = [b["id"] for b in data["items"]]
        assert book_without_category.id in book_ids
        assert book_with_category.id not in book_ids

    def test_filter_category__isnull_false(self, client, db):
        """Test filtering books where category IS NOT NULL."""
        from app.models import Book

        # Create books with and without category
        book_with_category = Book(title="Categorized Book", category="Victorian Poetry")
        book_without_category = Book(title="Uncategorized Book", category=None)
        db.add_all([book_with_category, book_without_category])
        db.commit()

        # Filter for books where category is not null
        response = client.get("/api/v1/books", params={"category__isnull": "false"})
        assert response.status_code == 200
        data = response.json()

        # Should only find the book with category
        book_ids = [b["id"] for b in data["items"]]
        assert book_with_category.id in book_ids
        assert book_without_category.id not in book_ids

    def test_filter_condition_grade__isnull_true(self, client, db):
        """Test filtering books where condition_grade IS NULL."""
        from app.models import Book

        # Create books with and without condition_grade
        book_with_grade = Book(title="Graded Book", condition_grade="VG")
        book_without_grade = Book(title="Ungraded Book", condition_grade=None)
        db.add_all([book_with_grade, book_without_grade])
        db.commit()

        # Filter for books where condition_grade is null
        response = client.get("/api/v1/books", params={"condition_grade__isnull": "true"})
        assert response.status_code == 200
        data = response.json()

        # Should only find the book without condition_grade
        book_ids = [b["id"] for b in data["items"]]
        assert book_without_grade.id in book_ids
        assert book_with_grade.id not in book_ids

    def test_filter_condition_grade__isnull_false(self, client, db):
        """Test filtering books where condition_grade IS NOT NULL."""
        from app.models import Book

        # Create books with and without condition_grade
        book_with_grade = Book(title="Graded Book", condition_grade="VG")
        book_without_grade = Book(title="Ungraded Book", condition_grade=None)
        db.add_all([book_with_grade, book_without_grade])
        db.commit()

        # Filter for books where condition_grade is not null
        response = client.get("/api/v1/books", params={"condition_grade__isnull": "false"})
        assert response.status_code == 200
        data = response.json()

        # Should only find the book with condition_grade
        book_ids = [b["id"] for b in data["items"]]
        assert book_with_grade.id in book_ids
        assert book_without_grade.id not in book_ids

    def test_filter_category__isnull_combined_with_other_filters(self, client, db):
        """Test that __isnull can be combined with other filters."""
        from app.models import Book

        # Create books with different combinations
        book1 = Book(title="Uncategorized ON_HAND", category=None, status="ON_HAND")
        book2 = Book(title="Uncategorized IN_TRANSIT", category=None, status="IN_TRANSIT")
        book3 = Book(title="Categorized ON_HAND", category="Poetry", status="ON_HAND")
        db.add_all([book1, book2, book3])
        db.commit()

        # Filter for uncategorized books that are ON_HAND
        response = client.get(
            "/api/v1/books",
            params={"category__isnull": "true", "status": "ON_HAND"},
        )
        assert response.status_code == 200
        data = response.json()

        # Should only find book1
        book_ids = [b["id"] for b in data["items"]]
        assert book1.id in book_ids
        assert book2.id not in book_ids
        assert book3.id not in book_ids

    def test_mutual_exclusion_category_and_category__isnull(self, client):
        """Test that passing both category and category__isnull returns 400."""
        response = client.get(
            "/api/v1/books",
            params={"category": "Victorian Poetry", "category__isnull": "true"},
        )
        assert response.status_code == 400
        assert "mutually exclusive" in response.json()["detail"]

    def test_mutual_exclusion_condition_grade_and_condition_grade__isnull(self, client):
        """Test that passing both condition_grade and condition_grade__isnull returns 400."""
        response = client.get(
            "/api/v1/books",
            params={"condition_grade": "FINE", "condition_grade__isnull": "true"},
        )
        assert response.status_code == 400
        assert "mutually exclusive" in response.json()["detail"]


class TestAnalysisEntityValidation:
    """Test entity validation in analysis upload endpoint."""

    @pytest.fixture(autouse=True)
    def clear_entity_cache(self):
        """Clear entity caches before each test to ensure test isolation."""
        from app.services.entity_matching import invalidate_entity_cache

        # Clear all entity caches before each test
        invalidate_entity_cache("publisher")
        invalidate_entity_cache("binder")
        invalidate_entity_cache("author")
        yield
        # Also clear after test for good measure
        invalidate_entity_cache("publisher")
        invalidate_entity_cache("binder")
        invalidate_entity_cache("author")

    def test_analysis_with_similar_binder_returns_409(self, client, db):
        """Analysis with fuzzy-matching binder name returns 409 Conflict."""
        from app.models import Binder, Book

        # Create existing binder
        binder = Binder(name="Riviere & Son", tier="TIER_1")
        db.add(binder)
        db.commit()

        # Create a book
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        # Create analysis markdown with a similar but not exact binder name
        analysis_md = """# Book Analysis

## Binding Context

**Binder Identification:**
- **Name:** Riviere and Son
- **Confidence:** HIGH
"""

        # Upload analysis - should fail with 409 due to similar binder
        response = client.put(
            f"/api/v1/books/{book.id}/analysis",
            content=analysis_md,
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 409
        data = response.json()
        # FastAPI wraps HTTPException detail in a "detail" key
        detail = data["detail"]
        assert detail["error"] == "similar_entity_exists"
        assert detail["entity_type"] == "binder"
        assert detail["input"] == "Riviere and Son"
        assert detail["suggestions"] is not None
        assert len(detail["suggestions"]) >= 1
        assert detail["suggestions"][0]["name"] == "Riviere & Son"

    def test_analysis_with_unknown_publisher_succeeds_with_warning(self, client, db):
        """Analysis with unknown publisher name succeeds with warning (allow_unknown=True)."""
        from app.models import Book, Publisher

        # Create a few publishers but NOT the one we'll request
        publisher = Publisher(name="Macmillan", tier="TIER_1")
        db.add(publisher)
        db.commit()

        # Create a book
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        # Create analysis markdown with an unknown publisher
        # Use **Publisher:** pattern which the parser recognizes
        analysis_md = """# Book Analysis

## Physical Description

**Publisher:** Completely Unknown Publisher Ltd
**Binding:** Full Morocco
"""

        # Upload analysis - should succeed with warning due to allow_unknown=True
        response = client.put(
            f"/api/v1/books/{book.id}/analysis",
            content=analysis_md,
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 200
        data = response.json()
        # Response includes warnings for skipped associations
        assert "warnings" in data
        assert any("Completely Unknown Publisher Ltd" in w for w in data["warnings"])
        assert any("not found" in w for w in data["warnings"])
        # Book should not have publisher_id set
        db.refresh(book)
        assert book.publisher_id is None

    def test_analysis_with_exact_match_binder_succeeds(self, client, db):
        """Analysis with exact binder name match succeeds."""
        from app.models import Binder, Book

        # Create existing binder
        binder = Binder(name="Zaehnsdorf", tier="TIER_1")
        db.add(binder)
        db.commit()

        # Create a book
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        # Create analysis markdown with exact binder name match
        analysis_md = """# Book Analysis

## Binding Context

**Binder Identification:**
- **Name:** Zaehnsdorf
- **Confidence:** HIGH
"""

        # Upload analysis - should succeed with exact match
        response = client.put(
            f"/api/v1/books/{book.id}/analysis",
            content=analysis_md,
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["binder_updated"] is True

        # Verify binder was associated
        db.refresh(book)
        assert book.binder_id == binder.id

    def test_analysis_with_exact_match_publisher_succeeds(self, client, db):
        """Analysis with exact publisher name match succeeds."""
        from app.models import Book, Publisher

        # Create existing publisher
        publisher = Publisher(name="Chapman and Hall", tier="TIER_1")
        db.add(publisher)
        db.commit()

        # Create a book
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        # Create analysis markdown with exact publisher name match
        # Use **Publisher:** pattern which the parser recognizes
        analysis_md = """# Book Analysis

## Physical Description

**Publisher:** Chapman and Hall
**Binding:** Full Morocco
"""

        # Upload analysis - should succeed with exact match
        response = client.put(
            f"/api/v1/books/{book.id}/analysis",
            content=analysis_md,
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["publisher_updated"] is True

        # Verify publisher was associated
        db.refresh(book)
        assert book.publisher_id == publisher.id

    def test_analysis_without_entities_succeeds(self, client, db):
        """Analysis without binder or publisher references succeeds."""
        from app.models import Book

        # Create a book
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        # Create simple analysis markdown without entities
        analysis_md = """# Book Analysis

## Executive Summary

This is a test book analysis.

## Recommendations

Buy this book.
"""

        # Upload analysis - should succeed
        response = client.put(
            f"/api/v1/books/{book.id}/analysis",
            content=analysis_md,
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["binder_updated"] is False
        assert data["publisher_updated"] is False

    def test_analysis_with_both_entities_failing_returns_all_errors(self, client, db):
        """Analysis with both binder and publisher fuzzy-matching returns all errors."""
        from app.models import Binder, Book, Publisher

        # Create existing binder and publisher
        binder = Binder(name="Riviere & Son", tier="TIER_1")
        publisher = Publisher(name="Macmillan and Co.", tier="TIER_1")
        db.add(binder)
        db.add(publisher)
        db.commit()

        # Create a book
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        # Create analysis with both similar but not exact entity names
        analysis_md = """# Book Analysis

## Binding Context

**Binder Identification:**
- **Name:** Riviere and Son
- **Confidence:** HIGH

## Physical Description

**Publisher:** Macmilan and Co
**Binding:** Full Morocco
"""

        # Upload analysis - should fail with 409 and BOTH errors
        response = client.put(
            f"/api/v1/books/{book.id}/analysis",
            content=analysis_md,
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 409
        data = response.json()
        detail = data["detail"]

        # Should have multiple_validation_errors with both entity errors
        assert detail["error"] == "multiple_validation_errors"
        assert "errors" in detail
        assert len(detail["errors"]) == 2

        # Check both entities are in errors
        entity_types = {e["entity_type"] for e in detail["errors"]}
        assert "binder" in entity_types
        assert "publisher" in entity_types

    def test_analysis_x_bmx_warning_header_set_on_warnings(self, client, db):
        """Analysis with skipped associations sets X-BMX-Warning header."""
        from app.models import Book, Publisher

        # Create a publisher (but not the one we'll request)
        publisher = Publisher(name="Macmillan", tier="TIER_1")
        db.add(publisher)
        db.commit()

        # Create a book
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        # Create analysis with unknown publisher (triggers warning)
        analysis_md = """# Book Analysis

## Physical Description

**Publisher:** Completely Unknown Publisher Ltd
**Binding:** Full Morocco
"""

        response = client.put(
            f"/api/v1/books/{book.id}/analysis",
            content=analysis_md,
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 200
        # Check X-BMX-Warning header is set
        assert "X-BMX-Warning" in response.headers
        warning_header = response.headers["X-BMX-Warning"]
        assert "Completely Unknown Publisher Ltd" in warning_header
        assert "not found" in warning_header

    def test_analysis_with_both_entities_succeeding(self, client, db):
        """Analysis with both exact match binder and publisher succeeds."""
        from app.models import Binder, Book, Publisher

        # Create existing binder and publisher
        binder = Binder(name="Zaehnsdorf", tier="TIER_1")
        publisher = Publisher(name="Chapman and Hall", tier="TIER_1")
        db.add(binder)
        db.add(publisher)
        db.commit()

        # Create a book
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        # Create analysis with both exact entity names
        analysis_md = """# Book Analysis

## Binding Context

**Binder Identification:**
- **Name:** Zaehnsdorf
- **Confidence:** HIGH

## Physical Description

**Publisher:** Chapman and Hall
**Binding:** Full Morocco
"""

        response = client.put(
            f"/api/v1/books/{book.id}/analysis",
            content=analysis_md,
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["binder_updated"] is True
        assert data["publisher_updated"] is True

        # Verify both entities were associated
        db.refresh(book)
        assert book.binder_id == binder.id
        assert book.publisher_id == publisher.id

    def test_analysis_fuzzy_match_with_force_includes_match_details(self, client, db):
        """Fuzzy match with force=true includes match name and confidence in warning."""
        from app.models import Binder, Book

        # Create existing binder
        binder = Binder(name="Riviere & Son", tier="TIER_1")
        db.add(binder)
        db.commit()

        # Create a book
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        # Create analysis with similar but not exact binder name
        analysis_md = """# Book Analysis

## Binding Context

**Binder Identification:**
- **Name:** Riviere and Son
- **Confidence:** HIGH
"""

        # Upload with force=true to bypass the error
        response = client.put(
            f"/api/v1/books/{book.id}/analysis?force=true",
            content=analysis_md,
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 200
        # Check X-BMX-Warning header includes fuzzy match details
        assert "X-BMX-Warning" in response.headers
        warning_header = response.headers["X-BMX-Warning"]
        assert "Riviere and Son" in warning_header
        assert "fuzzy matches" in warning_header
        assert "Riviere & Son" in warning_header
        # Should include confidence percentage
        assert "%" in warning_header


class TestTopBooks:
    """Tests for GET /api/v1/books/top (Collection Spotlight)."""

    def test_top_books_excludes_evaluating_status(self, client):
        """Top books endpoint should only return owned books, not EVALUATING.

        The spotlight is for "rediscovering your collection" - books you own.
        Books in EVALUATING status are still being considered for acquisition
        and should not appear in the spotlight.

        Fixes: https://github.com/markthebest12/bluemoxon/issues/1112
        """
        # Use high values to ensure books appear in top results regardless of limit
        # Create a book that SHOULD appear (ON_HAND, PRIMARY, has value)
        on_hand_response = client.post(
            "/api/v1/books",
            json={
                "title": "The Rubaiyat of Omar Khayyam",
                "status": "ON_HAND",
                "inventory_type": "PRIMARY",
                "value_mid": 999999,  # High value ensures it's in top results
            },
        )
        assert on_hand_response.status_code == 201
        on_hand_book = on_hand_response.json()

        # Create a book that should NOT appear (EVALUATING status)
        # Even with a higher value, EVALUATING should be excluded
        evaluating_response = client.post(
            "/api/v1/books",
            json={
                "title": "Idylls of the King",
                "status": "EVALUATING",
                "inventory_type": "PRIMARY",
                "value_mid": 9999999,  # Even higher value but still should be excluded
            },
        )
        assert evaluating_response.status_code == 201
        evaluating_book = evaluating_response.json()

        # Call the top books endpoint
        response = client.get("/api/v1/books/top")
        assert response.status_code == 200

        top_books = response.json()
        top_book_ids = [book["id"] for book in top_books]

        # ON_HAND book should be included
        assert on_hand_book["id"] in top_book_ids, "ON_HAND book should appear in spotlight"

        # EVALUATING book should NOT be included
        assert evaluating_book["id"] not in top_book_ids, (
            "EVALUATING book should NOT appear in spotlight"
        )

    def test_top_books_excludes_removed_status(self, client):
        """Top books should also exclude REMOVED status books."""
        # Use high values to ensure books appear in top results regardless of limit
        # Create ON_HAND book (should appear)
        on_hand_response = client.post(
            "/api/v1/books",
            json={
                "title": "In Memoriam",
                "status": "ON_HAND",
                "inventory_type": "PRIMARY",
                "value_mid": 999999,  # High value ensures it's in top results
            },
        )
        assert on_hand_response.status_code == 201
        on_hand_book = on_hand_response.json()

        # Create REMOVED book (should NOT appear)
        removed_response = client.post(
            "/api/v1/books",
            json={
                "title": "Sold Book",
                "status": "REMOVED",
                "inventory_type": "PRIMARY",
                "value_mid": 9999999,  # Even higher value but still should be excluded
            },
        )
        assert removed_response.status_code == 201
        removed_book = removed_response.json()

        response = client.get("/api/v1/books/top")
        assert response.status_code == 200

        top_book_ids = [book["id"] for book in response.json()]

        assert on_hand_book["id"] in top_book_ids
        assert removed_book["id"] not in top_book_ids, "REMOVED book should NOT appear in spotlight"

    def test_top_books_includes_in_transit(self, client):
        """Top books should include IN_TRANSIT books (purchased, on the way)."""
        # Use high value to ensure book appears in top results regardless of limit
        # IN_TRANSIT books are purchased - they're part of the collection
        in_transit_response = client.post(
            "/api/v1/books",
            json={
                "title": "A Christmas Carol",
                "status": "IN_TRANSIT",
                "inventory_type": "PRIMARY",
                "value_mid": 999999,  # High value ensures it's in top results
            },
        )
        assert in_transit_response.status_code == 201
        in_transit_book = in_transit_response.json()

        response = client.get("/api/v1/books/top")
        assert response.status_code == 200

        top_book_ids = [book["id"] for book in response.json()]

        assert in_transit_book["id"] in top_book_ids, "IN_TRANSIT book should appear in spotlight"


class TestIdsTruncation:
    """Tests for IDs parameter truncation indicator."""

    def test_ids_parameter_no_truncation(self, client):
        """When IDs are under 100, no truncation indicator is returned."""
        # Create 5 books
        book_ids = []
        for i in range(5):
            response = client.post("/api/v1/books", json={"title": f"Book {i}"})
            book_ids.append(response.json()["id"])

        # Request with less than 100 IDs
        ids_str = ",".join(str(bid) for bid in book_ids)
        response = client.get(f"/api/v1/books?ids={ids_str}")
        assert response.status_code == 200
        data = response.json()

        # Should indicate no truncation
        assert data.get("ids_truncated") is False
        assert data.get("ids_requested") == 5
        assert data.get("ids_processed") == 5

    def test_ids_parameter_with_truncation(self, client):
        """When IDs exceed 100, response should include truncation indicator."""
        # Create 5 books
        book_ids = []
        for i in range(5):
            response = client.post("/api/v1/books", json={"title": f"Book {i}"})
            book_ids.append(response.json()["id"])

        # Request with more than 100 IDs (simulate with repeated IDs)
        ids_repeated = book_ids * 30  # 150 IDs
        ids_str = ",".join(str(bid) for bid in ids_repeated)
        response = client.get(f"/api/v1/books?ids={ids_str}")
        assert response.status_code == 200
        data = response.json()

        # Should indicate truncation
        assert data.get("ids_truncated") is True
        assert data.get("ids_requested") == 150
        assert data.get("ids_processed") == 100
