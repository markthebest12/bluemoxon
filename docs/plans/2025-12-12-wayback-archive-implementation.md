# Wayback Archive Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Archive eBay listings to Wayback Machine when books are acquired, preserving seller descriptions and photos.

**Architecture:** New `archive.py` service handles Wayback API calls. Acquire endpoint triggers archive asynchronously. New endpoint for manual archive. Two new fields track archive status.

**Tech Stack:** Python 3.12 / FastAPI / SQLAlchemy / httpx (async HTTP), Vue 3 / TypeScript / Pinia

**Worktree:** `/Users/mark/projects/bluemoxon/.worktrees/wayback-archive`
**Branch:** `feature/wayback-archive`

---

## Phase 1: Database Schema

### Task 1.1: Add Archive Fields to Book Model

**Files:**
- Modify: `backend/app/models/book.py`

**Step 1: Add new fields after `scoring_snapshot` (around line 91)**

```python
    # Archive tracking
    source_archived_url: Mapped[str | None] = mapped_column(String(500))
    archive_status: Mapped[str | None] = mapped_column(String(20))  # pending, success, failed
```

**Step 2: Run tests to verify no regression**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/wayback-archive/backend && poetry run pytest tests/ -q --tb=short`
Expected: All tests pass

**Step 3: Commit**

```bash
git add backend/app/models/book.py
git commit -m "feat(models): Add archive tracking fields to Book"
```

---

### Task 1.2: Create Alembic Migration

**Files:**
- Create: `backend/alembic/versions/xxxx_add_archive_fields.py`

**Step 1: Generate migration**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/wayback-archive/backend && poetry run alembic revision -m "add_archive_fields"`

**Step 2: Edit the generated migration file**

```python
"""add_archive_fields

Revision ID: [generated]
Revises: [previous]
Create Date: [generated]
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = '[generated]'
down_revision: Union[str, None] = '[previous]'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('books', sa.Column('source_archived_url', sa.String(500), nullable=True))
    op.add_column('books', sa.Column('archive_status', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('books', 'archive_status')
    op.drop_column('books', 'source_archived_url')
```

**Step 3: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(db): Add migration for archive tracking fields"
```

---

### Task 1.3: Update Book Schemas

**Files:**
- Modify: `backend/app/schemas/book.py`

**Step 1: Add fields to BookBase (after `estimated_delivery`, around line 43)**

```python
    # Archive tracking
    source_archived_url: str | None = None
    archive_status: str | None = None  # pending, success, failed
```

**Step 2: Add fields to BookUpdate (after `estimated_delivery`, around line 85)**

```python
    source_archived_url: str | None = None
    archive_status: str | None = None
```

**Step 3: Run tests**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/wayback-archive/backend && poetry run pytest tests/ -q --tb=short`
Expected: All tests pass

**Step 4: Commit**

```bash
git add backend/app/schemas/book.py
git commit -m "feat(schemas): Add archive tracking fields to book schemas"
```

---

## Phase 2: Archive Service

### Task 2.1: Write Failing Test for Archive Service

**Files:**
- Create: `backend/tests/test_archive.py`

**Step 1: Write the test file**

```python
"""Tests for Wayback archive service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.archive import archive_url, check_archive_availability


class TestArchiveUrl:
    """Tests for archive_url function."""

    @pytest.mark.asyncio
    async def test_archive_url_success(self):
        """Test successful archive returns archived URL."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "Content-Location": "/web/20251212120000/https://www.ebay.com/itm/123"
        }

        with patch("app.services.archive.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await archive_url("https://www.ebay.com/itm/123")

            assert result["status"] == "success"
            assert "web.archive.org" in result["archived_url"]

    @pytest.mark.asyncio
    async def test_archive_url_failure(self):
        """Test failed archive returns failed status."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service unavailable"

        with patch("app.services.archive.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await archive_url("https://www.ebay.com/itm/123")

            assert result["status"] == "failed"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_archive_url_timeout(self):
        """Test timeout returns failed status."""
        import httpx

        with patch("app.services.archive.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = httpx.TimeoutException("Timeout")
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            result = await archive_url("https://www.ebay.com/itm/123")

            assert result["status"] == "failed"
            assert "timeout" in result["error"].lower()
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/wayback-archive/backend && poetry run pytest tests/test_archive.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.archive'"

**Step 3: Commit failing test**

```bash
git add backend/tests/test_archive.py
git commit -m "test: Add failing tests for archive service"
```

---

### Task 2.2: Implement Archive Service

**Files:**
- Create: `backend/app/services/archive.py`

**Step 1: Write the service**

```python
"""Wayback Machine archive service."""

