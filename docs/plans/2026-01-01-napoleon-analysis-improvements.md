# Napoleon Analysis Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement 5 improvements from GH #743 identified during the analysis truncation fix session.

**Architecture:** Backend changes to model defaults and stale job handling in books.py, enhanced error messages in worker.py, custom CSS tooltip component in frontend (no new dependencies), documentation in OPERATIONS.md.

**Tech Stack:** Python/FastAPI, Vue 3/TypeScript, Tailwind CSS

---

## Task 1: Change Default Model to Opus

Change the default analysis model from `sonnet` to `opus` for both sync and async endpoints.

**Files:**
- Modify: `backend/app/api/v1/books.py:1577`
- Modify: `backend/app/api/v1/books.py:1956`
- Modify: `backend/app/schemas/analysis_job.py:12`
- Test: `backend/tests/test_books.py`

**Step 1: Write the failing test**

Add to `backend/tests/test_books.py`:

```python
class TestGenerateAnalysisDefaults:
    """Tests for analysis generation default values."""

    def test_sync_endpoint_defaults_to_opus(self, client, db_session):
        """Test that sync analysis generation defaults to opus model."""
        from app.api.v1.books import GenerateAnalysisRequest

        request = GenerateAnalysisRequest()
        assert request.model == "opus"

    def test_async_endpoint_defaults_to_opus(self, client, db_session):
        """Test that async analysis generation defaults to opus model."""
        from app.api.v1.books import GenerateAnalysisAsyncRequest

        request = GenerateAnalysisAsyncRequest()
        assert request.model == "opus"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/test_books.py::TestGenerateAnalysisDefaults -v`
Expected: FAIL with `AssertionError: assert 'sonnet' == 'opus'`

**Step 3: Write minimal implementation**

In `backend/app/api/v1/books.py`, change line 1577:
```python
# Before
model: Literal["sonnet", "opus"] = "sonnet"

# After
model: Literal["sonnet", "opus"] = "opus"
```

In `backend/app/api/v1/books.py`, change line 1956:
```python
# Before
model: Literal["sonnet", "opus"] = "sonnet"

# After
model: Literal["sonnet", "opus"] = "opus"
```

In `backend/app/schemas/analysis_job.py`, change line 12:
```python
# Before
model: str = "sonnet"

# After
model: str = "opus"
```

**Step 4: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/test_books.py::TestGenerateAnalysisDefaults -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `cd backend && poetry run pytest tests/test_books.py -v`
Expected: All tests pass

**Step 6: Commit**

```bash
git add backend/app/api/v1/books.py backend/app/schemas/analysis_job.py backend/tests/test_books.py
git commit -m "feat(analysis): change default model from sonnet to opus"
```

---

## Task 2: Auto-Cleanup Stale Jobs on Re-trigger

Add logic to auto-fail stale jobs before checking for active jobs in the async generation endpoint.

**Files:**
- Modify: `backend/app/api/v1/books.py:1982-1995`
- Test: `backend/tests/test_books.py`

**Step 1: Write the failing test**

Add to `backend/tests/test_books.py`:

```python
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4


class TestStaleJobAutoCleanup:
    """Tests for stale job auto-cleanup on re-trigger."""

    def test_stale_running_job_auto_failed_on_retrigger(self, client, db_session):
        """Test that stale running jobs are auto-failed when re-triggering analysis."""
        from app.models import AnalysisJob, Book

        # Create a book
        book = Book(title="Test Book")
        db_session.add(book)
        db_session.commit()

        # Create a stale running job (older than 15 minutes)
        stale_time = datetime.now(UTC) - timedelta(minutes=20)
        stale_job = AnalysisJob(
            id=uuid4(),
            book_id=book.id,
            status="running",
            model="opus",
            created_at=stale_time,
            updated_at=stale_time,
        )
        db_session.add(stale_job)
        db_session.commit()
        stale_job_id = stale_job.id

        # Mock SQS send to avoid actual queue interaction
        with patch("app.api.v1.books.send_analysis_job"):
            response = client.post(f"/api/v1/books/{book.id}/analysis/generate-async")

        # Should succeed (stale job auto-failed, new job created)
        assert response.status_code == 202

        # Verify stale job was marked as failed
        db_session.refresh(stale_job)
        assert stale_job.status == "failed"
        assert "timed out" in stale_job.error_message.lower()

    def test_fresh_running_job_blocks_retrigger(self, client, db_session):
        """Test that fresh running jobs still block re-triggering."""
        from app.models import AnalysisJob, Book

        # Create a book
        book = Book(title="Test Book")
        db_session.add(book)
        db_session.commit()

        # Create a fresh running job (less than 15 minutes old)
        fresh_time = datetime.now(UTC) - timedelta(minutes=5)
        fresh_job = AnalysisJob(
            id=uuid4(),
            book_id=book.id,
            status="running",
            model="opus",
            created_at=fresh_time,
            updated_at=fresh_time,
        )
        db_session.add(fresh_job)
        db_session.commit()

        response = client.post(f"/api/v1/books/{book.id}/analysis/generate-async")

        # Should return 409 conflict (fresh job still active)
        assert response.status_code == 409
        assert "already in progress" in response.json()["detail"].lower()
```

**Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/test_books.py::TestStaleJobAutoCleanup -v`
Expected: FAIL - `test_stale_running_job_auto_failed_on_retrigger` fails with 409 status

**Step 3: Write minimal implementation**

In `backend/app/api/v1/books.py`, add stale job cleanup before the active job check (around line 1982):

```python
@router.post("/{book_id}/analysis/generate-async", status_code=202)
def generate_analysis_async(
    book_id: int,
    request: GenerateAnalysisAsyncRequest = Body(default=GenerateAnalysisAsyncRequest()),
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    """Start async analysis generation using AWS Bedrock.

    Returns immediately with job ID. Poll /analysis/status for progress.
    Requires admin role.
    """
    from datetime import UTC, datetime, timedelta

    from sqlalchemy.exc import IntegrityError

    from app.models import AnalysisJob
    from app.schemas.analysis_job import AnalysisJobResponse
    from app.services.sqs import send_analysis_job

    # Verify book exists
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Auto-fail stale "running" jobs before checking for active jobs
    # This handles cases where previous worker Lambda timed out or crashed
    stale_threshold = datetime.now(UTC) - timedelta(minutes=STALE_JOB_THRESHOLD_MINUTES)
    stale_jobs = (
        db.query(AnalysisJob)
        .filter(
            AnalysisJob.book_id == book_id,
            AnalysisJob.status == "running",
            AnalysisJob.updated_at < stale_threshold,
        )
        .all()
    )
    for stale_job in stale_jobs:
        stale_job.status = "failed"
        stale_job.error_message = (
            f"Job timed out after {STALE_JOB_THRESHOLD_MINUTES} minutes "
            "(auto-cleanup on re-trigger)"
        )
        stale_job.updated_at = datetime.now(UTC)
    if stale_jobs:
        db.commit()

    # Check for existing active job (after cleanup)
    active_job = (
        db.query(AnalysisJob)
        .filter(
            AnalysisJob.book_id == book_id,
            AnalysisJob.status.in_(["pending", "running"]),
        )
        .first()
    )
    if active_job:
        raise HTTPException(
            status_code=409,
            detail="Analysis job already in progress for this book",
        )

    # ... rest of function unchanged
```

**Step 4: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/test_books.py::TestStaleJobAutoCleanup -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `cd backend && poetry run pytest tests/test_books.py -v`
Expected: All tests pass

**Step 6: Commit**

```bash
git add backend/app/api/v1/books.py backend/tests/test_books.py
git commit -m "feat(analysis): auto-fail stale jobs on re-trigger"
```

---

## Task 3: Improve Error Messages for Image Size Issues

Enhance error messages when Bedrock fails due to input being too large.

**Files:**
- Modify: `backend/app/worker.py:318-327`
- Test: `backend/tests/test_worker.py`

**Step 1: Write the failing test**

Create or add to `backend/tests/test_worker.py`:

```python
import pytest
from unittest.mock import MagicMock, patch


class TestWorkerErrorMessages:
    """Tests for worker error message formatting."""

    def test_input_too_long_error_includes_image_context(self):
        """Test that 'Input is too long' errors include image count and size guidance."""
        from botocore.exceptions import ClientError

        # Simulate Bedrock ValidationException for input too long
        error_response = {
            "Error": {
                "Code": "ValidationException",
                "Message": "Input is too long for requested model."
            }
        }
        bedrock_error = ClientError(error_response, "InvokeModel")

        # Import the helper function we'll create
        from app.worker import format_analysis_error

        # Mock context: 15 images
        formatted = format_analysis_error(bedrock_error, image_count=15)

        assert "15 images" in formatted
        assert "800px" in formatted.lower() or "resize" in formatted.lower()

    def test_other_errors_not_modified(self):
        """Test that non-input-length errors pass through unchanged."""
        from app.worker import format_analysis_error

        generic_error = Exception("Something else went wrong")
        formatted = format_analysis_error(generic_error, image_count=5)

        assert formatted == "Something else went wrong"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/test_worker.py::TestWorkerErrorMessages -v`
Expected: FAIL with `ImportError: cannot import name 'format_analysis_error'`

**Step 3: Write minimal implementation**

Add helper function near the top of `backend/app/worker.py` (after imports):

```python
def format_analysis_error(error: Exception, image_count: int = 0) -> str:
    """Format error message with helpful context for analysis failures.

    Enhances error messages for common issues like input size limits.
    """
    error_str = str(error)

    # Check for Bedrock input size limit errors
    if "Input is too long" in error_str or "ValidationException" in error_str:
        return (
            f"{error_str}. "
            f"This book has {image_count} images. "
            f"Try resizing images to 800px max dimension to reduce payload size."
        )

    return error_str
```

Then update the exception handler (around line 318-327):

```python
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}", exc_info=True)

        # Mark job as failed with enhanced error message
        if job:
            job.status = "failed"
            # Get image count for context
            image_count = db.query(BookImage).filter(BookImage.book_id == book_id).count()
            job.error_message = format_analysis_error(e, image_count)[:1000]
            job.updated_at = datetime.now(UTC)
            db.commit()

        raise
