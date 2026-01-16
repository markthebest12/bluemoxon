# Orphan Cleanup UX Improvements - Design Document

**Date:** 2026-01-11
**Status:** Approved
**Author:** Claude + Mark

## Problem Statement

Current orphan image cleanup has poor UX:

1. **Artificial batch limit of 100** - Forces user to click "Delete Orphans" ~36 times to delete 3,609 orphans
2. **No confirmation before destructive action** - Delete button runs immediately
3. **Missing size information** - Only shows object count, not storage used or cost

## Solution Overview

Replace the current cleanup UI with a comprehensive orphan management experience:

1. Full scan results with size and cost information
2. Expandable details showing all orphans grouped by book
3. Inline confirmation before deletion
4. Background job with real-time progress tracking

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Size display | Fetch during scan | S3 `list_objects_v2` returns size, minimal overhead |
| Cost display | Show monthly S3 cost | ~$0.023/GB/month, helps quantify impact |
| Orphan grouping | By book (title if exists, folder ID if deleted) | Provides context for review |
| Confirmation | Inline expansion | Matches existing scoring box pattern |
| Delete execution | Backend job | Safe to navigate away, runs to completion |
| Progress | Real-time with percentage | Better UX for large deletions |
| Batch size | Internal only (500) | User doesn't need to see implementation detail |
| Dry run | Returns ALL orphans | Full data for informed decision |

## UI Design

### Scan Results (After "Scan Only" or initial state)

```
┌─────────────────────────────────────────────────────────────┐
│  ORPHAN SCAN RESULTS                                        │
│                                                             │
│  Found: 3,609 orphans                                       │
│  Size:  1.44 GB                                             │
│  Cost:  ~$0.03/month                                        │
│                                                             │
│  ▼ Show Details                                             │
└─────────────────────────────────────────────────────────────┘
```

### Expanded Details

```
┌─────────────────────────────────────────────────────────────┐
│  ▲ Hide Details                                             │
│                                                             │
│  A Christmas Carol (533)           12 orphans    4.8 MB     │
│  Pride and Prejudice (421)          8 orphans    3.2 MB     │
│  [Deleted Book] (folder 299)       45 orphans   18.0 MB     │
│  ...                                                        │
│  (scrollable list of ALL orphans grouped by book)           │
└─────────────────────────────────────────────────────────────┘
```

### Delete Confirmation (Inline Expansion)

```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️  CONFIRM DELETION                                       │
│                                                             │
│  This will permanently delete:                              │
│    • 3,609 orphaned images                                  │
│    • 1.44 GB of storage                                     │
│    • ~$0.03/month saved                                     │
│                                                             │
│  [ Cancel ]                    [ Confirm Delete ]           │
└─────────────────────────────────────────────────────────────┘
```

### Progress During Deletion

```
┌─────────────────────────────────────────────────────────────┐
│  DELETING ORPHANS                                           │
│                                                             │
│  [████████████░░░░░░░░░░░░░░░░░░░]  42%                     │
│                                                             │
│  Progress:  1,500 / 3,609 deleted                           │
│  Freed:     598 MB / 1.44 GB                                │
│  Saved:     ~$0.01 / $0.03 per month                        │
│                                                             │
│  (Safe to navigate away - job continues in background)      │
└─────────────────────────────────────────────────────────────┘
```

### Completion State

```
┌─────────────────────────────────────────────────────────────┐
│  ✓ CLEANUP COMPLETE                                         │
│                                                             │
│  Deleted:   3,609 orphaned images                           │
│  Freed:     1.44 GB                                         │
│  Savings:   ~$0.03/month                                    │
│                                                             │
│  [ Scan Again ]                                             │
└─────────────────────────────────────────────────────────────┘
```

## Technical Implementation

### Backend Changes

1. **Modify `cleanup_orphaned_images()` in `backend/lambdas/cleanup/handler.py`**
   - Return `Size` for each orphan from S3 scan
   - Return ALL orphan keys (remove 100 cap)
   - Group orphans by book folder with aggregated sizes
   - Resolve book IDs to titles where possible

2. **Add cleanup job infrastructure**
   - New job type: `cleanup`
   - Store progress in database (or Redis if available)
   - Progress fields: `total`, `completed`, `bytes_freed`

3. **New/modified endpoints**
   - `POST /admin/cleanup` - Now queues a job instead of running synchronously
   - `GET /admin/cleanup/status/{job_id}` - Returns progress percentage and stats
   - Response includes: `status`, `progress_pct`, `deleted`, `total`, `bytes_freed`, `bytes_total`

### Frontend Changes

1. **New component: `OrphanCleanupPanel.vue`**
   - Scan results display with count/size/cost
   - Expandable details list grouped by book
   - Inline confirmation expansion
   - Progress bar with real-time updates

2. **Utility: `formatBytes(bytes)` and `formatCost(bytes)`**
   - Human-readable size (KB/MB/GB based on magnitude)
   - Monthly S3 cost calculation (~$0.023/GB)

3. **Job polling integration**
   - Extend `useJobPolling` or create cleanup-specific polling
   - Handle navigate-away and return scenarios

### Data Structures

**Scan Response:**

```typescript
interface OrphanScanResult {
  total_count: number;
  total_bytes: number;
  orphans_by_book: {
    book_id: number | null;
    book_title: string | null;  // null if deleted
    folder_name: string;
    count: number;
    bytes: number;
    keys: string[];
  }[];
}
```

**Job Progress Response:**

```typescript
interface CleanupJobProgress {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress_pct: number;
  deleted: number;
  total: number;
  bytes_freed: number;
  bytes_total: number;
  error?: string;
}
```

## Size/Cost Formatting Rules

| Size Range | Display |
|------------|---------|
| < 1 KB | `{n} bytes` |
| < 1 MB | `{n} KB` |
| < 1 GB | `{n} MB` |
| >= 1 GB | `{n.nn} GB` |

**Cost calculation:** `bytes / (1024^3) * 0.023` displayed as `~${n.nn}/month`

## Migration Notes

- Remove `max_deletions` parameter from cleanup API (no longer needed)
- Keep `force_delete` parameter for backwards compatibility but deprecate
- Internal batch size of 500 for S3 delete operations

## Testing Considerations

- Mock S3 responses with various orphan counts and sizes
- Test progress polling with simulated slow deletions
- Test navigate-away and return behavior
- Test with 0 orphans (empty state)
- Test with very large orphan counts (10,000+)
