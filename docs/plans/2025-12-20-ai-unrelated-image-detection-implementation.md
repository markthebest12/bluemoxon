# AI-Powered Unrelated Image Detection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend Claude Vision analysis to identify and remove seller ads, logos, and unrelated book images from eBay imports.

**Architecture:** Add image relevance detection to existing `_analyze_images_with_claude()` prompt, parse response, delete unrelated images from S3 and database.

**Tech Stack:** Python, Claude Sonnet (Bedrock), S3 boto3

**Design Doc:** `docs/plans/2025-12-20-ai-unrelated-image-detection-design.md`

---

## Task 1: Extend Claude Vision Prompt

**Files:**

- Modify: `backend/app/services/eval_generation.py:246-287`

**Step 1: Add image relevance instructions to the prompt**

Find the current prompt (lines 246-287) and add the following section after "Notable features" and before "Provide your analysis as JSON":

```python
    # Build the analysis prompt
    prompt = f"""Analyze these images of an antiquarian book listing for acquisition evaluation.

BOOK: {book_title}

{f"SELLER DESCRIPTION: {listing_description}" if listing_description else ""}

Examine all images carefully and provide a detailed condition assessment. Look for:
- Binding condition (tight, loose, cracked, rebacked)
- Cover wear (rubbing, fading, stains, scratches)
- Spine condition (text legibility, sunning, cracking)
- Page condition (foxing, toning, tears, stains)
- Hinges (tight, starting, cracked)
- Any repairs or restoration
- Completeness (plates, maps, bookplates)
- Notable features (gilt edges, marbled endpapers, raised bands)

IMAGE RELEVANCE: For each image, determine if it shows the actual book being sold.
Mark as UNRELATED any images that are:
- Seller store logos or banners
- "Visit My Store" promotional images
- Completely different books (different titles, authors, or editions)
- Generic stock photos not of this specific item
- Seller contact/shipping information graphics

Return the 0-based index of each unrelated image in the unrelated_images array.
If ALL images show the book being sold, return an empty array.

Provide your analysis as JSON:
{{
    "condition_grade": "Fine|Very Good|Good|Fair|Poor",
    "condition_positives": [
        "Specific positive observation 1",
        "Specific positive observation 2"
    ],
    "condition_negatives": [
        "Specific negative observation 1",
        "Specific negative observation 2"
    ],
    "critical_issues": [
        "Issues that significantly impact value (empty if none)"
    ],
    "item_identification": {{
        "binding_type": "Full leather/Half leather/Cloth/etc",
        "binding_color": "Description of binding color",
        "decorative_elements": "Gilt, tooling, raised bands, etc",
        "estimated_age": "Victorian/Edwardian/Modern/etc",
        "binder_signature": "Name if visible, or null",
        "illustrations": "Description if present"
    }},
    "binding_analysis": "Detailed paragraph about the binding quality and attribution",
    "unrelated_images": [17, 18, 19],
    "unrelated_reasons": {{
        "17": "Brief reason why image 17 is unrelated",
        "18": "Brief reason why image 18 is unrelated"
    }}
}}

Return ONLY valid JSON, no other text."""
```

**Step 2: Commit**

```bash
git add backend/app/services/eval_generation.py
git commit -m "feat: add image relevance detection to Claude Vision prompt"
```

---

## Task 2: Update Return Type and Default Values

**Files:**

- Modify: `backend/app/services/eval_generation.py:220-243` (default return dict)
- Modify: `backend/app/services/eval_generation.py:324-331` (fallback return)
- Modify: `backend/app/services/eval_generation.py:335-342` (error return)
- Modify: `backend/app/services/eval_generation.py:345-352` (exception return)

**Step 1: Add unrelated_images to all return dicts**

Update the empty/error return dicts to include the new fields:

```python
        return {
            "condition_grade": None,
            "condition_positives": [],
            "condition_negatives": [],
            "critical_issues": [],
            "item_identification": {},
            "binding_analysis": None,
            "unrelated_images": [],
            "unrelated_reasons": {},
        }
```

Apply this to all 4 return locations (lines ~222-229, ~324-331, ~335-342, ~345-352).

**Step 2: Commit**

```bash
git add backend/app/services/eval_generation.py
git commit -m "feat: add unrelated_images field to analysis return type"
```

---

## Task 3: Add Image Deletion Function

**Files:**

- Create: `backend/app/services/image_cleanup.py`

**Step 1: Create the image cleanup service**

