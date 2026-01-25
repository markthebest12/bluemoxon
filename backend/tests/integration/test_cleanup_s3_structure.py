"""Integration tests for S3 bucket structure validation.

These tests connect to the real S3 bucket to validate that all objects
under the books/ prefix can be parsed by the cleanup Lambda.

USAGE:
    # Run against staging (default)
    AWS_PROFILE=bmx-staging RUN_INTEGRATION_TESTS=1 poetry run pytest \
        tests/integration/test_cleanup_s3_structure.py \
        -v -s --no-header

    # Run against production (requires prod credentials)
    AWS_PROFILE=bmx-prod RUN_INTEGRATION_TESTS=1 TEST_S3_BUCKET=bluemoxon-images \
        poetry run pytest tests/integration/test_cleanup_s3_structure.py -v -s

    # Skip in regular CI runs (marked with @pytest.mark.integration)
    poetry run pytest -m "not integration"

KEY PARSING LOGIC:
    This test validates that keys match what the cleanup Lambda can parse.
    The Lambda extracts book_id using this logic (from handler.py lines 192-216):

    1. Split key by '/' and get parts[1]
    2. Strip 'thumb_' prefix if present
    3. Try to parse as int (nested: books/{book_id}/...)
    4. If that fails, split by '_' and parse first part as int (flat: books/{id}_...)

    Keys that don't match this logic are SILENTLY SKIPPED by the Lambda,
    meaning they won't be grouped or deleted - potential orphan accumulation.
"""

import os

import boto3
import pytest

# Custom marker for integration tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_INTEGRATION_TESTS") != "1",
        reason="Integration test - set RUN_INTEGRATION_TESTS=1 to run",
    ),
]

# S3 bucket - configurable for staging vs production testing
# Default: staging. Set TEST_S3_BUCKET=bluemoxon-images for production.
S3_BUCKET = os.environ.get("TEST_S3_BUCKET", "bluemoxon-images-staging")
BOOKS_PREFIX = "books/"


def can_cleanup_lambda_parse_key(key: str) -> tuple[bool, int | None, str]:
    """Check if cleanup Lambda can parse a key and extract book_id.

    This replicates the EXACT parsing logic from cleanup Lambda handler.py
    lines 192-216. If this logic changes in the Lambda, it must change here too.

    Args:
        key: Full S3 key (e.g., "books/515/image.webp")

    Returns:
        Tuple of (can_parse, book_id_or_none, format_description)
    """
    parts = key.split("/")
    if len(parts) < 2:
        return False, None, "too few path segments"

    folder_part = parts[1]

    # Strip thumb_ prefix if present (nested thumbnail directories)
    if folder_part.startswith("thumb_"):
        folder_part = folder_part[6:]
        format_type = "thumbnail"
    else:
        format_type = "nested"

    # Try nested format first (folder_part is just the book_id)
    try:
        book_id = int(folder_part)
        return True, book_id, format_type

    except ValueError:
        pass

    # Try flat format: extract book_id before underscore
    try:
        book_id = int(folder_part.split("_")[0])
        return True, book_id, "flat"

    except (ValueError, IndexError):
        pass

    return False, None, f"cannot extract book_id from '{folder_part}'"


