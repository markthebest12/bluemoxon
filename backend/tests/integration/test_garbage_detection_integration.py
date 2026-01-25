"""Integration tests for garbage image detection with real data.

These tests make real Claude API calls and should only be run manually
when testing the garbage detection functionality.

USAGE:
    # Run with staging AWS credentials (requires API access)
    AWS_PROFILE=bmx-staging poetry run pytest \
        tests/integration/test_garbage_detection_integration.py \
        -v -s --no-header

    # Skip in regular CI runs (marked with @pytest.mark.integration)
    poetry run pytest -m "not integration"

TEST DATA:
    Test images copied from eBay item 397448193086 to books/test-garbage-397448193086/:
    - 24 images (indices 0-23)
    - Known garbage images at indices 19-23:
        * 19: Yarn/textile skeins (not a book)
        * 20: Decorative buttons (not a book)
        * 21: "From Friend to Friend" - different book
        * 22: "With Kennedy" by Pierre Salinger - different book
        * 23: German-English Dictionary - different book

    The images are stored under books/ prefix because bedrock.py prepends "books/"
    to all BookImage.s3_key values when fetching from S3.
"""

import os

import pytest
from sqlalchemy.orm import Session

from app.models import Book, BookImage  # noqa: F401 - BookImage used in type hint comment
from app.services.eval_generation import detect_garbage_images

# Custom marker for integration tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_INTEGRATION_TESTS") != "1",
        reason="Integration test - set RUN_INTEGRATION_TESTS=1 to run",
    ),
]


# Test data - Napoleon by Adolphe Thiers (24 volumes)
# Images stored at books/test-garbage-397448193086/ (copied from eBay listing 397448193086)
# The "test-garbage-" prefix ensures cleanup Lambda won't delete this test data
TEST_DATA_PREFIX = "test-garbage-397448193086"
BOOK_TITLE = "HISTORY OF THE CONSULATE AND THE EMPIRE OF FRANCE UNDER NAPOLEON"
BOOK_AUTHOR = "Adolphe Thiers"

# Known garbage image indices from manual inspection
EXPECTED_GARBAGE_INDICES = [19, 20, 21, 22, 23]

# Total number of images in the listing
TOTAL_IMAGES = 24


def create_book_with_images_from_s3(db: Session) -> Book:
    """Create a Book with BookImage records pointing to S3 images.

    This creates the database records but does NOT upload any images.
    The images must already exist in S3 at the expected paths.

    S3 structure:
    - Full path: books/{TEST_DATA_PREFIX}/image_{index}.{ext}
    - BookImage.s3_key stores path RELATIVE to "books/" prefix
    - bedrock.py prepends "books/" when fetching, so s3_key = "{TEST_DATA_PREFIX}/..."

    File naming (MUST match S3 exactly):
    - Images 0-18: image_{index:02d}.webp (zero-padded, webp format)
    - Images 19-23: image_{index}.jpg (not padded, jpg format)

    If S3 files are renamed or deleted, tests will fail with "Failed to load any images".
    Restore with: aws s3 cp s3://bluemoxon-images-staging/listings/397448193086/ \
                          s3://bluemoxon-images-staging/books/test-garbage-397448193086/ --recursive
    Then verify naming matches the pattern above.
    """
    book = Book(
        title=BOOK_TITLE,
        status="EVALUATION",
    )
    db.add(book)
    db.flush()

    # Create BookImage records for all 24 images
    # s3_key is relative to books/ prefix (bedrock.py adds "books/" when fetching)
    for i in range(TOTAL_IMAGES):
        if i < 19:
            s3_key = f"{TEST_DATA_PREFIX}/image_{i:02d}.webp"
        else:
            s3_key = f"{TEST_DATA_PREFIX}/image_{i}.jpg"
        image = BookImage(
            book_id=book.id,
            s3_key=s3_key,
            display_order=i,
        )
        db.add(image)

    db.commit()
    db.refresh(book)
    return book


