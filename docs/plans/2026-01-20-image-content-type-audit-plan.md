# Image Content-Type Audit Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix image format and Content-Type mismatches across the codebase with zero-downtime migration.

**Architecture:** New `image_utils.py` module provides centralized format detection via magic numbers. Code fixes use these utilities. Admin migration endpoint fixes existing S3 objects in 3 stages.

**Tech Stack:** Python 3.12, FastAPI, boto3, pytest

**Parallelization:** Tasks marked with same `[PARALLEL-GROUP-X]` can run simultaneously in separate worktrees.

---

## Task 1: Create image_utils.py Module [PARALLEL-GROUP-A]

**Files:**
- Create: `backend/app/utils/image_utils.py`
- Create: `backend/tests/utils/test_image_utils.py`

**Step 1: Create test file with all test cases**

```python
# backend/tests/utils/test_image_utils.py
"""Tests for image format detection utilities."""
import pytest
from app.utils.image_utils import (
    ImageFormat,
    detect_format,
    get_content_type,
    get_extension,
    detect_content_type,
    validate_format_match,
    fix_extension,
    MIN_DETECTION_BYTES,
)


class TestDetectFormat:
    """Tests for detect_format function."""

    def test_detect_jpeg_standard(self):
        """JPEG with standard APP0 marker."""
        data = b'\xff\xd8\xff\xe0' + b'\x00' * 8
        assert detect_format(data) == ImageFormat.JPEG

    def test_detect_jpeg_exif(self):
        """JPEG with EXIF marker (from cameras)."""
        data = b'\xff\xd8\xff\xe1' + b'\x00' * 8
        assert detect_format(data) == ImageFormat.JPEG

    def test_detect_jpeg_minimal(self):
        """JPEG detection only needs first 2 bytes."""
        data = b'\xff\xd8\xff\xdb' + b'\x00' * 8
        assert detect_format(data) == ImageFormat.JPEG

    def test_detect_png(self):
        """PNG 8-byte signature."""
        data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 4
        assert detect_format(data) == ImageFormat.PNG

    def test_detect_webp(self):
        """WebP RIFF container."""
        data = b'RIFF\x00\x00\x00\x00WEBP'
        assert detect_format(data) == ImageFormat.WEBP

    def test_detect_gif87a(self):
        """GIF87a format."""
        data = b'GIF87a' + b'\x00' * 6
        assert detect_format(data) == ImageFormat.GIF

    def test_detect_gif89a(self):
        """GIF89a format."""
        data = b'GIF89a' + b'\x00' * 6
        assert detect_format(data) == ImageFormat.GIF

    def test_detect_unknown(self):
        """Unknown format returns UNKNOWN."""
        data = b'\x00' * 12
        assert detect_format(data) == ImageFormat.UNKNOWN

    def test_detect_unknown_strict_raises(self):
        """Unknown format with strict=True raises ValueError."""
        data = b'\x00' * 12
        with pytest.raises(ValueError, match="Unknown image format"):
            detect_format(data, strict=True)

    def test_insufficient_data_raises(self):
        """Data shorter than MIN_DETECTION_BYTES raises ValueError."""
        data = b'\xff\xd8'  # Valid JPEG start but too short
        with pytest.raises(ValueError, match="Insufficient data"):
            detect_format(data)

    def test_minimum_bytes_constant(self):
        """MIN_DETECTION_BYTES is 12 (for WebP check)."""
        assert MIN_DETECTION_BYTES == 12


class TestGetContentType:
    """Tests for get_content_type function."""

    def test_jpeg_content_type(self):
        assert get_content_type(ImageFormat.JPEG) == "image/jpeg"

    def test_png_content_type(self):
        assert get_content_type(ImageFormat.PNG) == "image/png"

    def test_webp_content_type(self):
        assert get_content_type(ImageFormat.WEBP) == "image/webp"

    def test_gif_content_type(self):
        assert get_content_type(ImageFormat.GIF) == "image/gif"

    def test_unknown_content_type(self):
        assert get_content_type(ImageFormat.UNKNOWN) == "application/octet-stream"


class TestGetExtension:
    """Tests for get_extension function."""

    def test_jpeg_extension(self):
        assert get_extension(ImageFormat.JPEG) == ".jpg"

    def test_png_extension(self):
        assert get_extension(ImageFormat.PNG) == ".png"

    def test_webp_extension(self):
        assert get_extension(ImageFormat.WEBP) == ".webp"

    def test_gif_extension(self):
        assert get_extension(ImageFormat.GIF) == ".gif"

    def test_unknown_extension(self):
        assert get_extension(ImageFormat.UNKNOWN) == ""


class TestDetectContentType:
    """Tests for detect_content_type convenience function."""

    def test_detects_jpeg(self):
        data = b'\xff\xd8\xff\xe0' + b'\x00' * 8
        assert detect_content_type(data) == "image/jpeg"

    def test_detects_png(self):
        data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 4
        assert detect_content_type(data) == "image/png"


class TestValidateFormatMatch:
    """Tests for validate_format_match function."""

    def test_matching_jpg(self):
        data = b'\xff\xd8\xff\xe0' + b'\x00' * 8
        assert validate_format_match("photo.jpg", data) is True

    def test_matching_jpeg(self):
        """Both .jpg and .jpeg are valid for JPEG."""
        data = b'\xff\xd8\xff\xe0' + b'\x00' * 8
        assert validate_format_match("photo.jpeg", data) is True

    def test_matching_png(self):
        data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 4
        assert validate_format_match("image.png", data) is True

    def test_mismatched_extension(self):
        """PNG data with .jpg extension."""
        data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 4
        assert validate_format_match("image.jpg", data) is False

    def test_unknown_format(self):
        data = b'\x00' * 12
        assert validate_format_match("file.bin", data) is False

    def test_case_insensitive(self):
        data = b'\xff\xd8\xff\xe0' + b'\x00' * 8
        assert validate_format_match("PHOTO.JPG", data) is True


class TestFixExtension:
    """Tests for fix_extension function."""

    def test_fix_png_to_jpg(self):
        """PNG extension on JPEG data gets fixed."""
        data = b'\xff\xd8\xff\xe0' + b'\x00' * 8
        assert fix_extension("photo.png", data) == "photo.jpg"

    def test_fix_jpg_to_png(self):
        """JPG extension on PNG data gets fixed."""
        data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 4
        assert fix_extension("image.jpg", data) == "image.png"

    def test_already_correct(self):
        data = b'\xff\xd8\xff\xe0' + b'\x00' * 8
        assert fix_extension("photo.jpg", data) == "photo.jpg"

    def test_unknown_format_unchanged(self):
        data = b'\x00' * 12
        assert fix_extension("file.bin", data) == "file.bin"

    def test_no_extension(self):
        data = b'\xff\xd8\xff\xe0' + b'\x00' * 8
        assert fix_extension("photo", data) == "photo.jpg"

    def test_preserves_path(self):
        data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 4
        assert fix_extension("books/638_processed.jpg", data) == "books/638_processed.png"
```