```python
"""Image cleanup service for removing unrelated images."""

import logging

import boto3
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session

from app.models import BookImage
from app.core.config import settings

logger = logging.getLogger(__name__)


def delete_unrelated_images(
    book_id: int,
    unrelated_indices: list[int],
    unrelated_reasons: dict[str, str],
    db: Session,
) -> dict:
    """Delete images identified as unrelated to the book.

    Args:
        book_id: ID of the book
        unrelated_indices: List of 0-based image indices to delete
        unrelated_reasons: Dict mapping index to reason for deletion
        db: Database session

    Returns:
        Dict with deletion results:
            - deleted_count: Number of images deleted
            - deleted_keys: List of S3 keys deleted
            - errors: List of any errors encountered
    """
    if not unrelated_indices:
        return {"deleted_count": 0, "deleted_keys": [], "errors": []}

    logger.info(
        f"Deleting {len(unrelated_indices)} unrelated images from book {book_id}: "
        f"indices {unrelated_indices}"
    )

    # Get images for this book, ordered by position
    images = (
        db.query(BookImage)
        .filter(BookImage.book_id == book_id)
        .order_by(BookImage.position)
        .all()
    )

    if not images:
        logger.warning(f"No images found for book {book_id}")
        return {"deleted_count": 0, "deleted_keys": [], "errors": ["No images found"]}

    deleted_keys = []
    errors = []

    # Initialize S3 client
    s3 = boto3.client("s3")
    bucket = settings.IMAGES_BUCKET_NAME

    for idx in unrelated_indices:
        if idx < 0 or idx >= len(images):
            logger.warning(f"Invalid image index {idx} for book {book_id} (has {len(images)} images)")
            errors.append(f"Invalid index {idx}")
            continue

        image = images[idx]
        reason = unrelated_reasons.get(str(idx), "AI identified as unrelated")

        logger.info(
            f"Deleting image {image.id} (index {idx}) from book {book_id}: {reason}"
        )

        # Delete from S3
        if image.s3_key:
            try:
                s3.delete_object(Bucket=bucket, Key=image.s3_key)
                deleted_keys.append(image.s3_key)
                logger.info(f"Deleted S3 object: {image.s3_key}")
            except ClientError as e:
                error_msg = f"Failed to delete S3 object {image.s3_key}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue  # Don't delete DB record if S3 delete failed

        # Delete from database
        db.delete(image)

    # Commit deletions
    db.commit()

    # Reorder remaining images
    remaining_images = (
        db.query(BookImage)
        .filter(BookImage.book_id == book_id)
        .order_by(BookImage.position)
        .all()
    )
    for new_pos, img in enumerate(remaining_images):
        if img.position != new_pos:
            img.position = new_pos
    db.commit()

    logger.info(
        f"Deleted {len(deleted_keys)} unrelated images from book {book_id}, "
        f"{len(errors)} errors"
    )

    return {
        "deleted_count": len(deleted_keys),
        "deleted_keys": deleted_keys,
        "errors": errors,
    }
```

**Step 2: Commit**

```bash
git add backend/app/services/image_cleanup.py
git commit -m "feat: add image cleanup service for unrelated image deletion"
```

---

## Task 4: Integrate Cleanup into Eval Runbook Generation

**Files:**

- Modify: `backend/app/services/eval_generation.py:396-400`

**Step 1: Add import at top of file**

```python
from app.services.image_cleanup import delete_unrelated_images
```

**Step 2: Call cleanup after AI analysis**

Find the section after `_analyze_images_with_claude()` call (around line 400) and add:

```python
    # Run Claude Vision analysis if enabled and images available
    if run_ai_analysis and book.images:
        logger.info(f"Running Claude Vision analysis on {len(book.images)} images")
        ai_analysis = _analyze_images_with_claude(
            images=list(book.images),
            book_title=book.title,
            listing_description=listing_data.get("description"),
        )

        # Delete any unrelated images identified by AI
        unrelated_indices = ai_analysis.get("unrelated_images", [])
        if unrelated_indices:
            cleanup_result = delete_unrelated_images(
                book_id=book.id,
                unrelated_indices=unrelated_indices,
                unrelated_reasons=ai_analysis.get("unrelated_reasons", {}),
                db=db,
            )
            logger.info(
                f"Cleaned up {cleanup_result['deleted_count']} unrelated images "
                f"from book {book.id}"
            )
```

**Step 3: Commit**

```bash
git add backend/app/services/eval_generation.py
git commit -m "feat: integrate unrelated image cleanup into eval runbook generation"
```

---

## Task 5: Add Unit Tests

**Files:**

- Create: `backend/tests/services/test_image_cleanup.py`

**Step 1: Create test file**