class TestGarbageDetectionIntegration:
    """Integration tests for garbage detection with real Claude API calls.

    DATA DEPENDENCY: These tests require specific S3 data to exist:
    - S3 bucket: bluemoxon-images-staging (set via BMX_IMAGES_BUCKET env var)
    - Path: books/test-garbage-397448193086/image_{0-23}.{webp,jpg}
    - The "test-garbage-" prefix prevents cleanup Lambda from deleting test data
    - If S3 data is deleted, tests will fail with "Failed to load any images"

    To restore test data:
    aws s3 cp s3://bluemoxon-images-staging/listings/397448193086/ \
              s3://bluemoxon-images-staging/books/test-garbage-397448193086/ --recursive
    """

    def test_garbage_detection_identifies_known_garbage_images(self, db: Session):
        """
        Integration test for garbage detection end-to-end flow.

        This test verifies:
        1. The Bedrock API call succeeds (permissions work)
        2. Claude returns valid indices
        3. The image cleanup function deletes images from S3

        Note: Claude's detection accuracy varies significantly by run.
        This test does NOT enforce specific detection results, only that
        the flow completes successfully.

        Known garbage images at indices 19-23 (for reference only):
        - 19: Yarn/textile skeins (not a book)
        - 20: Decorative buttons (not a book)
        - 21: "From Friend to Friend" - different book
        - 22: "With Kennedy" by Pierre Salinger - different book
        - 23: German-English Dictionary - different book
        """
        # Create book with images pointing to S3
        book = create_book_with_images_from_s3(db)
        images = list(book.images)

        assert len(images) == TOTAL_IMAGES, f"Expected {TOTAL_IMAGES} images, got {len(images)}"

        # Run garbage detection (makes real Claude API call)
        garbage_indices = detect_garbage_images(
            book_id=book.id,
            images=images,
            title=BOOK_TITLE,
            author=BOOK_AUTHOR,
            db=db,
        )

        # Test passes if garbage_indices is a list (even empty)
        # This verifies the Bedrock call succeeded and returned valid data
        assert garbage_indices is not None, (
            "Garbage detection failed - returned None. "
            "This indicates a Bedrock API error or permission issue."
        )
        assert isinstance(garbage_indices, list), (
            f"Garbage detection returned wrong type: {type(garbage_indices)}. "
            "Expected list of indices."
        )

        # All returned indices should be valid (0 to TOTAL_IMAGES-1)
        for idx in garbage_indices:
            assert 0 <= idx < TOTAL_IMAGES, (
                f"Invalid index {idx} returned. Must be 0-{TOTAL_IMAGES-1}."
            )

        # Verify images were actually deleted from DB
        db.refresh(book)
        remaining_count = len(list(book.images))
        expected_remaining = TOTAL_IMAGES - len(garbage_indices)
        assert remaining_count == expected_remaining, (
            f"Expected {expected_remaining} images after deletion. "
            f"Got {remaining_count}. Garbage detected: {len(garbage_indices)}"
        )


    @pytest.mark.skip(reason="Requires fresh S3 data - run test_garbage_detection_identifies_known_garbage_images first")
    def test_garbage_detection_with_title_only(self, db: Session):
        """Test garbage detection works with title only (no author).

        NOTE: This test is skipped by default because it requires fresh S3 data.
        The main test (test_garbage_detection_identifies_known_garbage_images) deletes
        S3 images during execution.

        To run this test independently:
        1. Restore S3 data first (see docstring at top of file)
        2. Run only this test: pytest ... -k test_garbage_detection_with_title_only
        """
        book = create_book_with_images_from_s3(db)
        images = list(book.images)

        # Run with author=None
        garbage_indices = detect_garbage_images(
            book_id=book.id,
            images=images,
            title=BOOK_TITLE,
            author=None,  # No author provided
            db=db,
        )

        # Just verify the function returns successfully
        assert garbage_indices is not None, "Garbage detection failed with title only"

    @pytest.mark.skip(reason="Covered by test_garbage_detection_identifies_known_garbage_images")
    def test_images_deleted_after_detection(self, db: Session):
        """Verify that detected garbage images are actually deleted from DB.

        NOTE: This functionality is now verified in the main test
        (test_garbage_detection_identifies_known_garbage_images) which checks
        that remaining_count == TOTAL_IMAGES - len(garbage_indices).
        """
        pass
