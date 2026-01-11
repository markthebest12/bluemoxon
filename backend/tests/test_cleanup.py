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
        db.query(Book).filter(Book.id == stale_book.id).update({"updated_at": stale_date})
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
        db.query(Book).filter(Book.id == recent_book.id).update({"updated_at": recent_date})
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
        db.query(Book).filter(Book.id == stale_book.id).update({"updated_at": stale_date})
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

    @patch("lambdas.cleanup.handler.httpx.head")
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

    @patch("lambdas.cleanup.handler.httpx.head")
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

    @patch("lambdas.cleanup.handler.httpx.head")
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

    @patch("lambdas.cleanup.handler.httpx.head")
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
    """Tests for cleanup_orphaned_images function.

    IMPORTANT: These tests reflect the real-world key format mismatch:
    - S3 stores images with 'books/' prefix: "books/515/image_00.webp"
    - Database stores keys WITHOUT prefix: "515/image_00.webp"

    The cleanup function must handle this by:
    1. Only listing S3 objects under 'books/' prefix
    2. Stripping prefix when comparing to DB keys
    3. Using full S3 key when deleting
    """

    @patch("lambdas.cleanup.handler.boto3.client")
    def test_finds_orphaned_images_dry_run(self, mock_boto_client, db):
        """Test that orphaned images are found but not deleted in dry run mode."""
        # Setup mock S3 client with paginator
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Mock paginator for S3 listing - 3 images in S3 (with books/ prefix)
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "books/123/photo1.jpg"},
                    {"Key": "books/456/photo2.jpg"},
                    {"Key": "books/orphan/photo3.jpg"},  # Orphaned - not in DB
                ]
            }
        ]

        # Create book with 2 images in DB (WITHOUT books/ prefix)
        from app.models.image import BookImage

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image1 = BookImage(book_id=book.id, s3_key="123/photo1.jpg")
        image2 = BookImage(book_id=book.id, s3_key="456/photo2.jpg")
        db.add_all([image1, image2])
        db.commit()

        # Run cleanup (dry run by default)
        result = cleanup_orphaned_images(db, bucket="test-bucket")

        # Verify - should find orphan with full S3 key
        assert result["found"] == 1
        assert result["orphans_found"] == 1
        assert result["deleted"] == 0
        assert "books/orphan/photo3.jpg" in result["keys"]
        mock_s3.delete_object.assert_not_called()
        # Verify paginator was called with books/ prefix
        mock_paginator.paginate.assert_called_once_with(Bucket="test-bucket", Prefix="books/")
        # Verify enhanced output fields
        assert result["scan_prefix"] == "books/"
        assert result["total_objects_scanned"] == 3
        assert result["objects_in_database"] == 2
        assert "orphan_percentage" in result
        assert "sample_orphan_keys" in result
        # Verify orphans_by_prefix breakdown
        assert result["orphans_by_prefix"] == {"books/": 1}

    @patch("lambdas.cleanup.handler.boto3.client")
    def test_deletes_orphaned_images_when_enabled(self, mock_boto_client, db):
        """Test that orphaned images are deleted when delete=True."""
        # Setup mock S3 client with paginator
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Mock paginator for S3 listing - 2 images in S3 (with books/ prefix)
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "books/123/photo1.jpg"},
                    {"Key": "books/orphan/photo2.jpg"},  # Orphaned
                ]
            }
        ]

        # Create book with 1 image in DB (WITHOUT books/ prefix)
        from app.models.image import BookImage

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(book_id=book.id, s3_key="123/photo1.jpg")
        db.add(image)
        db.commit()

        # Run cleanup with delete=True
        result = cleanup_orphaned_images(db, bucket="test-bucket", delete=True)

        # Verify - deletes with full S3 key (including books/ prefix)
        assert result["found"] == 1
        assert result["deleted"] == 1
        assert "books/orphan/photo2.jpg" in result["keys"]
        mock_s3.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="books/orphan/photo2.jpg"
        )

    @patch("lambdas.cleanup.handler.boto3.client")
    def test_no_orphans_returns_empty(self, mock_boto_client, db):
        """Test that returns empty result when no orphans found."""
        # Setup mock S3 client with paginator
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Mock paginator for S3 listing - 1 image in S3 (with books/ prefix)
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "books/123/photo1.jpg"},
                ]
            }
        ]

        # Create book with matching image in DB (WITHOUT books/ prefix)
        from app.models.image import BookImage

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(book_id=book.id, s3_key="123/photo1.jpg")
        db.add(image)
        db.commit()

        # Run cleanup
        result = cleanup_orphaned_images(db, bucket="test-bucket")

        # Verify - no orphans because stripped S3 key matches DB key
        assert result["found"] == 0
        assert result["deleted"] == 0
        assert result["keys"] == []

    @patch("lambdas.cleanup.handler.boto3.client")
    def test_handles_multiple_pages(self, mock_boto_client, db):
        """Test that S3 paginator handles multiple pages correctly."""
        # Setup mock S3 client with paginator returning multiple pages
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        # Simulate multiple pages (> 1000 objects) with books/ prefix
        mock_paginator.paginate.return_value = [
            {"Contents": [{"Key": "books/page1/photo1.jpg"}]},
            {"Contents": [{"Key": "books/page2/photo2.jpg"}]},
            {"Contents": [{"Key": "books/orphan/photo3.jpg"}]},  # Orphaned
        ]

        # Create book with 2 images in DB (WITHOUT books/ prefix)
        from app.models.image import BookImage

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image1 = BookImage(book_id=book.id, s3_key="page1/photo1.jpg")
        image2 = BookImage(book_id=book.id, s3_key="page2/photo2.jpg")
        db.add_all([image1, image2])
        db.commit()

        # Run cleanup
        result = cleanup_orphaned_images(db, bucket="test-bucket")

        # Verify paginator was used with books/ prefix
        mock_s3.get_paginator.assert_called_once_with("list_objects_v2")
        mock_paginator.paginate.assert_called_once_with(Bucket="test-bucket", Prefix="books/")
        assert result["found"] == 1
        assert "books/orphan/photo3.jpg" in result["keys"]

    @patch("lambdas.cleanup.handler.boto3.client")
    def test_only_checks_books_prefix(self, mock_boto_client, db):
        """Test that cleanup only checks images under books/ prefix.

        This is critical - the bucket contains other files (lambda packages,
        listings, etc.) that should NOT be considered for orphan cleanup.
        """
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        # S3 returns only books/ prefix items (due to Prefix filter)
        mock_paginator.paginate.return_value = [{"Contents": [{"Key": "books/123/photo1.jpg"}]}]

        from app.models.image import BookImage

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(book_id=book.id, s3_key="123/photo1.jpg")
        db.add(image)
        db.commit()

        result = cleanup_orphaned_images(db, bucket="test-bucket")

        # Verify Prefix was passed to paginator
        mock_paginator.paginate.assert_called_once_with(Bucket="test-bucket", Prefix="books/")
        assert result["found"] == 0

    @patch("lambdas.cleanup.handler.boto3.client")
    def test_warns_on_high_orphan_percentage(self, mock_boto_client, db):
        """Test that a warning is returned when orphan percentage is high.

        This helps catch bugs where the orphan detection logic is broken
        (like the key format mismatch that caused the 2025-12-30 incident).
        """
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        # All items appear as orphans (simulating broken detection)
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "books/1/photo1.jpg"},
                    {"Key": "books/2/photo2.jpg"},
                    {"Key": "books/3/photo3.jpg"},
                    {"Key": "books/4/photo4.jpg"},
                ]
            }
        ]

        # No images in DB - 100% orphan rate
        result = cleanup_orphaned_images(db, bucket="test-bucket")

        # Verify warning is present for high orphan rate
        assert result["orphan_percentage"] == 100.0
        assert "WARNING" in result
        assert "High orphan rate" in result["WARNING"]
        # Verify orphans_by_prefix shows all 4 items under books/
        assert result["orphans_by_prefix"] == {"books/": 4}

    @patch("lambdas.cleanup.handler.boto3.client")
    def test_key_format_s3_prefix_stripped_for_db_comparison(self, mock_boto_client, db):
        """Explicit test: S3 'books/515/image.webp' matches DB '515/image.webp'.

        This is the exact bug that caused the 2025-12-30 incident.
        S3 stores with prefix, DB stores without - comparison must handle this.
        """
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        # S3 stores WITH books/ prefix
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "books/515/image_00.webp"},
                    {"Key": "books/515/image_01.webp"},
                    {"Key": "books/999/orphan.webp"},  # Not in DB
                ]
            }
        ]

        from app.models.image import BookImage

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        # DB stores WITHOUT books/ prefix - this is the key format difference
        image1 = BookImage(book_id=book.id, s3_key="515/image_00.webp")
        image2 = BookImage(book_id=book.id, s3_key="515/image_01.webp")
        db.add_all([image1, image2])
        db.commit()

        result = cleanup_orphaned_images(db, bucket="test-bucket")

        # Only the orphan should be found (books/999/orphan.webp)
        # The two images with matching DB keys should NOT be orphans
        assert result["orphans_found"] == 1
        assert "books/999/orphan.webp" in result["keys"]
        # Verify the matched images are NOT in orphans
        assert "books/515/image_00.webp" not in result["keys"]
        assert "books/515/image_01.webp" not in result["keys"]


