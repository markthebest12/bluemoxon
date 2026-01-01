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
    eBay item 397448193086 was re-extracted to S3 at listings/397448193086/:
    - 24 images extracted (indices 0-23)
    - Known garbage images at indices 19-23:
        * 19: Yarn/textile skeins (not a book)
        * 20: Decorative buttons (not a book)
        * 21: "From Friend to Friend" - different book
        * 22: "With Kennedy" by Pierre Salinger - different book
        * 23: German-English Dictionary - different book
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


# Book 539 listing data - Napoleon by Adolphe Thiers (24 volumes)
LISTING_ID = "397448193086"
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

    S3 path pattern: listings/{listing_id}/image_{index}.jpg
    """
    book = Book(
        title=BOOK_TITLE,
        status="EVALUATION",
    )
    db.add(book)
    db.flush()

    # Create BookImage records for all 24 images
    for i in range(TOTAL_IMAGES):
        s3_key = f"listings/{LISTING_ID}/image_{i}.jpg"
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
    - S3 bucket: bluemoxon-images (staging)
    - Path: listings/397448193086/image_{0-23}.jpg
    - If S3 data is cleaned up, tests will fail with "Failed to load any images"

    To restore test data, re-run eBay extraction for item 397448193086.
    """

    def test_garbage_detection_identifies_known_garbage_images(self, db: Session):
        """
        Integration test with real listing data.

        Book 539 (eBay 397448193086) has known garbage images at indices 19-23:
        - 19: Yarn/textile skeins (not a book)
        - 20: Decorative buttons (not a book)
        - 21: "From Friend to Friend" - different book
        - 22: "With Kennedy" by Pierre Salinger - different book
        - 23: German-English Dictionary - different book

        This test verifies that the garbage detection correctly identifies
        these images as unrelated to the Napoleon history book.
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

        # Verify expected garbage indices are detected
        for expected_idx in EXPECTED_GARBAGE_INDICES:
            assert expected_idx in garbage_indices, (
                f"Expected index {expected_idx} to be detected as garbage. Got: {garbage_indices}"
            )

        # Verify we didn't flag too many images (some tolerance for Claude variability)
        # We expect 5 garbage images, allow up to 7 (Claude might catch other ads)
        assert len(garbage_indices) <= 7, (
            f"Too many images flagged as garbage: {garbage_indices}. "
            f"Expected around {len(EXPECTED_GARBAGE_INDICES)}."
        )

        # Verify book content images (0-18) are NOT flagged
        book_content_indices = set(range(19))
        flagged_content = book_content_indices.intersection(set(garbage_indices))
        assert len(flagged_content) == 0, (
            f"Book content images incorrectly flagged as garbage: {flagged_content}. "
            f"These should be images of the Napoleon book."
        )

    def test_garbage_detection_with_title_only(self, db: Session):
        """Test garbage detection works with title only (no author)."""
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

        # Should still detect the obvious garbage (buttons, yarn, different books)
        # May be slightly less accurate without author, but should catch most
        assert len(garbage_indices) >= 3, (
            f"Expected at least 3 garbage images detected without author. Got: {garbage_indices}"
        )

    def test_images_deleted_after_detection(self, db: Session):
        """Verify that detected garbage images are actually deleted from DB."""
        book = create_book_with_images_from_s3(db)
        initial_count = len(list(book.images))
        assert initial_count == TOTAL_IMAGES

        # Run garbage detection
        garbage_indices = detect_garbage_images(
            book_id=book.id,
            images=list(book.images),
            title=BOOK_TITLE,
            author=BOOK_AUTHOR,
            db=db,
        )

        # Refresh book to get updated images
        db.refresh(book)
        final_count = len(list(book.images))

        # Verify images were deleted
        assert final_count == initial_count - len(garbage_indices), (
            f"Expected {initial_count - len(garbage_indices)} images after deletion. "
            f"Got {final_count}. Garbage detected: {garbage_indices}"
        )

        # Verify remaining images have correct display orders (no gaps in 0-18 range)
        remaining_orders = sorted([img.display_order for img in book.images])
        expected_orders = [i for i in range(TOTAL_IMAGES) if i not in garbage_indices]
        assert remaining_orders == expected_orders, (
            f"Remaining display orders don't match expected. "
            f"Got: {remaining_orders}, Expected: {expected_orders}"
        )
