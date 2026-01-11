# Listings Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Maximize parallelism - Tasks 1-3 can run in parallel, Task 4 depends on 1-3.

**Goal:** Add age-based cleanup for stale `listings/` S3 images (30+ days old)

**Architecture:** New `cleanup_stale_listings()` function in cleanup handler, two API endpoints (scan/delete), UI card in OrphanCleanupPanel

**Tech Stack:** Python/FastAPI backend, Vue 3 frontend, boto3 S3, pytest

**Design Doc:** `docs/plans/2026-01-11-listings-cleanup-design.md`

---

## Parallelization Strategy

```
Task 1 (Backend Core)  ──┐
Task 2 (API Endpoints) ──┼──► Task 4 (Integration)
Task 3 (Frontend UI)   ──┘
```

- **Tasks 1, 2, 3:** Can run in parallel (no dependencies)
- **Task 4:** Depends on 1-3 completing

---

## Task 1: Backend Core Logic (cleanup handler)

**Files:**
- Modify: `backend/lambdas/cleanup/handler.py`
- Test: `backend/tests/test_cleanup.py`

### Step 1.1: Write failing tests for cleanup_stale_listings

Add to `backend/tests/test_cleanup.py`:

```python
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

# Add these tests after existing cleanup tests

class TestCleanupStaleListings:
    """Tests for cleanup_stale_listings function."""

    def test_finds_old_files(self):
        """Files older than threshold are identified as stale."""
        from backend.lambdas.cleanup.handler import cleanup_stale_listings

        old_date = datetime.now(UTC) - timedelta(days=45)

        mock_s3 = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "listings/123456/image_00.webp", "Size": 1000, "LastModified": old_date},
                    {"Key": "listings/123456/image_01.webp", "Size": 2000, "LastModified": old_date},
                ]
            }
        ]
        mock_s3.get_paginator.return_value = mock_paginator

        with patch("boto3.client", return_value=mock_s3):
            result = cleanup_stale_listings(bucket="test-bucket", age_days=30, delete=False)

        assert result["total_count"] == 2
        assert result["total_bytes"] == 3000

    def test_keeps_recent_files(self):
        """Files newer than threshold are not marked stale."""
        from backend.lambdas.cleanup.handler import cleanup_stale_listings

        recent_date = datetime.now(UTC) - timedelta(days=5)

        mock_s3 = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "listings/123456/image_00.webp", "Size": 1000, "LastModified": recent_date},
                ]
            }
        ]
        mock_s3.get_paginator.return_value = mock_paginator

        with patch("boto3.client", return_value=mock_s3):
            result = cleanup_stale_listings(bucket="test-bucket", age_days=30, delete=False)

        assert result["total_count"] == 0

    def test_mixed_ages_in_folder(self):
        """Only old files deleted from mixed-age folder."""
        from backend.lambdas.cleanup.handler import cleanup_stale_listings

        old_date = datetime.now(UTC) - timedelta(days=45)
        recent_date = datetime.now(UTC) - timedelta(days=5)

        mock_s3 = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "listings/123456/image_00.webp", "Size": 1000, "LastModified": old_date},
                    {"Key": "listings/123456/image_01.webp", "Size": 2000, "LastModified": recent_date},
                ]
            }
        ]
        mock_s3.get_paginator.return_value = mock_paginator

        with patch("boto3.client", return_value=mock_s3):
            result = cleanup_stale_listings(bucket="test-bucket", age_days=30, delete=False)

        assert result["total_count"] == 1
        assert result["total_bytes"] == 1000

    def test_empty_prefix(self):
        """Empty listings prefix returns zero count."""
        from backend.lambdas.cleanup.handler import cleanup_stale_listings

        mock_s3 = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Contents": []}]
        mock_s3.get_paginator.return_value = mock_paginator

        with patch("boto3.client", return_value=mock_s3):
            result = cleanup_stale_listings(bucket="test-bucket", age_days=30, delete=False)

        assert result["total_count"] == 0
        assert result["total_bytes"] == 0

    def test_groups_by_item_id(self):
        """Results are grouped by item_id."""
        from backend.lambdas.cleanup.handler import cleanup_stale_listings

        old_date = datetime.now(UTC) - timedelta(days=45)

        mock_s3 = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "listings/111111/image_00.webp", "Size": 1000, "LastModified": old_date},
                    {"Key": "listings/222222/image_00.webp", "Size": 2000, "LastModified": old_date},
                    {"Key": "listings/222222/image_01.webp", "Size": 3000, "LastModified": old_date},
                ]
            }
        ]
        mock_s3.get_paginator.return_value = mock_paginator

        with patch("boto3.client", return_value=mock_s3):
            result = cleanup_stale_listings(bucket="test-bucket", age_days=30, delete=False)

        assert len(result["listings_by_item"]) == 2

        item_111111 = next(i for i in result["listings_by_item"] if i["item_id"] == "111111")
        assert item_111111["count"] == 1
        assert item_111111["bytes"] == 1000

        item_222222 = next(i for i in result["listings_by_item"] if i["item_id"] == "222222")
        assert item_222222["count"] == 2
        assert item_222222["bytes"] == 5000

    def test_delete_mode(self):
        """Delete mode actually deletes files."""
        from backend.lambdas.cleanup.handler import cleanup_stale_listings

        old_date = datetime.now(UTC) - timedelta(days=45)

        mock_s3 = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "listings/123456/image_00.webp", "Size": 1000, "LastModified": old_date},
                    {"Key": "listings/123456/image_01.webp", "Size": 2000, "LastModified": old_date},
                ]
            }
        ]
        mock_s3.get_paginator.return_value = mock_paginator
        mock_s3.delete_objects.return_value = {
            "Deleted": [{"Key": "listings/123456/image_00.webp"}, {"Key": "listings/123456/image_01.webp"}],
            "Errors": [],
        }

        with patch("boto3.client", return_value=mock_s3):
            result = cleanup_stale_listings(bucket="test-bucket", age_days=30, delete=True)

        assert result["deleted_count"] == 2
        mock_s3.delete_objects.assert_called_once()
```

