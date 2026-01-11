# Session: Orphan Cleanup UX Improvements

**Date:** 2026-01-11
**GitHub Issue:** #1057
**PR:** #1058
**Branch:** `feat/1057-orphan-cleanup-ux`
**Worktree:** `/Users/mark/projects/bluemoxon/.worktrees/feat-1057-orphan-cleanup-ux`
**Status:** CI running, merge when passes

---

## CRITICAL INSTRUCTIONS FOR CONTINUATION

### MUST USE Superpowers Skills

**THIS IS NOT OPTIONAL. INVOKE BEFORE ANY ACTION.**

- `superpowers:using-superpowers` - ALWAYS at session start
- `superpowers:receiving-code-review` - When handling review feedback
- `superpowers:test-driven-development` - For all implementation
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

## Current Status

**CI is running on PR #1058.** When CI passes, merge with:
```bash
gh pr merge 1058 --squash --delete-branch
```

## Code Review Fixes Applied

User reviewed PR and identified 8 issues. All have been fixed:

| Fix | Issue | Solution | Commit |
|-----|-------|----------|--------|
| 1 | Race condition: stale scan data | Lambda updates totals from fresh scan at job start | 407de09 |
| 2 | No concurrent job prevention | Returns 409 Conflict if pending/running job exists | 407de09 |
| 3 | Lambda timeout (3609 serial calls) | Uses `delete_objects` batch API (4 calls for 3609 items) | 407de09 |
| 4 | DB connection held during S3 scan | Phased approach: acquire/release per operation | 407de09 |
| 5 | Deprecated `datetime.utcnow()` | Changed to `datetime.now(UTC)` | 407de09 |
| 6 | Frontend swallows axios errors | Extracts `response.data.detail` for meaningful messages | 407de09 |
| 7 | No partial progress tracking | Tracks `failed_count` from delete_objects Errors array | 407de09 |
| 8 | Lambda cold start detection | Status endpoint marks jobs pending >5min as failed | 407de09 |

### Additional Fixes Required by CI

| Fix | Issue | Solution | Commit |
|-----|-------|----------|--------|
| Migration chain | Multiple heads (branch) | Fixed down_revision in z0012345cdef | 139efb4 |
| Migration registration | Not in migration_sql.py | Added SQL constants and MIGRATIONS entries | 1d41184 |

## Files Changed (Code Review Fixes)

- `backend/lambdas/cleanup/handler.py` - Batch delete, phased DB connections, partial tracking
- `backend/app/models/cleanup_job.py` - Added failed_count, fixed datetime.utcnow()
- `backend/app/api/v1/admin.py` - Concurrent job prevention, timeout detection, failed_count in response
- `backend/app/db/migration_sql.py` - Registered new migrations
- `backend/alembic/versions/z0012345cdef_add_cleanup_jobs_table.py` - Fixed down_revision
- `backend/alembic/versions/z1012345efgh_add_failed_count_to_cleanup_jobs.py` - NEW migration
- `backend/tests/test_cleanup.py` - Updated tests for new batch delete implementation
- `frontend/src/components/admin/OrphanCleanupPanel.vue` - Fixed axios error extraction

## Next Steps After Merge

1. **Watch deploy to staging:**
   ```bash
   gh run list --workflow "Deploy to Staging" --limit 1
   gh run watch <run-id> --exit-status
   ```

2. **Run migration in staging:**
   ```bash
   bmx-api POST /health/migrate
   ```

3. **Integration test in staging:**
   - Navigate to Admin > Maintenance
   - Click "Scan for Orphans"
   - Verify count, size, cost displayed
   - Click "Delete All Orphans"
   - Verify confirmation appears
   - Confirm and watch progress

4. **Promote to production:**
   ```bash
   gh pr create --base main --head staging --title "chore: Promote staging to production"
   ```

## Problem Statement

Current orphan image cleanup has poor UX:
1. **Artificial batch limit of 100** - Forces clicking "Delete Orphans" ~36 times for 3,609 orphans
2. **No confirmation before destructive action** - Delete runs immediately
3. **Missing size information** - Only shows object count, not storage used

## Solution Design

Replace with comprehensive orphan management:
1. **Full scan results** - Count + size (KB/MB/GB) + monthly S3 cost (~$0.023/GB)
2. **Expandable details** - All orphans grouped by book (title if exists, folder ID if deleted)
3. **Inline confirmation** - Summary before delete (not modal)
4. **Background job** - Runs to completion even if user navigates away
5. **Real-time progress** - Progress bar with deleted/freed/saved running totals

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/cleanup/orphans/scan` | GET | Scan with sizes, grouped by book |
| `/admin/cleanup/orphans/delete` | POST | Start deletion job (202 + job_id), returns 409 if job running |
| `/admin/cleanup/jobs/{job_id}` | GET | Get job progress, detects timeout |

## Design Documents

- `docs/plans/2026-01-11-orphan-cleanup-ux-design.md` - Full design spec
- `docs/plans/2026-01-11-orphan-cleanup-ux-impl.md` - Implementation plan