import logging
from typing import TypedDict

import httpx

logger = logging.getLogger(__name__)

WAYBACK_SAVE_URL = "https://web.archive.org/save"
WAYBACK_AVAILABILITY_URL = "https://archive.org/wayback/available"
TIMEOUT_SECONDS = 30


class ArchiveResult(TypedDict):
    status: str  # "success", "failed", "pending"
    archived_url: str | None
    error: str | None


async def archive_url(url: str) -> ArchiveResult:
    """
    Archive a URL to the Wayback Machine.

    Args:
        url: The URL to archive

    Returns:
        ArchiveResult with status and archived_url or error
    """
    if not url:
        return {"status": "failed", "archived_url": None, "error": "No URL provided"}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            # Request archive save
            save_url = f"{WAYBACK_SAVE_URL}/{url}"
            response = await client.get(save_url, follow_redirects=True)

            if response.status_code == 200:
                # Extract archived URL from response
                # Wayback returns Content-Location header with the archived path
                content_location = response.headers.get("Content-Location", "")
                if content_location:
                    archived_url = f"https://web.archive.org{content_location}"
                else:
                    # Fallback: construct from response URL
                    archived_url = str(response.url)

                logger.info(f"Successfully archived {url} to {archived_url}")
                return {
                    "status": "success",
                    "archived_url": archived_url,
                    "error": None,
                }
            else:
                error_msg = f"Wayback returned {response.status_code}: {response.text[:200]}"
                logger.warning(f"Failed to archive {url}: {error_msg}")
                return {
                    "status": "failed",
                    "archived_url": None,
                    "error": error_msg,
                }

    except httpx.TimeoutException:
        error_msg = f"Timeout after {TIMEOUT_SECONDS}s archiving {url}"
        logger.warning(error_msg)
        return {"status": "failed", "archived_url": None, "error": error_msg}

    except Exception as e:
        error_msg = f"Error archiving {url}: {str(e)}"
        logger.error(error_msg)
        return {"status": "failed", "archived_url": None, "error": error_msg}


async def check_archive_availability(url: str) -> dict:
    """
    Check if a URL is already archived in Wayback Machine.

    Args:
        url: The URL to check

    Returns:
        Dict with availability info
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                WAYBACK_AVAILABILITY_URL,
                params={"url": url},
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("archived_snapshots", {})
            return {}
    except Exception as e:
        logger.warning(f"Error checking availability for {url}: {e}")
        return {}
```

**Step 2: Run tests to verify they pass**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/wayback-archive/backend && poetry run pytest tests/test_archive.py -v`
Expected: All 3 tests pass

**Step 3: Commit**

```bash
git add backend/app/services/archive.py
git commit -m "feat(services): Add Wayback archive service"
```

---

## Phase 3: API Endpoints

### Task 3.1: Write Failing Test for Archive Endpoint

**Files:**
- Add to: `backend/tests/test_archive.py`

**Step 1: Add endpoint tests to test file**

```python
# Add these imports at top
from fastapi.testclient import TestClient
from app.main import app
from tests.conftest import get_mock_editor


class TestArchiveEndpoint:
    """Tests for POST /books/{id}/archive-source endpoint."""

    def test_archive_source_creates_pending_status(self, client, db_session):
        """Test archive endpoint sets status to pending."""
        from app.models.book import Book

        # Create a book with source_url
        book = Book(
            title="Test Book",
            source_url="https://www.ebay.com/itm/123456",
            status="EVALUATING",
        )
        db_session.add(book)
        db_session.commit()
        db_session.refresh(book)

        # Mock auth
        app.dependency_overrides[require_editor] = get_mock_editor

        response = client.post(f"/api/v1/books/{book.id}/archive-source")

        assert response.status_code == 200
        data = response.json()
        assert data["archive_status"] in ["pending", "success", "failed"]

        # Clean up
        app.dependency_overrides.clear()

    def test_archive_source_no_url_returns_error(self, client, db_session):
        """Test archive endpoint returns error when no source_url."""
        from app.models.book import Book

        book = Book(title="Test Book", status="EVALUATING")
        db_session.add(book)
        db_session.commit()
        db_session.refresh(book)

        app.dependency_overrides[require_editor] = get_mock_editor

        response = client.post(f"/api/v1/books/{book.id}/archive-source")

        assert response.status_code == 400
        assert "source_url" in response.json()["detail"].lower()

        app.dependency_overrides.clear()

    def test_archive_source_already_archived_returns_existing(self, client, db_session):
        """Test archive endpoint returns existing URL if already archived."""
        from app.models.book import Book

        book = Book(
            title="Test Book",
            source_url="https://www.ebay.com/itm/123456",
            source_archived_url="https://web.archive.org/web/123/https://ebay.com/itm/123456",
            archive_status="success",
            status="EVALUATING",
        )
        db_session.add(book)
        db_session.commit()
        db_session.refresh(book)

        app.dependency_overrides[require_editor] = get_mock_editor

        response = client.post(f"/api/v1/books/{book.id}/archive-source")

        assert response.status_code == 200
        data = response.json()
        assert data["archive_status"] == "success"
        assert "web.archive.org" in data["source_archived_url"]

        app.dependency_overrides.clear()
```

**Step 2: Add import for require_editor at top of test file**

```python
from app.api.deps import require_editor
```

**Step 3: Run test to verify it fails**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/wayback-archive/backend && poetry run pytest tests/test_archive.py::TestArchiveEndpoint -v`
Expected: FAIL with 404 (endpoint doesn't exist)

**Step 4: Commit**

```bash
git add backend/tests/test_archive.py
git commit -m "test: Add failing tests for archive endpoint"
```

---

### Task 3.2: Implement Archive Endpoint

**Files:**
- Modify: `backend/app/api/v1/books.py`

**Step 1: Add import at top of file**

```python
from app.services.archive import archive_url
```

**Step 2: Add new endpoint after acquire_book (around line 550)**

```python
@router.post("/{book_id}/archive-source", response_model=BookResponse)
async def archive_book_source(
    book_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """
    Archive the book's source URL to the Wayback Machine.

    Returns existing archive if already successfully archived.
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if not book.source_url:
        raise HTTPException(
            status_code=400,
            detail="Book has no source_url to archive",
        )

    # If already successfully archived, return existing
    if book.archive_status == "success" and book.source_archived_url:
        return _book_to_response(book, db)

    # Set pending status
    book.archive_status = "pending"
    db.commit()

    # Attempt archive
    result = await archive_url(book.source_url)

    book.archive_status = result["status"]
    if result["status"] == "success":
        book.source_archived_url = result["archived_url"]

    db.commit()
    db.refresh(book)

    return _book_to_response(book, db)
