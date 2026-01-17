# Auto-Process Book Images Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automatically process primary book images to remove backgrounds and add solid backgrounds (black/white based on brightness) via async Lambda processing.

**Architecture:** Lambda worker triggered via SQS when an image becomes primary. Uses rembg for background removal with quality validation. Retry strategy: 2x u2net+alpha, 1x isnet-general-use, then fallback to original.

**Tech Stack:** FastAPI, SQLAlchemy, AWS Lambda, SQS, rembg, ImageMagick, Terraform

**Design Document:** `docs/plans/2026-01-16-auto-process-book-images-design.md`

---

## Task 1: Add `is_background_processed` to BookImage Model

**Files:**
- Modify: `backend/app/models/image.py`
- Create: `backend/alembic/versions/xxxx_add_is_background_processed.py`
- Test: `backend/tests/models/test_image_processed_flag.py`

**Step 1: Write the failing test**

Create `backend/tests/models/test_image_processed_flag.py`:

```python
"""Tests for is_background_processed flag on BookImage."""

import pytest
from app.models import Book, BookImage


class TestIsBackgroundProcessed:
    def test_default_is_false(self, db):
        """New images should have is_background_processed=False by default."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(
            book_id=book.id,
            s3_key="test_123.jpg",
            display_order=0,
            is_primary=True,
        )
        db.add(image)
        db.commit()

        assert image.is_background_processed is False

    def test_can_set_to_true(self, db):
        """Should be able to set is_background_processed=True."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(
            book_id=book.id,
            s3_key="test_123.jpg",
            display_order=0,
            is_primary=True,
            is_background_processed=True,
        )
        db.add(image)
        db.commit()

        db.refresh(image)
        assert image.is_background_processed is True
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run pytest tests/models/test_image_processed_flag.py -v
```

Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'is_background_processed'`

**Step 3: Add field to BookImage model**

Edit `backend/app/models/image.py`, add after `is_primary` field:

```python
    is_background_processed: Mapped[bool] = mapped_column(default=False)
```

**Step 4: Run test to verify it passes**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run pytest tests/models/test_image_processed_flag.py -v
```

Expected: PASS

**Step 5: Create migration**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run alembic revision --autogenerate -m "add is_background_processed to book_images"
```

Review generated migration, ensure it has:
```python
op.add_column('book_images', sa.Column('is_background_processed', sa.Boolean(), nullable=False, server_default='false'))
```

**Step 6: Commit**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images
git add backend/app/models/image.py backend/tests/models/test_image_processed_flag.py backend/alembic/versions/
git commit -m "feat: add is_background_processed flag to BookImage model"
```

---

## Task 2: Create ImageProcessingJob Model

**Files:**
- Create: `backend/app/models/image_processing_job.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/models/test_image_processing_job.py`

**Step 1: Write the failing test**

Create `backend/tests/models/test_image_processing_job.py`:

```python
"""Tests for ImageProcessingJob model."""

import uuid
from datetime import datetime, UTC

import pytest
from app.models import Book, BookImage, ImageProcessingJob


class TestImageProcessingJobCreation:
    def test_create_job_with_required_fields(self, db):
        """Should create job with book_id and source_image_id."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(
            book_id=book.id,
            s3_key="test_123.jpg",
            display_order=0,
            is_primary=True,
        )
        db.add(image)
        db.commit()

        job = ImageProcessingJob(
            book_id=book.id,
            source_image_id=image.id,
        )
        db.add(job)
        db.commit()

        assert job.id is not None
        assert job.status == "pending"
        assert job.attempt_count == 0
        assert job.model_used is None
        assert job.failure_reason is None
        assert job.created_at is not None


class TestImageProcessingJobStatus:
    def test_status_transitions(self, db):
        """Should allow status transitions."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(book_id=book.id, s3_key="test.jpg", display_order=0)
        db.add(image)
        db.commit()

        job = ImageProcessingJob(book_id=book.id, source_image_id=image.id)
        db.add(job)
        db.commit()

        # Pending -> Processing
        job.status = "processing"
        job.attempt_count = 1
        job.model_used = "u2net-alpha"
        db.commit()
        assert job.status == "processing"

        # Processing -> Completed
        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        db.commit()
        assert job.status == "completed"


class TestImageProcessingJobRelationships:
    def test_book_relationship(self, db):
        """Should have relationship to Book."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(book_id=book.id, s3_key="test.jpg", display_order=0)
        db.add(image)
        db.commit()

        job = ImageProcessingJob(book_id=book.id, source_image_id=image.id)
        db.add(job)
        db.commit()

        db.refresh(job)
        assert job.book.title == "Test Book"

    def test_cascade_delete_on_book_delete(self, db):
        """Job should be deleted when book is deleted."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(book_id=book.id, s3_key="test.jpg", display_order=0)
        db.add(image)
        db.commit()

        job = ImageProcessingJob(book_id=book.id, source_image_id=image.id)
        db.add(job)
        db.commit()
        job_id = job.id

        db.delete(book)
        db.commit()

        assert db.get(ImageProcessingJob, job_id) is None
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run pytest tests/models/test_image_processing_job.py -v
```

Expected: FAIL with `ImportError: cannot import name 'ImageProcessingJob'`

**Step 3: Create the model**

Create `backend/app/models/image_processing_job.py`:

