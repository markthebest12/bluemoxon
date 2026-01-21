"""Tests for image migration service."""

from io import BytesIO
from unittest.mock import MagicMock, call

from botocore.exceptions import ClientError

from app.services.image_migration import (
    DEFAULT_BATCH_SIZE,
    MigrationResult,
    _batch_delete_with_errors,
    cleanup_stage_3,
    migrate_stage_1,
    migrate_stage_2,
)

# Magic bytes for different image formats
JPEG_MAGIC = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"  # Valid JPEG header (12+ bytes)
PNG_MAGIC = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00"  # Valid PNG header (12+ bytes)
TRUNCATED_BYTES = b"\xff\xd8"  # Only 2 bytes - too short


def _make_body(data: bytes) -> MagicMock:
    """Create a mock S3 response body with read() method."""
    body = MagicMock()
    body.read.return_value = data
    return body


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
        result = migrate_stage_1(mock_s3, "bucket", False, None, errors)

        assert isinstance(result, MigrationResult)
        assert result.stats["skipped"] == 1
        assert result.stats["processed"] == 0
        assert result.has_more is False
        assert result.continuation_token is None

    def test_pagination_handles_truncated_response(self):
        """Should continue fetching when IsTruncated is True."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.side_effect = [
            {
                "Contents": [{"Key": "books/123/image_01.jpg"}],
                "IsTruncated": True,
                "NextContinuationToken": "token1",
            },
            {
                "Contents": [{"Key": "books/456/image_01.jpg"}],
                "IsTruncated": True,
                "NextContinuationToken": "token2",
            },
            {
                "Contents": [{"Key": "books/789/image_01.jpg"}],
                "IsTruncated": False,
            },
        ]
        mock_s3.get_object.return_value = {"Body": _make_body(JPEG_MAGIC)}
        mock_s3.head_object.return_value = {"ContentType": "image/jpeg"}

        errors = []
        # Use large batch_size so all items are processed in one call
        result = migrate_stage_1(mock_s3, "bucket", False, None, errors, batch_size=1000)

        # Verify list_objects_v2 was called 3 times (once per page)
        assert mock_s3.list_objects_v2.call_count == 3

        # Verify continuation token was passed correctly
        calls = mock_s3.list_objects_v2.call_args_list
        assert "ContinuationToken" not in calls[0][1]
        assert calls[1][1]["ContinuationToken"] == "token1"
        assert calls[2][1]["ContinuationToken"] == "token2"

        # All 3 images should be processed
        assert result.stats["processed"] == 3
        assert result.stats["already_correct"] == 3
        assert result.has_more is False

    def test_error_accumulation(self):
        """Should collect errors and continue processing."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "books/123/image_01.jpg"},
                {"Key": "books/456/image_01.jpg"},  # This one will fail
                {"Key": "books/789/image_01.jpg"},
            ],
            "IsTruncated": False,
        }

        # First and third succeed, second fails
        mock_s3.get_object.side_effect = [
            {"Body": _make_body(JPEG_MAGIC)},
            ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject"),
            {"Body": _make_body(JPEG_MAGIC)},
        ]
        mock_s3.head_object.return_value = {"ContentType": "image/jpeg"}

        errors = []
        result = migrate_stage_1(mock_s3, "bucket", False, None, errors)

        # Should have 1 error collected
        assert len(errors) == 1
        assert "books/456/image_01.jpg" in errors[0]["key"]
        assert result.stats["errors"] == 1

        # Should still process other images
        assert result.stats["processed"] == 3
        assert result.stats["already_correct"] == 2

    def test_dry_run_does_not_modify(self):
        """Dry run should not call copy_object."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "books/123/image_01.jpg"}],
            "IsTruncated": False,
        }
        mock_s3.get_object.return_value = {"Body": _make_body(JPEG_MAGIC)}
        # Current ContentType is wrong
        mock_s3.head_object.return_value = {"ContentType": "image/png"}

        errors = []
        result = migrate_stage_1(mock_s3, "bucket", dry_run=True, limit=None, errors=errors)

        # Should record as fixed but NOT call copy_object
        assert result.stats["fixed"] == 1
        mock_s3.copy_object.assert_not_called()

    def test_real_execution_calls_copy_object(self):
        """Real execution should call copy_object to fix ContentType."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "books/123/image_01.jpg"}],
            "IsTruncated": False,
        }
        mock_s3.get_object.return_value = {"Body": _make_body(JPEG_MAGIC)}
        # Current ContentType is wrong
        mock_s3.head_object.return_value = {"ContentType": "image/png"}

        errors = []
        result = migrate_stage_1(mock_s3, "bucket", dry_run=False, limit=None, errors=errors)

        assert result.stats["fixed"] == 1
        mock_s3.copy_object.assert_called_once()
        call_kwargs = mock_s3.copy_object.call_args[1]
        assert call_kwargs["ContentType"] == "image/jpeg"
        assert call_kwargs["MetadataDirective"] == "REPLACE"

    def test_limit_parameter_stops_processing(self):
        """Should stop processing after limit is reached."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "books/1/image.jpg"},
                {"Key": "books/2/image.jpg"},
                {"Key": "books/3/image.jpg"},
                {"Key": "books/4/image.jpg"},
                {"Key": "books/5/image.jpg"},
            ],
            "IsTruncated": False,
        }
        mock_s3.get_object.return_value = {"Body": _make_body(JPEG_MAGIC)}
        mock_s3.head_object.return_value = {"ContentType": "image/jpeg"}

        errors = []
        result = migrate_stage_1(mock_s3, "bucket", False, limit=2, errors=errors)

        # Should stop after 2 items
        assert result.stats["processed"] == 2
        assert mock_s3.get_object.call_count == 2
        # Limit reached means no more (limit takes priority over batch_size)
        assert result.has_more is False

    def test_truncated_image_handling(self):
        """Should skip images with insufficient bytes for format detection."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "books/123/truncated.jpg"}],
            "IsTruncated": False,
        }
        # Return only 2 bytes (below MIN_DETECTION_BYTES of 12)
        mock_s3.get_object.return_value = {"Body": _make_body(TRUNCATED_BYTES)}

        errors = []
        result = migrate_stage_1(mock_s3, "bucket", False, None, errors)

        # Should be skipped (not an error, just a warning)
        assert result.stats["skipped"] == 1
        assert result.stats["processed"] == 1
        assert result.stats["errors"] == 0

    def test_unknown_format_skipped(self):
        """Should skip images with unknown format."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "books/123/unknown.dat"}],
            "IsTruncated": False,
        }
        # Return bytes that don't match any known format
        mock_s3.get_object.return_value = {"Body": _make_body(b"unknown_format!")}

        errors = []
        result = migrate_stage_1(mock_s3, "bucket", False, None, errors)

        assert result.stats["skipped"] == 1
        assert result.stats["processed"] == 1

    def test_already_correct_content_type_not_modified(self):
        """Should not modify images that already have correct ContentType."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "books/123/image.jpg"}],
            "IsTruncated": False,
        }
        mock_s3.get_object.return_value = {"Body": _make_body(JPEG_MAGIC)}
        mock_s3.head_object.return_value = {"ContentType": "image/jpeg"}

        errors = []
        result = migrate_stage_1(mock_s3, "bucket", dry_run=False, limit=None, errors=errors)

        assert result.stats["already_correct"] == 1
        assert result.stats["fixed"] == 0
        mock_s3.copy_object.assert_not_called()

    def test_batch_size_returns_continuation_token(self):
        """Should return continuation token when batch_size is reached."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "books/1/image.jpg"},
                {"Key": "books/2/image.jpg"},
                {"Key": "books/3/image.jpg"},
            ],
            "IsTruncated": True,
            "NextContinuationToken": "continue_here",
        }
        mock_s3.get_object.return_value = {"Body": _make_body(JPEG_MAGIC)}
        mock_s3.head_object.return_value = {"ContentType": "image/jpeg"}

        errors = []
        result = migrate_stage_1(mock_s3, "bucket", False, None, errors, batch_size=2)

        # Should process 2 items and return with has_more=True
        assert result.stats["processed"] == 2
        assert result.has_more is True
        # Continuation token should be set
        assert result.continuation_token is not None


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

    def test_pagination_handles_truncated_response(self):
        """Should continue fetching when IsTruncated is True."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.side_effect = [
            {
                "Contents": [{"Key": "books/thumb_123/image_01.png"}],
                "IsTruncated": True,
                "NextContinuationToken": "token1",
            },
            {
                "Contents": [{"Key": "books/thumb_456/image_01.png"}],
                "IsTruncated": False,
            },
        ]
        # .jpg doesn't exist, format is JPEG
        mock_s3.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        mock_s3.get_object.return_value = {"Body": _make_body(JPEG_MAGIC)}

        errors = []
        stats = migrate_stage_2(mock_s3, "bucket", False, None, errors)

        assert mock_s3.list_objects_v2.call_count == 2
        assert stats["processed"] == 2
        assert stats["copied"] == 2

    def test_dry_run_does_not_copy(self):
        """Dry run should not call copy_object."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "books/thumb_123/image.png"}],
            "IsTruncated": False,
        }
        # .jpg doesn't exist
        mock_s3.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        mock_s3.get_object.return_value = {"Body": _make_body(JPEG_MAGIC)}

        errors = []
        stats = migrate_stage_2(mock_s3, "bucket", dry_run=True, limit=None, errors=errors)

        assert stats["copied"] == 1
        mock_s3.copy_object.assert_not_called()

    def test_real_execution_copies_to_jpg(self):
        """Real execution should create .jpg copy."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "books/thumb_123/image.png"}],
            "IsTruncated": False,
        }
        # .jpg doesn't exist
        mock_s3.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        mock_s3.get_object.return_value = {"Body": _make_body(JPEG_MAGIC)}

        errors = []
        stats = migrate_stage_2(mock_s3, "bucket", dry_run=False, limit=None, errors=errors)

        assert stats["copied"] == 1
        mock_s3.copy_object.assert_called_once()
        call_kwargs = mock_s3.copy_object.call_args[1]
        assert call_kwargs["Key"] == "books/thumb_123/image.jpg"
        assert call_kwargs["ContentType"] == "image/jpeg"

    def test_limit_parameter_stops_processing(self):
        """Should stop processing after limit is reached."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "books/thumb_1/a.png"},
                {"Key": "books/thumb_2/b.png"},
                {"Key": "books/thumb_3/c.png"},
            ],
            "IsTruncated": False,
        }
        # .jpg doesn't exist
        mock_s3.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        mock_s3.get_object.return_value = {"Body": _make_body(JPEG_MAGIC)}

        errors = []
        stats = migrate_stage_2(mock_s3, "bucket", False, limit=1, errors=errors)

        assert stats["processed"] == 1
        assert stats["copied"] == 1

    def test_skips_if_jpg_already_exists(self):
        """Should skip copy if .jpg already exists."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "books/thumb_123/image.png"}],
            "IsTruncated": False,
        }
        # .jpg already exists
        mock_s3.head_object.return_value = {"ContentType": "image/jpeg"}

        errors = []
        stats = migrate_stage_2(mock_s3, "bucket", False, None, errors)

        assert stats["already_exists"] == 1
        assert stats["copied"] == 0
        mock_s3.copy_object.assert_not_called()

    def test_truncated_image_handling(self):
        """Should skip images with insufficient bytes and add to errors."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "books/thumb_123/truncated.png"}],
            "IsTruncated": False,
        }
        # .jpg doesn't exist
        mock_s3.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        # Return truncated data
        mock_s3.get_object.return_value = {"Body": _make_body(TRUNCATED_BYTES)}

        errors = []
        stats = migrate_stage_2(mock_s3, "bucket", False, None, errors)

        assert stats["skipped_not_jpeg"] == 1
        assert stats["processed"] == 1
        assert len(errors) == 1
        assert "truncated" in errors[0]["error"].lower()

    def test_skips_non_jpeg_content(self):
        """Should skip and log error if content is not JPEG."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "books/thumb_123/actually_png.png"}],
            "IsTruncated": False,
        }
        # .jpg doesn't exist
        mock_s3.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )
        # Content is actually PNG
        mock_s3.get_object.return_value = {"Body": _make_body(PNG_MAGIC)}

        errors = []
        stats = migrate_stage_2(mock_s3, "bucket", False, None, errors)

        assert stats["skipped_not_jpeg"] == 1
        assert len(errors) == 1
        assert "Expected JPEG but found png" in errors[0]["error"]

    def test_error_accumulation(self):
        """Should collect errors and continue processing."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "books/thumb_1/a.png"},
                {"Key": "books/thumb_2/b.png"},  # This one will fail
                {"Key": "books/thumb_3/c.png"},
            ],
            "IsTruncated": False,
        }

        def head_side_effect(**kwargs):
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject")

        mock_s3.head_object.side_effect = head_side_effect

        def get_side_effect(**kwargs):
            if "thumb_2" in kwargs.get("Key", ""):
                raise ClientError({"Error": {"Code": "AccessDenied"}}, "GetObject")
            return {"Body": _make_body(JPEG_MAGIC)}

        mock_s3.get_object.side_effect = get_side_effect

        errors = []
        stats = migrate_stage_2(mock_s3, "bucket", False, None, errors)

        assert stats["errors"] == 1
        assert stats["copied"] == 2
        assert len(errors) == 1


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
        mock_s3.head_object.side_effect = ClientError(
            {"Error": {"Code": "404"}}, "HeadObject"
        )

        errors = []
        stats = cleanup_stage_3(mock_s3, "bucket", False, None, errors)

        assert stats["skipped_no_jpg"] == 1
        assert stats["deleted"] == 0

    def test_pagination_handles_truncated_response(self):
        """Should continue fetching when IsTruncated is True."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.side_effect = [
            {
                "Contents": [{"Key": "books/thumb_1/a.png"}],
                "IsTruncated": True,
                "NextContinuationToken": "token1",
            },
            {
                "Contents": [{"Key": "books/thumb_2/b.png"}],
                "IsTruncated": False,
            },
        ]
        # .jpg exists for all
        mock_s3.head_object.return_value = {"ContentType": "image/jpeg"}
        # Return successful deletions in the Deleted list
        mock_s3.delete_objects.return_value = {
            "Deleted": [
                {"Key": "books/thumb_1/a.png"},
                {"Key": "books/thumb_2/b.png"},
            ]
        }

        errors = []
        stats = cleanup_stage_3(mock_s3, "bucket", False, None, errors)

        assert mock_s3.list_objects_v2.call_count == 2
        assert stats["processed"] == 2
        assert stats["deleted"] == 2

    def test_dry_run_does_not_delete(self):
        """Dry run should not call delete_objects."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "books/thumb_123/image.png"}],
            "IsTruncated": False,
        }
        # .jpg exists
        mock_s3.head_object.return_value = {"ContentType": "image/jpeg"}

        errors = []
        stats = cleanup_stage_3(mock_s3, "bucket", dry_run=True, limit=None, errors=errors)

        assert stats["deleted"] == 1
        mock_s3.delete_objects.assert_not_called()

    def test_real_execution_deletes(self):
        """Real execution should call delete_objects."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [{"Key": "books/thumb_123/image.png"}],
            "IsTruncated": False,
        }
        # .jpg exists
        mock_s3.head_object.return_value = {"ContentType": "image/jpeg"}
        # Return successful deletion
        mock_s3.delete_objects.return_value = {
            "Deleted": [{"Key": "books/thumb_123/image.png"}]
        }

        errors = []
        stats = cleanup_stage_3(mock_s3, "bucket", dry_run=False, limit=None, errors=errors)

        assert stats["deleted"] == 1
        mock_s3.delete_objects.assert_called_once()

    def test_limit_parameter_stops_processing(self):
        """Should stop processing after limit is reached and flush pending deletes."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "books/thumb_1/a.png"},
                {"Key": "books/thumb_2/b.png"},
                {"Key": "books/thumb_3/c.png"},
            ],
            "IsTruncated": False,
        }
        # .jpg exists for all
        mock_s3.head_object.return_value = {"ContentType": "image/jpeg"}
        # Return successful deletions
        mock_s3.delete_objects.return_value = {
            "Deleted": [
                {"Key": "books/thumb_1/a.png"},
                {"Key": "books/thumb_2/b.png"},
            ]
        }

        errors = []
        stats = cleanup_stage_3(mock_s3, "bucket", False, limit=2, errors=errors)

        assert stats["processed"] == 2
        assert stats["deleted"] == 2
        # Should have flushed pending deletes
        mock_s3.delete_objects.assert_called_once()

    def test_batch_delete_error_handling(self):
        """Should handle partial failures in batch delete."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "books/thumb_1/a.png"},
                {"Key": "books/thumb_2/b.png"},
            ],
            "IsTruncated": False,
        }
        # .jpg exists for all
        mock_s3.head_object.return_value = {"ContentType": "image/jpeg"}
        # Simulate partial failure - one succeeds, one fails
        mock_s3.delete_objects.return_value = {
            "Deleted": [{"Key": "books/thumb_1/a.png"}],
            "Errors": [
                {
                    "Key": "books/thumb_2/b.png",
                    "Code": "AccessDenied",
                    "Message": "Access denied",
                }
            ],
        }

        errors = []
        stats = cleanup_stage_3(mock_s3, "bucket", False, None, errors)

        # One succeeded, one failed
        assert stats["deleted"] == 1
        assert stats["errors"] == 1
        assert len(errors) == 1
        assert "books/thumb_2/b.png" in errors[0]["key"]
        assert "AccessDenied" in errors[0]["error"]

    def test_skips_non_png(self):
        """Should skip files that don't end in .png."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "books/thumb_1/a.jpg"},  # Not .png
                {"Key": "books/thumb_1/b.png"},  # Is .png
            ],
            "IsTruncated": False,
        }
        # .jpg exists
        mock_s3.head_object.return_value = {"ContentType": "image/jpeg"}
        # Return successful deletion
        mock_s3.delete_objects.return_value = {
            "Deleted": [{"Key": "books/thumb_1/b.png"}]
        }

        errors = []
        stats = cleanup_stage_3(mock_s3, "bucket", False, None, errors)

        # Only the .png should be processed
        assert stats["processed"] == 1
        assert stats["deleted"] == 1


class TestBatchDeleteWithErrors:
    """Tests for _batch_delete_with_errors helper function."""

    def test_empty_objects_returns_immediately(self):
        """Should return without calling S3 if objects list is empty."""
        mock_s3 = MagicMock()
        errors = []
        stats = {"deleted": 0, "errors": 0}

        _batch_delete_with_errors(mock_s3, "bucket", [], errors, stats)

        mock_s3.delete_objects.assert_not_called()
        assert len(errors) == 0

    def test_successful_delete(self):
        """Should successfully delete objects without errors."""
        mock_s3 = MagicMock()
        # Return successful deletions in Deleted list
        mock_s3.delete_objects.return_value = {
            "Deleted": [{"Key": "a.png"}, {"Key": "b.png"}]
        }
        errors = []
        stats = {"deleted": 0, "errors": 0}
        objects = [{"Key": "a.png"}, {"Key": "b.png"}]

        _batch_delete_with_errors(mock_s3, "bucket", objects, errors, stats)

        mock_s3.delete_objects.assert_called_once_with(
            Bucket="bucket", Delete={"Objects": objects}
        )
        assert len(errors) == 0
        assert stats["deleted"] == 2
        assert stats["errors"] == 0

    def test_all_objects_fail(self):
        """Should handle case where all deletes fail."""
        mock_s3 = MagicMock()
        # All fail - no Deleted list, only Errors
        mock_s3.delete_objects.return_value = {
            "Deleted": [],
            "Errors": [
                {"Key": "a.png", "Code": "AccessDenied", "Message": "No access"},
                {"Key": "b.png", "Code": "AccessDenied", "Message": "No access"},
            ],
        }
        errors = []
        stats = {"deleted": 0, "errors": 0}
        objects = [{"Key": "a.png"}, {"Key": "b.png"}]

        _batch_delete_with_errors(mock_s3, "bucket", objects, errors, stats)

        assert len(errors) == 2
        assert stats["deleted"] == 0
        assert stats["errors"] == 2

    def test_partial_failure(self):
        """Should correctly handle partial failures."""
        mock_s3 = MagicMock()
        # 2 succeed (a.png and c.png), 1 fails (b.png)
        mock_s3.delete_objects.return_value = {
            "Deleted": [{"Key": "a.png"}, {"Key": "c.png"}],
            "Errors": [
                {"Key": "b.png", "Code": "InternalError", "Message": "Server error"}
            ],
        }
        errors = []
        stats = {"deleted": 0, "errors": 0}
        objects = [{"Key": "a.png"}, {"Key": "b.png"}, {"Key": "c.png"}]

        _batch_delete_with_errors(mock_s3, "bucket", objects, errors, stats)

        assert len(errors) == 1
        assert errors[0]["key"] == "b.png"
        assert "InternalError" in errors[0]["error"]
        assert stats["deleted"] == 2
        assert stats["errors"] == 1

    def test_error_includes_timestamp(self):
        """Error entries should include timestamp."""
        mock_s3 = MagicMock()
        mock_s3.delete_objects.return_value = {
            "Deleted": [],
            "Errors": [{"Key": "a.png", "Code": "Error", "Message": "msg"}],
        }
        errors = []
        stats = {"deleted": 0, "errors": 0}

        _batch_delete_with_errors(mock_s3, "bucket", [{"Key": "a.png"}], errors, stats)

        assert "timestamp" in errors[0]
        # Should be ISO format
        assert "T" in errors[0]["timestamp"]
