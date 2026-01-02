# Session Log: FMV Comparables Missing from Production

**Date:** December 30, 2025
**Issue:** FMV comparable listings not appearing in production eval runbooks
**Status:** FIX READY - PR pending

---

## Background

### The Problem
User noticed that book 549 (Gibbon's Decline and Fall) displayed FMV comparables in the UI:
- Shows 5 AbeBooks listings with prices ($150, $495, $275, $350, $225)
- FMV range: $225-$350 with "high" confidence

But nearly all other books show FMV range WITHOUT comparables:
- Just shows price range (e.g., "$120-$200")
- `ebay_comparables: []` and `abebooks_comparables: []` in eval runbook
- `fmv_notes: "No comparable listings found"`

### Root Cause Discovered

**CloudWatch logs revealed the smoking gun:**
```
[ERROR] Error invoking scraper Lambda for listing extraction:
AccessDeniedException... User is not authorized to perform: lambda:InvokeFunction
on resource: arn:aws:lambda:us-west-2:...:function:bluemoxon-staging-scraper
```

**The production eval worker was calling the STAGING scraper Lambda!**

**Why:** `get_scraper_environment()` in `app/config.py` only checked:
- `BMX_SCRAPER_ENVIRONMENT` (not set)
- `BMX_ENVIRONMENT` (not set)
- Default: `"staging"`

But the Lambda has `ENVIRONMENT=prod` set - which wasn't being checked!

### Code Path
1. `app/eval_worker.py:122` calls `generate_eval_runbook(run_fmv_lookup=True)`
2. `app/services/eval_generation.py:459` calls `lookup_fmv()`
3. `app/services/fmv_lookup.py:60` calls `get_scraper_environment()`
4. `app/config.py:165` returns `"staging"` because `ENVIRONMENT` not checked
5. FMV lookup tries to invoke `bluemoxon-staging-scraper` → **AccessDeniedException**
6. Silently fails, returns empty comparables

---

## Fix Applied

**File:** `app/config.py`

**Change:** Updated `get_scraper_environment()` to also check `ENVIRONMENT`:
```python
def get_scraper_environment() -> str:
    return (
        os.getenv("BMX_SCRAPER_ENVIRONMENT")
        or os.getenv("BMX_ENVIRONMENT")
        or os.getenv("ENVIRONMENT", "staging")  # NEW: check ENVIRONMENT
    )
```

**Branch:** `fix/fmv-scraper-environment`
**Commit:** `6177fcb`

---

## Next Steps

### IMMEDIATE
1. **Push branch and create PR to staging**
   ```bash
   git push -u origin fix/fmv-scraper-environment
   gh pr create --base staging --title "fix(config): check ENVIRONMENT env var for scraper Lambda targeting"
   ```

2. **After merge to staging, validate in staging environment**
   - Regenerate an eval runbook for a test book
   - Verify comparables appear in response

3. **Promote to production**
   ```bash
   gh pr create --base main --head staging --title "chore: Promote staging to production (FMV scraper fix)"
   ```

4. **After production deploy, regenerate eval runbooks for affected books**
   - All books since eval worker was deployed need regeneration
   - Use `POST /books/{id}/eval-runbook/generate` endpoint

### FOLLOW-UP ISSUES
- #715: Record AI model version in Napoleon analysis
- #716: Sonnet vs Opus image analysis quality investigation
- #717: Volume extraction bug in eBay listing import

---

## Key Files

| File | Purpose |
|------|---------|
| `app/config.py:155-169` | `get_scraper_environment()` - THE FIX |
| `app/services/fmv_lookup.py` | FMV lookup service |
| `app/services/eval_generation.py` | Eval runbook generation |
| `app/eval_worker.py` | Lambda handler for eval jobs |

---

## Verification Commands

```bash
# Check Lambda environment variables
AWS_PROFILE=bmx-prod aws lambda get-function-configuration --function-name bluemoxon-prod-eval-runbook-worker --query 'Environment.Variables'

# Check eval worker logs for scraper errors
AWS_PROFILE=bmx-prod aws logs filter-log-events --log-group-name /aws/lambda/bluemoxon-prod-eval-runbook-worker --start-time 1735518000000 --limit 20 | jq '.events[].message'

# Check a book's eval runbook for comparables
bmx-api --prod GET /books/549/eval-runbook | jq '{fmv_notes, ebay_comparables, abebooks_comparables}'
```

---

## CRITICAL REMINDERS FOR CONTINUATION

### 1. ALWAYS Use Superpowers Skills
Before ANY task, check if a skill applies:
- `superpowers:brainstorming` - Before creative/feature work
- `superpowers:systematic-debugging` - Before fixing bugs
- `superpowers:verification-before-completion` - Before claiming work done
- `superpowers:finishing-a-development-branch` - When completing work

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

## Related Sessions
- `2025-12-30-greville-memoirs-valuation-investigation.md` - Initial discovery during Greville investigation
- `2025-12-30-issues-708-709.md` - Related FMV filtering work

## Git State at Session End
- Branch: `fix/fmv-scraper-environment`
- Commit: `6177fcb` (uncommitted changes: none)
- Status: Ready to push and create PR
