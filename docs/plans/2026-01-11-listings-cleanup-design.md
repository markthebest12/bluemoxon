# Design: Stale Listings Cleanup

**Issue:** #1056
**Date:** 2026-01-11
**Status:** Approved

---

## Problem

The `listings/` S3 prefix accumulates orphaned images (~100MB in prod, growing):

1. User pastes eBay URL → scraper stores images in `listings/{item_id}/`
2. User either imports (images copied to `books/`) or abandons (closes modal)
3. Original `listings/` images are never cleaned up

There's no persistent "evaluation" state - listings exist only in S3 with no database tracking.

## Solution

Age-based cleanup: Delete all `listings/*` objects older than 30 days.

**Rationale:** If a listing hasn't been imported within 30 days, it was abandoned. No database cross-reference needed.

---

## API Design

### Scan Endpoint (Dry Run)

```
GET /api/v1/admin/cleanup/listings/scan?age_days=30
```

**Response:**

```json
{
  "total_count": 147,
  "total_bytes": 98234567,
  "age_threshold_days": 30,
  "listings_by_item": [
    {
      "item_id": "127576080517",
      "count": 15,
      "bytes": 4523000,
      "oldest": "2025-12-01T06:37:17Z"
    }
  ]
}
```

### Delete Endpoint

```
POST /api/v1/admin/cleanup/listings/delete
Body: {"age_days": 30}
```

**Response:**

```json
{
  "deleted_count": 147,
  "deleted_bytes": 98234567
}
```

---

## Core Logic

```python
def cleanup_stale_listings(
    bucket: str,
    age_days: int = 30,
    delete: bool = False,
) -> dict:
    """Find and optionally delete stale listing images.

    Args:
        bucket: S3 bucket name
        age_days: Delete objects older than this (default 30)
        delete: If True, delete. Otherwise dry run.

    Returns:
        Dict with count, bytes, grouped by item_id, deleted count
    """
```

**Algorithm:**

1. Paginate through `listings/` prefix using S3 `list_objects_v2`
2. For each object, check `LastModified` against cutoff date
3. If older than threshold → mark as stale
4. Group stale objects by `item_id` (extracted from key path)
5. If `delete=True`, batch delete using `delete_objects` API (1000 keys/call)

**Key characteristics:**

- No database interaction (S3-only)
- Per-file age check (not per-folder)
- Groups results by `item_id` for UI display

---

## UI Integration

Extend `OrphanCleanupPanel.vue` with a second card for listings cleanup:

```
┌─────────────────────────────────────────────────┐
│ Stale Listings Cleanup                          │
│                                                 │
│ ⚠ Stale Listings Found                         │
│ Files: 147    Size: 93.7 MB    Age: 30+ days   │
│                                                 │
│ ▸ Show Details                                  │
│   ├─ Listing 127576080517: 15 files (4.3 MB)   │
│   └─ ...                                        │
│                                                 │
│ [Delete Stale Listings]  [Cancel]              │
└─────────────────────────────────────────────────┘
```

**UX pattern:** Same as orphan cleanup (scan → review → confirm → delete)

---

## Error Handling

| Case | Behavior |
|------|----------|
| Empty `listings/` prefix | Return `total_count: 0`, no error |
| All listings recent | Return `total_count: 0` stale |
| Mixed old/new in same folder | Only delete old files |
| S3 partial failure | Track `failed_count`, complete with warning |

---

## Testing

### Unit Tests (`test_cleanup.py`)

1. `test_cleanup_stale_listings_finds_old_files`
2. `test_cleanup_stale_listings_keeps_recent_files`
3. `test_cleanup_stale_listings_mixed_ages_in_folder`
4. `test_cleanup_stale_listings_empty_prefix`
5. `test_cleanup_stale_listings_delete_mode`
6. `test_cleanup_stale_listings_groups_by_item_id`

### API Tests (`test_admin_cleanup.py`)

1. `test_listings_scan_endpoint`
2. `test_listings_delete_endpoint`
3. `test_listings_scan_custom_age`

**Mocking:** Mock `boto3.client("s3")` with fake responses including `LastModified` timestamps.

---

## Files to Modify

| File | Changes |
|------|---------|
| `backend/lambdas/cleanup/handler.py` | Add `cleanup_stale_listings()` function |
| `backend/app/api/v1/admin.py` | Add scan/delete endpoints |
| `backend/tests/test_cleanup.py` | Add unit tests |
| `backend/tests/api/v1/test_admin_cleanup.py` | Add API tests |
| `frontend/src/components/admin/OrphanCleanupPanel.vue` | Add listings cleanup UI |

---

## Out of Scope

- Progress tracking (dataset too small to need it)
- Database cross-reference (not needed for age-based approach)
- Configurable age in UI (hardcode 30 days, parameter for API flexibility)
