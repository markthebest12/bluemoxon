# eBay Seller Banner Filtering Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Filter out seller promotional banners from eBay image imports based on aspect ratio and position.

**Architecture:** Add PIL dependency to scraper Lambda, implement `is_likely_banner()` detection function, integrate into image processing loop before S3 upload.

**Tech Stack:** Python, PIL/Pillow, Playwright scraper Lambda

**Design Doc:** `docs/plans/2025-12-20-ebay-banner-filtering-design.md`

---

## Task 1: Add Pillow Dependency

**Files:**

- Modify: `scraper/requirements.txt`

**Step 1: Add Pillow to requirements**

```txt
playwright==1.40.0
boto3>=1.34.0
Pillow>=10.0.0
```

**Step 2: Verify Dockerfile doesn't need changes**

The scraper Dockerfile uses `pip install -r requirements.txt`, so no changes needed.

**Step 3: Commit**

```bash
git add scraper/requirements.txt
git commit -m "chore: add Pillow dependency for banner detection"
```

---

## Task 2: Add Banner Detection Constants

**Files:**

- Modify: `scraper/handler.py:20-27`

**Step 1: Add imports and constants after existing constants**

Find this section (lines 20-27):

```python
# Max images per listing (eBay's limit is 24)
MAX_IMAGES = 24

# Min image size to filter out icons/thumbnails
MIN_IMAGE_SIZE = 10000  # 10KB

# Max listings to extract for FMV search
MAX_LISTINGS = 20
```

Add after it:

```python
# Banner detection thresholds
# Images in the last N positions with wide aspect ratio are likely seller banners
BANNER_ASPECT_RATIO_THRESHOLD = 2.0  # width/height > 2.0 = likely banner
BANNER_POSITION_WINDOW = 3  # Check last N images in carousel
```

**Step 2: Add PIL imports at top of file**

Find (lines 3-11):

```python
import json
import logging
import os
import re
import uuid
from pathlib import Path

import boto3
from playwright.sync_api import sync_playwright
```

Add after stdlib imports, before boto3:

```python
import io

from PIL import Image
```

**Step 3: Commit**

```bash
git add scraper/handler.py
git commit -m "feat: add banner detection constants and PIL import"
```

---

## Task 3: Implement Banner Detection Function

**Files:**

- Modify: `scraper/handler.py` (add function after `extract_item_id`)

**Step 1: Add the detection function after `extract_item_id` function (after line 38)**

```python
def is_likely_banner(image_data: bytes, position: int, total_images: int) -> bool:
    """Detect if image is likely a seller banner based on aspect ratio and position.

    Seller banners (e.g., "Visit My Store!") typically:
    - Appear at the end of the image carousel
    - Have wide aspect ratios (banner-shaped, not book-shaped)

    Args:
        image_data: Raw image bytes
        position: Zero-based index in the image list
        total_images: Total number of images in the listing

    Returns:
        True if image should be filtered out as a likely banner
    """
    # Only check images in the last N positions
    if position < total_images - BANNER_POSITION_WINDOW:
        return False

    try:
        img = Image.open(io.BytesIO(image_data))
        width, height = img.size
        if height <= 0:
            return False
        aspect_ratio = width / height
        is_banner = aspect_ratio > BANNER_ASPECT_RATIO_THRESHOLD
        if is_banner:
            logger.info(
                f"Detected likely banner: position {position}/{total_images}, "
                f"aspect ratio {aspect_ratio:.2f} (threshold: {BANNER_ASPECT_RATIO_THRESHOLD})"
            )
        return is_banner
    except Exception as e:
        logger.warning(f"Could not check banner status: {e}")
        return False  # Fail open - include image if can't read dimensions
```

**Step 2: Commit**

```bash
git add scraper/handler.py
git commit -m "feat: add is_likely_banner detection function"
```

---

## Task 4: Integrate Banner Detection into Image Loop

**Files:**

- Modify: `scraper/handler.py:322-347` (image processing loop)

**Step 1: Find the image processing loop**

Current code (lines 329-332):

```python
                            # Skip small images (likely icons/thumbnails)
                            if len(body) < MIN_IMAGE_SIZE:
                                logger.info(f"Skipping small image ({len(body)} bytes): {img_url}")
                                continue
```

**Step 2: Add banner detection after the size check**

Replace lines 329-332 with:

```python
                            # Skip small images (likely icons/thumbnails)
                            if len(body) < MIN_IMAGE_SIZE:
                                logger.info(f"Skipping small image ({len(body)} bytes): {img_url}")
                                continue

                            # Skip likely seller banners (wide images at end of carousel)
                            if is_likely_banner(body, idx, len(image_urls)):
                                logger.info(f"Skipping suspected seller banner: {img_url}")
                                continue
```

**Step 3: Commit**

```bash
git add scraper/handler.py
git commit -m "feat: integrate banner detection into image upload loop"
```

---

## Task 5: Add Unit Tests

**Files:**

- Create: `scraper/test_handler.py`

**Step 1: Create test file with banner detection tests**