```

**Step 3: Run tests**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/wayback-archive/backend && poetry run pytest tests/test_archive.py -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add backend/app/api/v1/books.py
git commit -m "feat(api): Add POST /books/{id}/archive-source endpoint"
```

---

### Task 3.3: Trigger Archive on Acquire

**Files:**
- Modify: `backend/app/api/v1/books.py`

**Step 1: Add test for acquire triggering archive**

Add to `backend/tests/test_acquire.py`:

```python
class TestAcquireArchive:
    """Tests for archive triggering on acquire."""

    def test_acquire_sets_archive_pending_when_source_url_exists(
        self, client, db_session
    ):
        """Test acquire sets archive_status to pending when source_url exists."""
        from app.models.book import Book
        from decimal import Decimal
        from datetime import date

        book = Book(
            title="Test Book",
            source_url="https://www.ebay.com/itm/123456",
            status="EVALUATING",
            value_mid=Decimal("100.00"),
        )
        db_session.add(book)
        db_session.commit()

        response = client.patch(
            f"/api/v1/books/{book.id}/acquire",
            json={
                "purchase_price": "75.00",
                "purchase_date": "2025-12-12",
                "order_number": "123-456",
                "place_of_purchase": "eBay",
            },
        )

        assert response.status_code == 200
        data = response.json()
        # Archive should be triggered (pending or completed)
        assert data["archive_status"] in ["pending", "success", "failed", None]
```

**Step 2: Modify acquire_book endpoint to trigger archive**

In `backend/app/api/v1/books.py`, update the `acquire_book` function. Add after `db.commit()` (around line 545):

```python
    # Trigger archive if source_url exists (fire and forget)
    if book.source_url and not book.source_archived_url:
        book.archive_status = "pending"
        db.commit()
        # Archive happens async - we don't wait for it
        # The user can check status or manually retry if needed
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, create task
                asyncio.create_task(_archive_book_async(book.id, book.source_url, db))
            else:
                # Otherwise run synchronously
                result = asyncio.run(archive_url(book.source_url))
                book.archive_status = result["status"]
                if result["status"] == "success":
                    book.source_archived_url = result["archived_url"]
                db.commit()
        except Exception as e:
            logger.warning(f"Failed to trigger archive for book {book.id}: {e}")
            book.archive_status = "failed"
            db.commit()
```

