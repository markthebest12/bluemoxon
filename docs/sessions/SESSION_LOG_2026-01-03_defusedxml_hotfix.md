# Session Log: defusedxml Production Outage & Fix

**Date**: 2026-01-03
**Issue**: Production down after PR #773 merge - Lambda failing with `No module named 'defusedxml'`
**Status**: RESOLVED - Production restored

---

## Summary

PR #773 (tracking worker redesign) introduced a USPS carrier plugin that imports `defusedxml` for safe XML parsing. The production Lambda failed to start because `defusedxml` wasn't included in the Lambda layer.

**Outage Duration**: ~45 minutes (from PR #773 merge to PR #776 deploy)

## Root Causes (3 layers of issues)

| # | Issue | Why It Happened |
|---|-------|-----------------|
| 1 | `defusedxml` only in dev dependencies | New code imported it but pyproject.toml didn't have it in main deps |
| 2 | `requirements.txt` missing `defusedxml` | Lambda layer is built from requirements.txt, which is manually maintained |
| 3 | Layer cache key used wrong file | Cache key was `poetry.lock` hash but layer is built from `requirements.txt` |

## Fix Timeline

| Time | PR | Fix | Result |
|------|----|----|--------|
| 08:12 | - | Production outage detected | Lambda 500 errors |
| 08:19 | #774 | Add `defusedxml` to `pyproject.toml` | Failed - layer uses requirements.txt |
| 08:29 | #775 | Add `defusedxml` to `requirements.txt` | Failed - cached layer reused |
| 08:38 | #776 | Fix layer cache key to use `requirements.txt` hash | Success - layer rebuilt |
| 08:45 | - | Production restored | Health check passing |

## Technical Details

### Error

```
[ERROR] Runtime.ImportModuleError: Unable to import module 'app.main': No module named 'defusedxml'
```

### Import Chain

`backend/app/services/carriers/usps.py:7`:

```python
import defusedxml.ElementTree as ET
```

### Layer Build Process

1. `deploy.yml` checks if layer exists in S3 using hash of source file
2. If exists, skips rebuild and uses cached layer
3. If not, builds layer from `requirements.txt` using Docker
4. Cache key was using `poetry.lock` hash, but layer is built from `requirements.txt`

### Fix in deploy.yml

```yaml
# Before (wrong):
LOCK_HASH=$(sha256sum backend/poetry.lock | cut -d' ' -f1 | head -c 16)

# After (correct):
REQ_HASH=$(sha256sum backend/requirements.txt | cut -d' ' -f1 | head -c 16)
```

## Prevention

When adding new production dependencies:

1. Add to `pyproject.toml` main dependencies
2. Run `poetry lock` to update lock file
3. **ALSO add to `requirements.txt`** (manually maintained for Lambda layer)
4. Verify the dependency appears in both files before merging

## Current State

- **Branch**: `main` at commit `b036dc6`
- **PRs Merged**: #774, #775, #776
- **Production**: Healthy, version `2026.01.03-b036dc6`
- **Deploy Run**: 20674889498 (success)

## Commands for Verification

```bash
bmx-api --prod GET /health/deep
bmx-api --prod GET /health/version
```

---

## CRITICAL REMINDERS FOR NEXT SESSION

### 1. ALWAYS Use Superpowers Skills

**If there's even a 1% chance a skill applies, INVOKE IT.**

| Situation | Skill |
|-----------|-------|
| Before creative/feature work | `superpowers:brainstorming` |
| Before multi-step implementation | `superpowers:writing-plans` |
| Executing plans in same session | `superpowers:subagent-driven-development` |
| Any implementation | `superpowers:test-driven-development` |
| After all tasks complete | `superpowers:finishing-a-development-branch` |
| Receiving review feedback | `superpowers:receiving-code-review` |
| Need isolated workspace | `superpowers:using-git-worktrees` |
| About to claim work is complete | `superpowers:verification-before-completion` |
| Debugging any issue | `superpowers:systematic-debugging` |

### 2. NEVER Use These (Permission Prompt Triggers)

```bash
# BAD - ALWAYS triggers prompts:
# Comment lines before commands
command \
  --with-continuation     # backslash line continuations
$(date +%s)               # command substitution
cmd1 && cmd2              # chaining with &&
cmd1 || cmd2              # chaining with ||
--password 'Test1234!'    # ! in quoted strings
```

### 3. ALWAYS Use These Patterns

```bash
# GOOD - Simple single-line commands:
poetry run pytest tests/
git add file.py
git commit -m "message"
aws lambda get-function-configuration --function-name foo

# Use bmx-api for BlueMoxon API calls (no prompts):
bmx-api GET /books
bmx-api --prod GET /health
bmx-api POST /books '{"title":"..."}'
```

**Make separate sequential Bash tool calls instead of && chaining.**

---

## Next Steps

1. Monitor production for any issues
2. Consider adding CI check to verify requirements.txt matches pyproject.toml main deps
3. Run pending database migrations if any failed during outage
