# Orphan Cleanup UX Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the 100-item batch limit with proper confirmation UX, size/cost display, and background job with progress tracking.

**Architecture:** Backend returns full orphan scan with sizes grouped by book, stores cleanup jobs in DB for progress tracking. Frontend displays scan results in expandable panel, polls for job progress during deletion.

**Tech Stack:** FastAPI, SQLAlchemy, Vue 3, TypeScript, S3, boto3

---

## Task 1: Backend - Add Size to Orphan Scan Response

**Files:**

- Modify: `backend/lambdas/cleanup/handler.py:98-196`
- Test: `backend/tests/test_cleanup.py`

**Step 1: Write the failing test**

Add to `backend/tests/test_cleanup.py`:

```python
class TestCleanupOrphanedImagesWithSize:
    """Tests for orphan scan with size information."""

    def test_scan_returns_size_per_orphan(self):
        """Test that scan returns size for each orphan."""
        # Mock S3 response with sizes
        mock_s3 = MagicMock()
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "books/123/image_00.webp", "Size": 102400},
                    {"Key": "books/123/image_01.webp", "Size": 204800},
                    {"Key": "books/456/image_00.webp", "Size": 51200},
                ]
            }
        ]

        with patch("backend.lambdas.cleanup.handler.boto3.client", return_value=mock_s3):
            with patch("backend.lambdas.cleanup.handler.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                # No images in DB = all are orphans
                mock_db.query.return_value.all.return_value = []

                result = cleanup_orphaned_images(mock_db, "test-bucket", delete=False)

        assert result["total_bytes"] == 358400  # 102400 + 204800 + 51200
        assert "orphans_by_book" in result
        assert len(result["orphans_by_book"]) == 2  # Two book folders

    def test_scan_groups_by_book_with_size(self):
        """Test that orphans are grouped by book folder with aggregated sizes."""
        mock_s3 = MagicMock()
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "books/123/image_00.webp", "Size": 100000},
                    {"Key": "books/123/image_01.webp", "Size": 200000},
                ]
            }
        ]

        with patch("backend.lambdas.cleanup.handler.boto3.client", return_value=mock_s3):
            with patch("backend.lambdas.cleanup.handler.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.all.return_value = []

                result = cleanup_orphaned_images(mock_db, "test-bucket", delete=False)

        book_group = result["orphans_by_book"][0]
        assert book_group["folder_id"] == 123
        assert book_group["count"] == 2
        assert book_group["bytes"] == 300000
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-1057-orphan-cleanup-ux/backend && poetry run pytest tests/test_cleanup.py::TestCleanupOrphanedImagesWithSize -v`

Expected: FAIL with KeyError or AssertionError (no total_bytes/orphans_by_book in current response)

**Step 3: Write minimal implementation**

Modify `cleanup_orphaned_images()` in `backend/lambdas/cleanup/handler.py`:

