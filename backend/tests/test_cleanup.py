"""Tests for cleanup Lambda functionality."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.models import Book
from lambdas.cleanup.handler import (
    check_expired_sources,
    cleanup_orphaned_images,
    cleanup_stale_evaluations,
    retry_failed_archives,
)


class TestCleanupStaleEvaluations:
    """Tests for cleanup_stale_evaluations function."""

    def test_archives_stale_evaluating_books(self, db):
        """Test that books in EVALUATING status for > 30 days are archived."""
        # Create a stale book (updated 35 days ago)
        stale_book = Book(
            title="Stale Evaluation",
            status="EVALUATING",
        )
        db.add(stale_book)
        db.commit()

        # Manually set updated_at to 35 days ago
        stale_date = datetime.now(UTC) - timedelta(days=35)
        db.query(Book).filter(Book.id == stale_book.id).update(
            {"updated_at": stale_date}
        )
        db.commit()

        # Run cleanup
        count = cleanup_stale_evaluations(db)

        # Verify
        db.refresh(stale_book)
        assert count == 1
        assert stale_book.status == "REMOVED"

    def test_does_not_archive_recent_evaluating_books(self, db):
        """Test that recent EVALUATING books are not archived."""
        # Create a recent book (updated 10 days ago)
        recent_book = Book(
            title="Recent Evaluation",
            status="EVALUATING",
        )
        db.add(recent_book)
        db.commit()

        # Set updated_at to 10 days ago (within threshold)
        recent_date = datetime.now(UTC) - timedelta(days=10)
        db.query(Book).filter(Book.id == recent_book.id).update(
            {"updated_at": recent_date}
        )
        db.commit()

        # Run cleanup
        count = cleanup_stale_evaluations(db)

        # Verify book is unchanged
        db.refresh(recent_book)
        assert count == 0
        assert recent_book.status == "EVALUATING"

    def test_does_not_archive_non_evaluating_books(self, db):
        """Test that stale books with other statuses are not archived."""
        # Create stale ON_HAND book
        stale_book = Book(
            title="Stale On Hand",
            status="ON_HAND",
        )
        db.add(stale_book)
        db.commit()

        # Manually set updated_at to 35 days ago
        stale_date = datetime.now(UTC) - timedelta(days=35)
        db.query(Book).filter(Book.id == stale_book.id).update(
            {"updated_at": stale_date}
        )
        db.commit()

        # Run cleanup
        count = cleanup_stale_evaluations(db)

        # Verify book is unchanged
        db.refresh(stale_book)
        assert count == 0
        assert stale_book.status == "ON_HAND"


class TestArchiveAttemptsField:
    """Tests for archive_attempts field on Book model."""

    def test_archive_attempts_defaults_to_zero(self, db):
        """Test that archive_attempts defaults to 0 when creating a book."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()
        db.refresh(book)

        assert book.archive_attempts == 0

    def test_archive_attempts_can_be_incremented(self, db):
        """Test that archive_attempts can be incremented."""
        book = Book(title="Test Book", archive_attempts=0)
        db.add(book)
        db.commit()

        book.archive_attempts += 1
        db.commit()
        db.refresh(book)

        assert book.archive_attempts == 1

    def test_archive_attempts_persists_value(self, db):
        """Test that archive_attempts value is persisted correctly."""
        book = Book(title="Test Book", archive_attempts=3)
        db.add(book)
        db.commit()

        # Query fresh from DB
        loaded_book = db.query(Book).filter(Book.id == book.id).first()
        assert loaded_book.archive_attempts == 3


