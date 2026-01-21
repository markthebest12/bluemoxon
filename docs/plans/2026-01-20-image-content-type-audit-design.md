# Design: Image Content-Type Audit (Issue #1201)

**Date**: 2026-01-20
**Issue**: [#1201](https://github.com/markthebest12/bluemoxon/issues/1201)
**Status**: Design Complete

## Problem

Image files have mismatched extensions and Content-Type headers across 5 locations:
- Thumbnails saved as JPEG have `.png` extensions
- Uploads hardcode `image/jpeg` regardless of actual format
- CloudFront caches incorrect Content-Type headers
- Browsers may show wrong download extensions

## Solution Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  image_utils.py (NEW)                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ detect_format() │  │ get_content_type│  │get_extension│ │
│  │ (magic numbers) │  │ (format→MIME)   │  │(format→ext) │ │
│  └────────┬────────┘  └────────┬────────┘  └──────┬──────┘ │
└───────────┼────────────────────┼─────────────────┼─────────┘
            │                    │                 │
     ┌──────┴──────┬─────────────┴────────┬────────┴───────┐
     ▼             ▼                      ▼                ▼
┌─────────┐  ┌──────────┐  ┌────────────────┐  ┌──────────────┐
│ images  │  │  books   │  │ image_processor│  │   bedrock    │
│ .py     │  │  .py     │  │  handler.py    │  │   .py        │
└─────────┘  └──────────┘  └────────────────┘  └──────────────┘
```

## Phase 1: image_utils.py Module

**Location**: `backend/app/utils/image_utils.py`

```python
from enum import Enum

class ImageFormat(Enum):
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    GIF = "gif"
    UNKNOWN = "unknown"

# Extension mapping - using .jpg (industry standard)
EXTENSIONS = {
    ImageFormat.JPEG: ".jpg",
    ImageFormat.PNG: ".png",
    ImageFormat.WEBP: ".webp",
    ImageFormat.GIF: ".gif",
}

CONTENT_TYPES = {
    ImageFormat.JPEG: "image/jpeg",
    ImageFormat.PNG: "image/png",
    ImageFormat.WEBP: "image/webp",
    ImageFormat.GIF: "image/gif",
}

MIN_DETECTION_BYTES = 12  # Minimum for WEBP detection

def detect_format(data: bytes, strict: bool = False) -> ImageFormat:
    """Detect image format from magic numbers.

    Args:
        data: Image bytes (minimum 12 bytes required)
        strict: If True, raise ValueError on unknown format

    Returns:
        ImageFormat enum value

    Raises:
        ValueError: If data too short or strict=True and format unknown
    """
    if len(data) < MIN_DETECTION_BYTES:
        raise ValueError(f"Insufficient data: need {MIN_DETECTION_BYTES} bytes, got {len(data)}")

    # JPEG: \xff\xd8 (only first 2 bytes matter)
    if data[:2] == b'\xff\xd8':
        return ImageFormat.JPEG

    # PNG: 8-byte signature
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return ImageFormat.PNG

    # WEBP: RIFF....WEBP (bytes 0-3 and 8-11)
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return ImageFormat.WEBP

    # GIF: GIF87a or GIF89a
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return ImageFormat.GIF

    if strict:
        raise ValueError("Unknown image format")
    return ImageFormat.UNKNOWN

def get_content_type(fmt: ImageFormat) -> str:
    """Return MIME type. Returns 'application/octet-stream' for UNKNOWN."""
    return CONTENT_TYPES.get(fmt, "application/octet-stream")

def get_extension(fmt: ImageFormat) -> str:
    """Return extension with dot. Returns '' for UNKNOWN."""
    return EXTENSIONS.get(fmt, "")

def detect_content_type(data: bytes) -> str:
    """Convenience: detect format and return MIME type."""
    return get_content_type(detect_format(data))

def validate_format_match(filename: str, data: bytes) -> bool:
    """Check if filename extension matches actual content."""
    actual = detect_format(data)
    if actual == ImageFormat.UNKNOWN:
        return False
    expected_ext = get_extension(actual)
    return filename.lower().endswith(expected_ext) or \
           (actual == ImageFormat.JPEG and filename.lower().endswith(".jpeg"))

def fix_extension(filename: str, data: bytes) -> str:
    """Return filename with correct extension based on actual content."""
    fmt = detect_format(data)
    if fmt == ImageFormat.UNKNOWN:
        return filename
    base = filename.rsplit('.', 1)[0] if '.' in filename else filename
    return base + get_extension(fmt)
```

## Phase 1: Code Fixes

### File 1: `backend/app/api/v1/images.py`

| Line | Current | Change |
|------|---------|--------|
| ~447 | `ExtraArgs={"ContentType": "image/jpeg"}` | Detect format, fix extension AND ContentType |
| ~457 | `ExtraArgs={"ContentType": "image/jpeg"}` | Keep (thumbnails are JPEG) |
| ~689 | `ExtraArgs={"ContentType": "image/jpeg"}` | Keep (regenerated thumbnails are JPEG) |

**Updated thumbnail key function** (deploy after Stage 2 migration):

```python
def get_thumbnail_key(s3_key: str) -> str:
    """Thumbnail key - always .jpg extension (thumbnails are JPEG)."""
    base = s3_key.rsplit('.', 1)[0] if '.' in s3_key else s3_key
    return f"thumb_{base}.jpg"
```

### File 2: `backend/app/api/v1/books.py`

| Line | Current | Change |
|------|---------|--------|
| ~322-326 | `copy_object()` with no metadata directive | Add `MetadataDirective='COPY'` to preserve source |
| ~341 | `ExtraArgs={"ContentType": "image/jpeg"}` | Keep (thumbnail is JPEG) |

### File 3: `backend/lambdas/image_processor/handler.py`

| Line | Current | Change |
|------|---------|--------|
| ~684 | `ContentType="image/jpeg"` | Keep (already correct) |

No changes needed - ContentType is already correct. Extension mismatch handled by migration.

### File 4: `backend/app/services/bedrock.py`

| Line | Current | Change |
|------|---------|--------|
| ~321-333 | Custom fallback logic | Replace with `detect_content_type()` from image_utils |

### File 5: `backend/app/services/image_cleanup.py`

No changes needed - `get_thumbnail_key()` imported from images.py.

## Phase 2: Migration (True Zero-Downtime)

### Deployment Order

```
1. Deploy migration endpoint (lookup still uses .png)
2. Run Stage 2 dry_run=true (verify plan)
3. Run Stage 2 dry_run=false (create .jpg copies, keep .png)
4. Verify: all thumbnails have .jpg copies
5. Deploy updated get_thumbnail_key() → returns .jpg
6. Run Stage 1 (fix ContentType on main images)
7. Run Stage 3 dry_run=true (verify cleanup plan)
8. Run Stage 3 dry_run=false (delete .png originals)
```

### Migration Stages

| Stage | Action | Destructive? |
|-------|--------|--------------|
| 1 | Fix ContentType on main images (skip thumbnails) | No |
| 2 | Copy thumb_*.png → thumb_*.jpg (verify JPEG first) | No |
| 3 | Delete thumb_*.png after verifying .jpg exists | Yes |

### Endpoint: `POST /api/v1/admin/migrate-image-formats`

**Request**:
```json
{
  "stage": 1,
  "dry_run": true,
  "limit": 100
}
```

**Response**:
```json
{
  "job_id": "mig_20260120_001",
  "stage": 1,
  "status": "running",
  "dry_run": false,
  "started_at": "2026-01-20T10:00:00Z",
  "completed_at": null,
  "stats": {
    "processed": 1200,
    "fixed": 203,
    "already_correct": 997,
    "skipped": 0,
    "errors": 0
  },
  "errors": []
}
```

### Poll Endpoint: `GET /api/v1/admin/migrate-image-formats/{job_id}`

### Implementation Details

- **Range requests**: Download only first 12 bytes for format detection (99.99% bandwidth savings)
- **Pagination**: Proper `ContinuationToken` handling for buckets >1000 objects
- **Rate limiting**: 100ms delay between batches to avoid S3 throttling
- **Batch deletes**: Stage 3 uses `delete_objects()` for efficiency (up to 1000 per call)
- **Idempotency**: Stage 2 skips if .jpg already exists
- **Format verification**: Stage 2 verifies thumbnail is actually JPEG before copying
- **Safety**: Stage 3 only deletes .png if .jpg exists

## Phase 3: Consolidation

After migration complete:
1. Remove any legacy `.png` fallback code
2. All new thumbnails created with `.jpg` extension
3. Single source of truth for format detection in `image_utils.py`

## Testing Strategy

### Unit Tests for image_utils.py

- `test_detect_format_jpeg` - various JPEG markers
- `test_detect_format_png` - PNG signature
- `test_detect_format_webp` - RIFF+WEBP
- `test_detect_format_gif` - GIF87a and GIF89a
- `test_detect_format_unknown` - random bytes
- `test_detect_format_insufficient_data` - <12 bytes raises
- `test_fix_extension` - corrects mismatched extensions
- `test_validate_format_match` - true/false cases

### Integration Tests

- Upload PNG, verify ContentType is `image/png`
- Upload JPEG, verify ContentType is `image/jpeg`
- Generate thumbnail, verify extension is `.jpg` and ContentType is `image/jpeg`
- Migration dry-run returns expected counts
- Migration creates correct .jpg copies

## Rollback Plan

### Phase 1 Rollback
Revert code changes - no data changes made.

### Phase 2 Rollback
- Stage 2: .png files still exist, just delete .jpg copies
- Stage 3: Cannot rollback (files deleted), but Stage 3 only runs after verification

## Success Criteria

1. All new uploads have correct ContentType based on actual format
2. All thumbnails have `.jpg` extension and `image/jpeg` ContentType
3. No 404s during migration (zero-downtime verified)
4. Migration endpoint shows 0 errors
5. `bedrock.py` uses centralized format detection