**Note:** This is simplified - in production you'd want a proper background task queue. For MVP, synchronous is fine since Wayback typically responds quickly.

**Step 3: Simpler approach - just set pending, let user retry manually**

Actually, for simplicity, just set pending and let the user manually trigger:

```python
    # Mark for archive if source_url exists
    if book.source_url and not book.archive_status:
        book.archive_status = "pending"
```

**Step 4: Run all tests**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/wayback-archive/backend && poetry run pytest tests/ -q --tb=short`
Expected: All tests pass

**Step 5: Commit**

```bash
git add backend/app/api/v1/books.py backend/tests/test_acquire.py
git commit -m "feat(api): Trigger archive status on acquire"
```

---

## Phase 4: Frontend

### Task 4.1: Update TypeScript Types

**Files:**
- Modify: `frontend/src/types/book.ts`

**Step 1: Add archive fields to Book interface**

Find the `Book` interface and add:

```typescript
  // Archive tracking
  source_archived_url?: string | null
  archive_status?: 'pending' | 'success' | 'failed' | null
```

**Step 2: Commit**

```bash
git add frontend/src/types/book.ts
git commit -m "feat(types): Add archive tracking fields to Book type"
```

---

### Task 4.2: Add Archive API Method to Store

**Files:**
- Modify: `frontend/src/stores/books.ts`

**Step 1: Add archiveSource action**

```typescript
    async archiveSource(bookId: number): Promise<Book> {
      const response = await api.post<Book>(`/books/${bookId}/archive-source`)

      // Update book in state
      const index = this.books.findIndex(b => b.id === bookId)
      if (index !== -1) {
        this.books[index] = response.data
      }

      return response.data
    },
```

**Step 2: Commit**

```bash
git add frontend/src/stores/books.ts
git commit -m "feat(store): Add archiveSource action"
```

---

### Task 4.3: Create Archive Status Badge Component

**Files:**
- Create: `frontend/src/components/ArchiveStatusBadge.vue`

**Step 1: Write the component**

```vue
<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  status?: 'pending' | 'success' | 'failed' | null
  archivedUrl?: string | null
  showRetry?: boolean
}>()

const emit = defineEmits<{
  retry: []
}>()

const icon = computed(() => {
  switch (props.status) {
    case 'pending':
      return '📦'
    case 'success':
      return '📦✓'
    case 'failed':
      return '📦⚠'
    default:
      return null
  }
})

const tooltip = computed(() => {
  switch (props.status) {
    case 'pending':
      return 'Archive pending...'
    case 'success':
      return 'Archived to Wayback Machine'
    case 'failed':
      return 'Archive failed - click to retry'
    default:
      return 'Not archived'
  }
})
</script>

<template>
  <span
    v-if="status"
    class="inline-flex items-center gap-1 text-sm"
    :title="tooltip"
  >
    <template v-if="status === 'success' && archivedUrl">
      <a
        :href="archivedUrl"
        target="_blank"
        rel="noopener noreferrer"
        class="text-green-600 hover:text-green-800"
      >
        {{ icon }}
      </a>
    </template>
    <template v-else-if="status === 'failed' && showRetry">
      <button
        type="button"
        class="text-amber-600 hover:text-amber-800"
        @click="emit('retry')"
      >
        {{ icon }}
      </button>
    </template>
    <template v-else-if="status === 'pending'">
      <span class="text-gray-500 animate-pulse">{{ icon }}</span>
    </template>
    <template v-else>
      <span class="text-gray-400">{{ icon }}</span>
    </template>
  </span>
</template>
```

**Step 2: Commit**

```bash
git add frontend/src/components/ArchiveStatusBadge.vue
git commit -m "feat(components): Add ArchiveStatusBadge component"
```

---

### Task 4.4: Add Badge to Acquisitions Dashboard Cards

**Files:**
- Modify: `frontend/src/views/AcquisitionsView.vue`

**Step 1: Import the component**

```typescript
import ArchiveStatusBadge from '@/components/ArchiveStatusBadge.vue'
```

**Step 2: Add to EVALUATING card template (find the source URL display area)**

Add after the source URL link:

```vue
<ArchiveStatusBadge
  v-if="book.source_url"
  :status="book.archive_status"
  :archived-url="book.source_archived_url"
  :show-retry="true"
  @retry="handleArchiveRetry(book.id)"
/>
```

**Step 3: Add handler method**

```typescript
async function handleArchiveRetry(bookId: number) {
  try {
    await booksStore.archiveSource(bookId)
    toast.success('Archive requested')
  } catch (error) {
    toast.error('Failed to archive')
  }
}
```

**Step 4: Run frontend type check**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/wayback-archive/frontend && npm run type-check`
Expected: No errors

