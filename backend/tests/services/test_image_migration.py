"""Tests for image migration service."""

from unittest.mock import MagicMock

from botocore.exceptions import ClientError

from app.services.image_migration import (
    cleanup_stage_3,
    migrate_stage_1,
    migrate_stage_2,
)


class TestMigrateStage1:
    """Tests for Stage 1: Fix ContentType on main images."""

    def test_skips_thumbnails(self):
        """Should skip objects with thumb_ in path."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "books/thumb_test.png"}],
            "IsTruncated": False,
        }

        errors = []
        stats = migrate_stage_1(mock_s3, "bucket", False, None, errors)

        assert stats["skipped"] == 1
        assert stats["processed"] == 0


class TestMigrateStage2:
    """Tests for Stage 2: Copy thumb_*.png to thumb_*.jpg."""

    def test_skips_non_png(self):
        """Should skip files that don't end in .png."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "books/thumb_test.jpg"}],
            "IsTruncated": False,
        }

        errors = []
        stats = migrate_stage_2(mock_s3, "bucket", False, None, errors)

        assert stats["processed"] == 0


class TestCleanupStage3:
    """Tests for Stage 3: Delete old .png thumbnails."""

    def test_skips_when_no_jpg(self):
        """Should not delete .png if .jpg doesn't exist."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "books/thumb_test.png"}],
            "IsTruncated": False,
        }
        # .jpg doesn't exist
        mock_s3.head_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        errors = []
        stats = cleanup_stage_3(mock_s3, "bucket", False, None, errors)

        assert stats["skipped_no_jpg"] == 1
        assert stats["deleted"] == 0