class TestCleanupHandler:
    """Tests for the main Lambda handler function."""

    @patch("lambdas.cleanup.handler.SessionLocal")
    @patch("lambdas.cleanup.handler.cleanup_stale_evaluations")
    @patch("lambdas.cleanup.handler.check_expired_sources")
    @patch("lambdas.cleanup.handler.cleanup_orphaned_images")
    @patch("lambdas.cleanup.handler.retry_failed_archives")
    def test_handler_runs_all_actions(
        self, mock_retry, mock_orphans, mock_expired, mock_stale, mock_session_local
    ):
        """Test handler with action='all' runs all cleanup functions."""
        from lambdas.cleanup.handler import handler

        # Setup mocks
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_stale.return_value = 2
        mock_expired.return_value = (10, 3)
        mock_orphans.return_value = {"found": 5, "deleted": 0, "keys": []}
        mock_retry.return_value = {"retried": 1, "succeeded": 1, "failed": 0}

        # Run handler (sync now)
        event = {"action": "all", "bucket": "test-bucket"}
        result = handler(event, None)

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

        # Verify session was closed
        mock_db.close.assert_called_once()

    @patch("lambdas.cleanup.handler.SessionLocal")
    @patch("lambdas.cleanup.handler.cleanup_stale_evaluations")
    def test_handler_runs_stale_action_only(self, mock_stale, mock_session_local):
        """Test handler with action='stale' only cleans stale evaluations."""
        from lambdas.cleanup.handler import handler

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_stale.return_value = 3

        event = {"action": "stale"}
        result = handler(event, None)

        mock_stale.assert_called_once()
        assert result["stale_evaluations_archived"] == 3
        assert "sources_checked" not in result
        mock_db.close.assert_called_once()

    @patch("lambdas.cleanup.handler.SessionLocal")
    @patch("lambdas.cleanup.handler.check_expired_sources")
    def test_handler_runs_expired_action_only(self, mock_expired, mock_session_local):
        """Test handler with action='expired' only checks expired sources."""
        from lambdas.cleanup.handler import handler

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_expired.return_value = (15, 5)

        event = {"action": "expired"}
        result = handler(event, None)

        mock_expired.assert_called_once()
        assert result["sources_checked"] == 15
        assert result["sources_expired"] == 5
        assert "stale_evaluations_archived" not in result
        mock_db.close.assert_called_once()

    @patch("lambdas.cleanup.handler.SessionLocal")
    @patch("lambdas.cleanup.handler.cleanup_orphaned_images")
    def test_handler_runs_orphans_action_with_delete(self, mock_orphans, mock_session_local):
        """Test handler with action='orphans' and delete_orphans=True."""
        from lambdas.cleanup.handler import handler

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_orphans.return_value = {"found": 10, "deleted": 10, "keys": ["a.jpg"]}

        event = {"action": "orphans", "bucket": "my-bucket", "delete_orphans": True}
        result = handler(event, None)

        mock_orphans.assert_called_once()
        # Verify delete=True was passed
        call_args = mock_orphans.call_args
        assert call_args[1]["delete"] is True
        assert call_args[1]["bucket"] == "my-bucket"
        assert result["orphans_found"] == 10
        assert result["orphans_deleted"] == 10
        mock_db.close.assert_called_once()

    @patch("lambdas.cleanup.handler.SessionLocal")
    @patch("lambdas.cleanup.handler.retry_failed_archives")
    def test_handler_runs_archives_action_only(self, mock_retry, mock_session_local):
        """Test handler with action='archives' only retries failed archives."""
        from lambdas.cleanup.handler import handler

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_retry.return_value = {"retried": 2, "succeeded": 1, "failed": 1}

        event = {"action": "archives"}
        result = handler(event, None)

        mock_retry.assert_called_once()
        assert result["archives_retried"] == 2
        assert result["archives_succeeded"] == 1
        assert result["archives_failed"] == 1
        mock_db.close.assert_called_once()

    def test_handler_returns_error_for_invalid_action(self):
        """Test handler returns error for unknown action."""
        from lambdas.cleanup.handler import handler

        event = {"action": "invalid_action"}
        result = handler(event, None)

        assert "error" in result
        assert "invalid_action" in result["error"].lower() or "unknown" in result["error"].lower()

    def test_handler_requires_bucket_for_orphans(self):
        """Test handler returns error when orphans action lacks bucket."""
        from lambdas.cleanup.handler import handler

        event = {"action": "orphans"}  # Missing bucket
        result = handler(event, None)

        assert "error" in result
        assert "bucket" in result["error"].lower()