Run: `poetry run pytest backend/tests/test_cleanup.py::TestCleanupStaleListings -v`
Expected: FAIL (function not defined)

### Step 1.2: Implement cleanup_stale_listings

Add to `backend/lambdas/cleanup/handler.py` after the `cleanup_orphaned_images_with_progress` function:

```python
def cleanup_stale_listings(
    bucket: str,
    age_days: int = 30,
    delete: bool = False,
) -> dict:
    """Find and optionally delete stale listing images.

    Scans the listings/ S3 prefix and identifies objects older than
    the specified age threshold. No database interaction needed.

    Args:
        bucket: S3 bucket name
        age_days: Delete objects older than this many days (default 30)
        delete: If True, delete stale objects. Otherwise dry run.

    Returns:
        Dict with:
        - total_count: number of stale objects
        - total_bytes: total size of stale objects
        - age_threshold_days: the threshold used
        - listings_by_item: list of groups with item_id, count, bytes, oldest
        - deleted_count: number deleted (0 if delete=False)
    """
    s3 = boto3.client("s3")
    S3_LISTINGS_PREFIX = "listings/"
    S3_DELETE_BATCH_SIZE = 1000

    cutoff_date = datetime.now(UTC) - timedelta(days=age_days)

    # Scan listings/ prefix
    paginator = s3.get_paginator("list_objects_v2")
    stale_keys: list[tuple[str, int, datetime]] = []  # (key, size, last_modified)

    for page in paginator.paginate(Bucket=bucket, Prefix=S3_LISTINGS_PREFIX):
        for obj in page.get("Contents", []):
            last_modified = obj["LastModified"]
            # Ensure timezone-aware comparison
            if last_modified.tzinfo is None:
                last_modified = last_modified.replace(tzinfo=UTC)

            if last_modified < cutoff_date:
                stale_keys.append((obj["Key"], obj.get("Size", 0), last_modified))

    # Group by item_id
    items_map: dict[str, list[tuple[str, int, datetime]]] = {}
    for key, size, last_modified in stale_keys:
        # Extract item_id from path: listings/{item_id}/filename
        parts = key.split("/")
        if len(parts) >= 2:
            item_id = parts[1]
            if item_id not in items_map:
                items_map[item_id] = []
            items_map[item_id].append((key, size, last_modified))

    # Build listings_by_item response
    listings_by_item = []
    for item_id in sorted(items_map.keys()):
        items = items_map[item_id]
        item_bytes = sum(size for _, size, _ in items)
        oldest = min(lm for _, _, lm in items)
        listings_by_item.append({
            "item_id": item_id,
            "count": len(items),
            "bytes": item_bytes,
            "oldest": oldest.isoformat(),
        })

    total_count = len(stale_keys)
    total_bytes = sum(size for _, size, _ in stale_keys)

    # Delete if requested
    deleted_count = 0
    if delete and stale_keys:
        all_keys = [key for key, _, _ in stale_keys]

        # Batch delete (max 1000 per call)
        for i in range(0, len(all_keys), S3_DELETE_BATCH_SIZE):
            batch = all_keys[i:i + S3_DELETE_BATCH_SIZE]
            delete_request = {"Objects": [{"Key": k} for k in batch], "Quiet": False}
            response = s3.delete_objects(Bucket=bucket, Delete=delete_request)
            deleted_count += len(response.get("Deleted", []))

    return {
        "total_count": total_count,
        "total_bytes": total_bytes,
        "age_threshold_days": age_days,
        "listings_by_item": listings_by_item,
        "deleted_count": deleted_count,
    }
```