```python
"""Tests for image cleanup service."""

import pytest
from unittest.mock import MagicMock, patch

from app.services.image_cleanup import delete_unrelated_images


class TestDeleteUnrelatedImages:
    """Tests for delete_unrelated_images function."""

    def test_empty_indices_returns_early(self, db_session):
        """Empty unrelated_indices should return immediately."""
        result = delete_unrelated_images(
            book_id=1,
            unrelated_indices=[],
            unrelated_reasons={},
            db=db_session,
        )
        assert result["deleted_count"] == 0
        assert result["deleted_keys"] == []
        assert result["errors"] == []

    @patch("app.services.image_cleanup.boto3.client")
    def test_deletes_images_from_s3_and_db(self, mock_boto, db_session, sample_book):
        """Should delete images from both S3 and database."""
        # Create mock S3 client
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3

        # Add test images to book
        from app.models import BookImage
        for i in range(5):
            img = BookImage(
                book_id=sample_book.id,
                s3_key=f"books/{sample_book.id}/image_{i:02d}.jpg",
                position=i,
            )
            db_session.add(img)
        db_session.commit()

        # Delete images at indices 3 and 4
        result = delete_unrelated_images(
            book_id=sample_book.id,
            unrelated_indices=[3, 4],
            unrelated_reasons={"3": "Seller logo", "4": "Different book"},
            db=db_session,
        )

        assert result["deleted_count"] == 2
        assert len(result["deleted_keys"]) == 2
        assert result["errors"] == []

        # Verify S3 delete was called
        assert mock_s3.delete_object.call_count == 2

        # Verify database state
        remaining = db_session.query(BookImage).filter_by(book_id=sample_book.id).all()
        assert len(remaining) == 3

    def test_invalid_index_adds_error(self, db_session, sample_book):
        """Invalid indices should be logged as errors."""
        result = delete_unrelated_images(
            book_id=sample_book.id,
            unrelated_indices=[99],  # Invalid
            unrelated_reasons={},
            db=db_session,
        )
        assert result["deleted_count"] == 0
        assert "Invalid index 99" in result["errors"]

    def test_no_images_returns_error(self, db_session):
        """Book with no images should return error."""
        result = delete_unrelated_images(
            book_id=99999,  # Non-existent
            unrelated_indices=[0],
            unrelated_reasons={},
            db=db_session,
        )
        assert result["deleted_count"] == 0
        assert "No images found" in result["errors"]
```

**Step 2: Run tests**

```bash
cd backend
poetry run pytest tests/services/test_image_cleanup.py -v
```

**Step 3: Commit**

```bash
git add backend/tests/services/test_image_cleanup.py
git commit -m "test: add unit tests for image cleanup service"
```

---

## Task 6: Manual Validation on Staging

**Step 1: Deploy to staging**

```bash
git push origin staging
gh run list --workflow deploy-staging.yml --limit 1
gh run watch <run-id> --exit-status
```

**Step 2: Re-run eval on book 506 to test detection**

```bash
# Trigger re-evaluation via API (will run AI analysis)
bmx-api POST /books/506/evaluate

# Check CloudWatch logs for unrelated image detection
AWS_PROFILE=bmx-staging aws logs filter-log-events --log-group-name /aws/lambda/bluemoxon-staging-api --filter-pattern "unrelated" --limit 20
```

**Step 3: Verify images were deleted**

```bash
# Check book's images via API
bmx-api GET /books/506

# Images 17-23 should no longer appear
```

---

## Task 7: Create PR and Deploy to Production

**Step 1: Create PR to main**

```bash
gh pr create --base main --head staging --title "feat: AI-powered unrelated image detection (#487)" --body "$(cat <<'EOF'
## Summary
- Extends Claude Vision analysis to identify seller ads, logos, and unrelated book images
- Automatically removes detected unrelated images from book carousel
- Addresses remaining issues from #487 that aspect-ratio filtering couldn't catch

## Changes
- Extended `_analyze_images_with_claude()` prompt to detect unrelated images
- Added `image_cleanup.py` service for S3/DB image deletion
- Integrated cleanup into eval runbook generation flow

## Test Plan
- [x] Unit tests for image cleanup service
- [x] Validated on book 506 in staging (images 17-23 detected as unrelated)
- [x] CloudWatch logs show detection and deletion

Closes #487

EOF
)"
```

**Step 2: Wait for CI and merge**

```bash
gh pr checks <pr-number> --watch
gh pr merge <pr-number> --squash --delete-branch
```

**Step 3: Watch production deploy**

```bash
gh run list --workflow Deploy --limit 1
gh run watch <run-id> --exit-status
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Extend Claude Vision prompt | `eval_generation.py` |
| 2 | Update return types | `eval_generation.py` |
| 3 | Add image cleanup service | `image_cleanup.py` (new) |
| 4 | Integrate cleanup into eval | `eval_generation.py` |
| 5 | Add unit tests | `test_image_cleanup.py` (new) |
| 6 | Manual validation | Staging environment |
| 7 | PR and deploy | Git workflow |
