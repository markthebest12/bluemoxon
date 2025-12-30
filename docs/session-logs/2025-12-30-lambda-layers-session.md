# Lambda Layers & Cleanup Bug Fix Session Log

**Date:** 2025-12-30
**Branch:** `fix/cleanup-lambda-orphan-detection` (PR #686 targeting staging)
**Worktree:** `/Users/mark/projects/bluemoxon/.worktrees/feat-lambda-layers`
**PRs:** #684 (Lambda Layers), #685 (IAM fix), #686 (Cleanup Fix) - #684/#685 merged, #686 pending

---

## CRITICAL RULES - READ FIRST

### 1. ALWAYS Use Superpowers Skills
**IF A SKILL APPLIES TO YOUR TASK, YOU MUST USE IT. This is not negotiable.**

Before ANY action, check if a skill applies:
- `superpowers:brainstorming` - Before creative/feature work
- `superpowers:writing-plans` - Before multi-step implementation
- `superpowers:executing-plans` - When implementing a plan
- `superpowers:systematic-debugging` - For ANY bug or unexpected behavior
- `superpowers:test-driven-development` - Before writing ANY new code
- `superpowers:receiving-code-review` - When receiving code review feedback
- `superpowers:verification-before-completion` - Before claiming work is done
- `superpowers:finishing-a-development-branch` - When implementation complete

### 2. NEVER Use These Bash Patterns (Trigger Permission Prompts)
```bash
# BAD - NEVER DO:
# This is a comment before command    # Comments with #
aws lambda get-function \             # Backslash continuations
  --function-name foo
aws logs filter --start-time $(date)  # $(...) substitution
cd dir && npm install                 # && chaining
cd dir || exit 1                      # || chaining
--password 'Test1234!'                # ! in quoted strings
```

### 3. ALWAYS Use These Patterns Instead
```bash
# GOOD - Simple single-line commands:
aws lambda get-function --function-name foo
aws logs filter --start-time 1234567890

# Separate Bash tool calls for sequential commands (NOT &&)
# Call 1:
cd /path/to/dir
# Call 2:
npm install

# Use bmx-api for all API calls:
bmx-api GET /books
bmx-api --prod GET /health
```

---

## Current Status

**Phase:** FIX COMPLETE - PR #686 AWAITING CI/MERGE

### Summary

The cleanup Lambda bug fix is complete with all safety improvements implemented:

| Item | Status |
|------|--------|
| Root cause fix (prefix + key stripping) | Done |
| Enhanced dry run output | Done |
| orphans_by_prefix breakdown | Done |
| max_deletions guard (default 100) | Done |
| Explicit key format test | Done |
| All 33 tests passing | Verified |
| PR #686 created | Awaiting CI |
| S3 restore | In progress (~30-40%) |

---

## INCIDENT: Cleanup Lambda Deleted Valid Images

The cleanup Lambda's orphan detection had TWO critical bugs that caused it to delete ~6,900 valid S3 objects.

**Impact:**
- ~6,900 S3 objects deleted across all prefixes
- Frontend showing broken images for all books
- Staging environment data loss (recoverable via S3 versioning)

### Root Cause #1: Key Format Mismatch
```python
# S3 stores: "books/515/image_00.webp" (WITH prefix)
# DB stores: "515/image_00.webp" (WITHOUT prefix)

# OLD CODE - comparison NEVER matches:
orphaned_keys = s3_keys - db_keys  # ALL S3 keys appear orphaned!
```

### Root Cause #2: No Prefix Filter on S3 Listing
```python
# OLD CODE - lists ENTIRE bucket:
for page in paginator.paginate(Bucket=bucket):  # No Prefix!
```

---

## Fix Implementation (COMPLETE)

### File: `backend/lambdas/cleanup/handler.py`

```python
def cleanup_orphaned_images(
    db: Session,
    bucket: str,
    delete: bool = False,
    max_deletions: int = 100,      # NEW: Safety guard
    force_delete: bool = False,    # NEW: Override for bulk ops
) -> dict:
    S3_BOOKS_PREFIX = "books/"

    # FIX 1: Only list objects under books/ prefix
    for page in paginator.paginate(Bucket=bucket, Prefix=S3_BOOKS_PREFIX):
        # FIX 2: Strip prefix before comparing to DB keys
        stripped_key = full_key[len(S3_BOOKS_PREFIX):]

    # FIX 3: Group orphans by prefix for visibility
    orphans_by_prefix: dict[str, int] = {}
    for key in orphaned_full_keys:
        prefix = key.split("/")[0] + "/"
        orphans_by_prefix[prefix] = orphans_by_prefix.get(prefix, 0) + 1

    # FIX 4: Deletion guard
    deletion_limit = None if force_delete else max_deletions
    if deletion_limit is not None and deleted >= deletion_limit:
        break

    # Enhanced output for dry run review
    result = {
        "scan_prefix": S3_BOOKS_PREFIX,
        "total_objects_scanned": len(s3_keys_full),
        "objects_in_database": len(db_keys),
        "orphans_found": len(orphaned_full_keys),
        "orphans_by_prefix": orphans_by_prefix,
        "orphan_percentage": orphan_percentage,
        "sample_orphan_keys": list(orphaned_full_keys)[:10],
        "deleted": deleted,
    }
```

### Tests: `backend/tests/test_cleanup.py` (33 tests passing)

Key new tests:
- `test_key_format_s3_prefix_stripped_for_db_comparison` - Explicit regression test for key mismatch
- `test_max_deletions_guard_stops_at_limit` - Verifies deletion guard works
- `test_max_deletions_guard_allows_override` - Verifies force_delete override
- `test_warns_on_high_orphan_percentage` - Verifies warning on suspicious orphan rate
- `test_orphans_by_prefix` - Verifies prefix breakdown in output

---

## Next Steps

### Immediate
1. **Wait for CI on PR #686** - `gh pr checks 686`
2. **Wait for S3 restore to complete** - Check: `AWS_PROFILE=bmx-staging aws s3api list-object-versions --bucket bluemoxon-images-staging --query 'DeleteMarkers[?IsLatest==\`true\`] | length(@)'`

### After CI Passes
3. **Merge PR #686 to staging**
4. **Wait for staging deploy**
5. **Test cleanup Lambda dry-run** - Should find ~0 orphans

### After Staging Verified
6. **Promote to production** via staging->main PR
7. **Close incident** and update postmortem

---

## Verification Commands

```bash
# Check CI status
gh pr checks 686

# Check S3 restore progress (delete markers remaining)
AWS_PROFILE=bmx-staging aws s3api list-object-versions --bucket bluemoxon-images-staging --query 'DeleteMarkers[?IsLatest==`true`] | length(@)'

# Test image accessibility
curl -sI "https://staging.app.bluemoxon.com/book-images/books/10_352c23c2d6c94065b7af7aa87717f605.jpg" | head -3

# Run cleanup tests locally
cd /Users/mark/projects/bluemoxon/.worktrees/feat-lambda-layers/backend
poetry run pytest tests/test_cleanup.py -v
```

---

## Key Files Modified

| File | Change |
|------|--------|
| `backend/lambdas/cleanup/handler.py` | Prefix filter, key stripping, max_deletions guard, enhanced output |
| `backend/tests/test_cleanup.py` | 33 tests including regression tests for key format and deletion guard |
| `docs/postmortems/2025-12-30-cleanup-lambda-s3-deletion.md` | Full RCA (updated to use books/ prefix) |
| `docs/session-logs/2025-12-30-lambda-layers-session.md` | This file |

---

## Lambda Layers Status (COMPLETE)

The Lambda Layers feature that started this session is complete:
- PRs #684, #685 merged to staging
- Package size: 50MB -> 456KB (99% reduction)
- Layer ARN: `arn:aws:lambda:us-west-2:652617421195:layer:bluemoxon-staging-deps:2`

**DO NOT promote to production until cleanup bug fix (PR #686) is merged and verified.**

---

## Recovery Script Location

```bash
# Restore script (removes S3 delete markers)
/Users/mark/projects/bluemoxon/.worktrees/feat-lambda-layers/infra/terraform/.tmp/restore_all_s3.sh

# Log file
/tmp/restore_progress.log
```

---

## Postmortem Reference

Full RCA in: `docs/postmortems/2025-12-30-cleanup-lambda-s3-deletion.md`
