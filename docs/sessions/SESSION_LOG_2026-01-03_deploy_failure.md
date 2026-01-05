# Session Log: Deploy Failure - defusedxml Missing

**Date**: 2026-01-03
**Issue**: Production deploy failed after PR #773 merge
**Status**: CRITICAL - Production Lambda failing to start

---

## Summary

PR #773 (tracking worker redesign) was merged to main, triggering a deploy. The deploy failed at the "Run database migrations" step because the Lambda cannot start - missing `defusedxml` module.

## Error

```
[ERROR] Runtime.ImportModuleError: Unable to import module 'app.main': No module named 'defusedxml'
```

## Root Cause Analysis

1. `defusedxml` is a transitive dependency of `py-serializable` which is required by `cyclonedx-python-lib`
2. `cyclonedx-python-lib` is in the `dev` group in poetry.lock
3. The Lambda layer build should NOT include dev dependencies
4. Something in the production code path is trying to import a module that transitively needs `defusedxml`

## Investigation Needed

1. Check what's importing `defusedxml` in the import chain
2. Verify the Lambda layer build process excludes dev dependencies
3. Check if any new code was added that requires this dependency
4. Verify production API is still working (previous Lambda version should be running)

## What Was Completed Before Failure

1. Fixed CI migration validation to handle merge migrations (tuple down_revision)
2. Registered new migrations (w6789012wxyz, x7890123abcd) in health.py
3. CI passed on PR #773
4. PR #773 merged to main
5. Deploy started but failed at migration step

## Next Steps

1. Check if production API is responding (previous Lambda alias should work)
2. Investigate the `defusedxml` import chain
3. Either add `defusedxml` to production dependencies OR fix the import issue
4. Re-run deploy after fix

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

## Current State

- **Branch**: `main` at commit `85493c0`
- **PR #773**: Merged
- **Deploy Run**: 20674487248 (failed)
- **Production**: Lambda failing to start (defusedxml missing)
- **Previous Lambda Version**: Should still be active via alias

## Commands for Next Session

```bash
# Check production health
bmx-api --prod GET /health/deep

# Check Lambda logs
AWS_PROFILE=bmx-prod aws logs filter-log-events --log-group-name /aws/lambda/bluemoxon-prod-api --limit 20

# Check current Lambda alias
AWS_PROFILE=bmx-prod aws lambda get-alias --function-name bluemoxon-prod-api --name live
```