```python
"""Image processing job model for async background removal."""

import uuid
from datetime import datetime, UTC

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ImageProcessingJob(Base):
    """Tracks async image processing jobs."""

    __tablename__ = "image_processing_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False
    )
    source_image_id: Mapped[int] = mapped_column(
        ForeignKey("book_images.id", ondelete="SET NULL"), nullable=True
    )
    processed_image_id: Mapped[int | None] = mapped_column(
        ForeignKey("book_images.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempt_count: Mapped[int] = mapped_column(default=0)
    model_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    book = relationship("Book", back_populates="image_processing_jobs")
    source_image = relationship(
        "BookImage", foreign_keys=[source_image_id], lazy="joined"
    )
    processed_image = relationship(
        "BookImage", foreign_keys=[processed_image_id], lazy="joined"
    )
```

**Step 4: Add to models __init__.py**

Edit `backend/app/models/__init__.py`, add import:

```python
from app.models.image_processing_job import ImageProcessingJob
```

And add to `__all__` list.

**Step 5: Add back_populates to Book model**

Edit `backend/app/models/book.py`, add relationship:

```python
    image_processing_jobs: Mapped[list["ImageProcessingJob"]] = relationship(
        "ImageProcessingJob", back_populates="book", cascade="all, delete-orphan"
    )
```

**Step 6: Run test to verify it passes**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run pytest tests/models/test_image_processing_job.py -v
```

Expected: PASS

**Step 7: Create migration**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run alembic revision --autogenerate -m "add image_processing_jobs table"
```

**Step 8: Commit**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images
git add backend/app/models/image_processing_job.py backend/app/models/__init__.py backend/app/models/book.py backend/tests/models/test_image_processing_job.py backend/alembic/versions/
git commit -m "feat: add ImageProcessingJob model for async image processing"
```

---

## Task 3: Measure Current Prompt Lengths (TDD Baseline)

**Files:**
- Test: `backend/tests/test_prompt_processed_image_note.py`

**Step 1: Write test measuring current prompt lengths**

Create `backend/tests/test_prompt_processed_image_note.py`:

```python
"""Tests for processed image note in AI prompts.

TDD requirement: Verify prompt lengths before and after adding processed image note.
"""

import pytest


# The note to be added (~180 chars)
PROCESSED_IMAGE_NOTE = """Note: This image has had its background digitally removed and replaced with a solid color. Disregard any edge artifacts, halos, or unnatural boundaries - focus your analysis on the book itself."""


class TestPromptLengthBaseline:
    """Measure current prompt lengths to establish baseline."""

    def test_processed_image_note_length(self):
        """Note should be approximately 180 characters."""
        assert len(PROCESSED_IMAGE_NOTE) < 250
        assert len(PROCESSED_IMAGE_NOTE) > 150

    def test_napoleon_prompt_has_headroom(self):
        """Napoleon prompt should have room for the note (<1% increase)."""
        from app.services.bedrock import FALLBACK_PROMPT

        # Fallback is ~1200 chars, S3 prompt is ~15000+ chars
        # Note is ~180 chars = ~1.2% of fallback, ~1.2% of full prompt
        # This is acceptable overhead
        note_percentage = (len(PROCESSED_IMAGE_NOTE) / len(FALLBACK_PROMPT)) * 100
        assert note_percentage < 20  # Less than 20% of fallback

    def test_note_does_not_contain_special_characters(self):
        """Note should be plain text without markup that could break prompts."""
        assert "```" not in PROCESSED_IMAGE_NOTE
        assert "---" not in PROCESSED_IMAGE_NOTE
        assert "<" not in PROCESSED_IMAGE_NOTE
        assert ">" not in PROCESSED_IMAGE_NOTE


class TestProcessedImageNoteIntegration:
    """Test that note is properly included/excluded based on flag."""

    def test_note_included_when_primary_is_processed(self):
        """Note should be added to prompt when primary image is processed."""
        # This test will be implemented after bedrock.py is modified
        pass

    def test_note_excluded_when_primary_not_processed(self):
        """Note should NOT be added when primary image is not processed."""
        # This test will be implemented after bedrock.py is modified
        pass

    def test_prompt_structure_preserved_with_note(self):
        """All existing prompt sections should remain intact."""
        # This test will be implemented after bedrock.py is modified
        pass
```

**Step 2: Run test to verify baseline passes**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run pytest tests/test_prompt_processed_image_note.py::TestPromptLengthBaseline -v
```

Expected: PASS (baseline measurements)

**Step 3: Commit baseline tests**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images
git add backend/tests/test_prompt_processed_image_note.py
git commit -m "test: add prompt length baseline tests for processed image note"
```

---

## Task 4: Add Processed Image Note to Bedrock Service

**Files:**
- Modify: `backend/app/services/bedrock.py`
- Test: `backend/tests/test_prompt_processed_image_note.py` (update)

**Step 1: Update tests with full implementation**

Update `backend/tests/test_prompt_processed_image_note.py`, replace the placeholder tests:

```python
"""Tests for processed image note in AI prompts."""

import pytest
from unittest.mock import MagicMock

from app.services.bedrock import build_bedrock_messages, PROCESSED_IMAGE_NOTE