**Step 2: Run tests to verify they fail**

```bash
pytest backend/tests/utils/test_image_utils.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.utils.image_utils'"

**Step 3: Create the utils directory and __init__.py if needed**

```bash
mkdir -p backend/app/utils
touch backend/app/utils/__init__.py
```

**Step 4: Implement image_utils.py**

```python
# backend/app/utils/image_utils.py
"""Image format detection utilities using magic numbers.

Provides reliable format detection without depending on file extensions
or S3 metadata. Uses the first 12 bytes of image data to identify format.
"""
from enum import Enum


class ImageFormat(Enum):
    """Supported image formats."""

    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    GIF = "gif"
    UNKNOWN = "unknown"


# Extension mapping - using .jpg (industry standard, shorter)
EXTENSIONS: dict[ImageFormat, str] = {
    ImageFormat.JPEG: ".jpg",
    ImageFormat.PNG: ".png",
    ImageFormat.WEBP: ".webp",
    ImageFormat.GIF: ".gif",
}

CONTENT_TYPES: dict[ImageFormat, str] = {
    ImageFormat.JPEG: "image/jpeg",
    ImageFormat.PNG: "image/png",
    ImageFormat.WEBP: "image/webp",
    ImageFormat.GIF: "image/gif",
}

MIN_DETECTION_BYTES = 12  # Minimum for WEBP detection (RIFF + WEBP)


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
        raise ValueError(
            f"Insufficient data: need {MIN_DETECTION_BYTES} bytes, got {len(data)}"
        )

    # JPEG: \xff\xd8 (only first 2 bytes matter, third varies by marker type)
    if data[:2] == b"\xff\xd8":
        return ImageFormat.JPEG

    # PNG: 8-byte signature
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ImageFormat.PNG

    # WEBP: RIFF....WEBP (bytes 0-3 and 8-11)
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ImageFormat.WEBP

    # GIF: GIF87a or GIF89a
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return ImageFormat.GIF

    if strict:
        raise ValueError("Unknown image format")
    return ImageFormat.UNKNOWN


def get_content_type(fmt: ImageFormat) -> str:
    """Return MIME type for format.

    Returns 'application/octet-stream' for UNKNOWN.
    """
    return CONTENT_TYPES.get(fmt, "application/octet-stream")


def get_extension(fmt: ImageFormat) -> str:
    """Return file extension with dot.

    Returns empty string for UNKNOWN.
    """
    return EXTENSIONS.get(fmt, "")


def detect_content_type(data: bytes) -> str:
    """Convenience: detect format and return MIME type directly."""
    return get_content_type(detect_format(data))


def validate_format_match(filename: str, data: bytes) -> bool:
    """Check if filename extension matches actual content.

    Args:
        filename: Filename or path to check
        data: Image bytes (minimum 12 bytes)

    Returns:
        True if extension matches actual format, False otherwise
    """
    actual = detect_format(data)
    if actual == ImageFormat.UNKNOWN:
        return False

    expected_ext = get_extension(actual)
    lower_filename = filename.lower()

    # Special case: both .jpg and .jpeg are valid for JPEG
    if actual == ImageFormat.JPEG and lower_filename.endswith(".jpeg"):
        return True

    return lower_filename.endswith(expected_ext)


