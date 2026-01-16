"""Integration tests for S3 bucket structure validation.

These tests connect to the real staging S3 bucket to validate that all objects
under the books/ prefix follow the expected naming conventions.

USAGE:
    # Run with staging AWS credentials
    AWS_PROFILE=bmx-staging RUN_INTEGRATION_TESTS=1 poetry run pytest \
        tests/integration/test_cleanup_s3_structure.py \
        -v -s --no-header

    # Skip in regular CI runs (marked with @pytest.mark.integration)
    poetry run pytest -m "not integration"

VALID KEY PATTERNS:
    1. Nested structure: books/{book_id}/{filename}.{ext}
       Example: books/515/image_00.webp

    2. Nested thumbnail: books/thumb_{book_id}/{filename}.{ext}
       Example: books/thumb_515/image_00.webp

    3. Flat upload (legacy): books/{book_id}_{uuid}.{ext}
       Example: books/10_abc123-def456.jpg

PURPOSE:
    This test validates the S3 bucket structure to ensure:
    - No orphaned or malformed keys exist
    - All keys can be parsed by the cleanup Lambda
    - No unexpected naming patterns have been introduced
"""

import os
import re

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

# S3 bucket configuration
STAGING_BUCKET = "bluemoxon-staging-images"
BOOKS_PREFIX = "books/"
MAX_OBJECTS = 1000

# Valid S3 key patterns for book images
VALID_PATTERNS = [
    # Nested structure: books/{book_id}/{filename}.{ext}
    # Example: books/515/image_00.webp, books/123/photo.jpg
    re.compile(r"^books/\d+/.+\.\w+$"),
    # Nested thumbnail: books/thumb_{book_id}/{filename}.{ext}
    # Example: books/thumb_515/image_00.webp
    re.compile(r"^books/thumb_\d+/.+\.\w+$"),
    # Flat upload (legacy): books/{book_id}_{uuid}.{ext}
    # Example: books/10_abc123-def456-789.jpg
    re.compile(r"^books/\d+_[a-f0-9-]+\.\w+$"),
]


def matches_any_pattern(key: str) -> bool:
    """Check if a key matches any of the valid patterns."""
    return any(pattern.match(key) for pattern in VALID_PATTERNS)


def get_pattern_description(key: str) -> str:
    """Return which pattern a key matches, or 'NONE' if invalid."""
    pattern_names = [
        "nested (books/{id}/{file})",
        "thumbnail (books/thumb_{id}/{file})",
        "flat (books/{id}_{uuid}.ext)",
    ]
    for pattern, name in zip(VALID_PATTERNS, pattern_names, strict=True):
        if pattern.match(key):
            return name
    return "NONE - INVALID"


