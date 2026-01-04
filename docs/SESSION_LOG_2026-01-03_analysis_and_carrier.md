# Session Log: Analysis Generation Fix + Carrier API Issues

**Date**: 2026-01-03
**Issues**: Analysis timeout, Carrier API (#516)

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

## Current Status

### ISSUE 1: Analysis Generation Failing (ACTIVE)

**Symptom:** Books 578, 579, 581 show "Failed - click to retry" for analysis generation.

**Root Cause Investigation (Phase 1 Complete):**

| Finding | Evidence |
|---------|----------|
| Bedrock timeout | `ReadTimeoutError` after 540 seconds |
| Wrong model | Jobs running with `sonnet` instead of `opus` |
| Frontend bug | `stores/books.ts` defaults to "sonnet", ignoring UI |

**Lambda Logs Evidence:**
```
[ERROR] Read timeout on endpoint URL: "https://bedrock-runtime.us-west-2.amazonaws.com/model/us.anthropic.claude-sonnet-4-5-20250929-v1:0/invoke"
Read timed out. (read timeout=540)
```

**Two Bugs Found:**

1. **Frontend store default wrong** (stores/books.ts:239, 265)
   ```javascript
   // CURRENT - wrong
   model: "sonnet" | "opus" = "sonnet"

   // SHOULD BE
   model: "sonnet" | "opus" = "opus"
   ```

2. **Bedrock 9-minute timeout** - May need:
   - Reduced input size (eBay pages are huge)
   - Increased timeout
   - Better error handling

**Books Affected:**
- Book 581: "A Naturalists Voyage / Journal of Researches"
- Book 578: "The Book of Snobs"
- Book 579: "The History of Pendennis..."
- All have `analysis_status: null`, 0 images, eBay source URLs

---

### ISSUE 2: Carrier API Project (#516)

**Status:** Phase 1 complete, Phase 2 issues created.

**Key Finding:** Tracking worker infrastructure NOT deployed (intentional - carriers broken).

**GitHub Issues Created (label: `carrier-api`):**

| Issue | Title | Priority |
|-------|-------|----------|
| #783 | Replace web scraping with official APIs | Critical |
| #784 | Carrier credential management via SSM | High |
| #785 | Wire email/SMS in tracking poller | High |
| #786 | Configure SES/SNS | High |
| #787 | Register FedEx/Pitney Bowes | Medium |
| #788 | Add circuit breaker | Medium |
| #789 | Stop polling delivered books | Low |
| #790 | CloudWatch metrics/alarms | Medium |
| #791 | Integration tests with mocks | Medium |
| #792 | Deploy tracking worker infra | Blocked |
| #780 | UI: NotificationPreferences | Blocked by #781 |
| #781 | API: GET /preferences endpoint | Medium |

**Carrier API Root Cause:**
All carriers scrape public websites instead of official APIs:
- USPS: HTTP 302 (redirect)
- UPS: Timeout
- Royal Mail: HTTP 403 (blocked)

---

## Next Steps (Priority Order)

### Immediate: Fix Analysis Generation

1. **Fix frontend model default** (TDD approach)
   - File: `frontend/src/stores/books.ts`
   - Change lines 239 and 265: `"sonnet"` -> `"opus"`
   - Write test first, then fix
   - Create PR for review

2. **Investigate Bedrock timeout**
   - Check if eBay content is too large
   - Consider streaming or chunking
   - May need to increase boto3 read_timeout

### After Analysis Fix: Carrier API Phase 2

Follow dependency chain:
```
#784 (credentials) -> #783 (official APIs) -> #792 (deploy)
#786 (SES/SNS) -> #785 (wire notifications)
#781 (GET endpoint) -> #780 (UI)
```

---

## Files Reference

### Analysis Generation
- `frontend/src/stores/books.ts` - Model default bug (lines 239, 265)
- `backend/app/services/bedrock.py` - Bedrock client config
- `backend/app/worker.py` - Analysis worker

### Carrier API
- `backend/app/services/carriers/*.py` - Carrier implementations
- `backend/app/services/carriers/__init__.py` - Carrier registry
- `backend/app/services/tracking_poller.py` - Polling logic
- `backend/app/services/notifications.py` - Notification sending
- `infra/terraform/modules/tracking-worker/` - Infrastructure

---

## API Testing Commands

```bash
# Check book status
bmx-api --prod GET /books/581

# Trigger analysis (will fail until fixed)
bmx-api --prod POST /books/581/analysis/generate

# Check Lambda logs (get timestamp first)
date +%s000
AWS_PROFILE=bmx-prod aws logs filter-log-events --log-group-name /aws/lambda/bluemoxon-prod-analysis-worker --filter-pattern "ERROR" --start-time 1767480000000 --limit 10

# Check Bedrock models
AWS_PROFILE=bmx-prod aws bedrock list-foundation-models --query "modelSummaries[?contains(modelId, 'sonnet')]" --output table --region us-west-2
```

---

## Lambda Configuration

| Function | Timeout | Memory |
|----------|---------|--------|
| bluemoxon-prod-analysis-worker | 600s | 256MB |
| Bedrock client read_timeout | 540s | - |

---

## Session History

1. Resumed from carrier API session
2. User reported analysis generation failing for 3 books
3. Invoked `systematic-debugging` skill
4. Found Bedrock timeout errors in Lambda logs
5. Discovered frontend model default bug
6. Created carrier API GitHub issues (#780-792)
7. Preparing session log for compaction

---

## Verification Checklist (Before Claiming Complete)

- [ ] Run tests: `npm run --prefix frontend test`
- [ ] Run lint: `npm run --prefix frontend lint`
- [ ] Verify analysis generates successfully for book 581
- [ ] Check Lambda logs show correct model (opus)
- [ ] No Bedrock timeout errors