Run: `poetry run pytest backend/tests/test_cleanup.py::TestCleanupStaleListings -v`
Expected: PASS (all 6 tests)

### Step 1.3: Commit

```bash
git add backend/lambdas/cleanup/handler.py backend/tests/test_cleanup.py
git commit -m "feat(cleanup): Add cleanup_stale_listings function

Scans listings/ S3 prefix and identifies objects older than threshold.
Groups results by item_id for UI display. Supports dry-run and delete modes.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 2: API Endpoints

**Files:**
- Modify: `backend/app/api/v1/admin.py`
- Test: `backend/tests/api/v1/test_admin_cleanup.py`

### Step 2.1: Write failing API tests

Add to `backend/tests/api/v1/test_admin_cleanup.py`:

```python
class TestListingsCleanupEndpoints:
    """Tests for listings cleanup API endpoints."""

    def test_listings_scan_endpoint(self, client, mock_editor_auth):
        """Scan endpoint returns stale listings info."""
        with patch("backend.lambdas.cleanup.handler.cleanup_stale_listings") as mock_cleanup:
            mock_cleanup.return_value = {
                "total_count": 10,
                "total_bytes": 5000,
                "age_threshold_days": 30,
                "listings_by_item": [{"item_id": "123", "count": 10, "bytes": 5000, "oldest": "2025-12-01T00:00:00+00:00"}],
                "deleted_count": 0,
            }

            response = client.get("/api/v1/admin/cleanup/listings/scan")

            assert response.status_code == 200
            data = response.json()
            assert data["total_count"] == 10
            assert data["total_bytes"] == 5000
            assert len(data["listings_by_item"]) == 1

    def test_listings_scan_custom_age(self, client, mock_editor_auth):
        """Scan endpoint accepts age_days parameter."""
        with patch("backend.lambdas.cleanup.handler.cleanup_stale_listings") as mock_cleanup:
            mock_cleanup.return_value = {
                "total_count": 5,
                "total_bytes": 2500,
                "age_threshold_days": 60,
                "listings_by_item": [],
                "deleted_count": 0,
            }

            response = client.get("/api/v1/admin/cleanup/listings/scan?age_days=60")

            assert response.status_code == 200
            mock_cleanup.assert_called_once()
            call_kwargs = mock_cleanup.call_args[1]
            assert call_kwargs["age_days"] == 60

    def test_listings_delete_endpoint(self, client, mock_editor_auth):
        """Delete endpoint removes stale listings."""
        with patch("backend.lambdas.cleanup.handler.cleanup_stale_listings") as mock_cleanup:
            mock_cleanup.return_value = {
                "total_count": 10,
                "total_bytes": 5000,
                "age_threshold_days": 30,
                "listings_by_item": [],
                "deleted_count": 10,
            }

            response = client.post("/api/v1/admin/cleanup/listings/delete", json={"age_days": 30})

            assert response.status_code == 200
            data = response.json()
            assert data["deleted_count"] == 10
            mock_cleanup.assert_called_once()
            call_kwargs = mock_cleanup.call_args[1]
            assert call_kwargs["delete"] is True