class TestS3BucketStructure:
    """Integration tests for S3 bucket structure validation.

    DATA DEPENDENCY: These tests require access to the staging S3 bucket.
    Requires AWS credentials with read access to bluemoxon-staging-images.
    """

    @pytest.fixture
    def s3_client(self):
        """Create an S3 client using the current AWS profile."""
        return boto3.client("s3")

    def test_all_book_keys_match_valid_patterns(self, s3_client):
        """
        Validate that all S3 keys under books/ prefix match expected patterns.

        This test:
        1. Lists all objects under the books/ prefix (up to MAX_OBJECTS)
        2. Validates each key matches one of the valid patterns
        3. Fails with a detailed report if any invalid keys are found

        Valid patterns:
        - Nested: books/{book_id}/{filename}.{ext}
        - Thumbnail: books/thumb_{book_id}/{filename}.{ext}
        - Flat: books/{book_id}_{uuid}.{ext}
        """
        # List objects under books/ prefix
        response = s3_client.list_objects_v2(
            Bucket=STAGING_BUCKET,
            Prefix=BOOKS_PREFIX,
            MaxKeys=MAX_OBJECTS,
        )

        # Handle empty bucket case
        if "Contents" not in response:
            pytest.skip("No objects found under books/ prefix - bucket may be empty")

        objects = response["Contents"]
        total_count = len(objects)

        # Check if truncated (more than MAX_OBJECTS)
        if response.get("IsTruncated"):
            pytest.fail(
                f"Bucket has more than {MAX_OBJECTS} objects under books/. "
                f"Increase MAX_OBJECTS or paginate to check all keys."
            )

        # Validate each key
        invalid_keys = []
        pattern_counts = {
            "nested": 0,
            "thumbnail": 0,
            "flat": 0,
        }

        for obj in objects:
            key = obj["Key"]

            # Skip directory markers (keys ending with /)
            if key.endswith("/"):
                continue

            if not matches_any_pattern(key):
                invalid_keys.append(key)
            else:
                # Count by pattern type for reporting
                if VALID_PATTERNS[0].match(key):
                    pattern_counts["nested"] += 1
                elif VALID_PATTERNS[1].match(key):
                    pattern_counts["thumbnail"] += 1
                elif VALID_PATTERNS[2].match(key):
                    pattern_counts["flat"] += 1

        # Build summary for assertion message
        summary = (
            f"\n\nS3 Structure Validation Results:\n"
            f"  Bucket: {STAGING_BUCKET}\n"
            f"  Prefix: {BOOKS_PREFIX}\n"
            f"  Total objects: {total_count}\n"
            f"  Pattern breakdown:\n"
            f"    - Nested (books/{{id}}/{{file}}): {pattern_counts['nested']}\n"
            f"    - Thumbnail (books/thumb_{{id}}/{{file}}): {pattern_counts['thumbnail']}\n"
            f"    - Flat (books/{{id}}_{{uuid}}.ext): {pattern_counts['flat']}\n"
            f"  Invalid keys: {len(invalid_keys)}"
        )

        # Fail with details if invalid keys found
        if invalid_keys:
            error_msg = (
                f"\n\nFound {len(invalid_keys)} invalid S3 keys that don't match any pattern:\n\n"
            )
            for key in invalid_keys[:50]:  # Limit to first 50 for readability
                error_msg += f"  - {key}\n"
            if len(invalid_keys) > 50:
                error_msg += f"  ... and {len(invalid_keys) - 50} more\n"

            error_msg += "\nExpected patterns:\n"
            error_msg += "  1. books/{book_id}/{filename}.{ext} (nested)\n"
            error_msg += "  2. books/thumb_{book_id}/{filename}.{ext} (thumbnail)\n"
            error_msg += "  3. books/{book_id}_{uuid}.{ext} (flat upload)\n"
            error_msg += summary

            pytest.fail(error_msg)

        # Success - all keys valid (summary included for -v output)
        assert len(invalid_keys) == 0, f"All keys should match valid patterns{summary}"

    def test_can_connect_to_s3_bucket(self, s3_client):
        """
        Verify we can connect to the staging S3 bucket.

        This is a sanity check to ensure AWS credentials are configured
        correctly before running the more detailed structure test.
        """
        # Just check we can list (even if empty)
        response = s3_client.list_objects_v2(
            Bucket=STAGING_BUCKET,
            Prefix=BOOKS_PREFIX,
            MaxKeys=1,
        )

        # If we get here without exception, connection works
        assert "Name" in response
        assert response["Name"] == STAGING_BUCKET

    def test_pattern_matching_unit_tests(self):
        """
        Unit tests for the pattern matching logic (no S3 connection needed).

        These verify the regex patterns work correctly before running
        the integration test.
        """
        # Valid nested structure
        assert matches_any_pattern("books/515/image_00.webp")
        assert matches_any_pattern("books/1/photo.jpg")
        assert matches_any_pattern("books/999999/file.png")
        assert matches_any_pattern("books/123/some-file-name.jpeg")

        # Valid thumbnail structure
        assert matches_any_pattern("books/thumb_515/image_00.webp")
        assert matches_any_pattern("books/thumb_1/photo.jpg")
        assert matches_any_pattern("books/thumb_999/thumb.png")

        # Valid flat structure (UUID format)
        assert matches_any_pattern("books/10_abc-def.jpg")
        assert matches_any_pattern("books/515_a1b2c3d4-e5f6-7890-abcd-ef1234567890.webp")
        assert matches_any_pattern("books/1_abcdef.png")

        # Invalid patterns that should NOT match
        assert not matches_any_pattern("books/")  # Just prefix
        assert not matches_any_pattern("books/image.jpg")  # No book ID
        assert not matches_any_pattern("listings/123/image.jpg")  # Wrong prefix
        assert not matches_any_pattern("books/abc/image.jpg")  # Non-numeric ID
        assert not matches_any_pattern("books/123_ABC.jpg")  # Uppercase in UUID
        assert not matches_any_pattern("books/123")  # No extension
        assert not matches_any_pattern("images/123/file.jpg")  # Wrong prefix