class TestCleanupOrphanedImagesWithSize:
    """Tests for orphan scan with size information."""

    @patch("lambdas.cleanup.handler.boto3.client")
    def test_scan_returns_size_per_orphan(self, mock_boto_client, db):
        """Test that scan returns size for each orphan."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "books/123/image_00.webp", "Size": 102400},
                    {"Key": "books/123/image_01.webp", "Size": 204800},
                    {"Key": "books/456/image_00.webp", "Size": 51200},
                ]
            }
        ]

        # No images in DB = all are orphans
        result = cleanup_orphaned_images(db, "test-bucket", delete=False)

        assert result["total_bytes"] == 358400  # 102400 + 204800 + 51200
        assert "orphans_by_book" in result
        assert len(result["orphans_by_book"]) == 2  # Two book folders (123 and 456)

    @patch("lambdas.cleanup.handler.boto3.client")
    def test_scan_groups_by_book_with_size(self, mock_boto_client, db):
        """Test that orphans are grouped by book folder with aggregated sizes."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "books/123/image_00.webp", "Size": 100000},
                    {"Key": "books/123/image_01.webp", "Size": 200000},
                ]
            }
        ]

        # No images in DB = all are orphans
        result = cleanup_orphaned_images(db, "test-bucket", delete=False)

        book_group = result["orphans_by_book"][0]
        assert book_group["folder_id"] == 123
        assert book_group["count"] == 2
        assert book_group["bytes"] == 300000

    @patch("lambdas.cleanup.handler.boto3.client")
    def test_scan_resolves_book_titles(self, mock_boto_client, db):
        """Test that book titles are resolved from DB when available."""
        from app.models import Book

        # Create a book in DB with known ID
        book = Book(title="Test Victorian Book")
        db.add(book)
        db.commit()
        book_id = book.id

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        # Orphan in a folder matching the book ID
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": f"books/{book_id}/orphan_image.webp", "Size": 50000},
                ]
            }
        ]

        result = cleanup_orphaned_images(db, "test-bucket", delete=False)

        book_group = result["orphans_by_book"][0]
        assert book_group["folder_id"] == book_id
        assert book_group["book_id"] == book_id
        assert book_group["book_title"] == "Test Victorian Book"

    @patch("lambdas.cleanup.handler.boto3.client")
    def test_scan_handles_unknown_book_folder(self, mock_boto_client, db):
        """Test that orphans in unknown book folders have null book info."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        # Orphan in a folder with no matching book in DB
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "books/99999/orphan_image.webp", "Size": 50000},
                ]
            }
        ]

        result = cleanup_orphaned_images(db, "test-bucket", delete=False)

        book_group = result["orphans_by_book"][0]
        assert book_group["folder_id"] == 99999
        assert book_group["book_id"] is None
        assert book_group["book_title"] is None


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


class TestCleanupWithProgress:
    """Tests for cleanup_orphaned_images_with_progress function."""

    @patch("lambdas.cleanup.handler.SessionLocal")
    @patch("lambdas.cleanup.handler.boto3.client")
    def test_job_updates_progress_during_deletion(self, mock_boto_client, mock_session_local):
        """Test that job progress is updated during batch deletion."""
        from lambdas.cleanup.handler import cleanup_orphaned_images_with_progress

        # Setup mock DB session and job
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_job = MagicMock()
        mock_job.id = "test-job-id"
        mock_job.status = "pending"
        mock_job.deleted_count = 0
        mock_job.deleted_bytes = 0
        mock_db.get.return_value = mock_job

        # Setup mock S3 client with paginator
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        # 3 orphaned images - all will be deleted
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "books/orphan1/image.jpg", "Size": 1000},
                    {"Key": "books/orphan2/image.jpg", "Size": 2000},
                    {"Key": "books/orphan3/image.jpg", "Size": 3000},
                ]
            }
        ]

        # Mock empty DB keys (all S3 keys are orphans)
        mock_db.query.return_value.all.return_value = []

        # Run cleanup with small batch size to trigger progress updates
        result = cleanup_orphaned_images_with_progress(
            bucket="test-bucket",
            job_id="test-job-id",
            batch_size=2,
        )

        # Verify result
        assert result["deleted"] == 3
        assert result["bytes_freed"] == 6000

        # Verify job status was updated
        assert mock_job.status == "completed"
        assert mock_job.deleted_count == 3
        assert mock_job.deleted_bytes == 6000
        assert mock_job.completed_at is not None

        # Verify S3 delete was called 3 times
        assert mock_s3.delete_object.call_count == 3

        # Verify DB commits happened (initial status + batch updates + final)
        assert mock_db.commit.call_count >= 2

        # Verify session was closed
        mock_db.close.assert_called_once()

    @patch("lambdas.cleanup.handler.SessionLocal")
    def test_job_not_found_returns_error(self, mock_session_local):
        """Test that missing job returns error."""
        from lambdas.cleanup.handler import cleanup_orphaned_images_with_progress

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.get.return_value = None  # Job not found

        result = cleanup_orphaned_images_with_progress(
            bucket="test-bucket",
            job_id="nonexistent-job-id",
        )

        assert "error" in result
        assert "not found" in result["error"]
        mock_db.close.assert_called_once()

    @patch("lambdas.cleanup.handler.SessionLocal")
    @patch("lambdas.cleanup.handler.boto3.client")
    def test_job_marked_failed_on_error(self, mock_boto_client, mock_session_local):
        """Test that job is marked as failed when an error occurs."""
        from lambdas.cleanup.handler import cleanup_orphaned_images_with_progress

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_job = MagicMock()
        mock_job.id = "test-job-id"
        mock_job.status = "pending"
        mock_db.get.return_value = mock_job

        # Setup S3 to raise an exception
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.get_paginator.side_effect = Exception("S3 connection error")

        result = cleanup_orphaned_images_with_progress(
            bucket="test-bucket",
            job_id="test-job-id",
        )

        assert "error" in result
        assert "S3 connection error" in result["error"]

        # Verify job was marked as failed
        assert mock_job.status == "failed"
        assert mock_job.error_message == "S3 connection error"
        mock_db.close.assert_called_once()


class TestHandlerWithJobId:
    """Tests for handler routing to progress tracking."""

    @patch("lambdas.cleanup.handler.cleanup_orphaned_images_with_progress")
    def test_handler_routes_job_id_to_progress_tracking(self, mock_progress_fn):
        """Test that handler routes job_id events to progress tracking function."""
        from lambdas.cleanup.handler import handler

        mock_progress_fn.return_value = {"deleted": 10, "bytes_freed": 50000}

        event = {
            "job_id": "test-job-123",
            "bucket": "test-bucket",
        }
        result = handler(event, None)

        # Verify progress function was called
        mock_progress_fn.assert_called_once_with(
            bucket="test-bucket",
            job_id="test-job-123",
        )
        assert result["deleted"] == 10
        assert result["bytes_freed"] == 50000

    @patch("lambdas.cleanup.handler.SessionLocal")
    @patch("lambdas.cleanup.handler.cleanup_stale_evaluations")
    def test_handler_routes_action_to_standard_cleanup(self, mock_stale, mock_session_local):
        """Test that handler routes action events to standard cleanup."""
        from lambdas.cleanup.handler import handler

        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_stale.return_value = 5

        # Event without job_id should use standard cleanup
        event = {"action": "stale"}
        result = handler(event, None)

        mock_stale.assert_called_once()
        assert result["stale_evaluations_archived"] == 5