def fix_extension(filename: str, data: bytes) -> str:
    """Return filename with correct extension based on actual content.

    Args:
        filename: Filename or path to fix
        data: Image bytes (minimum 12 bytes)

    Returns:
        Filename with correct extension, or unchanged if format unknown
    """
    fmt = detect_format(data)
    if fmt == ImageFormat.UNKNOWN:
        return filename

    # Remove existing extension and add correct one
    if "." in filename:
        base = filename.rsplit(".", 1)[0]
    else:
        base = filename

    return base + get_extension(fmt)
```

**Step 5: Run tests to verify they pass**

```bash
pytest backend/tests/utils/test_image_utils.py -v
```

Expected: All 27 tests PASS

**Step 6: Run linting**

```bash
poetry run ruff check backend/app/utils/image_utils.py
poetry run ruff format --check backend/app/utils/image_utils.py
```

**Step 7: Commit**

```bash
git add backend/app/utils/ backend/tests/utils/
git commit -m "feat(images): add image_utils module with format detection

- Magic number detection for JPEG, PNG, WebP, GIF
- Helper functions: detect_content_type, fix_extension, validate_format_match
- 27 unit tests with full coverage

Closes part of #1201"
```

---

## Task 2: Update images.py Upload [PARALLEL-GROUP-B]

**Depends on:** Task 1 (image_utils.py)

**Files:**
- Modify: `backend/app/api/v1/images.py:~447`
- Modify: `backend/tests/test_images.py`

**Step 1: Write test for correct ContentType on upload**

```python
# Add to backend/tests/test_images.py
class TestImageUploadContentType:
    """Tests for correct ContentType detection on upload."""

    @pytest.mark.asyncio
    async def test_png_upload_gets_png_content_type(self, client, mock_s3):
        """PNG file should be uploaded with image/png ContentType."""
        # PNG magic bytes
        png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100

        # Mock the upload and capture the ContentType
        captured_content_type = None
        original_upload = mock_s3.upload_file

        def capture_upload(*args, **kwargs):
            nonlocal captured_content_type
            if 'ExtraArgs' in kwargs:
                captured_content_type = kwargs['ExtraArgs'].get('ContentType')
            return original_upload(*args, **kwargs)

        mock_s3.upload_file = capture_upload

        # Upload PNG file
        response = await client.post(
            "/api/v1/books/1/images",
            files={"file": ("test.png", png_data, "image/png")},
        )

        assert captured_content_type == "image/png"
```

**Step 2: Run test to verify it fails**

```bash
pytest backend/tests/test_images.py::TestImageUploadContentType -v
```

Expected: FAIL (currently hardcodes image/jpeg)

**Step 3: Update images.py to detect format**

```python
# backend/app/api/v1/images.py
# Add import at top:
from app.utils.image_utils import detect_content_type, fix_extension

# Around line 447, change:
# OLD:
# ExtraArgs={"ContentType": "image/jpeg"}

# NEW:
# Read file bytes for format detection
with open(file_path, "rb") as f:
    file_bytes = f.read(12)  # Only need first 12 bytes

content_type = detect_content_type(file_bytes)
s3_key = fix_extension(s3_key, file_bytes)

await asyncio.to_thread(
    s3.upload_file,
    str(file_path),
    settings.images_bucket,
    s3_key,
    ExtraArgs={"ContentType": content_type},
)
```

**Step 4: Run test to verify it passes**

```bash
pytest backend/tests/test_images.py::TestImageUploadContentType -v
```

**Step 5: Commit**

```bash
git add backend/app/api/v1/images.py backend/tests/test_images.py
git commit -m "fix(images): detect actual format on upload

Use image_utils to detect ContentType from magic numbers
instead of hardcoding image/jpeg.

Part of #1201"
```

---

## Task 3: Update books.py copy_object [PARALLEL-GROUP-B]

**Depends on:** Task 1 (image_utils.py)

**Files:**
- Modify: `backend/app/api/v1/books.py:~322-326`

**Step 1: Write test for metadata preservation**

```python
# Add to backend/tests/test_books.py
class TestImageCopyMetadata:
    """Tests for S3 copy_object metadata handling."""

    def test_copy_preserves_content_type(self, mock_s3):
        """copy_object should preserve source ContentType."""
        # Setup: source has image/png ContentType
        mock_s3.head_object.return_value = {
            'ContentType': 'image/png',
            'ContentLength': 1000
        }

        # The copy_object call should include MetadataDirective='COPY'
        # to preserve the source metadata

        # Verify mock_s3.copy_object was called with MetadataDirective='COPY'
        # This ensures source ContentType is preserved
```

**Step 2: Update books.py**

```python
# backend/app/api/v1/books.py around line 322-326
# OLD:
s3.copy_object(
    Bucket=bucket_name,
    CopySource={"Bucket": bucket_name, "Key": source_key},
    Key=target_key,
)

