# Session: Markdownlint Setup and Sync Script Fixes

**Date:** 2026-01-16
**Branch:** staging → main

## Summary

This session accomplished two major tasks:
1. Set up markdownlint for documentation and fixed all lint errors
2. Fixed the prod-to-staging sync script to use Lambda instead of direct DB access

---

## Part 1: Markdownlint Setup

### Background

Ran `npx markdownlint-cli2 "docs/**/*.md"` and found **14,023 errors** across 289 files.

### Actions Taken

1. **Created `.markdownlint.json`** config to disable noisy rules:
   - MD013 (line-length > 80 chars) - impractical for docs
   - MD024 (duplicate headings) - intentional in TDD plans
   - MD029 (ordered list prefix) - stylistic
   - MD033 (inline HTML) - used for type annotations
   - MD036 (bold as heading) - stylistic
   - MD060 (table column style) - too strict

2. **Auto-fixed** safe issues (blank lines around fences, headings, lists)

3. **Added `text` language** to 522 unlabeled code blocks

4. **Fixed malformed tables** - escaped pipe characters in regex patterns and `||` operators

5. **Refactored CLAUDE.md** from 564 → 152 lines (73% reduction):
   - Consolidated 3 workflow sections into 1
   - Merged duplicate Quick Commands sections
   - Added markdownlint to validation checklist

### Final Result

**0 errors** across 290 files (including CLAUDE.md).

### Commits

| SHA | Description |
|-----|-------------|
| f3c0c38 | Auto-fixes + config for MD013, MD060 |
| 738a76a | Add `text` to 522 code blocks |
| 792afc3 | Disable stylistic rules, fix headings |
| af317c7 | Fix malformed tables (escape pipes) |
| 245d9f8 | Refactor CLAUDE.md (73% smaller) |

---

## Part 2: Sync Script Fix

### Background

User ran `scripts/sync-prod-to-staging.sh` and got connection timeout:

```text
pg_dump: error: connection to server at "bluemoxon-cluster..." failed: Operation timed out
```

### Root Cause

The script used direct `pg_dump`/`psql` which requires network access to RDS. Prod (Aurora) and Staging (RDS) are in different accounts/VPCs with no peering configured.

### Solution

Updated script to delegate DB sync to Lambda (which runs inside VPC with access to both databases):

1. **Script changes:**
   - Removed direct pg_dump/psql code
   - Added Lambda invocation for DB sync
   - Kept S3 sync local (works cross-account via download/upload)
   - Simplified prerequisites (no longer needs psql installed)

2. **Lambda fix** for type mismatches:
   - `admin_config.value`: prod has `numeric`, staging has `jsonb`
   - `eval_runbooks.condition_positives`: prod has `text[]`, staging has `jsonb`
   - Updated `adapt_row_for_insert()` to handle numeric→jsonb and text[]→jsonb conversions
   - Added logging for JSONB column detection

### Commits

| SHA | Description |
|-----|-------------|
| afbceff | Update filelock to 3.20.3 (Dependabot alert #8) |
| 94dcd53 | Update sync script to use Lambda + fix JSONB handling |

---

## Part 3: Dependabot Fix

Fixed moderate vulnerability: filelock TOCTOU symlink vulnerability
- Updated from 3.20.2 → 3.20.3
- Also updated: botocore, boto3, alembic, ruff

---

## Next Steps

1. **Redeploy db-sync Lambda** to apply the JSONB fix
2. **Re-run sync** after Lambda deploy: `scripts/sync-prod-to-staging.sh`
3. **Monitor** for any remaining type mismatch errors in Lambda logs

---

## CRITICAL REMINDERS FOR CONTINUATION

### 1. ALWAYS Use Superpowers Skills

**Invoke relevant skills BEFORE any response or action.** Even a 1% chance a skill might apply means invoke it first.

Key skills to remember:
- `superpowers:brainstorming` - Before any creative/feature work
- `superpowers:systematic-debugging` - Before proposing fixes for bugs
- `superpowers:test-driven-development` - Before implementing features
- `superpowers:verification-before-completion` - Before claiming work is done

### 2. NEVER Use Complex Bash Syntax

These trigger permission prompts that cannot be auto-approved:

```bash
# BAD - NEVER USE:
# This is a comment          # Comments before commands
aws lambda invoke \          # Backslash continuations
  --function-name foo
$(date +%s)                  # Command substitution
cmd1 && cmd2                 # Chaining with &&
cmd1 || cmd2                 # Chaining with ||
--password 'Test1234!'       # ! in quoted strings
```

### 3. ALWAYS Use Simple Commands

```bash
# GOOD - ALWAYS USE:
aws lambda invoke --function-name foo --payload '{}' out.json

# For sequential commands, make SEPARATE Bash tool calls:
# Call 1: git add .
# Call 2: git commit -m "message"
# Call 3: git push

# For API calls:
bmx-api GET /books
bmx-api --prod GET /books/123
bmx-api PATCH /books/123 '{"status":"OWNED"}'
```

### 4. Key Project Commands

```bash
# Validation (run as SEPARATE calls, not chained)
poetry run ruff check backend/
poetry run ruff format --check backend/
npm run --prefix frontend lint
npm run --prefix frontend format
npx markdownlint-cli2 "docs/**/*.md"

# Sync
scripts/sync-prod-to-staging.sh           # Uses Lambda for DB
scripts/sync-prod-to-staging.sh --images-only  # S3 only

# Deploy check
gh run list --workflow Deploy --limit 1
gh run watch <run-id> --exit-status
```

---

## Files Modified

- `.markdownlint.json` (created)
- `CLAUDE.md` (refactored)
- `docs/**/*.md` (274 files - lint fixes)
- `scripts/sync-prod-to-staging.sh` (use Lambda for DB sync)
- `backend/lambdas/db_sync/handler.py` (JSONB type handling)
- `poetry.lock` (filelock security fix)