```python
"""Unit tests for scraper handler banner detection."""

import io
import pytest
from PIL import Image

# Import after adding to handler.py
from handler import is_likely_banner, BANNER_ASPECT_RATIO_THRESHOLD, BANNER_POSITION_WINDOW


def create_test_image(width: int, height: int) -> bytes:
    """Create a test image with given dimensions."""
    img = Image.new("RGB", (width, height), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


class TestIsLikelyBanner:
    """Tests for is_likely_banner function."""

    def test_wide_image_at_end_is_banner(self):
        """Wide image (3:1 ratio) in last position should be detected as banner."""
        image_data = create_test_image(1200, 300)  # 4:1 ratio
        assert is_likely_banner(image_data, position=17, total_images=18) is True

    def test_portrait_image_at_end_not_banner(self):
        """Portrait image (2:3 ratio) in last position should NOT be detected as banner."""
        image_data = create_test_image(800, 1200)  # 0.67:1 ratio
        assert is_likely_banner(image_data, position=17, total_images=18) is False

    def test_wide_image_at_start_not_banner(self):
        """Wide image at start of carousel should NOT be detected (position filter)."""
        image_data = create_test_image(1200, 300)  # 4:1 ratio
        assert is_likely_banner(image_data, position=0, total_images=18) is False

    def test_wide_image_in_middle_not_banner(self):
        """Wide image in middle of carousel should NOT be detected."""
        image_data = create_test_image(1200, 300)  # 4:1 ratio
        assert is_likely_banner(image_data, position=10, total_images=18) is False

    def test_square_image_at_end_not_banner(self):
        """Square image at end should NOT be detected (aspect ratio filter)."""
        image_data = create_test_image(800, 800)  # 1:1 ratio
        assert is_likely_banner(image_data, position=17, total_images=18) is False

    def test_single_image_listing_not_filtered(self):
        """Single image listings should never be filtered."""
        image_data = create_test_image(1200, 300)  # 4:1 ratio
        assert is_likely_banner(image_data, position=0, total_images=1) is False

    def test_boundary_aspect_ratio(self):
        """Image exactly at threshold should be detected."""
        # 2.01:1 ratio (just over threshold of 2.0)
        image_data = create_test_image(1005, 500)
        assert is_likely_banner(image_data, position=17, total_images=18) is True

    def test_boundary_position(self):
        """Image at boundary of position window should be detected."""
        image_data = create_test_image(1200, 300)
        # Position 15 in 18 images = index 15, total-3 = 15, so 15 >= 15 = True
        assert is_likely_banner(image_data, position=15, total_images=18) is True
        # Position 14 should NOT be detected (14 < 15)
        assert is_likely_banner(image_data, position=14, total_images=18) is False

    def test_invalid_image_data_fails_open(self):
        """Invalid image data should fail open (not filter)."""
        assert is_likely_banner(b"not an image", position=17, total_images=18) is False

    def test_empty_image_data_fails_open(self):
        """Empty image data should fail open."""
        assert is_likely_banner(b"", position=17, total_images=18) is False
```

**Step 2: Run tests to verify they pass**

```bash
cd scraper
pip install pytest pillow
pytest test_handler.py -v
```

Expected: All tests pass.

**Step 3: Commit**

```bash
git add scraper/test_handler.py
git commit -m "test: add unit tests for banner detection"
```

---

## Task 6: Manual Validation

**Step 1: Build and test scraper locally (optional)**

```bash
cd scraper
docker build -t bluemoxon-scraper-test .
```

**Step 2: Deploy to staging and test**

After merging to staging, the scraper Lambda will be rebuilt.

Test with a known problematic listing:

```bash
# Invoke scraper for book 515's source URL
bmx-api GET /books/515  # Get source_url
# Re-scrape and check logs for "Skipping suspected seller banner"
```

**Step 3: Verify in CloudWatch logs**

```bash
AWS_PROFILE=bmx-staging aws logs filter-log-events \
  --log-group-name /aws/lambda/bluemoxon-staging-scraper \
  --filter-pattern "seller banner" \
  --limit 10
```

---

## Task 7: Create PR and Deploy

**Step 1: Push branch and create PR**

```bash
git push -u origin fix/ebay-banner-filtering
gh pr create --base staging --title "fix: filter seller banners from eBay image imports (#487)" --body "..."
```

**Step 2: Wait for CI and merge**

```bash
gh pr checks <PR_NUMBER> --watch
gh pr merge <PR_NUMBER> --squash --delete-branch
```

**Step 3: Watch staging deploy**

```bash
gh run list --workflow Deploy --limit 1
gh run watch <RUN_ID> --exit-status
```

**Step 4: Test on staging, then promote to production**

After validating on staging:

```bash
gh pr create --base main --head staging --title "fix: filter seller banners from eBay image imports (#487)"
# Wait for CI, merge, watch production deploy
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add Pillow dependency | `scraper/requirements.txt` |
| 2 | Add constants and imports | `scraper/handler.py` |
| 3 | Implement detection function | `scraper/handler.py` |
| 4 | Integrate into image loop | `scraper/handler.py` |
| 5 | Add unit tests | `scraper/test_handler.py` |
| 6 | Manual validation | CloudWatch logs |
| 7 | PR and deploy | Git workflow |