```python
def cleanup_orphaned_images(
    db: Session,
    bucket: str,
    delete: bool = False,
) -> dict:
    """Find and optionally delete orphaned images in S3.

    Returns full orphan details with sizes grouped by book folder.
    """
    s3 = boto3.client("s3")
    S3_BOOKS_PREFIX = "books/"

    # Collect all S3 objects with sizes
    s3_objects: dict[str, int] = {}  # key -> size in bytes
    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=bucket, Prefix=S3_BOOKS_PREFIX):
        for obj in page.get("Contents", []):
            s3_objects[obj["Key"]] = obj["Size"]

    # Get all image keys from database
    db_keys = {f"{S3_BOOKS_PREFIX}{key}" for (key,) in db.query(BookImage.s3_key).all() if key}

    # Find orphaned keys
    orphaned_keys = set(s3_objects.keys()) - db_keys

    # Group orphans by book folder
    orphans_by_book: dict[int, dict] = {}
    for key in orphaned_keys:
        # Extract book ID from path: books/123/image_00.webp -> 123
        parts = key.replace(S3_BOOKS_PREFIX, "").split("/")
        if len(parts) >= 2:
            try:
                folder_id = int(parts[0])
            except ValueError:
                folder_id = 0  # Non-numeric folder
        else:
            folder_id = 0

        if folder_id not in orphans_by_book:
            orphans_by_book[folder_id] = {
                "folder_id": folder_id,
                "book_id": None,
                "book_title": None,
                "count": 0,
                "bytes": 0,
                "keys": [],
            }

        orphans_by_book[folder_id]["count"] += 1
        orphans_by_book[folder_id]["bytes"] += s3_objects[key]
        orphans_by_book[folder_id]["keys"].append(key)

    # Resolve book titles where possible
    folder_ids = [fid for fid in orphans_by_book.keys() if fid > 0]
    if folder_ids:
        from app.models import Book
        books = db.query(Book.id, Book.title).filter(Book.id.in_(folder_ids)).all()
        book_map = {b.id: b.title for b in books}
        for folder_id, group in orphans_by_book.items():
            if folder_id in book_map:
                group["book_id"] = folder_id
                group["book_title"] = book_map[folder_id]

    # Calculate totals
    total_bytes = sum(s3_objects[k] for k in orphaned_keys)
    orphans_list = sorted(orphans_by_book.values(), key=lambda x: -x["bytes"])

    deleted = 0
    if delete:
        for key in orphaned_keys:
            s3.delete_object(Bucket=bucket, Key=key)
            deleted += 1

    return {
        "total_count": len(orphaned_keys),
        "total_bytes": total_bytes,
        "orphans_by_book": orphans_list,
        "deleted": deleted,
        # Legacy fields for backwards compatibility
        "found": len(orphaned_keys),
        "orphans_found": len(orphaned_keys),
    }
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-1057-orphan-cleanup-ux/backend && poetry run pytest tests/test_cleanup.py::TestCleanupOrphanedImagesWithSize -v`

Expected: PASS

**Step 5: Commit**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-1057-orphan-cleanup-ux
git add backend/lambdas/cleanup/handler.py backend/tests/test_cleanup.py
git commit -m "feat(cleanup): Add size info to orphan scan response"
```

---

## Task 2: Backend - Create CleanupJob Model

**Files:**

- Create: `backend/app/models/cleanup_job.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/xxxx_add_cleanup_jobs_table.py`
- Test: `backend/tests/test_cleanup_job_model.py`

**Step 1: Write the failing test**

Create `backend/tests/test_cleanup_job_model.py`:

```python
"""Tests for CleanupJob model."""

import uuid
from datetime import datetime, UTC

import pytest


