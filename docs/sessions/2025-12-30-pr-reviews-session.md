# PR Reviews Session Log

**Date:** 2025-12-30
**Session:** Code review of PRs #680, #682, #684, #686, #691

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
- `superpowers:requesting-code-review` - After completing significant code
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
bmx-api POST /admin/cleanup '{"action": "stale"}'
```

---

## PRs Reviewed

### PR #680: Entity Management UI Improvements

**Status:** APPROVED
**Changes:** Focus trapping, semantic status tokens, validation improvements

**Key Fixes Applied:**

- Created custom `useFocusTrap.ts` composable (avoids VueUse 7.x→14.x version conflict)
- Created custom `useDebounce.ts` composable
- Fixed error handling: DEV gets `console.error`, TEST silent, PROD gets `console.warn`
- Fixed Vue Set reactivity with full reassignment pattern

---

### PR #682: Cleanup Lambda

**Status:** APPROVED
**Changes:** New Lambda for database maintenance tasks

**Key Fixes Applied:**

- Async handler pattern: `asyncio.run(_async_handler(event))`
- S3 pagination with `get_paginator("list_objects_v2")`
- Direct `SessionLocal()` instead of `next(get_db())` for Lambda
- Batch limits: `EXPIRED_CHECK_BATCH_SIZE = 25`, `ARCHIVE_RETRY_BATCH_SIZE = 10`
- Transient error handling (Timeout/ConnectionError vs definitive 404/410)

---

### PR #684: Lambda Layers

**Status:** APPROVED
**Changes:** Separate Python dependencies into Lambda Layer (~50MB → <1MB code packages)

**Key Fixes Applied:**

1. **Race condition fixed:** Layer updated BEFORE code (old code + new layer = safe)
2. **Layer version reuse:** Conditional publish only when content changes
3. **Rollback support:** Captures state, prints recovery commands on failure
4. **Cleanup Lambda version publish:** Added for consistency

**Architecture:**

- `build-layer` job builds layer with poetry.lock hash caching
- `build-backend` copies only app code (no pip install)
- Deploy: update layer → wait → update code → wait → publish version

---

### PR #686: Cleanup Lambda Orphan Fix

**Status:** APPROVED WITH RESERVATIONS
**Changes:** Fix critical bug that deleted ~6,900 valid S3 objects

**Root Cause:**

1. No prefix filter on S3 listing (listed entire bucket)
2. Key format mismatch (S3: `books/123/img.jpg`, DB: `123/img.jpg`)

**Key Fixes Applied:**

- `books/` prefix filter on S3 listing
- Strip prefix before DB comparison
- `max_deletions` guard (default 100) with `force_delete` override
- `orphans_by_prefix` breakdown in output
- High orphan rate warning (>50%)
- Legacy `keys` field capped to 100 items

**Must Fix:**

- Align postmortem with actual implementation (`books/` not `images/`)
- Remove session log files from commits

---

### PR #691: Staging to Production Promotion

**Status:** IN REVIEW (session compacted)
**Changes:** 45 files, combines cleanup fix with Lambda Layers

**Concerns:**

- Very large PR (45 files, 5464 additions)
- Alembic revision IDs look fabricated (`u4567890stuv`, `v5678901uvwx`)
- Session logs still being committed

---

## Key Technical Patterns

### Lambda Async Handler Pattern

```python
def handler(event: dict, context) -> dict:
    return asyncio.run(_async_handler(event))

async def _async_handler(event: dict) -> dict:
    db = SessionLocal()  # Direct session, not generator
    try:
        # ... async operations
    finally:
        db.close()
```

### S3 Orphan Detection Pattern

```python
S3_BOOKS_PREFIX = "books/"

# Only list objects under books/ prefix
for page in paginator.paginate(Bucket=bucket, Prefix=S3_BOOKS_PREFIX):
    full_key = obj["Key"]
    # Strip prefix for DB comparison
    stripped_key = full_key[len(S3_BOOKS_PREFIX):]

# Compare stripped keys to DB keys
orphaned_stripped = s3_keys_stripped - db_keys

# Convert back to full keys for deletion
orphaned_full_keys = {f"{S3_BOOKS_PREFIX}{k}" for k in orphaned_stripped}
```

### Vue Set Reactivity Pattern

```typescript
// BAD - Vue doesn't detect Set mutations
savingIds.value.add(key)

// GOOD - Full reassignment triggers reactivity
savingIds.value = new Set([...savingIds.value, key])
```

---

## Next Steps

1. **Complete PR #691 review** - Verify all PR #686 fixes are included
2. **Verify Alembic chain** - Ensure `t3456789opqr` → `u4567890stuv` → `v5678901uvwx` exists
3. **Remove session logs** - These shouldn't be committed to the repo
4. **Watch staging deploy** - After merge, verify smoke tests pass
5. **Test cleanup dry-run** - Confirm orphan detection works correctly

---

## Commands Reference

```bash
# Check PR diff
gh pr diff 691

# Watch deploy workflow
gh run list --workflow Deploy --limit 1
gh run watch <run-id> --exit-status

# Test cleanup endpoint (staging)
bmx-api POST /admin/cleanup '{"action": "orphans"}'

# Test cleanup endpoint (production)
bmx-api --prod POST /admin/cleanup '{"action": "stale"}'

# Check Lambda logs
AWS_PROFILE=bmx-staging aws logs filter-log-events --log-group-name /aws/lambda/bluemoxon-staging-cleanup --limit 20
```

---

## Files Modified Across PRs

| Category | Key Files |
|----------|-----------|
| Frontend | `useFocusTrap.ts`, `useDebounce.ts`, `TransitionModal.vue`, `AdminConfigView.vue` |
| Backend | `lambdas/cleanup/handler.py`, `app/api/v1/admin.py`, `app/models/book.py` |
| Terraform | `modules/lambda-layer/`, `modules/cleanup-lambda/`, `main.tf` |
| Deploy | `.github/workflows/deploy.yml` |
| Migrations | `u4567890stuv_add_archive_attempts.py`, `v5678901uvwx_add_source_expired.py` |
