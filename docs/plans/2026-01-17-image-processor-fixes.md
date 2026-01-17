# Image Processor Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix two critical issues in the image processor Lambda: missing thumbnails and wrong source image selection.

**Architecture:**
- Fix 1: Add thumbnail generation after processed image upload, using same approach as API endpoint
- Fix 2: Add smart source selection logic in Lambda that queries all book images and picks best source based on image_type priority

**Tech Stack:** Python 3.12, Pillow, boto3, SQLAlchemy

---

## Task 1: Add Thumbnail Constants to Handler

**Files:**
- Modify: `backend/lambdas/image_processor/handler.py`

**Step 1: Add thumbnail constants after existing constants (around line 52)**

Add after `MAX_IMAGE_DIMENSION = 4096`:

```python
# Thumbnail settings (matches API endpoint in images.py)
THUMBNAIL_MAX_SIZE = (300, 300)
THUMBNAIL_QUALITY = 85
```

**Step 2: Commit**

```bash
git add backend/lambdas/image_processor/handler.py
git commit -m "feat: add thumbnail constants to image processor"
```

---

## Task 2: Add Thumbnail Generation Function

**Files:**
- Modify: `backend/lambdas/image_processor/handler.py`
- Test: `backend/lambdas/image_processor/tests/test_handler.py`

**Step 1: Write the failing test**

Add to `backend/lambdas/image_processor/tests/test_handler.py`:

```python
class TestThumbnailGeneration:
    """Tests for thumbnail generation."""

    def test_generate_thumbnail_creates_jpeg(self):
        """Should create a JPEG thumbnail from PNG."""
        from handler import generate_thumbnail

        # Create a test RGBA image (100x150)
        test_image = Image.new("RGBA", (100, 150), (255, 0, 0, 255))

        thumbnail = generate_thumbnail(test_image)

        assert thumbnail is not None
        assert thumbnail.mode == "RGB"  # JPEG doesn't support alpha
        assert thumbnail.size[0] <= 300
        assert thumbnail.size[1] <= 300

    def test_generate_thumbnail_maintains_aspect_ratio(self):
        """Should maintain aspect ratio when resizing."""
        from handler import generate_thumbnail

        # Create a tall image (200x400)
        test_image = Image.new("RGB", (200, 400), (0, 255, 0))

        thumbnail = generate_thumbnail(test_image)

        # Should be 150x300 (scaled to fit 300x300 maintaining ratio)
        assert thumbnail.size == (150, 300)

    def test_generate_thumbnail_handles_small_images(self):
        """Should not upscale small images."""
        from handler import generate_thumbnail

        # Create a small image (50x50)
        test_image = Image.new("RGB", (50, 50), (0, 0, 255))

        thumbnail = generate_thumbnail(test_image)

        # Should stay 50x50, not upscaled
        assert thumbnail.size == (50, 50)
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
PYTHONPATH=. poetry run pytest lambdas/image_processor/tests/test_handler.py::TestThumbnailGeneration -v
```

Expected: FAIL with `ImportError: cannot import name 'generate_thumbnail'`

**Step 3: Write the implementation**

Add to `handler.py` after `add_background` function (around line 396):

```python
def generate_thumbnail(image: Image.Image) -> Image.Image:
    """Generate a thumbnail from a PIL Image.

    Args:
        image: PIL Image (RGB or RGBA)

    Returns:
        Thumbnail as RGB PIL Image (JPEG-compatible)
    """
    # Convert to RGB if necessary (for PNG with transparency)
    if image.mode in ("RGBA", "P"):
        # Create white background for transparency
        background = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode == "RGBA":
            background.paste(image, mask=image.split()[3])
        else:
            background.paste(image)
        image = background

    # Create thumbnail maintaining aspect ratio
    # thumbnail() modifies in place, so copy first
    thumb = image.copy()
    thumb.thumbnail(THUMBNAIL_MAX_SIZE, Image.Resampling.LANCZOS)

    return thumb
```

**Step 4: Run test to verify it passes**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
PYTHONPATH=. poetry run pytest lambdas/image_processor/tests/test_handler.py::TestThumbnailGeneration -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/lambdas/image_processor/handler.py backend/lambdas/image_processor/tests/test_handler.py
git commit -m "feat: add generate_thumbnail function to image processor"
```

---

## Task 3: Add Thumbnail Upload to Process Flow

**Files:**
- Modify: `backend/lambdas/image_processor/handler.py`

**Step 1: Add thumbnail generation and upload after processed image upload**

In `process_image()` function, after line 560 (`upload_to_s3` for processed image), add:

```python
            # Generate and upload thumbnail
            thumbnail = generate_thumbnail(final_image)
            thumb_s3_key = f"thumb_{db_s3_key.replace('.png', '.jpg')}"
            full_thumb_s3_key = f"books/{thumb_s3_key}"

            thumb_buffer = io.BytesIO()
            thumbnail.save(thumb_buffer, format="JPEG", quality=THUMBNAIL_QUALITY, optimize=True)
            thumb_bytes = thumb_buffer.getvalue()

            logger.info(f"Uploading thumbnail to s3://{IMAGES_BUCKET}/{full_thumb_s3_key}")
            upload_to_s3(IMAGES_BUCKET, full_thumb_s3_key, thumb_bytes, "image/jpeg")
