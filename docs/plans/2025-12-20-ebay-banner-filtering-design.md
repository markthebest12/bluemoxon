# eBay Seller Banner Filtering Design

**Issue:** #487 - Non-related images from eBay listings imported into book carousel
**Date:** 2025-12-20
**Status:** Approved

## Problem

eBay sellers add promotional banners (e.g., "Visit My Store!") at the end of their image carousels. These get imported alongside legitimate book photos, degrading collection quality.

**Examples:**

- Book 515: image_17 is a seller store banner
- Book 514: images 04-09 are seller promotional content

## Decision: Block Automatically

After evaluating warn vs block approaches, **automatic blocking** was chosen because:

- Cost of false positive (missing one book photo) is low - user can manually upload
- Cost of false negative (ads in carousel) is higher - degrades collection quality
- Keeps import flow simple with no UI changes required

## Detection Logic

Block an image if **both** conditions are met:

1. Image is in the **last 3 positions** of the carousel
2. Image has **wide aspect ratio** (width/height > 2.0)

### Why Both Conditions

| Condition | Alone | Combined |
|-----------|-------|----------|
| Position only | Would filter legitimate last photos | High confidence |
| Aspect ratio only | Some book photos are landscape | High confidence |

### Edge Cases

- **Single image listings:** Never filtered (position 0 of 1)
- **Legitimate panoramic photos:** Rare; user can manually upload
- **Failed dimension reads:** Fail open (include the image)

## Implementation

**File:** `scraper/handler.py`

**Constants:**

```python
BANNER_ASPECT_RATIO_THRESHOLD = 2.0  # width/height > 2.0 = likely banner
BANNER_POSITION_WINDOW = 3  # Check last N images
```

**Detection function:**

```python
def is_likely_banner(image_data: bytes, position: int, total_images: int) -> bool:
    """Detect if image is likely a seller banner."""
    if position < total_images - BANNER_POSITION_WINDOW:
        return False

    try:
        img = Image.open(io.BytesIO(image_data))
        width, height = img.size
        aspect_ratio = width / height if height > 0 else 0
        return aspect_ratio > BANNER_ASPECT_RATIO_THRESHOLD
    except Exception:
        return False  # Fail open
```

**Integration point:** Image processing loop (lines 322-347), before S3 upload.

## Testing

**Unit tests:**

- Wide image at end position → blocked
- Portrait image at end position → allowed
- Wide image at start position → allowed

**Manual validation:**

- Book 515 image_17 should be blocked on re-scrape
- Book 514 images should be evaluated

## Rollout

1. Deploy to staging
2. Re-scrape test listing with known banner
3. Verify banner skipped in CloudWatch logs
4. Deploy to production

**Monitoring:** Track `Skipping suspected seller banner` log entries.

## Future Tuning

If false positives occur:

- Tighten aspect ratio threshold (2.5 instead of 2.0)
- Reduce position window (last 2 instead of 3)
- Add URL pattern matching as additional signal