```

Run: `poetry run pytest backend/tests/api/v1/test_admin_cleanup.py::TestListingsCleanupEndpoints -v`
Expected: FAIL (404 endpoints not found)

### Step 2.2: Implement API endpoints

Add to `backend/app/api/v1/admin.py`:

```python
from backend.lambdas.cleanup.handler import cleanup_stale_listings

# Add these endpoints in the admin router

@router.get("/cleanup/listings/scan")
async def scan_stale_listings(
    age_days: int = 30,
    _: dict = Depends(require_editor),
):
    """Scan for stale listing images (dry run).

    Returns count and size of listings older than age_days threshold.
    """
    bucket = get_images_bucket()
    result = cleanup_stale_listings(bucket=bucket, age_days=age_days, delete=False)
    return result


class ListingsDeleteRequest(BaseModel):
    age_days: int = 30


@router.post("/cleanup/listings/delete")
async def delete_stale_listings(
    request: ListingsDeleteRequest,
    _: dict = Depends(require_editor),
):
    """Delete stale listing images.

    Permanently removes listings older than age_days threshold.
    """
    bucket = get_images_bucket()
    result = cleanup_stale_listings(bucket=bucket, age_days=request.age_days, delete=True)
    return result
```

Run: `poetry run pytest backend/tests/api/v1/test_admin_cleanup.py::TestListingsCleanupEndpoints -v`
Expected: PASS (all 3 tests)

### Step 2.3: Commit

```bash
git add backend/app/api/v1/admin.py backend/tests/api/v1/test_admin_cleanup.py
git commit -m "feat(api): Add listings cleanup scan/delete endpoints

GET /admin/cleanup/listings/scan - dry run scan
POST /admin/cleanup/listings/delete - delete stale listings

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Frontend UI

**Files:**
- Modify: `frontend/src/components/admin/OrphanCleanupPanel.vue`
- Test: `frontend/src/components/admin/__tests__/OrphanCleanupPanel.spec.ts`

### Step 3.1: Add listings cleanup section to OrphanCleanupPanel

Extend `OrphanCleanupPanel.vue` to add a second card for listings cleanup. Add state, methods, and template section.

**Add to script setup (after existing orphan state):**

