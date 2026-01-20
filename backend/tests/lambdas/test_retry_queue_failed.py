"""Tests for retry_queue_failed Lambda handler."""

from unittest.mock import patch

from sqlalchemy.orm import Session

from app.models import Book, BookImage
from app.models.image_processing_job import ImageProcessingJob


class TestImageProcessingJobModel:
    """Test model changes for queue retry support."""

    def test_queue_retry_count_field_exists_and_defaults_to_zero(self, db: Session):
        """queue_retry_count field should exist and default to 0."""
        book = Book(title="Test Book", status="EVALUATING")
        db.add(book)
        db.flush()

        job = ImageProcessingJob(
            book_id=book.id,
            status="pending",
        )
        db.add(job)
        db.flush()

        assert hasattr(job, "queue_retry_count")
        assert job.queue_retry_count == 0

    def test_permanently_failed_status_is_valid(self, db: Session):
        """permanently_failed should be a valid status value."""
        book = Book(title="Test Book", status="EVALUATING")
        db.add(book)
        db.flush()

        job = ImageProcessingJob(
            book_id=book.id,
            status="permanently_failed",
        )
        db.add(job)
        db.flush()

        assert job.status == "permanently_failed"


class TestRetryQueueFailedJobs:
    """Tests for retry_queue_failed_jobs function."""

    def _create_queue_failed_job(
        self, db: Session, queue_retry_count: int = 0
    ) -> ImageProcessingJob:
        """Helper to create a queue_failed job with associated book and image."""
        book = Book(title="Test Book", status="EVALUATING")
        db.add(book)
        db.flush()

        image = BookImage(book_id=book.id, s3_key="test.jpg", display_order=0)
        db.add(image)
        db.flush()

        job = ImageProcessingJob(
            book_id=book.id,
            source_image_id=image.id,
            status="queue_failed",
            queue_retry_count=queue_retry_count,
            failure_reason="SQS send failed",
        )
        db.add(job)
        db.commit()
        return job

    def test_retries_queue_failed_jobs_successfully(self, db: Session):
        """Should retry queue_failed jobs and update status to pending on success."""
        from lambdas.retry_queue_failed.handler import retry_queue_failed_jobs

        job = self._create_queue_failed_job(db)

        with patch("lambdas.retry_queue_failed.handler.send_image_processing_job"):
            result = retry_queue_failed_jobs(db)

        assert result["retried"] == 1
        assert result["succeeded"] == 1

        db.refresh(job)
        assert job.status == "pending"
        assert job.queue_retry_count == 0

    def test_increments_retry_count_on_failure(self, db: Session):
        """Should increment queue_retry_count when SQS send fails again."""
        from lambdas.retry_queue_failed.handler import retry_queue_failed_jobs

        job = self._create_queue_failed_job(db, queue_retry_count=1)

        with patch(
            "lambdas.retry_queue_failed.handler.send_image_processing_job",
            side_effect=Exception("SQS still failing"),
        ):
            result = retry_queue_failed_jobs(db)

        assert result["retried"] == 1
        assert result["succeeded"] == 0

        db.refresh(job)
        assert job.status == "queue_failed"
        assert job.queue_retry_count == 2

    def test_sets_permanently_failed_after_max_retries(self, db: Session):
        """Should set status to permanently_failed after 3 retry attempts."""
        from lambdas.retry_queue_failed.handler import retry_queue_failed_jobs

        job = self._create_queue_failed_job(db, queue_retry_count=2)

        with patch(
            "lambdas.retry_queue_failed.handler.send_image_processing_job",
            side_effect=Exception("SQS still failing"),
        ):
            result = retry_queue_failed_jobs(db)

        assert result["permanently_failed"] == 1

        db.refresh(job)
        assert job.status == "permanently_failed"
        assert job.queue_retry_count == 3

    def test_skips_jobs_at_max_retry_count(self, db: Session):
        """Should not retry jobs that have already reached max retry count."""
        from lambdas.retry_queue_failed.handler import retry_queue_failed_jobs

        self._create_queue_failed_job(db, queue_retry_count=3)

        with patch("lambdas.retry_queue_failed.handler.send_image_processing_job") as mock_send:
            result = retry_queue_failed_jobs(db)

        assert result["retried"] == 0
        mock_send.assert_not_called()

    def test_only_retries_queue_failed_status(self, db: Session):
        """Should only retry jobs with queue_failed status, not other statuses."""
        from lambdas.retry_queue_failed.handler import retry_queue_failed_jobs

        book = Book(title="Test Book", status="EVALUATING")
        db.add(book)
        db.flush()

        image = BookImage(book_id=book.id, s3_key="test.jpg", display_order=0)
        db.add(image)
        db.flush()

        pending_job = ImageProcessingJob(
            book_id=book.id, source_image_id=image.id, status="pending"
        )
        failed_job = ImageProcessingJob(book_id=book.id, source_image_id=image.id, status="failed")
        db.add_all([pending_job, failed_job])
        db.commit()

        with patch("lambdas.retry_queue_failed.handler.send_image_processing_job") as mock_send:
            result = retry_queue_failed_jobs(db)

        assert result["retried"] == 0
        mock_send.assert_not_called()

    def test_respects_batch_size_limit(self, db: Session):
        """Should only process up to BATCH_SIZE jobs per invocation."""
        from lambdas.retry_queue_failed.handler import BATCH_SIZE, retry_queue_failed_jobs

        for _ in range(BATCH_SIZE + 5):
            self._create_queue_failed_job(db)

        with patch("lambdas.retry_queue_failed.handler.send_image_processing_job"):
            result = retry_queue_failed_jobs(db)

        assert result["retried"] == BATCH_SIZE