```

**Step 2: Run existing tests to ensure no regression**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
PYTHONPATH=. poetry run pytest lambdas/image_processor/tests/test_handler.py -v
```

Expected: All tests pass

**Step 3: Commit**

```bash
git add backend/lambdas/image_processor/handler.py
git commit -m "feat: add thumbnail upload to image processor flow"
```

---

## Task 4: Add Source Image Selection Constants

**Files:**
- Modify: `backend/lambdas/image_processor/handler.py`

**Step 1: Add image type priority constants after thumbnail constants**

```python
# Image type priority for source selection (highest priority first)
# Lambda will select best source image based on this order
IMAGE_TYPE_PRIORITY = ["title_page", "binding", "cover", "spine"]
```

**Step 2: Commit**

```bash
git add backend/lambdas/image_processor/handler.py
git commit -m "feat: add image type priority constants"
```

---

## Task 5: Add Source Image Selection Function

**Files:**
- Modify: `backend/lambdas/image_processor/handler.py`
- Test: `backend/lambdas/image_processor/tests/test_handler.py`

**Step 1: Write the failing tests**

Add to `backend/lambdas/image_processor/tests/test_handler.py`:

```python
class TestSourceImageSelection:
    """Tests for smart source image selection."""

    def test_selects_title_page_over_others(self):
        """Should select title_page type if available."""
        from handler import select_best_source_image

        images = [
            MagicMock(id=1, image_type="cover", is_primary=True),
            MagicMock(id=2, image_type="title_page", is_primary=False),
            MagicMock(id=3, image_type="interior", is_primary=False),
        ]

        result = select_best_source_image(images, primary_image_id=1)
        assert result.id == 2

    def test_selects_binding_when_no_title_page(self):
        """Should select binding type if no title_page."""
        from handler import select_best_source_image

        images = [
            MagicMock(id=1, image_type="interior", is_primary=True),
            MagicMock(id=2, image_type="binding", is_primary=False),
            MagicMock(id=3, image_type=None, is_primary=False),
        ]

        result = select_best_source_image(images, primary_image_id=1)
        assert result.id == 2

    def test_selects_cover_when_no_binding(self):
        """Should select cover type if no title_page or binding."""
        from handler import select_best_source_image

        images = [
            MagicMock(id=1, image_type="interior", is_primary=True),
            MagicMock(id=2, image_type="cover", is_primary=False),
        ]

        result = select_best_source_image(images, primary_image_id=1)
        assert result.id == 2

    def test_falls_back_to_primary_when_no_preferred_types(self):
        """Should fall back to primary image if no preferred types."""
        from handler import select_best_source_image

        images = [
            MagicMock(id=1, image_type=None, is_primary=True),
            MagicMock(id=2, image_type="interior", is_primary=False),
            MagicMock(id=3, image_type=None, is_primary=False),
        ]

        result = select_best_source_image(images, primary_image_id=1)
        assert result.id == 1

    def test_falls_back_to_passed_image_id_when_all_null(self):
        """Should use passed image_id if no types and no primary flag."""
        from handler import select_best_source_image

        images = [
            MagicMock(id=1, image_type=None, is_primary=False),
            MagicMock(id=2, image_type=None, is_primary=False),
            MagicMock(id=3, image_type=None, is_primary=False),
        ]

        result = select_best_source_image(images, primary_image_id=2)
        assert result.id == 2

    def test_skips_already_processed_images(self):
        """Should not select images that are already background processed."""
        from handler import select_best_source_image

        images = [
            MagicMock(id=1, image_type="title_page", is_primary=False, is_background_processed=True),
            MagicMock(id=2, image_type="binding", is_primary=False, is_background_processed=False),
            MagicMock(id=3, image_type=None, is_primary=True, is_background_processed=False),
        ]

        result = select_best_source_image(images, primary_image_id=3)
        assert result.id == 2  # Skips processed title_page, picks binding
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
PYTHONPATH=. poetry run pytest lambdas/image_processor/tests/test_handler.py::TestSourceImageSelection -v
```

Expected: FAIL with `ImportError: cannot import name 'select_best_source_image'`

**Step 3: Write the implementation**

Add to `handler.py` after the `generate_thumbnail` function:

```python
def select_best_source_image(images: list, primary_image_id: int):
    """Select the best source image for processing.

    Priority order:
    1. title_page (if exists and not already processed)
    2. binding (if exists and not already processed)
    3. cover (if exists and not already processed)
    4. spine (if exists and not already processed)
    5. Primary image (fallback)
    6. Image matching primary_image_id (final fallback)

    Args:
        images: List of BookImage objects for the book
        primary_image_id: ID of the image that triggered processing

    Returns:
        Best source image to process
    """
    # Filter out already processed images
    unprocessed = [
        img for img in images
        if not getattr(img, "is_background_processed", False)
    ]

    if not unprocessed:
        # All images processed, fall back to the requested one
        for img in images:
            if img.id == primary_image_id:
                return img
        return images[0] if images else None

    # Check for preferred image types in priority order
    for image_type in IMAGE_TYPE_PRIORITY:
        for img in unprocessed:
            if getattr(img, "image_type", None) == image_type:
                return img

    # Fall back to primary image
    for img in unprocessed:
        if getattr(img, "is_primary", False):
            return img

    # Final fallback: the image that was passed in
    for img in unprocessed:
        if img.id == primary_image_id:
            return img

    # Last resort: first unprocessed image
    return unprocessed[0]
```

