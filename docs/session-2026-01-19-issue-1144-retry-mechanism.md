# Session Log: Issue #1144 - Retry Mechanism for Queue Failed Jobs

**Date:** 2026-01-19 to 2026-01-20
**Issue:** [#1144](https://github.com/markthebest12/bluemoxon/issues/1144)
**PRs:** [#1192](https://github.com/markthebest12/bluemoxon/pull/1192) (staging), [#1193](https://github.com/markthebest12/bluemoxon/pull/1193) (production)

## Summary

Implemented a retry mechanism for image processing jobs that failed during SQS queue submission. The feature includes:

1. **Scheduled Lambda** (`bluemoxon-{env}-retry-queue-failed`): Runs every 5 minutes
2. **Admin Endpoint** (`POST /admin/image-processing/retry-queue-failed`): Manual triggering
3. **Max 3 retries** before marking as `permanently_failed`
4. **Race condition protection** using `SELECT FOR UPDATE SKIP LOCKED`

## Technical Implementation

### Key Files

- `backend/app/services/retry_queue_failed.py` - Core shared service
- `backend/lambdas/retry_queue_failed/handler.py` - Lambda handler
- `backend/app/api/v1/admin.py` - Admin endpoint
- `backend/alembic/versions/z1234567defg_add_queue_retry_count.py` - Migration
- `infra/terraform/modules/retry-queue-failed-worker/` - Terraform module

### Code Review Fixes Applied

| Issue | Fix |
|-------|-----|
| Race condition | Added `with_for_update(skip_locked=True, of=ImageProcessingJob)` |
| DRY violation | Extracted logic to `app/services/retry_queue_failed.py` |
| Wrong feature flag | Changed from `cleanup_lambda_enabled` to `image_processor_enabled` |
| No query ordering | Added `order_by(created_at.asc())` to prevent starvation |
| Batch commit | Changed to commit per job for SQS/DB consistency |
| Misleading comment | Updated Terraform module description |
| Undocumented reset | Added comments explaining `queue_retry_count` reset behavior |

### PostgreSQL FOR UPDATE Challenge

Initial implementation failed with:
```
FOR UPDATE cannot be applied to the nullable side of an outer join
```

**Fix:** Added `lazyload("*")` to prevent eager loading of relationships:
```python
jobs = (
    db.query(ImageProcessingJob)
    .options(lazyload("*"))
    .filter(...)
    .with_for_update(skip_locked=True, of=ImageProcessingJob)
    .all()
)
```

## Deployment Steps

1. Feature branch -> PR to staging (#1192)
2. Merged to staging, validated Lambda and admin endpoint
3. Terraform apply in staging to create Lambda infrastructure
4. PR staging -> main (#1193)
5. Merged to production
6. Terraform apply in production to create Lambda infrastructure
7. Validated both Lambda and admin endpoint in production
8. Closed issue #1144

---

## CRITICAL REMINDERS FOR FUTURE SESSIONS

### 1. ALWAYS Use Superpowers Skills

**MANDATORY:** Check for applicable skills BEFORE any action. Even a 1% chance means invoke the skill.

Key skills for this project:
- `superpowers:using-superpowers` - How to use skills
- `superpowers:test-driven-development` - TDD (write test first, watch it fail)
- `superpowers:receiving-code-review` - Verify before implementing, no sycophancy
- `superpowers:verification-before-completion` - Run verification commands before claiming success
- `superpowers:brainstorming` - For new features, explore before implementing

**Red flags to STOP:**
- "This is just a simple task" - Skills still apply
- "Let me explore first" - Skills tell you HOW to explore
- "I can check quickly" - Skills provide structured approach

### 2. NEVER Use These Bash Patterns (Trigger Permission Prompts)

| Pattern | Example | Why Bad |
|---------|---------|---------|
| `#` comments | `# this runs tests` | Permission prompt |
| `\` continuations | `cmd \`<br>`--flag` | Permission prompt |
| `$(...)` substitution | `echo $(date)` | Permission prompt |
| `||` or `&&` chaining | `cmd1 && cmd2` | Permission prompt |
| `!` in strings | `echo "Hello!"` | Permission prompt |

### 3. ALWAYS Use These Instead

| Good Pattern | Example |
|--------------|---------|
| Simple single-line | `git status` |
| Separate Bash calls | First call: `npm install`, Second call: `npm test` |
| `bmx-api` for API | `bmx-api GET /books` (staging) or `bmx-api --prod GET /books` |
| Description field | Use `description` parameter for comments |
| Alternate chars | Use `@`, `#`, `$` instead of `!` in strings |

### 4. Validation Before Claiming Success

Per `superpowers:verification-before-completion`:
- Run actual verification commands
- Check output shows success
- Evidence before assertions

Example:
```bash
# Good: Run and verify
bmx-api --prod GET /health/deep
# Output shows "status":"healthy" -> NOW claim success

# Bad: Claim success without verification
"The endpoint should work now"
```

## Lessons Learned

1. **New Lambda infrastructure requires Terraform apply** - CI/CD only deploys to existing Lambdas
2. **FOR UPDATE with SQLAlchemy relationships** - Use `lazyload("*")` to prevent outer join conflicts
3. **Migration registration** - New migrations must be added to `migration_sql.py` for health.py sync
4. **Commit per job** - When SQS and DB must stay in sync, commit after each operation

## Files Changed

```
backend/
  app/
    services/retry_queue_failed.py (NEW)
    api/v1/admin.py (MODIFIED)
    models/image_processing_job.py (MODIFIED)
    db/migration_sql.py (MODIFIED)
  lambdas/
    retry_queue_failed/
      __init__.py (NEW)
      handler.py (NEW)
  alembic/versions/
    z1234567defg_add_queue_retry_count.py (NEW)
  tests/
    test_retry_queue_failed.py (NEW)

infra/terraform/
  main.tf (MODIFIED)
  outputs.tf (MODIFIED)
  modules/
    retry-queue-failed-worker/ (NEW)
      main.tf
      variables.tf
      outputs.tf

.github/workflows/
  deploy.yml (MODIFIED)
```