class TestSourceExpiredField:
    """Tests for source_expired field on Book model."""

    def test_source_expired_defaults_to_none(self, db):
        """Test that source_expired defaults to None when creating a book."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()
        db.refresh(book)

        assert book.source_expired is None

    def test_source_expired_can_be_set_true(self, db):
        """Test that source_expired can be set to True."""
        book = Book(title="Test Book", source_url="https://example.com/book")
        db.add(book)
        db.commit()

        book.source_expired = True
        db.commit()
        db.refresh(book)

        assert book.source_expired is True

    def test_source_expired_can_be_set_false(self, db):
        """Test that source_expired can be set to False."""
        book = Book(title="Test Book", source_url="https://example.com/book")
        db.add(book)
        db.commit()

        book.source_expired = False
        db.commit()
        db.refresh(book)

        assert book.source_expired is False


class TestCheckExpiredSources:
    """Tests for check_expired_sources function."""

    @patch("lambdas.cleanup.handler.requests.head")
    def test_marks_source_expired_on_404(self, mock_head, db):
        """Test that sources returning 404 are marked as expired."""
        # Create book with source URL
        book = Book(
            title="Test Book",
            source_url="https://example.com/expired-item",
        )
        db.add(book)
        db.commit()

        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response

        # Run check
        checked, expired = check_expired_sources(db)

        # Verify
        db.refresh(book)
        assert checked == 1
        assert expired == 1
        assert book.source_expired is True

    @patch("lambdas.cleanup.handler.requests.head")
    def test_marks_source_valid_on_200(self, mock_head, db):
        """Test that sources returning 200 are marked as not expired."""
        # Create book with source URL
        book = Book(
            title="Test Book",
            source_url="https://example.com/valid-item",
        )
        db.add(book)
        db.commit()

        # Mock 200 response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        # Run check
        checked, expired = check_expired_sources(db)

        # Verify
        db.refresh(book)
        assert checked == 1
        assert expired == 0
        assert book.source_expired is False

    @patch("lambdas.cleanup.handler.requests.head")
    def test_skips_already_checked_sources(self, mock_head, db):
        """Test that sources already checked are skipped."""
        # Create book with already-checked source
        book = Book(
            title="Test Book",
            source_url="https://example.com/already-checked",
            source_expired=False,
        )
        db.add(book)
        db.commit()

        # Run check
        checked, expired = check_expired_sources(db)

        # Verify HEAD was not called
        assert checked == 0
        assert expired == 0
        mock_head.assert_not_called()

    @patch("lambdas.cleanup.handler.requests.head")
    def test_skips_books_without_source_url(self, mock_head, db):
        """Test that books without source_url are skipped."""
        # Create book without source URL
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        # Run check
        checked, expired = check_expired_sources(db)

        # Verify
        assert checked == 0
        assert expired == 0
        mock_head.assert_not_called()


class TestCleanupOrphanedImages:
    """Tests for cleanup_orphaned_images function."""

    @patch("lambdas.cleanup.handler.boto3.client")
    def test_finds_orphaned_images_dry_run(self, mock_boto_client, db):
        """Test that orphaned images are found but not deleted in dry run mode."""
        # Setup mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Mock S3 listing - 3 images in S3
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "images/book1/photo1.jpg"},
                {"Key": "images/book2/photo2.jpg"},
                {"Key": "images/orphan/photo3.jpg"},  # Orphaned
            ]
        }

        # Create book with 2 images in DB
        from app.models.image import BookImage

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image1 = BookImage(book_id=book.id, s3_key="images/book1/photo1.jpg")
        image2 = BookImage(book_id=book.id, s3_key="images/book2/photo2.jpg")
        db.add_all([image1, image2])
        db.commit()

        # Run cleanup (dry run by default)
        result = cleanup_orphaned_images(db, bucket="test-bucket")

        # Verify
        assert result["found"] == 1
        assert result["deleted"] == 0
        assert "images/orphan/photo3.jpg" in result["keys"]
        mock_s3.delete_object.assert_not_called()

    @patch("lambdas.cleanup.handler.boto3.client")
    def test_deletes_orphaned_images_when_enabled(self, mock_boto_client, db):
        """Test that orphaned images are deleted when delete=True."""
        # Setup mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Mock S3 listing - 2 images in S3
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "images/book1/photo1.jpg"},
                {"Key": "images/orphan/photo2.jpg"},  # Orphaned
            ]
        }

        # Create book with 1 image in DB
        from app.models.image import BookImage

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(book_id=book.id, s3_key="images/book1/photo1.jpg")
        db.add(image)
        db.commit()

        # Run cleanup with delete=True
        result = cleanup_orphaned_images(db, bucket="test-bucket", delete=True)

        # Verify
        assert result["found"] == 1
        assert result["deleted"] == 1
        assert "images/orphan/photo2.jpg" in result["keys"]
        mock_s3.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="images/orphan/photo2.jpg"
        )

    @patch("lambdas.cleanup.handler.boto3.client")
    def test_no_orphans_returns_empty(self, mock_boto_client, db):
        """Test that returns empty result when no orphans found."""
        # Setup mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Mock S3 listing - 1 image in S3
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "images/book1/photo1.jpg"},
            ]
        }

        # Create book with matching image in DB
        from app.models.image import BookImage

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(book_id=book.id, s3_key="images/book1/photo1.jpg")
        db.add(image)
        db.commit()

        # Run cleanup
        result = cleanup_orphaned_images(db, bucket="test-bucket")

        # Verify
        assert result["found"] == 0
        assert result["deleted"] == 0
        assert result["keys"] == []


class TestCleanupHandler:
    """Tests for the main Lambda handler function."""

    @pytest.mark.asyncio
    @patch("app.db.session.get_db")
    @patch("lambdas.cleanup.handler.cleanup_stale_evaluations")
    @patch("lambdas.cleanup.handler.check_expired_sources")
    @patch("lambdas.cleanup.handler.cleanup_orphaned_images")
    @patch("lambdas.cleanup.handler.retry_failed_archives")
    async def test_handler_runs_all_actions(
        self, mock_retry, mock_orphans, mock_expired, mock_stale, mock_get_db
    ):
        """Test handler with action='all' runs all cleanup functions."""
        from lambdas.cleanup.handler import handler

        # Setup mocks
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_stale.return_value = 2
        mock_expired.return_value = (10, 3)
        mock_orphans.return_value = {"found": 5, "deleted": 0, "keys": []}
        mock_retry.return_value = {"retried": 1, "succeeded": 1, "failed": 0}

        # Run handler
        event = {"action": "all", "bucket": "test-bucket"}
        result = await handler(event, None)

        # Verify all functions called
        mock_stale.assert_called_once()
        mock_expired.assert_called_once()
        mock_orphans.assert_called_once()
        mock_retry.assert_called_once()

        # Verify result structure
        assert result["stale_evaluations_archived"] == 2
        assert result["sources_checked"] == 10
        assert result["sources_expired"] == 3
        assert result["orphans_found"] == 5
        assert result["archives_retried"] == 1

    @pytest.mark.asyncio
    @patch("app.db.session.get_db")
    @patch("lambdas.cleanup.handler.cleanup_stale_evaluations")
    async def test_handler_runs_stale_action_only(self, mock_stale, mock_get_db):
        """Test handler with action='stale' only cleans stale evaluations."""
        from lambdas.cleanup.handler import handler

        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_stale.return_value = 3

        event = {"action": "stale"}
        result = await handler(event, None)

        mock_stale.assert_called_once()
        assert result["stale_evaluations_archived"] == 3
        assert "sources_checked" not in result

    @pytest.mark.asyncio
    @patch("app.db.session.get_db")
    @patch("lambdas.cleanup.handler.check_expired_sources")
    async def test_handler_runs_expired_action_only(self, mock_expired, mock_get_db):
        """Test handler with action='expired' only checks expired sources."""
        from lambdas.cleanup.handler import handler

        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_expired.return_value = (15, 5)

        event = {"action": "expired"}
        result = await handler(event, None)

        mock_expired.assert_called_once()
        assert result["sources_checked"] == 15
        assert result["sources_expired"] == 5
        assert "stale_evaluations_archived" not in result

    @pytest.mark.asyncio
    @patch("app.db.session.get_db")
    @patch("lambdas.cleanup.handler.cleanup_orphaned_images")
    async def test_handler_runs_orphans_action_with_delete(self, mock_orphans, mock_get_db):
        """Test handler with action='orphans' and delete_orphans=True."""
        from lambdas.cleanup.handler import handler

        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_orphans.return_value = {"found": 10, "deleted": 10, "keys": ["a.jpg"]}

        event = {"action": "orphans", "bucket": "my-bucket", "delete_orphans": True}
        result = await handler(event, None)

        mock_orphans.assert_called_once()
        # Verify delete=True was passed
        call_args = mock_orphans.call_args
        assert call_args[1]["delete"] is True
        assert call_args[1]["bucket"] == "my-bucket"
        assert result["orphans_found"] == 10
        assert result["orphans_deleted"] == 10

    @pytest.mark.asyncio
    @patch("app.db.session.get_db")
    @patch("lambdas.cleanup.handler.retry_failed_archives")
    async def test_handler_runs_archives_action_only(self, mock_retry, mock_get_db):
        """Test handler with action='archives' only retries failed archives."""
        from lambdas.cleanup.handler import handler

        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_retry.return_value = {"retried": 2, "succeeded": 1, "failed": 1}

        event = {"action": "archives"}
        result = await handler(event, None)

        mock_retry.assert_called_once()
        assert result["archives_retried"] == 2
        assert result["archives_succeeded"] == 1
        assert result["archives_failed"] == 1

    @pytest.mark.asyncio
    async def test_handler_returns_error_for_invalid_action(self):
        """Test handler returns error for unknown action."""
        from lambdas.cleanup.handler import handler

        event = {"action": "invalid_action"}
        result = await handler(event, None)

        assert "error" in result
        assert "invalid_action" in result["error"].lower() or "unknown" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_handler_requires_bucket_for_orphans(self):
        """Test handler returns error when orphans action lacks bucket."""
        from lambdas.cleanup.handler import handler

        event = {"action": "orphans"}  # Missing bucket
        result = await handler(event, None)

        assert "error" in result
        assert "bucket" in result["error"].lower()


class TestRetryFailedArchives:
    """Tests for retry_failed_archives function."""

    @pytest.mark.asyncio
    @patch("lambdas.cleanup.handler.archive_url")
    async def test_retries_failed_archives(self, mock_archive, db):
        """Test that failed archives are retried and updated on success."""
        # Create book with failed archive
        book = Book(
            title="Test Book",
            source_url="https://example.com/book",
            archive_status="failed",
            archive_attempts=1,
        )
        db.add(book)
        db.commit()

        # Mock successful archive
        mock_archive.return_value = {
            "status": "success",
            "archived_url": "https://web.archive.org/web/123/https://example.com/book",
            "error": None,
        }

        # Run retry
        result = await retry_failed_archives(db)

        # Verify
        db.refresh(book)
        assert result["retried"] == 1
        assert result["succeeded"] == 1
        assert result["failed"] == 0
        assert book.archive_status == "success"
        assert book.archive_attempts == 2
        assert book.source_archived_url is not None

    @pytest.mark.asyncio
    @patch("lambdas.cleanup.handler.archive_url")
    async def test_increments_attempts_on_failure(self, mock_archive, db):
        """Test that attempts are incremented even on failure."""
        # Create book with failed archive
        book = Book(
            title="Test Book",
            source_url="https://example.com/book",
            archive_status="failed",
            archive_attempts=1,
        )
        db.add(book)
        db.commit()

        # Mock failed archive
        mock_archive.return_value = {
            "status": "failed",
            "archived_url": None,
            "error": "Timeout",
        }

        # Run retry
        result = await retry_failed_archives(db)

        # Verify
        db.refresh(book)
        assert result["retried"] == 1
        assert result["succeeded"] == 0
        assert result["failed"] == 1
        assert book.archive_status == "failed"
        assert book.archive_attempts == 2

    @pytest.mark.asyncio
    @patch("lambdas.cleanup.handler.archive_url")
    async def test_skips_books_at_max_attempts(self, mock_archive, db):
        """Test that books at max attempts (3) are skipped."""
        # Create book with max attempts
        book = Book(
            title="Test Book",
            source_url="https://example.com/book",
            archive_status="failed",
            archive_attempts=3,
        )
        db.add(book)
        db.commit()

        # Run retry
        result = await retry_failed_archives(db)

        # Verify
        assert result["retried"] == 0
        mock_archive.assert_not_called()

    @pytest.mark.asyncio
    @patch("lambdas.cleanup.handler.archive_url")
    async def test_skips_successful_archives(self, mock_archive, db):
        """Test that successful archives are not retried."""
        # Create book with successful archive
        book = Book(
            title="Test Book",
            source_url="https://example.com/book",
            archive_status="success",
            source_archived_url="https://web.archive.org/web/123/...",
            archive_attempts=1,
        )
        db.add(book)
        db.commit()

        # Run retry
        result = await retry_failed_archives(db)

        # Verify
        assert result["retried"] == 0
        mock_archive.assert_not_called()