**Step 4: Run test to verify it passes**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
PYTHONPATH=. poetry run pytest lambdas/image_processor/tests/test_handler.py::TestSourceImageSelection -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/lambdas/image_processor/handler.py backend/lambdas/image_processor/tests/test_handler.py
git commit -m "feat: add select_best_source_image function"
```

---

## Task 6: Integrate Source Selection into Process Flow

**Files:**
- Modify: `backend/lambdas/image_processor/handler.py`

**Step 1: Modify process_image to use smart source selection**

In `process_image()` function, after querying the job (around line 470), add source selection:

Replace this section (lines 472-478):
```python
            source_image = db.query(BookImage).filter(BookImage.id == image_id).first()
            if not source_image:
                job.status = "failed"
                job.failure_reason = "Source image not found"
                job.completed_at = datetime.now(UTC)
                db.commit()
                return False
```

With:
```python
            # Get all images for this book to select best source
            all_images = (
                db.query(BookImage)
                .filter(BookImage.book_id == book_id)
                .all()
            )

            if not all_images:
                job.status = "failed"
                job.failure_reason = "No images found for book"
                job.completed_at = datetime.now(UTC)
                db.commit()
                return False

            # Select best source image based on type priority
            source_image = select_best_source_image(all_images, image_id)
            logger.info(
                f"Selected source image {source_image.id} "
                f"(type={source_image.image_type}, requested={image_id})"
            )
```

**Step 2: Run all handler tests**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
PYTHONPATH=. poetry run pytest lambdas/image_processor/tests/test_handler.py -v
```

Expected: All tests pass

**Step 3: Commit**

```bash
git add backend/lambdas/image_processor/handler.py
git commit -m "feat: integrate smart source selection into process flow"
```

---

## Task 7: Run Full Test Suite and Linting

**Step 1: Run ruff check**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run ruff check backend/lambdas/image_processor/
```

Fix any issues.

**Step 2: Run ruff format**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run ruff format backend/lambdas/image_processor/
```

**Step 3: Run full backend test suite**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run pytest tests/ -q --tb=short
```

Expected: All tests pass

**Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: lint and format fixes"
```

---

## Task 8: Update Session Log

**Step 1: Update session log with fix status**

Update `/Users/mark/projects/bluemoxon/.worktrees/auto-process-images/docs/sessions/session-2026-01-17-image-processor-issues.md`:

Add to "Files Modified This Session":
- `backend/lambdas/image_processor/handler.py` - Added thumbnail generation and smart source selection

Update Issues status to FIXED.

**Step 2: Commit**

```bash
git add docs/sessions/session-2026-01-17-image-processor-issues.md
git commit -m "docs: update session log with fix status"
```

---

## Task 9: Create PR for Review

**Step 1: Push branch**

```bash
git push origin feat/auto-process-images
```

**Step 2: Create PR to staging**

```bash
gh pr create --base staging --title "fix: Add thumbnail generation and smart source selection to image processor" --body "## Summary

Fixes two critical issues in the image processor Lambda:

1. **Missing Thumbnails** - Processed images now have thumbnails generated and uploaded
2. **Wrong Source Image** - Lambda now selects best source image based on type priority

## Changes

- Added \`generate_thumbnail()\` function matching API endpoint behavior
- Added \`select_best_source_image()\` with priority: title_page > binding > cover > spine > primary
- Added thumbnail upload after processed image upload
- Integrated smart source selection into process flow

## Issue

Part of #1136

## Test Plan

- [ ] Unit tests pass (new tests for thumbnail and source selection)
- [ ] Lint checks pass
- [ ] Deploy to staging
- [ ] Test with book 635 (Ruskin) - verify thumbnail appears
- [ ] Test with book 626 (Charles O'Malley) - verify correct source selected

Generated with Claude Code"
```

**Step 3: Wait for user review**

Per user requirements, PRs need review before merging to staging.

---

## Post-Implementation: Staging Validation

After PR is merged to staging:

1. **Trigger reprocessing** for test books:
```bash
# Queue book 635 for reprocessing
bmx-api POST /books/635/reprocess-image

# Queue book 626 for reprocessing
bmx-api POST /books/626/reprocess-image
```

2. **Check Lambda logs**:
```bash
AWS_PROFILE=bmx-staging aws logs tail /aws/lambda/bluemoxon-staging-image-processor --since 5m
```

3. **Verify thumbnails exist**:
```bash
bmx-api GET /books/635/images
bmx-api GET /books/626/images
```

4. **Visual verification** - Check images display correctly on staging website
