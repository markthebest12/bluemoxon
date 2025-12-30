# Lambda Layers & Cleanup Bug Fix Session Log

**Date:** 2025-12-30
**Branch:** `feat/lambda-layers` (merged to staging)
**Worktree:** `/Users/mark/projects/bluemoxon/.worktrees/feat-lambda-layers`
**PRs:** #684 (Lambda Layers), #685 (IAM fix) - Both merged to staging

---

## CRITICAL RULES - READ FIRST

### 1. ALWAYS Use Superpowers Skills
**IF A SKILL APPLIES TO YOUR TASK, YOU MUST USE IT. This is not negotiable.**

Before ANY action, check if a skill applies:
- `superpowers:brainstorming` - Before creative/feature work
- `superpowers:writing-plans` - Before multi-step implementation
- `superpowers:executing-plans` - When implementing a plan
- `superpowers:systematic-debugging` - For ANY bug or unexpected behavior
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

**Phase:** CRITICAL BUG FIX IN PROGRESS - S3 RESTORE RUNNING

### INCIDENT: Cleanup Lambda Deleted Valid Images

The cleanup Lambda's orphan detection had TWO critical bugs that caused it to delete ~6,900 valid S3 objects.

**Impact:**
- ~6,900 S3 objects deleted across all prefixes
- Frontend showing broken images for all books
- Staging environment data loss (recoverable via S3 versioning)

**Recovery Status:**
- S3 versioning enabled - recovery in progress
- Restore script running in background (PID 17846)
- ~800 delete markers remaining (was 6,858)
- Bug fix implemented and tests passing

---

## Root Cause Analysis

### Bug #1: Key Format Mismatch
```python
# S3 stores: "books/515/image_00.webp" (WITH prefix)
# DB stores: "515/image_00.webp" (WITHOUT prefix)

# OLD CODE - comparison NEVER matches:
orphaned_keys = s3_keys - db_keys  # ALL S3 keys appear orphaned!
```

### Bug #2: No Prefix Filter on S3 Listing
```python
# OLD CODE - lists ENTIRE bucket:
for page in paginator.paginate(Bucket=bucket):  # No Prefix!

# This included: books/, listings/, lambda/, prompts/, etc.
# All non-BookImage files automatically flagged as "orphans"
```

### Breakdown of Deleted Objects
| Prefix | Count |
|--------|-------|
| `books/` | 5,089 |
| `listings/` | 1,486 |
| `images/` | 300 |
| Other | 17 |
| **Total** | **~6,900** |

---

## Fix Implementation (DONE)

### File: `backend/lambdas/cleanup/handler.py`

```python
def cleanup_orphaned_images(db: Session, bucket: str, delete: bool = False) -> dict:
    S3_BOOKS_PREFIX = "books/"

    # FIX 1: Only list objects under books/ prefix
    for page in paginator.paginate(Bucket=bucket, Prefix=S3_BOOKS_PREFIX):
        for obj in page.get("Contents", []):
            full_key = obj["Key"]
            # FIX 2: Strip prefix before comparing to DB keys
            if full_key.startswith(S3_BOOKS_PREFIX):
                stripped_key = full_key[len(S3_BOOKS_PREFIX):]
                s3_keys_stripped.add(stripped_key)

    # Compare stripped keys to DB keys (now they match!)
    orphaned_stripped = s3_keys_stripped - db_keys

    # Convert back to full keys for deletion
    orphaned_full_keys = {f"{S3_BOOKS_PREFIX}{k}" for k in orphaned_stripped}
```

### Tests Updated: `backend/tests/test_cleanup.py`
- All tests now use real-world key formats (`books/` prefix in S3, no prefix in DB)
- Added `test_only_checks_books_prefix` to verify prefix filtering
- All 5 orphan tests passing

---

## Next Steps

### Immediate (In Progress)
1. **S3 restore completing** - check: `tail /tmp/restore_progress.log`
2. **Verify images visible** - check: `curl -sI "https://staging.app.bluemoxon.com/book-images/books/10_352c23c2d6c94065b7af7aa87717f605.jpg"`

### After Restore Complete
3. **Enhance dry run output** per postmortem (`docs/postmortems/2025-12-30-cleanup-lambda-s3-deletion.md`):
   - Add `scan_prefix`, `total_objects_scanned`, `objects_in_database`
   - Add `orphan_percentage` and warnings for >50%
   - Add `sample_orphan_keys` for sanity check
4. **Commit and push fix** to staging
5. **Test cleanup dry-run** - should find 0 orphans now
6. **Production promotion** - ONLY after staging verified

### Verification Commands
```bash
# Check restore progress
tail -10 /tmp/restore_progress.log

# Check remaining delete markers
AWS_PROFILE=bmx-staging aws s3api list-object-versions --bucket bluemoxon-images-staging --query 'DeleteMarkers[?IsLatest==`true`] | length(@)'

# Test image accessibility
curl -sI "https://staging.app.bluemoxon.com/book-images/books/10_352c23c2d6c94065b7af7aa87717f605.jpg" | head -3

# Check S3 object count
AWS_PROFILE=bmx-staging aws s3 ls s3://bluemoxon-images-staging/books/ --summarize | tail -3
```

---

## Key Files Modified

| File | Change |
|------|--------|
| `backend/lambdas/cleanup/handler.py` | Fixed prefix filter + key comparison |
| `backend/tests/test_cleanup.py` | Updated tests for real key formats |
| `docs/postmortems/2025-12-30-cleanup-lambda-s3-deletion.md` | Full RCA and fix plan |
| `docs/session-logs/2025-12-30-lambda-layers-session.md` | This file |

---

## Recovery Script Location

```bash
# Restore script (removes S3 delete markers)
/Users/mark/projects/bluemoxon/.worktrees/feat-lambda-layers/infra/terraform/.tmp/restore_all_s3.sh

# Log file
/tmp/restore_progress.log
```

---

## Lambda Layers Status (COMPLETE)

The Lambda Layers feature that started this session is complete:
- PRs #684, #685 merged to staging
- Package size: 50MB → 456KB (99% reduction)
- Layer ARN: `arn:aws:lambda:us-west-2:652617421195:layer:bluemoxon-staging-deps:2`

**DO NOT promote to production until cleanup bug is fixed and verified.**

---

## Postmortem Reference

Full RCA and enhanced fix details in:
`docs/postmortems/2025-12-30-cleanup-lambda-s3-deletion.md`

Key improvements still needed:
- Enhanced dry run output with context
- Warnings for high orphan percentage
- Sample keys in output for review