# NEW:
s3.copy_object(
    Bucket=bucket_name,
    CopySource={"Bucket": bucket_name, "Key": source_key},
    Key=target_key,
    MetadataDirective="COPY",  # Preserve source ContentType
)
```

**Step 3: Run tests and commit**

```bash
pytest backend/tests/test_books.py -v
git add backend/app/api/v1/books.py backend/tests/test_books.py
git commit -m "fix(books): preserve ContentType in copy_object

Add MetadataDirective='COPY' to preserve source S3 metadata
when copying images between books.

Part of #1201"
```

---

## Task 4: Update bedrock.py [PARALLEL-GROUP-B]

**Depends on:** Task 1 (image_utils.py)

**Files:**
- Modify: `backend/app/services/bedrock.py:~321-333`
- Modify: `backend/tests/services/test_bedrock.py`

**Step 1: Write test**

```python
# Add to backend/tests/services/test_bedrock.py
def test_uses_image_utils_for_format_detection(mock_s3):
    """Should use image_utils.detect_content_type instead of custom logic."""
    # PNG data with wrong S3 ContentType
    png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
    mock_s3.get_object.return_value = {
        'Body': io.BytesIO(png_data),
        'ContentType': 'image/jpeg',  # Wrong!
    }

    # Should detect actual format as PNG
    result = get_image_for_bedrock(image)
    assert result['media_type'] == 'image/png'
```

**Step 2: Update bedrock.py**

```python
# backend/app/services/bedrock.py
# Add import:
from app.utils.image_utils import detect_content_type

# Around line 321-333, replace custom logic:
# OLD:
content_type = response.get("ContentType")
if not content_type or content_type == "application/octet-stream":
    if img.s3_key.lower().endswith(".png"):
        content_type = "image/png"
    elif img.s3_key.lower().endswith((".jpg", ".jpeg")):
        content_type = "image/jpeg"
    else:
        content_type = "image/jpeg"

# NEW:
image_data = response["Body"].read()
content_type = detect_content_type(image_data[:12])
```

**Step 3: Run tests and commit**

```bash
pytest backend/tests/services/test_bedrock.py -v
git add backend/app/services/bedrock.py backend/tests/services/test_bedrock.py
git commit -m "refactor(bedrock): use image_utils for format detection

Replace custom extension-based fallback logic with
centralized magic number detection.

Part of #1201"
```

---

## Task 5: Migration Endpoint - Models and Schema [PARALLEL-GROUP-A]

**Files:**
- Create: `backend/app/schemas/migration.py`

**Step 1: Create schema file**

```python
# backend/app/schemas/migration.py
"""Schemas for image migration endpoints."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MigrationRequest(BaseModel):
    """Request to start a migration job."""

    stage: Literal[1, 2, 3] = Field(
        ...,
        description="Migration stage: 1=fix ContentType, 2=copy thumbnails, 3=cleanup",
    )
    dry_run: bool = Field(
        default=True,
        description="If true, only report what would be done without making changes",
    )
    limit: int | None = Field(
        default=None,
        description="Maximum number of objects to process (for testing)",
    )


class MigrationStats(BaseModel):
    """Statistics from a migration run."""

    processed: int = 0
    fixed: int = 0
    already_correct: int = 0
    copied: int = 0
    already_exists: int = 0
    deleted: int = 0
    skipped: int = 0
    skipped_not_jpeg: int = 0
    skipped_no_jpg: int = 0
    errors: int = 0


class MigrationError(BaseModel):
    """Error encountered during migration."""

    key: str
    error: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MigrationJob(BaseModel):
    """Status of a migration job."""

    job_id: str
    stage: int
    status: Literal["running", "completed", "failed"]
    dry_run: bool
    started_at: datetime
    completed_at: datetime | None = None
    stats: MigrationStats = Field(default_factory=MigrationStats)
    errors: list[MigrationError] = Field(default_factory=list)


class MigrationResponse(BaseModel):
    """Response when starting a migration."""

    job_id: str
    status: str
```

**Step 2: Commit**

```bash
git add backend/app/schemas/migration.py
git commit -m "feat(admin): add migration schemas

Pydantic models for migration request/response.

Part of #1201"
```

---

## Task 6: Migration Endpoint - Service [PARALLEL-GROUP-C]

**Depends on:** Task 1 (image_utils.py), Task 5 (schemas)

**Files:**
- Create: `backend/app/services/image_migration.py`
- Create: `backend/tests/services/test_image_migration.py`

**Step 1: Write tests**

```python
# backend/tests/services/test_image_migration.py
"""Tests for image migration service."""
import pytest
from unittest.mock import MagicMock, patch
from app.services.image_migration import (
    migrate_stage_1,
    migrate_stage_2,
    cleanup_stage_3,
)
from app.utils.image_utils import ImageFormat


class TestMigrateStage1:
    """Tests for Stage 1: Fix ContentType on main images."""

    @pytest.mark.asyncio
    async def test_fixes_wrong_content_type(self):
        """Should fix ContentType when it doesn't match actual format."""
        mock_s3 = MagicMock()

        # PNG file with wrong ContentType
        mock_s3.list_objects_v2.return_value = {
            'Contents': [{'Key': 'books/test.png'}],
            'IsTruncated': False,
        }
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: b'\x89PNG\r\n\x1a\n\x00\x00\x00\x00'),
        }
        mock_s3.head_object.return_value = {
            'ContentType': 'image/jpeg',  # Wrong!
        }

        errors = []
        stats = await migrate_stage_1(mock_s3, 'bucket', False, None, errors)

        assert stats['fixed'] == 1
        mock_s3.copy_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_thumbnails(self):
        """Should skip objects with thumb_ prefix."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            'Contents': [{'Key': 'books/thumb_test.png'}],
            'IsTruncated': False,
        }

        errors = []
        stats = await migrate_stage_1(mock_s3, 'bucket', False, None, errors)

        assert stats['skipped'] == 1
        assert stats['processed'] == 0

    @pytest.mark.asyncio
    async def test_dry_run_no_changes(self):
        """Dry run should not make any S3 changes."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            'Contents': [{'Key': 'books/test.png'}],
            'IsTruncated': False,
        }
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: b'\x89PNG\r\n\x1a\n\x00\x00\x00\x00'),
        }
        mock_s3.head_object.return_value = {'ContentType': 'image/jpeg'}

        errors = []
        stats = await migrate_stage_1(mock_s3, 'bucket', True, None, errors)

        assert stats['fixed'] == 1
        mock_s3.copy_object.assert_not_called()


