# Session Log: Analysis Regeneration & Opus Access Bug

**Date:** December 30, 2025
**Issues:**
1. Analysis regeneration not updating in UI
2. Opus 4.5 model access denied in Bedrock
**Status:** INVESTIGATION COMPLETE - Fix needed for Opus access

---

## Background

### Issue Reported
User regenerated analysis for book 553 (Greville Memoirs) but UI still showed old timestamp "December 30, 2025 at 8:49 PM Pacific" instead of updated analysis.

### Root Cause Discovered

**The Opus regeneration job FAILED with AccessDeniedException:**
```
AccessDeniedException: Model access is denied due to IAM user or service role is
not authorized to perform the required AWS Marketplace actions
(aws-marketplace:ViewSubscriptions, aws-marketplace:Subscribe) to enable access
to this model.
```

**Key Finding:** User selected Opus model for regeneration, but Opus 4.5 requires AWS Marketplace subscription that appears to be misconfigured or expired.

### Evidence

```bash
bmx-api --prod GET /books/553/analysis/status
```
Returns:
```json
{
  "job_id": "d87d1067-0749-4929-95ef-9628971b5262",
  "status": "failed",
  "model": "opus",
  "error_message": "AccessDeniedException... aws-marketplace:ViewSubscriptions..."
}
```

### Investigation Summary

| Check | Result |
|-------|--------|
| IAM Bedrock permissions | ✅ Both API and Worker roles have `bedrock:InvokeModel` for Opus |
| Model ID | ✅ Correct: `us.anthropic.claude-opus-4-5-20251101-v1:0` |
| Sonnet works | ✅ Job started successfully for Sonnet |
| Opus sync API | ❌ Same AccessDeniedException |
| AWS Marketplace subscription | ❌ Appears to be the issue |

---

## Related Issue: FMV Scraper Environment Bug

**Branch:** `fix/fmv-scraper-environment`
**Commit:** `6177fcb`
**Issue:** #718

Production eval worker was calling staging scraper Lambda because `get_scraper_environment()` didn't check `ENVIRONMENT` env var.

**Fix applied to `app/config.py`:**
```python
def get_scraper_environment() -> str:
    return (
        os.getenv("BMX_SCRAPER_ENVIRONMENT")
        or os.getenv("BMX_ENVIRONMENT")
        or os.getenv("ENVIRONMENT", "staging")  # Added ENVIRONMENT check
    )
```

---

## Next Steps

### IMMEDIATE - FMV Fix
1. **Push branch and create PR**
   ```bash
   git push -u origin fix/fmv-scraper-environment
   ```
   Then:
   ```bash
   gh pr create --base staging --title "fix(config): check ENVIRONMENT env var for scraper Lambda targeting (#718)"
   ```

2. **After merge to staging, validate**
   ```bash
   bmx-api POST /books/538/eval-runbook/generate
   ```
   Verify comparables appear in response.

3. **Promote to production**
   ```bash
   gh pr create --base main --head staging --title "chore: Promote staging to production (FMV scraper fix)"
   ```

### IMMEDIATE - Opus Access
1. **Check Bedrock Model Access in AWS Console**
   - Navigate to: Bedrock > Model Access
   - Verify Claude Opus 4.5 is enabled
   - May need to re-request access via AWS Marketplace

2. **Alternative: Use Sonnet for now**
   - Sonnet analysis works correctly
   - Sonnet job was running successfully when session ended

### FOLLOW-UP Issues
| Issue | Title | Status |
|-------|-------|--------|
| #718 | fix: Production FMV lookup calling staging scraper | PR pending |
| #717 | fix: eBay listing extraction fails to capture volume count | OPEN |
| #716 | investigation: Sonnet vs Opus image analysis quality | OPEN |
| #715 | feat: Record AI model version in Napoleon analysis | OPEN |

---

## Key Files

| File | Purpose |
|------|---------|
| `app/config.py:155-169` | `get_scraper_environment()` - FMV fix |
| `app/services/bedrock.py:30-34` | Model ID configuration |
| `frontend/src/composables/useJobPolling.ts` | Analysis job polling |
| `frontend/src/components/books/AnalysisViewer.vue` | Analysis generation UI |

---

## CRITICAL REMINDERS FOR CONTINUATION

### 1. ALWAYS Use Superpowers Skills

Before ANY task, check if a skill applies:
- `superpowers:brainstorming` - Before creative/feature work
- `superpowers:systematic-debugging` - Before fixing bugs
- `superpowers:verification-before-completion` - Before claiming work done
- `superpowers:finishing-a-development-branch` - When completing work
- `superpowers:test-driven-development` - Before writing implementation code

**If there's even a 1% chance a skill applies, INVOKE IT.**

### 2. Bash Command Rules - NEVER USE

These trigger permission prompts and break auto-approve:
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` or `$((...))` command/arithmetic substitution
- `||` or `&&` chaining (even simple chaining breaks auto-approve)
- `!` in quoted strings (bash history expansion corrupts values)

### 3. Bash Command Rules - ALWAYS USE

- Simple single-line commands only
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls (no permission prompts)
- Use command description field instead of inline comments

**Example - WRONG:**
```bash
# Check status and update
bmx-api GET /books/553 && bmx-api PUT /books/553 '{"volumes": 8}'
```

**Example - CORRECT:**
```bash
bmx-api GET /books/553
```
Then separate call:
```bash
bmx-api PUT /books/553 '{"volumes": 8}'
```

---

## Git State at Session End

- **Branch:** `fix/fmv-scraper-environment` (not yet pushed)
- **Commit:** `6177fcb`
- **Working directory:** Clean
- **Status:** Ready to push and create PR

## Sonnet Job Status

A Sonnet regeneration job was started for book 553:
- **Job ID:** `fb99b78c-ed3b-45d0-9fc2-d85bb56ad206`
- **Status at session end:** `running` (Bedrock invocation in progress)
- **Expected completion:** ~5 minutes after 05:49 UTC

Check status with:
```bash
bmx-api --prod GET /books/553/analysis/status
```

---

## Verification Commands

```bash
# Check Opus job that failed
bmx-api --prod GET /books/553/analysis/status

# Test Sonnet generation
bmx-api --prod POST /books/553/analysis/generate-async '{"model": "sonnet"}'

# Check Bedrock model access (in AWS Console or via CLI)
AWS_PROFILE=bmx-prod aws bedrock list-foundation-models --query "modelSummaries[?contains(modelId, 'opus')].modelId"
```