```

**Step 4: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/test_worker.py::TestWorkerErrorMessages -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `cd backend && poetry run pytest -v`
Expected: All tests pass

**Step 6: Commit**

```bash
git add backend/app/worker.py backend/tests/test_worker.py
git commit -m "feat(analysis): enhance error messages with image count and resize guidance"
```

---

## Task 4: Fix Warning Icon Hover Tooltip

Replace HTML `title` attribute with custom CSS tooltip for instant display and mobile support.

**Files:**
- Modify: `frontend/src/components/AnalysisIssuesWarning.vue`
- Create: `frontend/src/components/BaseTooltip.vue`
- Test: `frontend/src/components/__tests__/AnalysisIssuesWarning.spec.ts`

**Step 1: Create BaseTooltip component**

Create `frontend/src/components/BaseTooltip.vue`:

```vue
<script setup lang="ts">
import { ref } from "vue";

defineProps<{
  content: string;
  position?: "top" | "bottom" | "left" | "right";
}>();

const isVisible = ref(false);
</script>

<template>
  <div
    class="relative inline-block"
    @mouseenter="isVisible = true"
    @mouseleave="isVisible = false"
    @focus="isVisible = true"
    @blur="isVisible = false"
  >
    <slot />
    <div
      v-show="isVisible"
      role="tooltip"
      class="absolute z-50 px-2 py-1 text-xs text-white bg-gray-900 rounded shadow-lg whitespace-pre-line max-w-xs"
      :class="{
        'bottom-full left-1/2 -translate-x-1/2 mb-1': position === 'top' || !position,
        'top-full left-1/2 -translate-x-1/2 mt-1': position === 'bottom',
        'right-full top-1/2 -translate-y-1/2 mr-1': position === 'left',
        'left-full top-1/2 -translate-y-1/2 ml-1': position === 'right',
      }"
    >
      {{ content }}
      <div
        class="absolute w-2 h-2 bg-gray-900 transform rotate-45"
        :class="{
          'top-full left-1/2 -translate-x-1/2 -mt-1': position === 'top' || !position,
          'bottom-full left-1/2 -translate-x-1/2 -mb-1': position === 'bottom',
          'left-full top-1/2 -translate-y-1/2 -ml-1': position === 'left',
          'right-full top-1/2 -translate-y-1/2 -mr-1': position === 'right',
        }"
      />
    </div>
  </div>