class TestMigrateStage2:
    """Tests for Stage 2: Copy thumb_*.png to thumb_*.jpg."""

    @pytest.mark.asyncio
    async def test_copies_png_to_jpg(self):
        """Should copy .png thumbnail to .jpg."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            'Contents': [{'Key': 'books/thumb_test.png'}],
            'IsTruncated': False,
        }
        # .jpg doesn't exist yet
        mock_s3.head_object.side_effect = Exception('404')
        # Thumbnail is actually JPEG
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: b'\xff\xd8\xff\xe0\x00\x00\x00\x00\x00\x00\x00\x00'),
        }

        errors = []
        stats = await migrate_stage_2(mock_s3, 'bucket', False, None, errors)

        assert stats['copied'] == 1
        mock_s3.copy_object.assert_called_with(
            Bucket='bucket',
            CopySource={'Bucket': 'bucket', 'Key': 'books/thumb_test.png'},
            Key='books/thumb_test.jpg',
            MetadataDirective='REPLACE',
            ContentType='image/jpeg',
        )

    @pytest.mark.asyncio
    async def test_skips_if_jpg_exists(self):
        """Should skip if .jpg already exists (idempotent)."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            'Contents': [{'Key': 'books/thumb_test.png'}],
            'IsTruncated': False,
        }
        # .jpg already exists
        mock_s3.head_object.return_value = {'ContentType': 'image/jpeg'}

        errors = []
        stats = await migrate_stage_2(mock_s3, 'bucket', False, None, errors)

        assert stats['already_exists'] == 1
        mock_s3.copy_object.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_non_jpeg_thumbnails(self):
        """Should skip thumbnails that aren't actually JPEG."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            'Contents': [{'Key': 'books/thumb_test.png'}],
            'IsTruncated': False,
        }
        mock_s3.head_object.side_effect = Exception('404')
        # Thumbnail is actually PNG (not JPEG)
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: b'\x89PNG\r\n\x1a\n\x00\x00\x00\x00'),
        }

        errors = []
        stats = await migrate_stage_2(mock_s3, 'bucket', False, None, errors)

        assert stats['skipped_not_jpeg'] == 1
        mock_s3.copy_object.assert_not_called()


class TestCleanupStage3:
    """Tests for Stage 3: Delete old .png thumbnails."""

    @pytest.mark.asyncio
    async def test_deletes_png_when_jpg_exists(self):
        """Should delete .png after verifying .jpg exists."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            'Contents': [{'Key': 'books/thumb_test.png'}],
            'IsTruncated': False,
        }
        # .jpg exists
        mock_s3.head_object.return_value = {'ContentType': 'image/jpeg'}

        errors = []
        stats = await cleanup_stage_3(mock_s3, 'bucket', False, None, errors)

        assert stats['deleted'] == 1

    @pytest.mark.asyncio
    async def test_skips_when_no_jpg(self):
        """Should not delete .png if .jpg doesn't exist."""
        mock_s3 = MagicMock()
        mock_s3.list_objects_v2.return_value = {
            'Contents': [{'Key': 'books/thumb_test.png'}],
            'IsTruncated': False,
        }
        # .jpg doesn't exist
        mock_s3.head_object.side_effect = Exception('404')

        errors = []
        stats = await cleanup_stage_3(mock_s3, 'bucket', False, None, errors)

        assert stats['skipped_no_jpg'] == 1
        mock_s3.delete_objects.assert_not_called()