class TestS3BucketStructure:
    """Integration tests for S3 bucket structure validation.

    DATA DEPENDENCY: These tests require access to S3 bucket.
    - Staging: AWS_PROFILE=bmx-staging (default)
    - Production: AWS_PROFILE=bmx-prod TEST_S3_BUCKET=bluemoxon-images
    """

    @pytest.fixture
    def s3_client(self):
        """Create an S3 client using the current AWS profile."""
        return boto3.client("s3")

    def test_all_book_keys_parseable_by_cleanup_lambda(self, s3_client):
        """
        Validate all S3 keys under books/ can be parsed by cleanup Lambda.

        Uses pagination to handle buckets of any size. Reports unparseable
        keys that would be silently skipped by the Lambda (orphan accumulation risk).
        """
        paginator = s3_client.get_paginator("list_objects_v2")

        unparseable_keys: list[tuple[str, str]] = []  # (key, reason)
        format_counts = {"nested": 0, "thumbnail": 0, "flat": 0}
        total_count = 0

        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=BOOKS_PREFIX):
            for obj in page.get("Contents", []):
                key = obj["Key"]

                # Skip directory markers
                if key.endswith("/"):
                    continue

                total_count += 1
                can_parse, book_id, format_or_reason = can_cleanup_lambda_parse_key(key)

                if can_parse:
                    format_counts[format_or_reason] += 1
                else:
                    unparseable_keys.append((key, format_or_reason))

        # Handle empty bucket
        if total_count == 0:
            pytest.skip(f"No objects found under {BOOKS_PREFIX} in {S3_BUCKET}")

        # Build summary
        summary = (
            f"\n\nS3 Structure Validation Results:\n"
            f"  Bucket: {S3_BUCKET}\n"
            f"  Prefix: {BOOKS_PREFIX}\n"
            f"  Total objects: {total_count}\n"
            f"  Format breakdown:\n"
            f"    - Nested (books/{{id}}/{{file}}): {format_counts['nested']}\n"
            f"    - Thumbnail (books/thumb_{{id}}/{{file}}): {format_counts['thumbnail']}\n"
            f"    - Flat (books/{{id}}_{{uuid}}.ext): {format_counts['flat']}\n"
            f"  Unparseable: {len(unparseable_keys)}"
        )

        # Fail with details if unparseable keys found
        if unparseable_keys:
            error_msg = (
                f"\n\nFound {len(unparseable_keys)} keys the cleanup Lambda cannot parse:\n\n"
            )
            for key, reason in unparseable_keys[:50]:
                error_msg += f"  - {key}\n    Reason: {reason}\n"
            if len(unparseable_keys) > 50:
                error_msg += f"  ... and {len(unparseable_keys) - 50} more\n"

            error_msg += "\nThese keys will be SILENTLY SKIPPED by cleanup Lambda.\n"
            error_msg += "Risk: Orphaned images accumulate without detection.\n"
            error_msg += summary

            pytest.fail(error_msg)

        # Success
        assert len(unparseable_keys) == 0, f"All keys should be parseable{summary}"

    def test_can_connect_to_s3_bucket(self, s3_client):
        """Verify AWS credentials work for the configured bucket."""
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=BOOKS_PREFIX,
            MaxKeys=1,
        )
        assert "Name" in response
        assert response["Name"] == S3_BUCKET

    def test_parsing_logic_matches_cleanup_lambda(self):
        """Unit tests verifying parsing logic matches cleanup Lambda exactly.

        These test cases are derived from handler.py lines 192-216.
        If the Lambda changes, these tests should fail.
        """
        # Nested format: books/{book_id}/{filename}
        assert can_cleanup_lambda_parse_key("books/515/image_00.webp") == (
            True,
            515,
            "nested",
        )
        assert can_cleanup_lambda_parse_key("books/1/photo.jpg") == (True, 1, "nested")
        assert can_cleanup_lambda_parse_key("books/999999/file.png") == (
            True,
            999999,
            "nested",
        )

        # Thumbnail format: books/thumb_{book_id}/{filename}
        assert can_cleanup_lambda_parse_key("books/thumb_515/image_00.webp") == (
            True,
            515,
            "thumbnail",
        )
        assert can_cleanup_lambda_parse_key("books/thumb_1/photo.jpg") == (
            True,
            1,
            "thumbnail",
        )

        # Flat format: books/{book_id}_{anything}.{ext}
        # Note: Lambda doesn't validate UUID format, just extracts number before _
        assert can_cleanup_lambda_parse_key("books/10_abc-def.jpg") == (
            True,
            10,
            "flat",
        )
        assert can_cleanup_lambda_parse_key("books/515_UPPERCASE.webp") == (
            True,
            515,
            "flat",
        )
        assert can_cleanup_lambda_parse_key("books/1_anything-goes-here.png") == (
            True,
            1,
            "flat",
        )

        # Invalid patterns that Lambda CANNOT parse
        result = can_cleanup_lambda_parse_key("books/")
        assert result[0] is False

        result = can_cleanup_lambda_parse_key("books/abc/image.jpg")
        assert result[0] is False  # Non-numeric book_id

        result = can_cleanup_lambda_parse_key("books/abc_def.jpg")
        assert result[0] is False  # Flat but non-numeric prefix

        # Note: "listings/123/image.jpg" would PARSE successfully (parts[1]="123")
        # but the integration test only lists books/ prefix, so this is filtered
        # at the S3 level, not the parsing level.
        result = can_cleanup_lambda_parse_key("listings/123/image.jpg")
        assert result[0] is True  # Parses fine, prefix filtering is caller's job
        assert result[1] == 123

        result = can_cleanup_lambda_parse_key("image.jpg")
        assert result[0] is False  # No path segments