</template>
```

**Step 2: Update AnalysisIssuesWarning to use tooltip**

Replace `frontend/src/components/AnalysisIssuesWarning.vue`:

```vue
<script setup lang="ts">
import { formatAnalysisIssues } from "@/composables/useFormatters";
import BaseTooltip from "./BaseTooltip.vue";

defineProps<{
  issues: string[] | null | undefined;
}>();
</script>

<template>
  <BaseTooltip
    v-if="issues?.length"
    :content="formatAnalysisIssues(issues)"
    position="top"
  >
    <span
      class="text-amber-500 cursor-help"
      role="img"
      aria-label="Analysis has issues"
    >
      ⚠️
    </span>
  </BaseTooltip>
</template>
```

**Step 3: Write test for tooltip behavior**

Create or update `frontend/src/components/__tests__/AnalysisIssuesWarning.spec.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import AnalysisIssuesWarning from "../AnalysisIssuesWarning.vue";

describe("AnalysisIssuesWarning", () => {
  it("renders nothing when issues is null", () => {
    const wrapper = mount(AnalysisIssuesWarning, {
      props: { issues: null },
    });
    expect(wrapper.text()).toBe("");
  });

  it("renders nothing when issues is empty array", () => {
    const wrapper = mount(AnalysisIssuesWarning, {
      props: { issues: [] },
    });
    expect(wrapper.text()).toBe("");
  });

  it("renders warning emoji when issues exist", () => {
    const wrapper = mount(AnalysisIssuesWarning, {
      props: { issues: ["truncated"] },
    });
    expect(wrapper.text()).toContain("⚠️");
  });

  it("shows tooltip on hover", async () => {
    const wrapper = mount(AnalysisIssuesWarning, {
      props: { issues: ["truncated"] },
    });

    // Tooltip hidden initially
    expect(wrapper.find('[role="tooltip"]').isVisible()).toBe(false);

    // Trigger hover
    await wrapper.find(".relative").trigger("mouseenter");

    // Tooltip visible
    expect(wrapper.find('[role="tooltip"]').isVisible()).toBe(true);
    expect(wrapper.find('[role="tooltip"]').text()).toContain("Truncated");
  });

  it("has correct aria attributes for accessibility", () => {
    const wrapper = mount(AnalysisIssuesWarning, {
      props: { issues: ["truncated"] },
    });
    const span = wrapper.find('[role="img"]');
    expect(span.attributes("aria-label")).toBe("Analysis has issues");
  });
});
```

**Step 4: Run tests**

Run: `cd frontend && npm run test:run -- src/components/__tests__/AnalysisIssuesWarning.spec.ts`
Expected: All tests pass

**Step 5: Verify lint and type-check**

Run: `cd frontend && npm run lint`
Run: `cd frontend && npm run type-check`
Expected: No errors

**Step 6: Commit**

```bash
git add frontend/src/components/BaseTooltip.vue frontend/src/components/AnalysisIssuesWarning.vue frontend/src/components/__tests__/AnalysisIssuesWarning.spec.ts
git commit -m "fix(frontend): replace HTML title with CSS tooltip for instant display"
```

---

## Task 5: Document Image Resize Thresholds

Add troubleshooting section to OPERATIONS.md with confirmed thresholds.

**Files:**
- Modify: `docs/OPERATIONS.md`

**Step 1: Add section to OPERATIONS.md**

Add before the final section of `docs/OPERATIONS.md`:

```markdown
## Analysis Troubleshooting