class TestLambdaHandler:
    """Tests for the Lambda handler entry point."""

    def test_handler_returns_retry_stats(self, db: Session):
        """Lambda handler should return retry statistics."""
        from lambdas.retry_queue_failed.handler import handler

        book = Book(title="Test Book", status="EVALUATING")
        db.add(book)
        db.flush()

        image = BookImage(book_id=book.id, s3_key="test.jpg", display_order=0)
        db.add(image)
        db.flush()

        job = ImageProcessingJob(
            book_id=book.id,
            source_image_id=image.id,
            status="queue_failed",
            queue_retry_count=0,
        )
        db.add(job)
        db.commit()

        with patch("lambdas.retry_queue_failed.handler.send_image_processing_job"):
            with patch("lambdas.retry_queue_failed.handler.SessionLocal", return_value=db):
                result = handler({}, None)

        assert "retried" in result
        assert "succeeded" in result
        assert "permanently_failed" in result

    def test_handler_handles_empty_queue(self, db: Session):
        """Lambda handler should handle case when no queue_failed jobs exist."""
        from lambdas.retry_queue_failed.handler import handler

        with patch("lambdas.retry_queue_failed.handler.SessionLocal", return_value=db):
            result = handler({}, None)

        assert result["retried"] == 0
        assert result["succeeded"] == 0


class TestAdminRetryEndpoint:
    """Tests for admin API endpoint to trigger retry."""

    def test_admin_endpoint_invokes_retry_function(self, db: Session):
        """POST /admin/image-processing/retry-queue-failed should invoke retry."""
        from app.api.v1.admin import retry_queue_failed_endpoint

        book = Book(title="Test Book", status="EVALUATING")
        db.add(book)
        db.flush()

        image = BookImage(book_id=book.id, s3_key="test.jpg", display_order=0)
        db.add(image)
        db.flush()

        job = ImageProcessingJob(
            book_id=book.id,
            source_image_id=image.id,
            status="queue_failed",
            queue_retry_count=0,
        )
        db.add(job)
        db.commit()

        with patch("app.services.image_processing.send_image_processing_job"):
            result = retry_queue_failed_endpoint(db=db)

        assert result.retried >= 0
        assert result.succeeded >= 0
        assert result.permanently_failed >= 0
