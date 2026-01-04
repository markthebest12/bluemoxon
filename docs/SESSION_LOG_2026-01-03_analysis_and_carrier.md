# Session Log: Analysis Model Default Fix

**Date**: 2026-01-03
**PR**: #794 (pending CI, merge approved)
**Branch**: `fix/analysis-model-default-complete`

---

## CRITICAL SESSION RULES (MUST FOLLOW)

### 1. Superpowers Skills - USE AT ALL STAGES
**Invoke relevant skills BEFORE any response or action.** Even 1% chance = invoke.
- `superpowers:brainstorming` - Before any creative/feature work
- `superpowers:test-driven-development` - Before writing implementation code
- `superpowers:verification-before-completion` - Before claiming work is done
- `superpowers:systematic-debugging` - Before proposing fixes for any bug
- `superpowers:code-reviewer` - After significant code changes

**RED FLAGS - If you think these, STOP and invoke the skill:**
- "This is simple, I'll just..."
- "Let me quickly fix this..."
- "I'm confident this works..."

### 2. Bash Command Rules (AVOID PERMISSION PROMPTS)
**NEVER use:**
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings

**ALWAYS use:**
- Simple single-line commands
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls (no permission prompts)

### 3. PR Review Gates
- User reviews PR before staging merge
- User reviews staging->main PR before prod merge
- No auto-merging without explicit approval

---

## Issue Summary

### Problem
Books 578, 579, 581 failed analysis generation with Bedrock timeout (540s) using wrong model.

### Root Cause
**AcquisitionsView.vue bypassed the store and hardcoded `model: "sonnet"`**

The frontend had inconsistent defaults:
- `AcquisitionsView.vue:237` - hardcoded `"sonnet"` (P0 - actual bug path)
- `stores/books.ts:239,265` - defaulted to `"sonnet"`
- UI components - defaulted to `"opus"` (correct but overridden)

Backend also had inconsistent defaults:
- `models/analysis_job.py:35` - `default="sonnet"`
- `services/bedrock.py:408,540` - `model: str = "sonnet"`
- `worker.py:114` - `body.get("model", "sonnet")`
- Alembic migration - `server_default='sonnet'`

### Solution Applied
Created `DEFAULT_ANALYSIS_MODEL` constant in both frontend and backend, then fixed ALL locations:

**Frontend (7 files):**
| File | Change |
|------|--------|
| `config.ts` | Added `DEFAULT_ANALYSIS_MODEL = "opus"` constant |
| `AcquisitionsView.vue:237` | Use constant instead of hardcoded "sonnet" |
| `stores/books.ts` | Both function defaults use constant |
| `BookDetailView.vue` | `selectedModel` uses constant |
| `AnalysisViewer.vue` | `selectedModel` uses constant |
| `vitest.config.ts` | Added `__APP_VERSION__` define for tests |
| `books-generate.spec.ts` | Updated tests to expect opus + correct model IDs |

**Backend (5 files):**
| File | Change |
|------|--------|
| `constants.py` | NEW - `DEFAULT_ANALYSIS_MODEL = "opus"` |
| `models/analysis_job.py` | Column default uses constant |
| `services/bedrock.py` | Both function defaults use constant |
| `worker.py` | Job processing default uses constant |
| `health.py` | Registered migration `7a6d67bc123e` |

**Migration:**
- `7a6d67bc123e` - `ALTER TABLE analysis_jobs ALTER COLUMN model SET DEFAULT 'opus'`

**Sync Test:**
- `test_constants_sync.py` - Verifies frontend/backend constants match

---

## Current Status

### PR #794
- **Status**: CI running, merge approved by user
- **Branch**: `fix/analysis-model-default-complete`
- **Last CI run**: 20685313082 (all checks passing so far)

### Verification
- 202 frontend tests pass
- 63+ backend tests pass
- Lint/type-check clean
- Migration registered in health.py

---

## Next Steps (After Merge)

1. **Watch deploy workflow** after merge to staging
   ```bash
   gh run list --workflow Deploy --limit 1
   gh run watch <run-id> --exit-status
   ```

2. **Run migration** on staging
   ```bash
   curl -s https://staging.api.bluemoxon.com/api/v1/health/migrate
   ```

3. **Test analysis generation** for book 581
   ```bash
   bmx-api POST /books/581/analysis/generate-async
   ```

4. **Verify Lambda logs** show opus model
   ```bash
   AWS_PROFILE=bmx-staging aws logs filter-log-events --log-group-name /aws/lambda/bluemoxon-staging-analysis-worker --filter-pattern "opus" --limit 10
   ```

5. **Promote to production** after staging validation
   ```bash
   gh pr create --base main --head staging --title "chore: Promote analysis model fix to production"
   ```

---

## Files Reference

### Constants (Single Source of Truth)
- `frontend/src/config.ts` - `DEFAULT_ANALYSIS_MODEL`
- `backend/app/constants.py` - `DEFAULT_ANALYSIS_MODEL`

### Intentional Sonnet Usage (DO NOT CHANGE)
- `services/fmv_lookup.py` - FMV lookup
- `services/eval_generation.py` - Eval runbooks
- `api/v1/books.py` - `extract_structured_data` calls

### Model IDs (from bedrock.py)
- opus: `us.anthropic.claude-opus-4-5-20251101-v1:0`
- sonnet: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`

---

## Lessons Learned

1. **Always trace complete data flow** - First fix only covered store, not direct API calls
2. **Search ALL occurrences** before fixing - Use `grep` across entire codebase
3. **Use constants** - Prevents drift when updating for future models
4. **Add sync tests** - Catches frontend/backend constant mismatches
5. **Register migrations in health.py** - CI validation catches this

---

## Related Issues

### Carrier API (Separate Project)
GitHub issues #780-792 created with `carrier-api` label. Not blocked by this fix.

### Books Affected
- Book 581: "A Naturalists Voyage / Journal of Researches"
- Book 578: "The Book of Snobs"
- Book 579: "The History of Pendennis..."