class TestPromptLengthBaseline:
    """Measure current prompt lengths to establish baseline."""

    def test_processed_image_note_length(self):
        """Note should be approximately 180 characters."""
        assert len(PROCESSED_IMAGE_NOTE) < 250
        assert len(PROCESSED_IMAGE_NOTE) > 150

    def test_napoleon_prompt_has_headroom(self):
        """Napoleon prompt should have room for the note (<1% increase)."""
        from app.services.bedrock import FALLBACK_PROMPT

        note_percentage = (len(PROCESSED_IMAGE_NOTE) / len(FALLBACK_PROMPT)) * 100
        assert note_percentage < 20

    def test_note_does_not_contain_special_characters(self):
        """Note should be plain text without markup that could break prompts."""
        assert "```" not in PROCESSED_IMAGE_NOTE
        assert "---" not in PROCESSED_IMAGE_NOTE
        assert "<" not in PROCESSED_IMAGE_NOTE
        assert ">" not in PROCESSED_IMAGE_NOTE


class TestProcessedImageNoteIntegration:
    """Test that note is properly included/excluded based on flag."""

    def test_note_included_when_primary_is_processed(self):
        """Note should be added to prompt when primary image is processed."""
        book_data = {"title": "Test Book"}
        images = [{"type": "image", "source": {"type": "base64", "data": "abc"}}]

        messages = build_bedrock_messages(
            book_data=book_data,
            images=images,
            source_content=None,
            primary_image_processed=True,
        )

        content_text = messages[0]["content"][0]["text"]
        assert PROCESSED_IMAGE_NOTE in content_text

    def test_note_excluded_when_primary_not_processed(self):
        """Note should NOT be added when primary image is not processed."""
        book_data = {"title": "Test Book"}
        images = [{"type": "image", "source": {"type": "base64", "data": "abc"}}]

        messages = build_bedrock_messages(
            book_data=book_data,
            images=images,
            source_content=None,
            primary_image_processed=False,
        )

        content_text = messages[0]["content"][0]["text"]
        assert PROCESSED_IMAGE_NOTE not in content_text

    def test_note_excluded_when_flag_not_provided(self):
        """Note should NOT be added when flag is not provided (backwards compat)."""
        book_data = {"title": "Test Book"}
        images = [{"type": "image", "source": {"type": "base64", "data": "abc"}}]

        messages = build_bedrock_messages(
            book_data=book_data,
            images=images,
            source_content=None,
        )

        content_text = messages[0]["content"][0]["text"]
        assert PROCESSED_IMAGE_NOTE not in content_text

    def test_prompt_structure_preserved_with_note(self):
        """All existing prompt sections should remain intact."""
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "publisher": "Test Publisher",
            "condition_notes": "Very good",
        }
        images = [{"type": "image", "source": {"type": "base64", "data": "abc"}}]

        messages = build_bedrock_messages(
            book_data=book_data,
            images=images,
            source_content=None,
            primary_image_processed=True,
        )

        content_text = messages[0]["content"][0]["text"]

        # Verify all standard sections present
        assert "## Book Metadata" in content_text
        assert "Title: Test Book" in content_text
        assert "Author: Test Author" in content_text
        assert "Publisher: Test Publisher" in content_text
        assert "## Images" in content_text
```

**Step 2: Run tests to verify they fail**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run pytest tests/test_prompt_processed_image_note.py::TestProcessedImageNoteIntegration -v
```

Expected: FAIL with `TypeError: build_bedrock_messages() got an unexpected keyword argument 'primary_image_processed'`

**Step 3: Modify bedrock.py to add note support**

Edit `backend/app/services/bedrock.py`:

1. Add constant after imports (around line 50):

```python
# Processed image note for AI prompts
PROCESSED_IMAGE_NOTE = """Note: This image has had its background digitally removed and replaced with a solid color. Disregard any edge artifacts, halos, or unnatural boundaries - focus your analysis on the book itself."""
```

2. Update `build_bedrock_messages` function signature and body (around line 343):

```python
def build_bedrock_messages(
    book_data: dict,
    images: list[dict],
    source_content: str | None,
    primary_image_processed: bool = False,
) -> list[dict]:
    """Build messages array for Bedrock Claude API.

    Args:
        book_data: Dict with book metadata
        images: List of Bedrock-formatted image blocks
        source_content: Optional HTML content from source URL
        primary_image_processed: Whether primary image has background removed

    Returns:
        Messages array for Bedrock invoke_model
    """
    # Build the text prompt with book metadata
    text_parts = ["Analyze this book for the collection:\n\n## Book Metadata"]

    if book_data.get("title"):
        text_parts.append(f"- Title: {book_data['title']}")
    # ... (rest of existing code)

    # Add image instructions if images provided
    if images:
        text_parts.append(f"\n## Images\n{len(images)} images are attached below.")

        # Add processed image note if primary was processed
        if primary_image_processed:
            text_parts.append(f"\n{PROCESSED_IMAGE_NOTE}")

    user_text = "\n".join(text_parts)
    # ... (rest of existing code)
```

**Step 4: Run tests to verify they pass**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run pytest tests/test_prompt_processed_image_note.py -v
```

Expected: PASS

**Step 5: Run full test suite to ensure no regressions**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run pytest tests/ -q --tb=no
```

Expected: All tests pass

