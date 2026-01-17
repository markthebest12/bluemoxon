"""Integration tests for image processing service.

These tests verify components work together without heavy mocking,
catching issues that unit tests with mocks might miss.
"""

from unittest.mock import patch

from app.models import Book, BookImage, ImageProcessingJob
from app.services.image_processing import get_sqs_client, queue_image_processing


class TestSQSClientIntegration:
    """Verify SQS client instantiation works."""

    def test_sqs_client_can_be_instantiated(self):
        """SQS client should be creatable (may fail without AWS creds, that's OK)."""
        # This verifies boto3 is properly configured and imports work
        try:
            client = get_sqs_client()
            assert client is not None
        except Exception as e:
            # Expected in test env without AWS creds
            # But it should be a credential/config error, not an import error
            error_str = str(e).lower()
            error_type = type(e).__name__
            assert (
                "credentials" in error_str
                or "region" in error_str
                or "NoCredentialsError" in error_type
            ), f"Unexpected error type: {error_type}: {e}"


class TestModelIntegration:
    """Verify models work together correctly."""

    def test_image_processing_job_relationships(self, db):
        """ImageProcessingJob should properly relate to Book and BookImage."""
        # Create a book
        book = Book(title="Test Book for Integration")
        db.add(book)
        db.flush()

        # Create a source image
        source_image = BookImage(
            book_id=book.id,
            s3_key="test/source.jpg",
            cloudfront_url="https://cdn.example.com/test/source.jpg",
            display_order=1,
            is_primary=True,
        )
        db.add(source_image)
        db.flush()

        # Create a job referencing it
        job = ImageProcessingJob(
            book_id=book.id,
            source_image_id=source_image.id,
        )
        db.add(job)
        db.flush()

        # Verify relationships work
        assert job.book_id == book.id
        assert job.source_image_id == source_image.id
        assert job.status == "pending"
        assert job.attempt_count == 0

        # Verify we can query back
        fetched = db.query(ImageProcessingJob).filter(ImageProcessingJob.id == job.id).first()
        assert fetched is not None
        assert fetched.source_image_id == source_image.id

        db.rollback()

    def test_book_image_processed_flag(self, db):
        """BookImage.is_background_processed flag should work correctly."""
        # Create a book
        book = Book(title="Test Book for Processing Flag")
        db.add(book)
        db.flush()

        # Unprocessed image
        unprocessed = BookImage(
            book_id=book.id,
            s3_key="test/unprocessed.jpg",
            cloudfront_url="https://cdn.example.com/test/unprocessed.jpg",
            display_order=1,
            is_background_processed=False,
        )
        db.add(unprocessed)

        # Processed image
        processed = BookImage(
            book_id=book.id,
            s3_key="test/processed.png",
            cloudfront_url="https://cdn.example.com/test/processed.png",
            display_order=2,
            is_background_processed=True,
        )
        db.add(processed)
        db.flush()

        # Query for processed images only
        processed_images = (
            db.query(BookImage)
            .filter(
                BookImage.book_id == book.id,
                BookImage.is_background_processed == True,  # noqa: E712
            )
            .all()
        )

        assert len(processed_images) == 1
        assert processed_images[0].s3_key == "test/processed.png"

        db.rollback()


class TestServiceIntegration:
    """Verify service functions work with real objects."""

    def test_queue_image_processing_creates_job(self, db):
        """queue_image_processing should create a job in the database."""
        # Create a book
        book = Book(title="Test Book for Queue")
        db.add(book)
        db.flush()

        # Create a source image
        source_image = BookImage(
            book_id=book.id,
            s3_key="test/source.jpg",
            cloudfront_url="https://cdn.example.com/test/source.jpg",
            display_order=1,
            is_primary=True,
        )
        db.add(source_image)
        db.flush()

        # Mock only the SQS send (we don't want to actually send)
        with patch("app.services.image_processing.send_image_processing_job") as mock_send:
            job = queue_image_processing(db, book.id, source_image.id)

        # Job should be created
        assert job is not None
        assert job.book_id == book.id
        assert job.source_image_id == source_image.id
        assert job.status == "pending"

        # SQS should have been called
        mock_send.assert_called_once()

        db.rollback()

    def test_queue_image_processing_prevents_duplicates(self, db):
        """Should not create duplicate jobs for same image."""
        # Create a book
        book = Book(title="Test Book for Duplicates")
        db.add(book)
        db.flush()

        source_image = BookImage(
            book_id=book.id,
            s3_key="test/source.jpg",
            cloudfront_url="https://cdn.example.com/test/source.jpg",
            display_order=1,
            is_primary=True,
        )
        db.add(source_image)
        db.flush()

        with patch("app.services.image_processing.send_image_processing_job"):
            # First call creates job
            job1 = queue_image_processing(db, book.id, source_image.id)
            assert job1 is not None

            # Second call should return None (duplicate prevention)
            job2 = queue_image_processing(db, book.id, source_image.id)
            assert job2 is None

        db.rollback()