class TestCleanupJobModel:
    """Tests for CleanupJob database model."""

    def test_create_cleanup_job(self, db_session):
        """Test creating a cleanup job."""
        from app.models.cleanup_job import CleanupJob

        job = CleanupJob(
            total_count=3609,
            total_bytes=1500000000,
        )
        db_session.add(job)
        db_session.commit()

        assert job.id is not None
        assert isinstance(job.id, uuid.UUID)
        assert job.status == "pending"
        assert job.total_count == 3609
        assert job.total_bytes == 1500000000
        assert job.deleted_count == 0
        assert job.deleted_bytes == 0
        assert job.created_at is not None

    def test_cleanup_job_progress(self, db_session):
        """Test updating cleanup job progress."""
        from app.models.cleanup_job import CleanupJob

        job = CleanupJob(total_count=100, total_bytes=1000000)
        db_session.add(job)
        db_session.commit()

        # Update progress
        job.status = "running"
        job.deleted_count = 50
        job.deleted_bytes = 500000
        db_session.commit()

        assert job.status == "running"
        assert job.deleted_count == 50
        assert job.progress_pct == 50.0

    def test_cleanup_job_completion(self, db_session):
        """Test completing a cleanup job."""
        from app.models.cleanup_job import CleanupJob

        job = CleanupJob(total_count=100, total_bytes=1000000)
        db_session.add(job)
        db_session.commit()

        job.status = "completed"
        job.deleted_count = 100
        job.deleted_bytes = 1000000
        job.completed_at = datetime.now(UTC)
        db_session.commit()

        assert job.status == "completed"
        assert job.completed_at is not None
        assert job.progress_pct == 100.0
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-1057-orphan-cleanup-ux/backend && poetry run pytest tests/test_cleanup_job_model.py -v`

Expected: FAIL with ModuleNotFoundError (no cleanup_job module)

**Step 3: Write minimal implementation**

Create `backend/app/models/cleanup_job.py`:

```python
"""Cleanup Job model for tracking async cleanup operations."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CleanupJob(Base):
    """Track async cleanup jobs with progress."""

    __tablename__ = "cleanup_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )  # pending, running, completed, failed

    # Totals from scan
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Progress
    deleted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deleted_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    @property
    def progress_pct(self) -> float:
        """Calculate progress percentage."""
        if self.total_count == 0:
            return 0.0
        return round(self.deleted_count / self.total_count * 100, 1)
```

Update `backend/app/models/__init__.py` to include CleanupJob.

**Step 4: Create migration**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-1057-orphan-cleanup-ux/backend && poetry run alembic revision --autogenerate -m "add_cleanup_jobs_table"`

**Step 5: Run test to verify it passes**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-1057-orphan-cleanup-ux/backend && poetry run pytest tests/test_cleanup_job_model.py -v`

Expected: PASS

**Step 6: Commit**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-1057-orphan-cleanup-ux
git add backend/app/models/cleanup_job.py backend/app/models/__init__.py backend/alembic/versions/ backend/tests/test_cleanup_job_model.py
git commit -m "feat(cleanup): Add CleanupJob model for progress tracking"
```

---

## Task 3: Backend - Add Cleanup Job API Endpoints

**Files:**

- Modify: `backend/app/api/v1/admin.py`
- Test: `backend/tests/api/v1/test_admin_cleanup.py`

**Step 1: Write the failing tests**

Add to `backend/tests/api/v1/test_admin_cleanup.py`:

```python
class TestOrphanScanEndpoint:
    """Tests for GET /admin/cleanup/orphans/scan endpoint."""

    def test_scan_returns_full_orphan_data(self, client: TestClient):
        """Test scan returns all orphans with sizes grouped by book."""
        with patch("app.api.v1.admin.boto3") as mock_boto3:
            mock_lambda = MagicMock()
            mock_boto3.client.return_value = mock_lambda
            mock_lambda.invoke.return_value = {
                "StatusCode": 200,
                "Payload": MagicMock(
                    read=lambda: json.dumps({
                        "total_count": 100,
                        "total_bytes": 50000000,
                        "orphans_by_book": [
                            {
                                "folder_id": 123,
                                "book_id": 123,
                                "book_title": "Test Book",
                                "count": 50,
                                "bytes": 25000000,
                                "keys": ["books/123/image_00.webp"],
                            }
                        ],
                    }).encode()
                ),
            }

            response = client.get("/api/v1/admin/cleanup/orphans/scan")

            assert response.status_code == 200
            data = response.json()
            assert data["total_count"] == 100
            assert data["total_bytes"] == 50000000
            assert len(data["orphans_by_book"]) == 1
            assert data["orphans_by_book"][0]["book_title"] == "Test Book"


class TestOrphanDeleteJobEndpoint:
    """Tests for POST /admin/cleanup/orphans/delete endpoint."""

    def test_delete_creates_job_and_returns_id(self, client: TestClient, db_session):
        """Test delete starts a job and returns job ID."""
        response = client.post(
            "/api/v1/admin/cleanup/orphans/delete",
            json={"total_count": 100, "total_bytes": 50000000},
        )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"


class TestCleanupJobStatusEndpoint:
    """Tests for GET /admin/cleanup/jobs/{job_id} endpoint."""

    def test_get_job_status(self, client: TestClient, db_session):
        """Test getting cleanup job status."""
        from app.models.cleanup_job import CleanupJob

        job = CleanupJob(total_count=100, total_bytes=50000000)
        job.status = "running"
        job.deleted_count = 50
        job.deleted_bytes = 25000000
        db_session.add(job)
        db_session.commit()

        response = client.get(f"/api/v1/admin/cleanup/jobs/{job.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["progress_pct"] == 50.0
        assert data["deleted_count"] == 50

    def test_get_nonexistent_job_returns_404(self, client: TestClient):
        """Test getting nonexistent job returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/admin/cleanup/jobs/{fake_id}")
        assert response.status_code == 404
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-1057-orphan-cleanup-ux/backend && poetry run pytest tests/api/v1/test_admin_cleanup.py::TestOrphanScanEndpoint -v`

Expected: FAIL with 404 (endpoint doesn't exist)

**Step 3: Write minimal implementation**

Add to `backend/app/api/v1/admin.py`:

```python
# Add new imports
from uuid import UUID
from app.models.cleanup_job import CleanupJob

