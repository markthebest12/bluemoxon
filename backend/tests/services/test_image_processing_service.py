"""Tests for image processing service."""

from unittest.mock import patch

import pytest

from app.models import Book, BookImage, ImageProcessingJob


class TestQueueImageProcessing:
    """Tests for queuing image processing jobs."""

    def test_creates_job_record(self, db):
        """Should create ImageProcessingJob in database."""
        from app.services.image_processing import queue_image_processing

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(
            book_id=book.id,
            s3_key="test_123.jpg",
            display_order=0,
            is_primary=True,
        )
        db.add(image)
        db.commit()

        with patch("app.services.image_processing.send_image_processing_job"):
            job = queue_image_processing(db, book.id, image.id)

        assert job is not None
        assert job.book_id == book.id
        assert job.source_image_id == image.id
        assert job.status == "pending"

    def test_sends_sqs_message(self, db):
        """Should send message to SQS queue."""
        from app.services.image_processing import queue_image_processing

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(book_id=book.id, s3_key="test.jpg", display_order=0)
        db.add(image)
        db.commit()

        with patch("app.services.image_processing.send_image_processing_job") as mock_send:
            job = queue_image_processing(db, book.id, image.id)
            mock_send.assert_called_once_with(str(job.id), book.id, image.id)

    def test_skips_if_pending_job_exists(self, db):
        """Should not create duplicate job if one is already pending."""
        from app.services.image_processing import queue_image_processing

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(book_id=book.id, s3_key="test.jpg", display_order=0)
        db.add(image)
        db.commit()

        existing_job = ImageProcessingJob(
            book_id=book.id,
            source_image_id=image.id,
            status="pending",
        )
        db.add(existing_job)
        db.commit()

        with patch("app.services.image_processing.send_image_processing_job") as mock_send:
            result = queue_image_processing(db, book.id, image.id)
            mock_send.assert_not_called()
            assert result is None

    def test_skips_if_processing_job_exists(self, db):
        """Should not create duplicate job if one is already processing."""
        from app.services.image_processing import queue_image_processing

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(book_id=book.id, s3_key="test.jpg", display_order=0)
        db.add(image)
        db.commit()

        existing_job = ImageProcessingJob(
            book_id=book.id,
            source_image_id=image.id,
            status="processing",
        )
        db.add(existing_job)
        db.commit()

        with patch("app.services.image_processing.send_image_processing_job") as mock_send:
            result = queue_image_processing(db, book.id, image.id)
            mock_send.assert_not_called()
            assert result is None

    def test_creates_new_job_if_previous_completed(self, db):
        """Should create new job if previous job is completed."""
        from app.services.image_processing import queue_image_processing

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(book_id=book.id, s3_key="test.jpg", display_order=0)
        db.add(image)
        db.commit()

        existing_job = ImageProcessingJob(
            book_id=book.id,
            source_image_id=image.id,
            status="completed",
        )
        db.add(existing_job)
        db.commit()

        with patch("app.services.image_processing.send_image_processing_job"):
            result = queue_image_processing(db, book.id, image.id)
            assert result is not None
            assert result.id != existing_job.id

    def test_creates_new_job_if_previous_failed(self, db):
        """Should create new job if previous job failed."""
        from app.services.image_processing import queue_image_processing

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(book_id=book.id, s3_key="test.jpg", display_order=0)
        db.add(image)
        db.commit()

        existing_job = ImageProcessingJob(
            book_id=book.id,
            source_image_id=image.id,
            status="failed",
        )
        db.add(existing_job)
        db.commit()

        with patch("app.services.image_processing.send_image_processing_job"):
            result = queue_image_processing(db, book.id, image.id)
            assert result is not None
            assert result.id != existing_job.id


class TestGetImageProcessingQueueUrl:
    """Tests for SQS queue URL retrieval."""

    def test_returns_queue_url(self):
        """Should return queue URL from settings."""
        from app.services.image_processing import get_image_processing_queue_url

        with patch("app.services.image_processing.get_settings") as mock_settings:
            mock_settings.return_value.image_processing_queue_name = "test-queue"
            mock_settings.return_value.aws_region = "us-east-1"
            with patch("app.services.image_processing.boto3") as mock_boto:
                mock_sts = mock_boto.client.return_value
                mock_sts.get_caller_identity.return_value = {"Account": "123456789"}
                url = get_image_processing_queue_url()
                assert "test-queue" in url
                assert "123456789" in url

    def test_raises_if_queue_not_configured(self):
        """Should raise ValueError if queue name not set."""
        from app.services.image_processing import get_image_processing_queue_url

        with patch("app.services.image_processing.get_settings") as mock_settings:
            mock_settings.return_value.image_processing_queue_name = None
            with pytest.raises(ValueError, match="IMAGE_PROCESSING_QUEUE_NAME"):
                get_image_processing_queue_url()