```typescript
// Listings cleanup state
const listingsScanning = ref(false)
const listingsScanResult = ref<{
  total_count: number
  total_bytes: number
  age_threshold_days: number
  listings_by_item: Array<{
    item_id: string
    count: number
    bytes: number
    oldest: string
  }>
} | null>(null)
const listingsDeleting = ref(false)
const listingsShowDetails = ref(false)
const listingsConfirmDelete = ref(false)
const listingsError = ref<string | null>(null)

async function scanListings() {
  listingsScanning.value = true
  listingsError.value = null
  listingsScanResult.value = null

  try {
    const response = await api.get('/admin/cleanup/listings/scan')
    listingsScanResult.value = response.data
  } catch (e) {
    listingsError.value = getErrorMessage(e, 'Failed to scan listings')
  } finally {
    listingsScanning.value = false
  }
}

async function deleteListings() {
  listingsDeleting.value = true
  listingsError.value = null

  try {
    await api.post('/admin/cleanup/listings/delete', { age_days: 30 })
    listingsScanResult.value = null
    listingsConfirmDelete.value = false
  } catch (e) {
    listingsError.value = getErrorMessage(e, 'Failed to delete listings')
  } finally {
    listingsDeleting.value = false
  }
}

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString()
}
```

**Add to template (after orphan cleanup card):**

```vue
<!-- Stale Listings Cleanup -->
<div class="card">
  <div class="card-header">
    <h3 class="card-title">Stale Listings Cleanup</h3>
  </div>
  <div class="card-body">
    <!-- Error -->
    <div v-if="listingsError" class="alert alert-error mb-4">
      {{ listingsError }}
    </div>

    <!-- No scan yet -->
    <div v-if="!listingsScanResult && !listingsScanning">
      <p class="text-gray-600 mb-4">
        Scan for listing images older than 30 days that were never imported.
      </p>
      <button class="btn-primary" @click="scanListings">
        Scan Listings
      </button>
    </div>

    <!-- Scanning -->
    <div v-else-if="listingsScanning" class="flex items-center gap-3">
      <div class="spinner"></div>
      <span>Scanning listings...</span>
    </div>

    <!-- Results -->
    <div v-else-if="listingsScanResult">
      <!-- Summary -->
      <div v-if="listingsScanResult.total_count === 0" class="alert alert-success">
        No stale listings found.
      </div>
      <div v-else class="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
        <div class="flex items-center gap-2 text-amber-800 font-medium mb-2">
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
          </svg>
          Stale Listings Found
        </div>
        <div class="flex gap-8 text-sm text-amber-700">
          <div>Files: <strong>{{ listingsScanResult.total_count }}</strong></div>
          <div>Size: <strong>{{ formatBytes(listingsScanResult.total_bytes) }}</strong></div>
          <div>Age: <strong>{{ listingsScanResult.age_threshold_days }}+ days</strong></div>
        </div>
      </div>

      <!-- Expandable Details -->
      <div v-if="listingsScanResult.total_count > 0">
        <button
          class="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-800 mb-3"
          @click="listingsShowDetails = !listingsShowDetails"
        >
          <svg
            class="w-4 h-4 transition-transform"
            :class="{ 'rotate-90': listingsShowDetails }"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd"/>
          </svg>
          {{ listingsShowDetails ? 'Hide' : 'Show' }} Details
        </button>

        <div v-if="listingsShowDetails" class="border rounded-lg overflow-hidden mb-4">
          <table class="w-full text-sm">
            <thead class="bg-gray-50">
              <tr>
                <th class="text-left px-4 py-2">Listing ID</th>
                <th class="text-right px-4 py-2">Files</th>
                <th class="text-right px-4 py-2">Size</th>
                <th class="text-right px-4 py-2">Oldest</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in listingsScanResult.listings_by_item" :key="item.item_id" class="border-t">
                <td class="px-4 py-2 font-mono text-xs">{{ item.item_id }}</td>
                <td class="text-right px-4 py-2">{{ item.count }}</td>
                <td class="text-right px-4 py-2">{{ formatBytes(item.bytes) }}</td>
                <td class="text-right px-4 py-2">{{ formatDate(item.oldest) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Delete Confirmation -->
        <div v-if="!listingsConfirmDelete" class="flex gap-3">
          <button class="btn-danger" @click="listingsConfirmDelete = true">
            Delete Stale Listings
          </button>
          <button class="btn-secondary" @click="listingsScanResult = null">
            Cancel
          </button>
        </div>
        <div v-else class="bg-red-50 border border-red-200 rounded-lg p-4">
          <p class="text-red-800 mb-3">
            This will permanently delete {{ listingsScanResult.total_count }} files
            ({{ formatBytes(listingsScanResult.total_bytes) }}). This cannot be undone.
          </p>
          <div class="flex gap-3">
            <button
              class="btn-danger"
              :disabled="listingsDeleting"
              @click="deleteListings"
            >
              {{ listingsDeleting ? 'Deleting...' : 'Confirm Delete' }}
            </button>
            <button
              class="btn-secondary"
              :disabled="listingsDeleting"
              @click="listingsConfirmDelete = false"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>

      <!-- Rescan button when no stale listings -->
      <div v-else class="mt-4">
        <button class="btn-secondary" @click="scanListings">
          Scan Again
        </button>
      </div>
    </div>
  </div>
</div>
```