# Add new Pydantic models
class OrphanGroup(BaseModel):
    """Group of orphans by book folder."""
    folder_id: int
    book_id: int | None
    book_title: str | None
    count: int
    bytes: int
    keys: list[str]


class OrphanScanResult(BaseModel):
    """Full orphan scan result."""
    total_count: int
    total_bytes: int
    orphans_by_book: list[OrphanGroup]


class DeleteJobRequest(BaseModel):
    """Request to start orphan deletion job."""
    total_count: int
    total_bytes: int


class DeleteJobResponse(BaseModel):
    """Response when starting deletion job."""
    job_id: UUID
    status: str


class CleanupJobStatus(BaseModel):
    """Cleanup job status response."""
    job_id: UUID
    status: str
    progress_pct: float
    total_count: int
    total_bytes: int
    deleted_count: int
    deleted_bytes: int
    error_message: str | None = None
    created_at: str
    completed_at: str | None = None


# Add new endpoints
@router.get("/cleanup/orphans/scan", response_model=OrphanScanResult)
def scan_orphans(_user=Depends(require_admin)):
    """Scan for orphaned images and return full details with sizes."""
    from app.config import get_settings

    settings = get_settings()
    lambda_client = boto3.client("lambda", region_name=settings.aws_region)

    payload = {
        "action": "orphans",
        "delete_orphans": False,
        "bucket": settings.images_bucket,
    }

    function_name = f"bluemoxon-{settings.environment}-cleanup"
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )

    result = json.loads(response["Payload"].read())

    if "error" in result:
        raise HTTPException(status_code=500, detail=f"Scan error: {result['error']}")

    return OrphanScanResult(
        total_count=result.get("total_count", result.get("found", 0)),
        total_bytes=result.get("total_bytes", 0),
        orphans_by_book=result.get("orphans_by_book", []),
    )


