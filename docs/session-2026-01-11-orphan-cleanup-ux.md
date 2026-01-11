# Session: Orphan Cleanup UX Improvements

**Date:** 2026-01-11
**GitHub Issue:** #1057
**PRs:** #1058 (merged), #1059 (merged), #1061 (merged to prod)
**Branch:** `fix/1057-orphan-scan-details` (current fix in progress)
**Worktree:** `/Users/mark/projects/bluemoxon/.worktrees/feat-1057-orphan-cleanup-ux`
**Status:** Fix for flat S3 key format in progress

---

## CRITICAL INSTRUCTIONS FOR CONTINUATION

### MUST USE Superpowers Skills

**THIS IS NOT OPTIONAL. INVOKE BEFORE ANY ACTION.**

- `superpowers:using-superpowers` - ALWAYS at session start
- `superpowers:receiving-code-review` - When handling review feedback
- `superpowers:test-driven-development` - For all implementation
- `superpowers:systematic-debugging` - For any bugs or unexpected behavior
- `superpowers:verification-before-completion` - Before claiming work is done
- `superpowers:finishing-a-development-branch` - When ready to merge

### NEVER Use These (Permission Prompt Triggers)

```
FORBIDDEN - will cause permission prompts:
- # comment lines before commands
- \ backslash line continuations
- $(...) or $((...)) command substitution
- || or && chaining
- ! in quoted strings (bash history expansion)
```

### ALWAYS Use

```
REQUIRED patterns:
- Simple single-line commands only
- Separate sequential Bash tool calls instead of &&
- git -C <path> for git commands (not cd && git)
- bmx-api for all BlueMoxon API calls (no permission prompts)
```

**Example - WRONG:**
```bash
cd /path && git add file.py && git commit -m "msg"
```

**Example - CORRECT:**
```bash
git -C /path add file.py
```
Then separate call:
```bash
git -C /path commit -m "msg"
```

---

## Current Bug: Flat S3 Key Format Not Parsed

### Problem
Production shows 2472 orphans but `orphans_by_book` is empty and details table is empty.

### Root Cause (CONFIRMED)
Two S3 key formats exist:
1. **Nested (scraper imports):** `books/{book_id}/image_NN.webp` - WORKS
2. **Flat (manual uploads):** `books/{book_id}_{uuid}.ext` - FAILS to parse

The code only handled nested format:
```python
# OLD - only handles nested
folder_id = int(parts[1])  # "500" works, "10_uuid.jpg" fails with ValueError
```

### Fix Applied (NOT YET DEPLOYED)
File: `backend/lambdas/cleanup/handler.py` lines 161-183

```python
# NEW - handles both formats
try:
    # Try nested format first (parts[1] is just the book_id)
    folder_id = int(parts[1])
except ValueError:
    # Try flat format: extract book_id before underscore
    try:
        folder_id = int(parts[1].split("_")[0])
    except (ValueError, IndexError):
        continue
```

### Tests
All 40 cleanup tests pass with the fix.

---

## Next Steps

1. **Commit and push the fix:**
   ```bash
   git -C /Users/mark/projects/bluemoxon/.worktrees/feat-1057-orphan-cleanup-ux add backend/lambdas/cleanup/handler.py
   ```
   Then:
   ```bash
   git -C /Users/mark/projects/bluemoxon/.worktrees/feat-1057-orphan-cleanup-ux commit -m "fix: Handle both flat and nested S3 key formats in orphan grouping"
   ```

2. **Create PR to staging:**
   ```bash
   gh pr create --repo markthebest12/bluemoxon --base staging --head fix/1057-orphan-scan-details --title "fix: Handle both S3 key formats in orphan scan" --body "Fixes orphan scan details being empty for flat format keys (book_id_uuid.ext)"
   ```

3. **Wait for CI, merge, deploy to staging**

4. **Verify in staging:**
   ```bash
   bmx-api GET /admin/cleanup/orphans/scan
   ```
   Should return populated `orphans_by_book` for ALL orphans (both formats)

5. **Promote to production:**
   ```bash
   gh pr create --base main --head staging --title "chore: Promote staging to production"
   ```

---

## Completed Work

### PR #1058 - Main Feature (MERGED)
- Full orphan cleanup UX with size display, progress tracking
- Batch delete using S3 `delete_objects` API
- Concurrent job prevention (409 Conflict)
- Lambda timeout detection
- Background job with progress updates

### PR #1059 - Bug Fix (MERGED)
- Lambda handler wasn't passing through `total_bytes` and `orphans_by_book`
- Added pass-through in `_async_handler`

### PR #1061 - Production Promotion (MERGED)
- Promoted #1058 and #1059 to production

---

## Code Review Fixes Applied (from #1058)

| Fix | Issue | Solution |
|-----|-------|----------|
| 1 | Race condition: stale scan data | Lambda updates totals from fresh scan at job start |
| 2 | No concurrent job prevention | Returns 409 Conflict if pending/running job exists |
| 3 | Lambda timeout (3609 serial calls) | Uses `delete_objects` batch API (4 calls for 3609 items) |
| 4 | DB connection held during S3 scan | Phased approach: acquire/release per operation |
| 5 | Deprecated `datetime.utcnow()` | Changed to `datetime.now(UTC)` |
| 6 | Frontend swallows axios errors | Extracts `response.data.detail` for meaningful messages |
| 7 | No partial progress tracking | Tracks `failed_count` from delete_objects Errors array |
| 8 | Lambda cold start detection | Status endpoint marks jobs pending >5min as failed |

---

## Key Files

- `backend/lambdas/cleanup/handler.py` - Main cleanup logic (FIX IS HERE)
- `backend/app/api/v1/admin.py` - API endpoints for cleanup
- `backend/app/models/cleanup_job.py` - CleanupJob model
- `frontend/src/components/admin/OrphanCleanupPanel.vue` - Frontend UI
- `backend/tests/test_cleanup.py` - Tests (40 tests, all passing)

---

## S3 Key Format Reference

| Source | Format | Example | Environment |
|--------|--------|---------|-------------|
| Manual Upload | Flat | `books/10_abc123def.jpg` | Both |
| Scraper Import | Nested | `books/500/image_00.webp` | Both |

Both formats exist in both staging and production. The format is determined by how the image was added, not by environment.