### Image Size Issues

When analysis jobs fail with "Input is too long" errors, the total base64 payload size exceeds Bedrock's input limit. This is caused by:
- Too many images
- Large image file sizes (high-quality JPEGs)

**Confirmed Working Thresholds:**

| Max Dimension | Max Images | Notes |
|---------------|------------|-------|
| 1600px | 12 | Works for low-quality JPEGs |
| 1200px | 16-18 | Works for moderate-quality JPEGs |
| 800px | 18-20 | **Reliable floor** - works regardless of JPEG quality |

**Root cause:** Base64 payload size matters more than pixel count. High-quality JPEGs (675KB-1.8MB per image) fail even at 1200px dimensions.

**Resolution workflow:**

1. Check image count: `bmx-api --prod GET "/books/{BOOK_ID}/images" | jq 'length'`

2. If > 12 images, resize to 800px:
   ```bash
   # Create temp directory
   mkdir -p .tmp/book{BOOK_ID}

   # Download images
   AWS_PROFILE=bmx-prod aws s3 cp s3://bluemoxon-images/books/ .tmp/book{BOOK_ID}/ --recursive --exclude "*" --include "{BOOK_ID}_*.jpeg"

   # Resize to 800px max dimension
   sips --resampleHeightWidthMax 800 .tmp/book{BOOK_ID}/*.jpeg

   # Upload back
   AWS_PROFILE=bmx-prod aws s3 cp .tmp/book{BOOK_ID}/ s3://bluemoxon-images/books/ --recursive --exclude "*" --include "{BOOK_ID}_*.jpeg"
   ```

3. Re-trigger analysis: `bmx-api --prod POST "/books/{BOOK_ID}/analysis/generate-async" '{"model": "opus"}'`

4. Verify success: `bmx-api --prod GET "/books/{BOOK_ID}" | jq '{id, analysis_issues}'`

### Stale Analysis Jobs

Jobs that show as "running" for more than 15 minutes are automatically marked as failed:
- On `GET /analysis/status` call
- On `POST /analysis/generate-async` re-trigger (allows immediate retry)

To check for stale jobs:
```bash
bmx-api --prod GET "/books/{BOOK_ID}/analysis/status"
```
```

**Step 2: Verify markdown is valid**

Review the file manually to ensure formatting is correct.

**Step 3: Commit**

```bash
git add docs/OPERATIONS.md
git commit -m "docs: add image resize thresholds and analysis troubleshooting"
```

---

## Final Steps

**Step 1: Run all backend tests**

Run: `cd backend && poetry run pytest -v`
Expected: All tests pass

**Step 2: Run all frontend tests**

Run: `cd frontend && npm run test:run`
Expected: All tests pass

**Step 3: Run linters**

Run: `cd backend && poetry run ruff check .`
Run: `cd backend && poetry run ruff format --check .`
Run: `cd frontend && npm run lint`
Run: `cd frontend && npm run type-check`
Expected: No errors

**Step 4: Create PR**

```bash
git push -u origin feat/napoleon-improvements
gh pr create --base staging --title "feat: Napoleon analysis improvements (#743)" --body "## Summary
- Change default model from sonnet to opus for both sync/async endpoints
- Auto-fail stale jobs on re-trigger (allows immediate retry)
- Enhance error messages with image count and resize guidance
- Replace HTML title tooltip with CSS tooltip (instant display, mobile support)
- Document image resize thresholds in operations runbook

## Test Plan
- [x] Backend tests pass
- [x] Frontend tests pass
- [x] Lint checks pass

Closes #743"
```

**Step 5: Watch CI**

Run: `gh pr checks --watch`
Expected: All CI checks pass