@router.post("/cleanup/orphans/delete", response_model=DeleteJobResponse, status_code=202)
def start_orphan_delete(
    request: DeleteJobRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Start background job to delete orphaned images."""
    job = CleanupJob(
        total_count=request.total_count,
        total_bytes=request.total_bytes,
    )
    db.add(job)
    db.commit()

    # TODO: Queue actual deletion work (Task 4)

    return DeleteJobResponse(job_id=job.id, status=job.status)


@router.get("/cleanup/jobs/{job_id}", response_model=CleanupJobStatus)
def get_cleanup_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Get cleanup job status and progress."""
    job = db.get(CleanupJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return CleanupJobStatus(
        job_id=job.id,
        status=job.status,
        progress_pct=job.progress_pct,
        total_count=job.total_count,
        total_bytes=job.total_bytes,
        deleted_count=job.deleted_count,
        deleted_bytes=job.deleted_bytes,
        error_message=job.error_message,
        created_at=job.created_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-1057-orphan-cleanup-ux/backend && poetry run pytest tests/api/v1/test_admin_cleanup.py -v`

Expected: PASS

**Step 5: Commit**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-1057-orphan-cleanup-ux
git add backend/app/api/v1/admin.py backend/tests/api/v1/test_admin_cleanup.py
git commit -m "feat(cleanup): Add orphan scan and job status endpoints"
```

---

## Task 4: Backend - Implement Background Deletion with Progress

**Files:**

- Modify: `backend/lambdas/cleanup/handler.py`
- Modify: `backend/app/api/v1/admin.py`
- Test: `backend/tests/test_cleanup.py`

**Step 1: Write the failing test**

Add to `backend/tests/test_cleanup.py`:

```python
class TestCleanupWithProgress:
    """Tests for cleanup with progress callback."""

    def test_delete_calls_progress_callback(self):
        """Test that deletion calls progress callback for each batch."""
        progress_calls = []

        def on_progress(deleted: int, deleted_bytes: int):
            progress_calls.append((deleted, deleted_bytes))

        # Mock S3 and run deletion with progress tracking
        # ... (implementation details)

        assert len(progress_calls) > 0
```

**Step 2-5: Implementation**

Modify cleanup Lambda to accept `job_id` parameter and update job progress in DB as it deletes batches.

The Lambda will:

1. Query CleanupJob by ID
2. Set status to "running"
3. Delete in batches of 500, updating job progress after each batch
4. Set status to "completed" when done

**Step 6: Commit**

```bash
git commit -m "feat(cleanup): Add progress tracking to deletion job"
```

---

## Task 5: Frontend - Add Format Utilities

**Files:**

- Create: `frontend/src/utils/format.ts`
- Test: `frontend/src/utils/__tests__/format.spec.ts`

**Step 1: Write the failing test**

Create `frontend/src/utils/__tests__/format.spec.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { formatBytes, formatCost } from '../format';

describe('formatBytes', () => {
  it('formats bytes correctly', () => {
    expect(formatBytes(500)).toBe('500 B');
    expect(formatBytes(1024)).toBe('1.0 KB');
    expect(formatBytes(1536)).toBe('1.5 KB');
    expect(formatBytes(1048576)).toBe('1.0 MB');
    expect(formatBytes(1073741824)).toBe('1.00 GB');
    expect(formatBytes(1500000000)).toBe('1.40 GB');
  });

  it('handles zero', () => {
    expect(formatBytes(0)).toBe('0 B');
  });
});

describe('formatCost', () => {
  it('calculates S3 monthly cost', () => {
    // 1 GB = $0.023/month
    expect(formatCost(1073741824)).toBe('~$0.02/month');
    // 10 GB
    expect(formatCost(10737418240)).toBe('~$0.23/month');
    // 100 GB
    expect(formatCost(107374182400)).toBe('~$2.30/month');
  });

  it('handles small sizes', () => {
    expect(formatCost(1000000)).toBe('~$0.00/month');
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-1057-orphan-cleanup-ux/frontend && npm run test -- --run src/utils/__tests__/format.spec.ts`

Expected: FAIL with module not found

**Step 3: Write minimal implementation**

Create `frontend/src/utils/format.ts`:

```typescript
/**
 * Format bytes to human-readable string.
 * Uses appropriate unit based on magnitude.
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  if (i === 0) return `${bytes} B`;
  if (i >= 3) {
    // GB and above: show 2 decimal places
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${units[i]}`;
  }
  // KB and MB: show 1 decimal place
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${units[i]}`;
}

/**
 * Calculate estimated monthly S3 storage cost.
 * S3 Standard: ~$0.023 per GB per month
 */
export function formatCost(bytes: number): string {
  const GB = 1024 * 1024 * 1024;
  const costPerGB = 0.023;
  const cost = (bytes / GB) * costPerGB;
  return `~$${cost.toFixed(2)}/month`;
}
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/mark/projects/bluemoxon/.worktrees/feat-1057-orphan-cleanup-ux/frontend && npm run test -- --run src/utils/__tests__/format.spec.ts`

Expected: PASS

**Step 5: Commit**

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-1057-orphan-cleanup-ux
git add frontend/src/utils/format.ts frontend/src/utils/__tests__/format.spec.ts
git commit -m "feat(frontend): Add formatBytes and formatCost utilities"
```

---

## Task 6: Frontend - Create OrphanCleanupPanel Component

**Files:**

- Create: `frontend/src/components/admin/OrphanCleanupPanel.vue`
- Test: `frontend/src/components/admin/__tests__/OrphanCleanupPanel.spec.ts`

**Step 1: Write the failing test**

Create `frontend/src/components/admin/__tests__/OrphanCleanupPanel.spec.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { nextTick } from 'vue';
import OrphanCleanupPanel from '../OrphanCleanupPanel.vue';
import { api } from '@/services/api';

vi.mock('@/services/api');

describe('OrphanCleanupPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders scan button initially', () => {
    const wrapper = mount(OrphanCleanupPanel);
    expect(wrapper.text()).toContain('Scan Only');
  });

  it('displays scan results after scanning', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        total_count: 3609,
        total_bytes: 1500000000,
        orphans_by_book: [
          {
            folder_id: 123,
            book_id: 123,
            book_title: 'Test Book',
            count: 100,
            bytes: 50000000,
            keys: [],
          },
        ],
      },
    });

    const wrapper = mount(OrphanCleanupPanel);
    await wrapper.find('[data-testid="scan-button"]').trigger('click');
    await nextTick();

    expect(wrapper.text()).toContain('3,609');
    expect(wrapper.text()).toContain('1.40 GB');
  });

  it('shows expandable details', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        total_count: 100,
        total_bytes: 50000000,
        orphans_by_book: [
          {
            folder_id: 123,
            book_id: 123,
            book_title: 'Test Book',
            count: 50,
            bytes: 25000000,
            keys: [],
          },
        ],
      },
    });

    const wrapper = mount(OrphanCleanupPanel);
    await wrapper.find('[data-testid="scan-button"]').trigger('click');
    await nextTick();

    // Initially collapsed
    expect(wrapper.find('[data-testid="orphan-details"]').exists()).toBe(false);

    // Click to expand
    await wrapper.find('[data-testid="show-details"]').trigger('click');
    expect(wrapper.find('[data-testid="orphan-details"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('Test Book');
  });
});
```

**Step 2-5: Implement component**

Create the Vue component with:

- Scan button that calls `/admin/cleanup/orphans/scan`
- Results display with count, size, cost
- Expandable details list grouped by book
- Delete button with inline confirmation
- Progress display during deletion
- Job polling for progress updates

**Step 6: Commit**

```bash
git commit -m "feat(frontend): Add OrphanCleanupPanel component"
```

---

## Task 7: Frontend - Integrate Component into AdminConfigView

**Files:**

- Modify: `frontend/src/views/AdminConfigView.vue`

**Step 1-5: Replace old cleanup UI with new component**

Replace the orphan section in AdminConfigView with the new OrphanCleanupPanel component.

**Step 6: Commit**

```bash
git commit -m "feat(frontend): Integrate OrphanCleanupPanel into AdminConfigView"
```

---

## Task 8: Frontend - Add Cleanup Job Polling

**Files:**

- Create: `frontend/src/composables/useCleanupJobPolling.ts`
- Test: `frontend/src/composables/__tests__/useCleanupJobPolling.spec.ts`

**Step 1: Write the failing test**

```typescript
import { describe, it, expect, vi } from 'vitest';
import { useCleanupJobPolling } from '../useCleanupJobPolling';