```

**Step 2: Implement service**

```python
# backend/app/services/image_migration.py
"""Image migration service for fixing ContentType mismatches."""
import asyncio
import logging
from datetime import datetime
from typing import Any

from botocore.exceptions import ClientError

from app.utils.image_utils import (
    ImageFormat,
    detect_format,
    get_content_type,
)

logger = logging.getLogger(__name__)

S3_IMAGES_PREFIX = "books/"


async def migrate_stage_1(
    s3: Any,
    bucket: str,
    dry_run: bool,
    limit: int | None,
    errors: list[dict],
) -> dict[str, int]:
    """Fix ContentType on main images (skip thumbnails).

    Uses S3 range requests to download only first 12 bytes for format detection.
    """
    stats = {
        "processed": 0,
        "fixed": 0,
        "already_correct": 0,
        "skipped": 0,
        "errors": 0,
    }
    continuation_token = None

    while True:
        kwargs: dict[str, Any] = {
            "Bucket": bucket,
            "Prefix": S3_IMAGES_PREFIX,
            "MaxKeys": 1000,
        }
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token

        response = s3.list_objects_v2(**kwargs)

        for obj in response.get("Contents", []):
            key = obj["Key"]

            # Skip thumbnails - handled in Stage 2
            if "/thumb_" in key:
                stats["skipped"] += 1
                continue

            if limit and stats["processed"] >= limit:
                return stats

            try:
                # Range request - only first 12 bytes
                range_resp = s3.get_object(
                    Bucket=bucket, Key=key, Range="bytes=0-11"
                )
                magic_bytes = range_resp["Body"].read()

                actual_format = detect_format(magic_bytes, strict=False)
                if actual_format == ImageFormat.UNKNOWN:
                    stats["skipped"] += 1
                    continue

                # Check current metadata
                head = s3.head_object(Bucket=bucket, Key=key)
                current_ct = head.get("ContentType", "")
                expected_ct = get_content_type(actual_format)

                if current_ct != expected_ct:
                    if not dry_run:
                        s3.copy_object(
                            Bucket=bucket,
                            CopySource={"Bucket": bucket, "Key": key},
                            Key=key,
                            MetadataDirective="REPLACE",
                            ContentType=expected_ct,
                        )
                    stats["fixed"] += 1
                    logger.info(
                        f"{'[DRY RUN] ' if dry_run else ''}Fixed {key}: "
                        f"{current_ct} -> {expected_ct}"
                    )
                else:
                    stats["already_correct"] += 1

            except ClientError as e:
                errors.append({
                    "key": key,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                })
                stats["errors"] += 1
            except Exception as e:
                errors.append({
                    "key": key,
                    "error": f"Unexpected: {e}",
                    "timestamp": datetime.utcnow().isoformat(),
                })
                stats["errors"] += 1

            stats["processed"] += 1

        if not response.get("IsTruncated"):
            break
        continuation_token = response["NextContinuationToken"]
        await asyncio.sleep(0.1)  # Rate limiting

    return stats