**Step 6: Commit**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images
git add backend/app/services/bedrock.py backend/tests/test_prompt_processed_image_note.py
git commit -m "feat: add processed image note to bedrock prompts"
```

---

## Task 5: Create Image Processing SQS Service

**Files:**
- Create: `backend/app/services/image_processing.py`
- Test: `backend/tests/services/test_image_processing_service.py`

**Step 1: Write the failing test**

Create `backend/tests/services/test_image_processing_service.py`:

```python
"""Tests for image processing service."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models import Book, BookImage, ImageProcessingJob


class TestQueueImageProcessing:
    """Tests for queuing image processing jobs."""

    def test_creates_job_record(self, db):
        """Should create ImageProcessingJob in database."""
        from app.services.image_processing import queue_image_processing

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(
            book_id=book.id,
            s3_key="test_123.jpg",
            display_order=0,
            is_primary=True,
        )
        db.add(image)
        db.commit()

        with patch("app.services.image_processing.send_image_processing_job"):
            job = queue_image_processing(db, book.id, image.id)

        assert job is not None
        assert job.book_id == book.id
        assert job.source_image_id == image.id
        assert job.status == "pending"

    def test_sends_sqs_message(self, db):
        """Should send message to SQS queue."""
        from app.services.image_processing import queue_image_processing

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(book_id=book.id, s3_key="test.jpg", display_order=0)
        db.add(image)
        db.commit()

        with patch("app.services.image_processing.send_image_processing_job") as mock_send:
            job = queue_image_processing(db, book.id, image.id)
            mock_send.assert_called_once_with(str(job.id), book.id, image.id)

    def test_skips_if_pending_job_exists(self, db):
        """Should not create duplicate job if one is already pending."""
        from app.services.image_processing import queue_image_processing

        book = Book(title="Test Book")
        db.add(book)
        db.commit()

        image = BookImage(book_id=book.id, s3_key="test.jpg", display_order=0)
        db.add(image)
        db.commit()

        # Create existing pending job
        existing_job = ImageProcessingJob(
            book_id=book.id,
            source_image_id=image.id,
            status="pending",
        )
        db.add(existing_job)
        db.commit()

        with patch("app.services.image_processing.send_image_processing_job") as mock_send:
            result = queue_image_processing(db, book.id, image.id)
            mock_send.assert_not_called()
            assert result is None


class TestGetImageProcessingQueueUrl:
    """Tests for SQS queue URL retrieval."""

    def test_returns_queue_url(self):
        """Should return queue URL from settings."""
        from app.services.image_processing import get_image_processing_queue_url

        with patch("app.services.image_processing.get_settings") as mock_settings:
            mock_settings.return_value.image_processing_queue_name = "test-queue"
            with patch("app.services.image_processing.get_sqs_client") as mock_client:
                mock_client.return_value.get_queue_url.return_value = {
                    "QueueUrl": "https://sqs.us-west-2.amazonaws.com/123/test-queue"
                }
                url = get_image_processing_queue_url()
                assert "test-queue" in url
```

**Step 2: Run test to verify it fails**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run pytest tests/services/test_image_processing_service.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.image_processing'`

**Step 3: Create the service**

Create `backend/app/services/image_processing.py`:

```python
"""Image processing service for async background removal."""

import logging

import boto3
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ImageProcessingJob

logger = logging.getLogger(__name__)


def get_sqs_client():
    """Get SQS client."""
    settings = get_settings()
    return boto3.client("sqs", region_name=settings.aws_region)


def get_image_processing_queue_url() -> str:
    """Get the image processing SQS queue URL."""
    settings = get_settings()
    client = get_sqs_client()
    response = client.get_queue_url(QueueName=settings.image_processing_queue_name)
    return response["QueueUrl"]


def send_image_processing_job(job_id: str, book_id: int, image_id: int) -> None:
    """Send image processing job to SQS queue.

    Args:
        job_id: UUID of the ImageProcessingJob
        book_id: Book ID
        image_id: Source image ID to process
    """
    import json

    client = get_sqs_client()
    queue_url = get_image_processing_queue_url()

    message = {
        "job_id": job_id,
        "book_id": book_id,
        "image_id": image_id,
    }

    client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message),
    )
    logger.info(f"Queued image processing job {job_id} for book {book_id}")


def queue_image_processing(
    db: Session, book_id: int, image_id: int
) -> ImageProcessingJob | None:
    """Queue an image for background removal processing.

    Creates an ImageProcessingJob record and sends to SQS.
    Skips if a pending/processing job already exists for this image.

    Args:
        db: Database session
        book_id: Book ID
        image_id: Source image ID

    Returns:
        Created job, or None if skipped (duplicate)
    """
    # Check for existing pending/processing job
    existing = (
        db.query(ImageProcessingJob)
        .filter(
            ImageProcessingJob.book_id == book_id,
            ImageProcessingJob.source_image_id == image_id,
            ImageProcessingJob.status.in_(["pending", "processing"]),
        )
        .first()
    )

    if existing:
        logger.info(
            f"Skipping duplicate image processing for book {book_id}, "
            f"existing job {existing.id} is {existing.status}"
        )
        return None

    # Create job record
    job = ImageProcessingJob(
        book_id=book_id,
        source_image_id=image_id,
    )
    db.add(job)
    db.commit()

    # Send to SQS
    send_image_processing_job(str(job.id), book_id, image_id)

    return job
```

**Step 4: Add queue name to settings**

Edit `backend/app/config.py`, add to Settings class:

```python
    image_processing_queue_name: str = "bluemoxon-image-processing"
```

**Step 5: Run tests to verify they pass**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run pytest tests/services/test_image_processing_service.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images
git add backend/app/services/image_processing.py backend/app/config.py backend/tests/services/test_image_processing_service.py
git commit -m "feat: add image processing SQS service"
```

---

## Task 6: Trigger Processing on Primary Image Change

**Files:**
- Modify: `backend/app/api/v1/images.py`
- Test: `backend/tests/test_images.py` (add tests)

**Step 1: Write the failing tests**

Add to `backend/tests/test_images.py`:

```python
class TestImageProcessingTrigger:
    """Tests for auto-triggering image processing on primary change."""

    def test_upload_as_primary_queues_processing(self, client, db):
        """Uploading an image as primary should queue processing."""
        from unittest.mock import patch

        # Create book
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        # Create minimal PNG
        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        with patch("app.api.v1.images.queue_image_processing") as mock_queue:
            response = client.post(
                f"/api/v1/books/{book_id}/images",
                files={"file": ("test.png", io.BytesIO(png_data), "image/png")},
            )
            assert response.status_code == 201

            # First image becomes primary, should trigger processing
            mock_queue.assert_called_once()

    def test_reorder_to_primary_queues_processing(self, client, db):
        """Reordering an image to primary position should queue processing."""
        from unittest.mock import patch

        # Create book with two images
        response = client.post("/api/v1/books", json={"title": "Test Book"})
        book_id = response.json()["id"]

        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        # Upload two images (processing queued for first)
        with patch("app.api.v1.images.queue_image_processing"):
            client.post(
                f"/api/v1/books/{book_id}/images",
                files={"file": ("test1.png", io.BytesIO(png_data), "image/png")},
            )
            client.post(
                f"/api/v1/books/{book_id}/images",
                files={"file": ("test2.png", io.BytesIO(png_data), "image/png")},
            )

        # Get image IDs
        response = client.get(f"/api/v1/books/{book_id}/images")
        images = response.json()
        image_ids = [img["id"] for img in images]

        # Reorder to make second image primary
        with patch("app.api.v1.images.queue_image_processing") as mock_queue:
            new_order = [image_ids[1], image_ids[0]]
            response = client.put(
                f"/api/v1/books/{book_id}/images/reorder",
                json=new_order,
            )
            assert response.status_code == 200

            # Should trigger processing for new primary
            mock_queue.assert_called_once()
```

**Step 2: Run tests to verify they fail**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run pytest tests/test_images.py::TestImageProcessingTrigger -v
```

Expected: FAIL

**Step 3: Add import and trigger to images.py**

Edit `backend/app/api/v1/images.py`:

1. Add import at top:
```python
from app.services.image_processing import queue_image_processing
```

2. In `upload_image` function, after setting is_primary and committing, add:
```python
        # Queue background processing if this is the new primary image
        if db_image.is_primary:
            try:
                queue_image_processing(db, book_id, db_image.id)
            except Exception as e:
                logger.warning(f"Failed to queue image processing: {e}")
```

3. In `reorder_images` function, after reordering and committing, add:
```python
    # Queue processing for new primary if it changed
    new_primary = images[0] if images else None
    if new_primary and new_primary.id != (old_primary_id if 'old_primary_id' in locals() else None):
        try:
            queue_image_processing(db, book_id, new_primary.id)
        except Exception as e:
            logger.warning(f"Failed to queue image processing: {e}")
```

**Step 4: Run tests to verify they pass**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run pytest tests/test_images.py::TestImageProcessingTrigger -v
```

Expected: PASS

**Step 5: Run full test suite**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run pytest tests/ -q --tb=no
```

Expected: All pass

**Step 6: Commit**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images
git add backend/app/api/v1/images.py backend/tests/test_images.py
git commit -m "feat: trigger image processing on primary image change"
```

---

## Task 7: Create Terraform Module for Image Processor Lambda

**Files:**
- Create: `infra/terraform/modules/image-processor/main.tf`
- Create: `infra/terraform/modules/image-processor/variables.tf`
- Create: `infra/terraform/modules/image-processor/outputs.tf`

**Step 1: Create module directory**

```bash
mkdir -p /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/infra/terraform/modules/image-processor
```

**Step 2: Create variables.tf**

Create `infra/terraform/modules/image-processor/variables.tf`:

```hcl
variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name (staging/production)"
  type        = string
}

variable "s3_bucket" {
  description = "S3 bucket containing Lambda deployment package"
  type        = string
}

variable "s3_key" {
  description = "S3 key for Lambda deployment package"
  type        = string
}

variable "images_bucket" {
  description = "S3 bucket for book images"
  type        = string
}

variable "images_cdn_domain" {
  description = "CloudFront domain for images CDN"
  type        = string
}

variable "database_secret_arn" {
  description = "ARN of the database credentials secret"
  type        = string
}

variable "memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 1024  # rembg needs more memory
}

variable "timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 300  # 5 minutes for processing
}

variable "reserved_concurrency" {
  description = "Reserved concurrent executions"
  type        = number
  default     = 2  # Limit parallel processing
}

variable "environment_variables" {
  description = "Additional environment variables"
  type        = map(string)
  default     = {}
}
```

**Step 3: Create main.tf**

Create `infra/terraform/modules/image-processor/main.tf`:

```hcl
# SQS Queue for image processing jobs
resource "aws_sqs_queue" "jobs" {
  name                       = "${var.name_prefix}-image-processing"
  visibility_timeout_seconds = 360  # 6 minutes (longer than Lambda timeout)
  message_retention_seconds  = 345600  # 4 days
  receive_wait_time_seconds  = 20  # Long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3  # After 3 attempts, send to DLQ
  })

  tags = {
    Environment = var.environment
    Service     = "image-processing"
  }
}

# Dead letter queue
resource "aws_sqs_queue" "dlq" {
  name                       = "${var.name_prefix}-image-processing-dlq"
  message_retention_seconds  = 1209600  # 14 days

  tags = {
    Environment = var.environment
    Service     = "image-processing"
  }
}

# IAM role for Lambda
resource "aws_iam_role" "worker_exec" {
  name = "${var.name_prefix}-image-processor-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# CloudWatch Logs policy
resource "aws_iam_role_policy_attachment" "worker_logs" {
  role       = aws_iam_role.worker_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# SQS policy
resource "aws_iam_role_policy" "worker_sqs" {
  name = "${var.name_prefix}-image-processor-sqs"
  role = aws_iam_role.worker_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.jobs.arn
      }
    ]
  })
}

# S3 policy for images bucket
resource "aws_iam_role_policy" "worker_s3" {
  name = "${var.name_prefix}-image-processor-s3"
  role = aws_iam_role.worker_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = "arn:aws:s3:::${var.images_bucket}/*"
      }
    ]
  })
}

# Secrets Manager policy
resource "aws_iam_role_policy" "worker_secrets" {
  name = "${var.name_prefix}-image-processor-secrets"
  role = aws_iam_role.worker_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "secretsmanager:GetSecretValue"
        Resource = var.database_secret_arn
      }
    ]
  })
}

# Lambda function
resource "aws_lambda_function" "worker" {
  function_name = "${var.name_prefix}-image-processor"
  role          = aws_iam_role.worker_exec.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = var.timeout
  memory_size   = var.memory_size

  s3_bucket = var.s3_bucket
  s3_key    = var.s3_key

  reserved_concurrent_executions = var.reserved_concurrency

  environment {
    variables = merge({
      ENVIRONMENT        = var.environment
      BMX_IMAGES_BUCKET  = var.images_bucket
      BMX_IMAGES_CDN_DOMAIN = var.images_cdn_domain
      DB_SECRET_ARN      = var.database_secret_arn
    }, var.environment_variables)
  }

  tags = {
    Environment = var.environment
    Service     = "image-processing"
  }
}

# SQS trigger for Lambda
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn                   = aws_sqs_queue.jobs.arn
  function_name                      = aws_lambda_function.worker.arn
  batch_size                         = 1  # Process one at a time
  function_response_types            = ["ReportBatchItemFailures"]
  maximum_batching_window_in_seconds = 0
}
```

**Step 4: Create outputs.tf**

Create `infra/terraform/modules/image-processor/outputs.tf`:

```hcl
output "queue_url" {
  description = "SQS queue URL"
  value       = aws_sqs_queue.jobs.url
}

output "queue_arn" {
  description = "SQS queue ARN"
  value       = aws_sqs_queue.jobs.arn
}

output "queue_name" {
  description = "SQS queue name"
  value       = aws_sqs_queue.jobs.name
}

output "dlq_url" {
  description = "Dead letter queue URL"
  value       = aws_sqs_queue.dlq.url
}

output "function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.worker.function_name
}

output "function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.worker.arn
}

output "role_name" {
  description = "Lambda execution role name"
  value       = aws_iam_role.worker_exec.name
}
```

**Step 5: Commit**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images
git add infra/terraform/modules/image-processor/
git commit -m "feat: add Terraform module for image processor Lambda"
```

---

## Task 8: Create Lambda Worker Handler

**Files:**
- Create: `backend/lambdas/image-processor/handler.py`
- Create: `backend/lambdas/image-processor/requirements.txt`
- Test: `backend/tests/workers/test_image_processor.py`

**Step 1: Write the failing tests**

Create `backend/tests/workers/test_image_processor.py`:

```python
"""Tests for image processor Lambda worker."""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestQualityValidation:
    """Tests for image quality validation."""

    def test_area_check_passes_when_sufficient(self):
        """Should pass when subject area >= 50% of original."""
        from lambdas.image_processor.handler import validate_image_quality

        # 100x100 original, 80x80 subject = 64% area
        result = validate_image_quality(
            original_width=100,
            original_height=100,
            subject_width=80,
            subject_height=80,
        )
        assert result["passed"] is True

    def test_area_check_fails_when_insufficient(self):
        """Should fail when subject area < 50% of original."""
        from lambdas.image_processor.handler import validate_image_quality

        # 100x100 original, 50x50 subject = 25% area
        result = validate_image_quality(
            original_width=100,
            original_height=100,
            subject_width=50,
            subject_height=50,
        )
        assert result["passed"] is False
        assert result["reason"] == "area_too_small"

    def test_aspect_ratio_check_passes_when_similar(self):
        """Should pass when aspect ratio within +-20%."""
        from lambdas.image_processor.handler import validate_image_quality

        # Original 100x150 (0.67), Subject 90x130 (0.69) = 3% diff
        result = validate_image_quality(
            original_width=100,
            original_height=150,
            subject_width=90,
            subject_height=130,
        )
        assert result["passed"] is True

    def test_aspect_ratio_check_fails_when_different(self):
        """Should fail when aspect ratio differs by >20%."""
        from lambdas.image_processor.handler import validate_image_quality

        # Original 100x100 (1.0), Subject 100x50 (2.0) = 100% diff
        result = validate_image_quality(
            original_width=100,
            original_height=100,
            subject_width=100,
            subject_height=50,
        )
        assert result["passed"] is False
        assert result["reason"] == "aspect_ratio_mismatch"


class TestRetryStrategy:
    """Tests for retry strategy with model fallback."""

    def test_first_attempt_uses_u2net_alpha(self):
        """First attempt should use u2net with alpha matting."""
        from lambdas.image_processor.handler import get_processing_config

        config = get_processing_config(attempt=1)
        assert config["model"] == "u2net"
        assert config["alpha_matting"] is True
        assert config["model_name"] == "u2net-alpha"

    def test_second_attempt_uses_u2net_alpha(self):
        """Second attempt should retry u2net with alpha matting."""
        from lambdas.image_processor.handler import get_processing_config

        config = get_processing_config(attempt=2)
        assert config["model"] == "u2net"
        assert config["alpha_matting"] is True

    def test_third_attempt_uses_isnet(self):
        """Third attempt should fall back to isnet-general-use."""
        from lambdas.image_processor.handler import get_processing_config

        config = get_processing_config(attempt=3)
        assert config["model"] == "isnet-general-use"
        assert config["alpha_matting"] is False
        assert config["model_name"] == "isnet-general-use"


class TestBrightnessCalculation:
    """Tests for brightness-based background color selection."""

    def test_dark_book_gets_black_background(self):
        """Book with brightness < 128 should get black background."""
        from lambdas.image_processor.handler import select_background_color

        assert select_background_color(brightness=100) == "black"
        assert select_background_color(brightness=0) == "black"
        assert select_background_color(brightness=127) == "black"

    def test_light_book_gets_white_background(self):
        """Book with brightness >= 128 should get white background."""
        from lambdas.image_processor.handler import select_background_color

        assert select_background_color(brightness=128) == "white"
        assert select_background_color(brightness=200) == "white"
        assert select_background_color(brightness=255) == "white"
```

**Step 2: Run tests to verify they fail**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run pytest tests/workers/test_image_processor.py -v
```

Expected: FAIL with `ModuleNotFoundError`

**Step 3: Create Lambda handler**

Create directory:
```bash
mkdir -p /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend/lambdas/image_processor
```

Create `backend/lambdas/image_processor/__init__.py`:
```python
"""Image processor Lambda package."""
```

Create `backend/lambdas/image_processor/handler.py`:

```python
"""Image processor Lambda handler.