describe('useCleanupJobPolling', () => {
  it('polls for job status', async () => {
    // Test polling logic
  });

  it('stops polling when job completes', async () => {
    // Test completion handling
  });
});
```

**Step 2-5: Implement composable**

Similar to useJobPolling but for cleanup jobs with progress percentage.

**Step 6: Commit**

```bash
git commit -m "feat(frontend): Add useCleanupJobPolling composable"
```

---

## Task 9: Integration Testing

**Files:**

- Test manually in staging environment

**Steps:**

1. Deploy to staging
2. Navigate to Admin > Maintenance
3. Click "Scan Only" - verify full results with sizes
4. Expand details - verify all orphans listed grouped by book
5. Click "Delete Orphans" - verify confirmation appears
6. Confirm - verify progress bar updates
7. Navigate away and back - verify progress resumes/completes

---

## Task 10: Create PR to Staging

**Steps:**

1. Run all linters and tests
2. Push branch
3. Create PR targeting staging
4. Wait for CI
5. Request review

```bash
cd /Users/mark/projects/bluemoxon/.worktrees/feat-1057-orphan-cleanup-ux
poetry run ruff check backend/
poetry run ruff format --check backend/
npm run --prefix frontend lint
npm run --prefix frontend format
npm run --prefix frontend type-check
git push -u origin feat/1057-orphan-cleanup-ux
gh pr create --base staging --title "feat: Improve orphan cleanup UX with size display and progress tracking (#1057)" --body "..."
```