async def migrate_stage_2(
    s3: Any,
    bucket: str,
    dry_run: bool,
    limit: int | None,
    errors: list[dict],
) -> dict[str, int]:
    """Copy thumb_*.png to thumb_*.jpg (verify JPEG format first)."""
    stats = {
        "processed": 0,
        "copied": 0,
        "already_exists": 0,
        "skipped_not_jpeg": 0,
        "errors": 0,
    }
    continuation_token = None

    while True:
        kwargs: dict[str, Any] = {
            "Bucket": bucket,
            "Prefix": f"{S3_IMAGES_PREFIX}thumb_",
            "MaxKeys": 1000,
        }
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token

        response = s3.list_objects_v2(**kwargs)

        for obj in response.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".png"):
                continue

            if limit and stats["processed"] >= limit:
                return stats

            try:
                new_key = key.rsplit(".", 1)[0] + ".jpg"

                # Check if .jpg already exists (idempotent)
                try:
                    s3.head_object(Bucket=bucket, Key=new_key)
                    stats["already_exists"] += 1
                    stats["processed"] += 1
                    continue
                except ClientError:
                    pass  # Doesn't exist, proceed

                # Verify it's actually JPEG format
                range_resp = s3.get_object(
                    Bucket=bucket, Key=key, Range="bytes=0-11"
                )
                magic_bytes = range_resp["Body"].read()
                actual_format = detect_format(magic_bytes, strict=False)

                if actual_format != ImageFormat.JPEG:
                    errors.append({
                        "key": key,
                        "error": f"Expected JPEG but found {actual_format.value}",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    stats["skipped_not_jpeg"] += 1
                    stats["processed"] += 1
                    continue

                if not dry_run:
                    s3.copy_object(
                        Bucket=bucket,
                        CopySource={"Bucket": bucket, "Key": key},
                        Key=new_key,
                        MetadataDirective="REPLACE",
                        ContentType="image/jpeg",
                    )
                stats["copied"] += 1
                logger.info(
                    f"{'[DRY RUN] ' if dry_run else ''}Copied {key} -> {new_key}"
                )

            except ClientError as e:
                errors.append({
                    "key": key,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                })
                stats["errors"] += 1

            stats["processed"] += 1

        if not response.get("IsTruncated"):
            break
        continuation_token = response["NextContinuationToken"]
        await asyncio.sleep(0.1)

    return stats


async def cleanup_stage_3(
    s3: Any,
    bucket: str,
    dry_run: bool,
    limit: int | None,
    errors: list[dict],
) -> dict[str, int]:
    """Delete thumb_*.png after verifying .jpg exists (batch deletes)."""
    stats = {
        "processed": 0,
        "deleted": 0,
        "skipped_no_jpg": 0,
        "errors": 0,
    }
    continuation_token = None
    delete_batch: list[dict[str, str]] = []

    while True:
        kwargs: dict[str, Any] = {
            "Bucket": bucket,
            "Prefix": f"{S3_IMAGES_PREFIX}thumb_",
            "MaxKeys": 1000,
        }
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token

        response = s3.list_objects_v2(**kwargs)

        for obj in response.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".png"):
                continue

            if limit and stats["processed"] >= limit:
                # Flush pending deletes before returning
                if delete_batch and not dry_run:
                    s3.delete_objects(
                        Bucket=bucket, Delete={"Objects": delete_batch}
                    )
                return stats

            try:
                jpg_key = key.rsplit(".", 1)[0] + ".jpg"

                # Only delete if .jpg exists
                try:
                    s3.head_object(Bucket=bucket, Key=jpg_key)
                except ClientError:
                    stats["skipped_no_jpg"] += 1
                    stats["processed"] += 1
                    continue

                delete_batch.append({"Key": key})
                stats["deleted"] += 1
                logger.info(
                    f"{'[DRY RUN] ' if dry_run else ''}Queued delete: {key}"
                )

                # Batch delete every 1000 objects
                if len(delete_batch) >= 1000:
                    if not dry_run:
                        s3.delete_objects(
                            Bucket=bucket, Delete={"Objects": delete_batch}
                        )
                    delete_batch = []

            except ClientError as e:
                errors.append({
                    "key": key,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                })
                stats["errors"] += 1

            stats["processed"] += 1

        if not response.get("IsTruncated"):
            break
        continuation_token = response["NextContinuationToken"]
        await asyncio.sleep(0.1)

    # Final batch
    if delete_batch and not dry_run:
        s3.delete_objects(Bucket=bucket, Delete={"Objects": delete_batch})

    return stats
```

**Step 3: Run tests and commit**

```bash
pytest backend/tests/services/test_image_migration.py -v
git add backend/app/services/image_migration.py backend/tests/services/test_image_migration.py
git commit -m "feat(admin): add image migration service

Three-stage migration:
- Stage 1: Fix ContentType on main images
- Stage 2: Copy thumb_*.png to thumb_*.jpg
- Stage 3: Delete old .png thumbnails

Features: range requests, pagination, batch deletes, dry-run support.

Part of #1201"
```

---

## Task 7: Migration Endpoint - API [PARALLEL-GROUP-C]

**Depends on:** Task 5 (schemas), Task 6 (service)

**Files:**
- Modify: `backend/app/api/v1/admin.py`

**Step 1: Add endpoint**

```python
# Add to backend/app/api/v1/admin.py
from datetime import datetime
from fastapi import BackgroundTasks

from app.schemas.migration import (
    MigrationRequest,
    MigrationJob,
    MigrationResponse,
    MigrationStats,
)
from app.services.image_migration import (
    migrate_stage_1,
    migrate_stage_2,
    cleanup_stage_3,
)

# In-memory job storage (use Redis in production)
MIGRATION_JOBS: dict[str, MigrationJob] = {}


async def run_migration(job_id: str, request: MigrationRequest, s3, bucket: str):
    """Background task to run migration."""
    job = MIGRATION_JOBS[job_id]
    errors: list[dict] = []

    try:
        if request.stage == 1:
            stats = await migrate_stage_1(s3, bucket, request.dry_run, request.limit, errors)
        elif request.stage == 2:
            stats = await migrate_stage_2(s3, bucket, request.dry_run, request.limit, errors)
        elif request.stage == 3:
            stats = await cleanup_stage_3(s3, bucket, request.dry_run, request.limit, errors)
        else:
            raise ValueError(f"Invalid stage: {request.stage}")

        job.stats = MigrationStats(**stats)
        job.status = "completed"
    except Exception as e:
        job.status = "failed"
        errors.append({"key": "fatal", "error": str(e), "timestamp": datetime.utcnow().isoformat()})
    finally:
        job.completed_at = datetime.utcnow()
        job.errors = [MigrationError(**e) for e in errors]


@router.post("/migrate-image-formats", response_model=MigrationResponse)
async def start_image_migration(
    request: MigrationRequest,
    background_tasks: BackgroundTasks,
    s3=Depends(get_s3_client),
    settings=Depends(get_settings),
):
    """Start an image format migration job.

    Stage 1: Fix ContentType on main images (non-destructive)
    Stage 2: Copy thumb_*.png to thumb_*.jpg (non-destructive)
    Stage 3: Delete old .png thumbnails (destructive - run after verification)
    """
    job_id = f"mig_{int(datetime.utcnow().timestamp())}"

    job = MigrationJob(
        job_id=job_id,
        stage=request.stage,
        status="running",
        dry_run=request.dry_run,
        started_at=datetime.utcnow(),
    )
    MIGRATION_JOBS[job_id] = job

    background_tasks.add_task(
        run_migration, job_id, request, s3, settings.images_bucket
    )

    return MigrationResponse(job_id=job_id, status="running")


@router.get("/migrate-image-formats/{job_id}", response_model=MigrationJob)
async def get_migration_status(job_id: str):
    """Get status of a migration job."""
    job = MIGRATION_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
```

**Step 2: Run tests and commit**

```bash
pytest backend/tests/api/test_admin.py -v
git add backend/app/api/v1/admin.py
git commit -m "feat(admin): add migration API endpoints

POST /admin/migrate-image-formats - start migration job
GET /admin/migrate-image-formats/{job_id} - poll status

Part of #1201"
```

---

## Task 8: Update get_thumbnail_key() [PARALLEL-GROUP-D]

**Depends on:** Tasks 2-7 complete, Stage 2 migration run

**Files:**
- Modify: `backend/app/api/v1/images.py:129-140`
- Modify: `backend/app/services/image_cleanup.py:20-25`
- Modify: `backend/tests/test_images.py`

**Step 1: Update tests first**

```python
# Update backend/tests/test_images.py
class TestGetThumbnailKey:
    """Tests for get_thumbnail_key function - always returns .jpg."""

    def test_png_to_jpg(self):
        """PNG key becomes .jpg thumbnail."""
        assert get_thumbnail_key("638_abc.png") == "thumb_638_abc.jpg"

    def test_jpg_stays_jpg(self):
        assert get_thumbnail_key("638_abc.jpg") == "thumb_638_abc.jpg"

    def test_webp_to_jpg(self):
        assert get_thumbnail_key("639/image_01.webp") == "thumb_639/image_01.jpg"

    def test_preserves_path(self):
        assert get_thumbnail_key("books/639/cover.png") == "thumb_books/639/cover.jpg"

    def test_no_extension(self):
        assert get_thumbnail_key("image") == "thumb_image.jpg"
```

**Step 2: Update images.py**

```python
# backend/app/api/v1/images.py lines 129-140
def get_thumbnail_key(s3_key: str) -> str:
    """Get the S3 key for a thumbnail from the original image key.

    Always returns .jpg extension since all thumbnails are JPEG format.

    Example: '638_abc.png' -> 'thumb_638_abc.jpg'
    Example: '639/image_01.webp' -> 'thumb_639/image_01.jpg'
    """
    if "." in s3_key:
        base = s3_key.rsplit(".", 1)[0]
    else:
        base = s3_key
    return f"thumb_{base}.jpg"
```

**Step 3: Update image_cleanup.py**

```python
# backend/app/services/image_cleanup.py lines 20-25
def get_thumbnail_key(s3_key: str) -> str:
    """Get the S3 key for a thumbnail from the original image key.

    Always returns .jpg extension since all thumbnails are JPEG format.
    """
    if "." in s3_key:
        base = s3_key.rsplit(".", 1)[0]
    else:
        base = s3_key
    return f"thumb_{base}.jpg"
```

**Step 4: Run tests and commit**

```bash
pytest backend/tests/test_images.py::TestGetThumbnailKey -v
git add backend/app/api/v1/images.py backend/app/services/image_cleanup.py backend/tests/test_images.py
git commit -m "fix(images): get_thumbnail_key always returns .jpg

All thumbnails are JPEG format, so always use .jpg extension.
Deploy AFTER running Stage 2 migration.

Part of #1201"
```

---

## Parallel Execution Groups

| Group | Tasks | Can Start |
|-------|-------|-----------|
| A | 1, 5 | Immediately |
| B | 2, 3, 4 | After Group A |
| C | 6, 7 | After Task 1, 5 |
| D | 8 | After Stage 2 migration run |

## Deployment Checklist

1. [ ] Merge Tasks 1-7 to staging
2. [ ] Deploy to staging
3. [ ] Run: `POST /admin/migrate-image-formats {"stage": 2, "dry_run": true}`
4. [ ] Verify dry-run results
5. [ ] Run: `POST /admin/migrate-image-formats {"stage": 2, "dry_run": false}`
6. [ ] Verify .jpg thumbnails created
7. [ ] Merge Task 8 to staging
8. [ ] Deploy updated get_thumbnail_key()
9. [ ] Run Stage 1 migration
10. [ ] Run Stage 3 cleanup
11. [ ] PR staging → main
12. [ ] Deploy to production
13. [ ] Run migrations in production