Processes book images to remove backgrounds and add solid backgrounds
based on book brightness.
"""

import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime, UTC

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BRIGHTNESS_THRESHOLD = 128


def get_processing_config(attempt: int) -> dict:
    """Get rembg processing configuration for attempt number.

    Args:
        attempt: Attempt number (1, 2, or 3)

    Returns:
        Dict with model and alpha_matting settings
    """
    if attempt <= 2:
        return {
            "model": "u2net",
            "alpha_matting": True,
            "model_name": "u2net-alpha",
        }
    else:
        return {
            "model": "isnet-general-use",
            "alpha_matting": False,
            "model_name": "isnet-general-use",
        }


def validate_image_quality(
    original_width: int,
    original_height: int,
    subject_width: int,
    subject_height: int,
) -> dict:
    """Validate processed image quality.

    Args:
        original_width: Original image width
        original_height: Original image height
        subject_width: Extracted subject width
        subject_height: Extracted subject height

    Returns:
        Dict with passed (bool) and reason (str if failed)
    """
    # Area check: subject should be >= 50% of original
    original_area = original_width * original_height
    subject_area = subject_width * subject_height
    area_ratio = subject_area / original_area

    if area_ratio < 0.5:
        return {"passed": False, "reason": "area_too_small"}

    # Aspect ratio check: should be within +-20%
    original_aspect = original_width / original_height
    subject_aspect = subject_width / subject_height
    aspect_diff = abs(original_aspect - subject_aspect) / original_aspect

    if aspect_diff > 0.2:
        return {"passed": False, "reason": "aspect_ratio_mismatch"}

    return {"passed": True, "reason": None}


def select_background_color(brightness: int) -> str:
    """Select background color based on image brightness.

    Args:
        brightness: Average brightness (0-255)

    Returns:
        "black" or "white"
    """
    return "black" if brightness < BRIGHTNESS_THRESHOLD else "white"


def calculate_brightness(image_path: str) -> int:
    """Calculate average brightness of image using ImageMagick.

    Args:
        image_path: Path to image file

    Returns:
        Brightness value 0-255
    """
    result = subprocess.run(
        [
            "magick",
            image_path,
            "-colorspace",
            "Gray",
            "-format",
            "%[fx:mean*255]",
            "info:",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(float(result.stdout.strip()))


def get_subject_bounds(image_path: str) -> tuple[int, int]:
    """Get dimensions of non-transparent subject area.

    Args:
        image_path: Path to image with transparency

    Returns:
        Tuple of (width, height) of subject bounding box
    """
    result = subprocess.run(
        ["magick", image_path, "-trim", "-format", "%wx%h", "info:"],
        capture_output=True,
        text=True,
        check=True,
    )
    dims = result.stdout.strip().split("x")
    return int(dims[0]), int(dims[1])


def remove_background(
    input_path: str,
    output_path: str,
    model: str,
    alpha_matting: bool,
) -> bool:
    """Remove background using rembg.

    Args:
        input_path: Input image path
        output_path: Output image path (PNG with transparency)
        model: Model name (u2net, isnet-general-use)
        alpha_matting: Whether to use alpha matting

    Returns:
        True if successful
    """
    cmd = ["rembg", "i", "-m", model]
    if alpha_matting:
        cmd.append("-a")
    cmd.extend([input_path, output_path])

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def add_background(input_path: str, output_path: str, color: str) -> bool:
    """Add solid background color to image.

    Args:
        input_path: Input image path (PNG with transparency)
        output_path: Output image path
        color: Background color (black/white)

    Returns:
        True if successful
    """
    result = subprocess.run(
        [
            "magick",
            input_path,
            "-background",
            color,
            "-flatten",
            output_path,
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def lambda_handler(event, context):
    """Lambda entry point for SQS-triggered image processing.

    Args:
        event: SQS event with Records
        context: Lambda context

    Returns:
        Dict with batchItemFailures for partial batch failure reporting
    """
    failures = []

    for record in event.get("Records", []):
        try:
            message = json.loads(record["body"])
            job_id = message["job_id"]
            book_id = message["book_id"]
            image_id = message["image_id"]

            logger.info(f"Processing job {job_id} for book {book_id}, image {image_id}")

            # Process the image
            success = process_image(job_id, book_id, image_id)

            if not success:
                failures.append({"itemIdentifier": record["messageId"]})

        except Exception as e:
            logger.error(f"Error processing record: {e}")
            failures.append({"itemIdentifier": record["messageId"]})

    return {"batchItemFailures": failures}


def process_image(job_id: str, book_id: int, image_id: int) -> bool:
    """Process a single image.

    Args:
        job_id: ImageProcessingJob ID
        book_id: Book ID
        image_id: Source image ID

    Returns:
        True if successful
    """
    # This will be implemented with database connection
    # For now, return False to indicate not yet implemented
    logger.info(f"Processing not yet fully implemented for job {job_id}")
    return False
```

Create `backend/lambdas/image_processor/requirements.txt`:

```
rembg[cpu]==2.0.50
pillow>=10.0.0
boto3>=1.28.0
psycopg2-binary>=2.9.0
sqlalchemy>=2.0.0
```

**Step 4: Run tests to verify they pass**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
PYTHONPATH=. poetry run pytest tests/workers/test_image_processor.py -v
```

Expected: PASS for quality validation and config tests

**Step 5: Commit**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images
git add backend/lambdas/image_processor/ backend/tests/workers/test_image_processor.py
git commit -m "feat: add image processor Lambda handler with quality validation"
```

---

## Task 9: Run Linting and Full Test Suite

**Step 1: Run ruff check**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run ruff check .
```

Fix any issues.

**Step 2: Run ruff format**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run ruff format --check .
```

Fix any formatting issues.

**Step 3: Run full test suite**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images/backend
poetry run pytest tests/ -q --tb=short
```

All tests should pass.

**Step 4: Commit any fixes**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images
git add -A
git commit -m "fix: lint and format fixes"
```

---

## Task 10: Update Session Log and Create PR

**Step 1: Update session log**

Update `/Users/mark/projects/bluemoxon/docs/session-20260116-141152-issue-1136.md` with implementation progress.

**Step 2: Push branch**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/auto-process-images
git push -u origin feat/auto-process-images
```

**Step 3: Create PR to staging**

```bash
gh pr create --base staging --title "feat: Auto-process book images during eval import" --body "## Summary

Implements automatic background removal and solid background addition for primary book images.

- Adds ImageProcessingJob model for async job tracking
- Adds is_background_processed flag to BookImage
- Creates SQS service for queueing processing jobs
- Triggers processing when image becomes primary
- Adds Terraform module for image-processor Lambda
- Creates Lambda handler with quality validation and retry logic

## Issue

Closes #1136

## Test Plan

- [ ] Unit tests pass
- [ ] Lint checks pass
- [ ] Manual test: upload image, verify job created
- [ ] Manual test: verify processed image quality

Generated with Claude Code"
```

**Step 4: Wait for review before merge**

Per user requirements, PRs need review before merging to staging.

---

## Remaining Work (Post-MVP)

These items can be done in follow-up PRs:

1. **Complete Lambda implementation** - Full database integration, S3 upload, image reordering
2. **Wire up Terraform module** - Add to main Terraform config for staging/production
3. **Deploy Lambda package** - Build and deploy rembg container image
4. **Integration testing** - End-to-end test in staging
5. **Pass processed flag to bedrock** - Update callers to pass `primary_image_processed` flag