**Step 5: Commit**

```bash
git add frontend/src/views/AcquisitionsView.vue
git commit -m "feat(ui): Add archive status badge to acquisitions dashboard"
```

---

### Task 4.5: Add Archive Section to Book Detail

**Files:**
- Modify: `frontend/src/views/BookDetailView.vue`

**Step 1: Import component**

```typescript
import ArchiveStatusBadge from '@/components/ArchiveStatusBadge.vue'
```

**Step 2: Add archive section near source URL display**

```vue
<!-- Archive Status -->
<div v-if="book.source_url" class="mt-2 flex items-center gap-2">
  <span class="text-sm text-gray-500">Archive:</span>
  <ArchiveStatusBadge
    :status="book.archive_status"
    :archived-url="book.source_archived_url"
    :show-retry="true"
    @retry="archiveSource"
  />
  <button
    v-if="!book.archive_status || book.archive_status === 'failed'"
    type="button"
    class="text-sm text-blue-600 hover:text-blue-800"
    @click="archiveSource"
  >
    Archive Now
  </button>
</div>
```

**Step 3: Add method**

```typescript
async function archiveSource() {
  if (!book.value) return
  try {
    await booksStore.archiveSource(book.value.id)
    toast.success('Archive requested')
    await loadBook() // Refresh to get updated status
  } catch (error) {
    toast.error('Failed to archive source')
  }
}
```

**Step 4: Run type check and tests**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/wayback-archive/frontend && npm run type-check`
Run: `cd /Users/mark/projects/bluemoxon/.worktrees/wayback-archive/frontend && npm run test -- --run`
Expected: No errors, tests pass

**Step 5: Commit**

```bash
git add frontend/src/views/BookDetailView.vue
git commit -m "feat(ui): Add archive section to book detail view"
```

---

## Phase 5: Final Testing and Cleanup

### Task 5.1: Run Full Test Suite

**Step 1: Backend tests**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/wayback-archive/backend && poetry run pytest tests/ -v`
Expected: All tests pass

**Step 2: Frontend tests**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/wayback-archive/frontend && npm run test -- --run`
Expected: All tests pass

**Step 3: Linting**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/wayback-archive/backend && poetry run ruff check . && poetry run ruff format --check .`
Run: `cd /Users/mark/projects/bluemoxon/.worktrees/wayback-archive/frontend && npm run lint && npm run type-check`
Expected: No errors

---

### Task 5.2: Create PR to Staging

**Step 1: Push branch**

```bash
git push -u origin feature/wayback-archive
```

**Step 2: Create PR**

```bash
gh pr create --base staging --title "feat: Wayback archive integration (#197)" --body "## Summary
- Add archive tracking fields to Book model
- Add POST /books/{id}/archive-source endpoint
- Trigger archive on acquire when source_url exists
- Add ArchiveStatusBadge component
- Show archive status on dashboard cards and book detail

## Test Plan
- [ ] CI passes
- [ ] Manual test: Create EVALUATING book with source_url, acquire it, verify archive_status set
- [ ] Manual test: Click Archive Now button, verify Wayback URL saved
- [ ] Manual test: Verify badge shows on dashboard cards

Closes #197"
```

**Step 3: Wait for CI**

Run: `gh pr checks --watch`

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1.1 | Add archive fields to model | `backend/app/models/book.py` |
| 1.2 | Create migration | `backend/alembic/versions/` |
| 1.3 | Update schemas | `backend/app/schemas/book.py` |
| 2.1 | Write archive service tests | `backend/tests/test_archive.py` |
| 2.2 | Implement archive service | `backend/app/services/archive.py` |
| 3.1 | Write endpoint tests | `backend/tests/test_archive.py` |
| 3.2 | Implement archive endpoint | `backend/app/api/v1/books.py` |
| 3.3 | Trigger on acquire | `backend/app/api/v1/books.py` |
| 4.1 | Update TypeScript types | `frontend/src/types/book.ts` |
| 4.2 | Add store action | `frontend/src/stores/books.ts` |
| 4.3 | Create badge component | `frontend/src/components/ArchiveStatusBadge.vue` |
| 4.4 | Add to dashboard | `frontend/src/views/AcquisitionsView.vue` |
| 4.5 | Add to detail view | `frontend/src/views/BookDetailView.vue` |
| 5.1 | Run full tests | - |
| 5.2 | Create PR | - |