### Step 3.2: Add tests for listings cleanup UI

Add to `frontend/src/components/admin/__tests__/OrphanCleanupPanel.spec.ts`:

```typescript
describe('Listings Cleanup', () => {
  it('shows scan button initially', async () => {
    const wrapper = mount(OrphanCleanupPanel)
    expect(wrapper.text()).toContain('Scan Listings')
  })

  it('shows results after scan', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        total_count: 10,
        total_bytes: 5000,
        age_threshold_days: 30,
        listings_by_item: [{ item_id: '123', count: 10, bytes: 5000, oldest: '2025-12-01T00:00:00Z' }]
      }
    })

    const wrapper = mount(OrphanCleanupPanel)
    await wrapper.find('button:contains("Scan Listings")').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Stale Listings Found')
    expect(wrapper.text()).toContain('Files: 10')
  })

  it('shows no stale listings message when count is 0', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        total_count: 0,
        total_bytes: 0,
        age_threshold_days: 30,
        listings_by_item: []
      }
    })

    const wrapper = mount(OrphanCleanupPanel)
    await wrapper.find('button:contains("Scan Listings")').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('No stale listings found')
  })
})
```

Run: `npm run --prefix frontend test -- --run OrphanCleanupPanel`
Expected: PASS

### Step 3.3: Commit

```bash
git add frontend/src/components/admin/OrphanCleanupPanel.vue frontend/src/components/admin/__tests__/OrphanCleanupPanel.spec.ts
git commit -m "feat(ui): Add listings cleanup to OrphanCleanupPanel

Adds scan/delete UI for stale listings with expandable details table.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Integration & Validation

**Depends on:** Tasks 1, 2, 3

### Step 4.1: Run full test suite

```bash
poetry run pytest backend/ -v
npm run --prefix frontend test -- --run
```

Expected: All tests pass

### Step 4.2: Run linters

```bash
poetry run ruff check backend/
poetry run ruff format --check backend/
npm run --prefix frontend lint
npm run --prefix frontend format
npm run --prefix frontend type-check
```

Expected: No errors

### Step 4.3: Final commit (if any lint fixes needed)

```bash
git add -A
git commit -m "chore: Fix lint issues

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

### Step 4.4: Create PR to staging

```bash
git push -u origin feat/1056-listings-cleanup
gh pr create --base staging --title "feat: Add listings/ directory cleanup to maintenance Lambda (#1056)" --body "## Summary
- Add \`cleanup_stale_listings()\` function to cleanup handler
- Add scan/delete API endpoints for listings cleanup
- Add UI card to OrphanCleanupPanel for listings cleanup

## Test Plan
- [ ] CI passes
- [ ] Manual test in staging: scan shows stale listings
- [ ] Manual test in staging: delete removes stale listings

Closes #1056"
```

---

## Session Log Updates

After each task, update `docs/session-2026-01-11-listings-cleanup.md` with progress.
