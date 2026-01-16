# Wayback Archive Design

**Date:** 2025-12-12
**Status:** Approved
**Issue:** #197

## Overview

Preserve eBay listing content after purchase by archiving to the Wayback Machine. Listings become unavailable after sale - this captures seller descriptions, photos, and condition notes for future reference.

## Decisions

| Decision | Choice |
|----------|--------|
| Archive timing | Auto on acquire + manual button |
| Archive method | Wayback Machine API |
| Failure handling | Warn user + queue for retry |
| Data storage | Two fields on Book table |
| Retry mechanism | Deferred to Cleanup Lambda (#189) |
| UI placement | Dashboard cards + detail page |

---

## Data Model

**New fields on `books` table:**

```sql
source_archived_url   VARCHAR(500)  -- Wayback URL when successful
archive_status        VARCHAR(20)   -- NULL, 'pending', 'success', 'failed'
```

**Status values:**

| Status | Meaning |
|--------|---------|
| `NULL` | No archive attempted (no source_url, or pre-feature books) |
| `pending` | Archive requested, awaiting confirmation |
| `success` | Archived, URL stored in `source_archived_url` |
| `failed` | Archive failed, queued for retry when #189 is built |

---

## API Design

### Modified Endpoint

```text
PATCH /books/{id}/acquire
```

- Existing endpoint, add side effect: trigger Wayback archive if `source_url` exists
- Archive happens async (don't block acquire response)
- Returns book with `archive_status: "pending"`

### New Endpoint

```text
POST /books/{id}/archive-source
```

- Manual trigger for archiving
- Request: `{}` (no body needed, uses existing `source_url`)
- Response: `{ "status": "pending" | "success" | "failed", "archived_url": "..." }`
- Idempotent: if already archived, returns existing URL

---

## Wayback Integration

**Archive flow:**

```text
1. Acquire triggered (or manual button)
2. Set archive_status = 'pending'
3. POST https://web.archive.org/save/{source_url}
4. If 200:
   - Parse archived URL from response headers
   - Set archive_status = 'success', source_archived_url = result
5. If error (429 rate limit, 502, timeout):
   - Set archive_status = 'failed'
   - Log error details
   - Return warning to frontend
```

**Rate limits:** ~15 requests/minute unauthenticated. Fine for acquisition volume.

**Archived URL format:**

```text
https://web.archive.org/web/20251212153000/https://www.ebay.com/itm/123
```

**Timeout:** 30 seconds. Mark as failed if exceeded.

---

## Frontend UI

### Acquisitions Dashboard Cards

```text
┌─────────────────────────────────────┐
│ Felix Holt, the Radical             │
│ George Eliot • 3 vols • $701        │
│ eBay ↗  📦 pending                  │
├─────────────────────────────────────┤
│ SCORE: 105  ████░░░░ CONDITIONAL    │
└─────────────────────────────────────┘
```

### Archive Status Icons

| Status | Display |
|--------|---------|
| `NULL` | (nothing) |
| `pending` | 📦 spinner |
| `success` | 📦✓ (clickable → Wayback URL) |
| `failed` | 📦⚠ (clickable → retry) |

### Book Detail Page

Source URL section shows:

- Link to original listing
- Link to archived version (if success)
- "Archive Now" button (if NULL or failed)
- Status badge

### Toast Notifications

- Success: "Listing archived"
- Failure: "Archive failed - you can retry from book details"

---

## Implementation Tasks

### Backend

1. Add migration: `source_archived_url`, `archive_status` columns
2. Update Book model and schemas
3. Create `archive_source()` service function (Wayback API call)
4. Add `POST /books/{id}/archive-source` endpoint
5. Modify `PATCH /books/{id}/acquire` to trigger archive
6. Add tests for archive service and endpoints

### Frontend

7. Update Book types with new fields
2. Add archive status badge component
3. Add badge to EVALUATING cards in dashboard
4. Add archive section to book detail page
5. Add "Archive Now" button with loading state
6. Add toast notifications for archive results

### Deferred to #189

- Retry failed archives in Cleanup Lambda

---

## Sequencing

Do #197 before #198. Wayback is simpler and pairs well with the eBay integration just deployed (Phase 4: #196).
