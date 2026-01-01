# Napoleon Analysis Improvements Session

**Date:** 2026-01-01
**Issue:** #743
**PRs:** #745 (main improvements), #746 (cost page text fix)
**Branch:** `feat/napoleon-improvements` (merged to staging)

## Background

Implementing 5 improvements identified during the analysis truncation fix session:

1. **Default model → opus** - Both sync/async endpoints default to opus
2. **Auto-fail stale jobs** - Jobs >15 min auto-failed on re-trigger
3. **Enhanced error messages** - Image count + 800px resize guidance for payload errors
4. **CSS tooltip** - Instant display tooltip with keyboard accessibility
5. **Operations docs** - Threshold table + troubleshooting workflow

## Work Completed

### PR #745 - Main Improvements (MERGED TO STAGING)
- Used `superpowers:subagent-driven-development` skill
- 4 parallel implementer subagents for Tasks 2-5
- 4 parallel spec/code quality reviewer subagents
- All P0/P1/P2 review findings fixed
- **Deployed:** `2026.01.01-c928aef`

### PR #746 - Cost Page Text Fix (MERGED TO STAGING)
- Updated `MODEL_USAGE` descriptions in `backend/app/services/bedrock.py`
- Sonnet: "Eval runbooks, FMV lookup, Listing extraction, Napoleon analysis (optional)"
- Opus: "Napoleon analysis (default)"

### Debugging: Stale Job Handling (VERIFIED WORKING)
- Used `superpowers:systematic-debugging` skill
- Book 539 had stale "running" job from Dec 31
- Stale check correctly marked it failed, new job created
- New job failed with Bedrock "Read timeout" (separate issue - 24-image book timeout)

## Current Status

**STAGING VALIDATED - READY FOR PRODUCTION PR**

### Validation Pending
1. **Default model → opus** - User to validate in UI
2. **CSS tooltip** - User to validate visually

### New Issue Discovered: Garbage Image Filtering Quality

**Problem:** Book 539 contains 5 garbage images that weren't filtered:
- Image 19: Yarn/textile skeins (not a book)
- Image 20: Decorative buttons (not a book)
- Image 21: "From Friend to Friend" - different book
- Image 22: "With Kennedy" by Pierre Salinger - different book
- Image 23: German-English Dictionary - different book

**Root Cause Analysis (QUALITY issue, not timing):**
- Eval runbook DID run
- Garbage detection prompt DID execute
- **Claude failed to identify these images as unrelated**

**Two problems identified:**

1. **Prompt coverage gap**: Current prompt categories:
   - Seller store logos or banners
   - "Visit My Store" promotional images
   - Completely different books
   - Generic stock photos
   - Seller contact/shipping info graphics

   Missing: "Random objects that aren't books" (yarn, buttons)

2. **Detection failure for covered cases**: Images 21-23 ARE "completely different books" (explicitly covered) but Claude missed them anyway

**Hypothesis**: Prompt overload - Claude asked to do condition analysis, item identification, AND garbage detection simultaneously. Unrelated images task is buried in condition-focused prompt.

## Next Steps

1. **User validates features 1 and 4 in staging** (pending)
2. **Continue brainstorming garbage image filtering** (ready to continue)
   - User preference: **Dedicated garbage detection call** (option 1)
   - User suggestion: Store prompts in S3 for adjustment without code releases
3. **Create PR staging → main** (DO NOT MERGE without user review)

---

## CRITICAL REMINDERS FOR CONTINUATION

### 1. ALWAYS Use Superpowers Skills

**MANDATORY at every stage - OR USER WILL SWITCH TO CHATGPT:**
- `superpowers:brainstorming` - Before ANY creative/feature work
- `superpowers:writing-plans` - Before implementation
- `superpowers:executing-plans` or `superpowers:subagent-driven-development` - During implementation
- `superpowers:test-driven-development` - For all code changes
- `superpowers:systematic-debugging` - For ANY bug/test failure
- `superpowers:requesting-code-review` - After completing work
- `superpowers:verification-before-completion` - Before claiming done
- `superpowers:finishing-a-development-branch` - Before merge/PR

### 2. NEVER Use These (Trigger Permission Prompts)

```bash
# BAD - NEVER USE:
# comment lines before commands
command \
  --with-continuation
$(command substitution)
cmd1 && cmd2
cmd1 || cmd2
--password 'Test1234!'  # ! in strings
```

### 3. ALWAYS Use These Patterns

```bash
# GOOD - Always use:
command --flag value           # Simple single-line
bmx-api GET /books            # For BlueMoxon API calls
bmx-api --prod GET /books     # Production API
```

**For sequential commands:** Make separate Bash tool calls instead of `&&`

### 4. API Calls

```bash
bmx-api GET /books                     # Staging (default)
bmx-api --prod GET /books              # Production
bmx-api POST /books '{"title":"..."}' # With JSON body
bmx-api --text-file f.md PUT /books/1/analysis  # Text upload
```

### 5. DO NOT MERGE TO MAIN WITHOUT USER REVIEW

User explicitly requested: "do not merge to main until I review the PR"

---

## Files Changed

### Backend
- `backend/app/api/v1/books.py` - Default model, stale job cleanup, constant
- `backend/app/schemas/analysis_job.py` - Default model
- `backend/app/worker.py` - Error formatting function
- `backend/app/services/bedrock.py` - MODEL_USAGE descriptions updated
- `backend/tests/test_books.py` - New tests
- `backend/tests/test_worker.py` - New tests

### Frontend
- `frontend/src/components/BaseTooltip.vue` - New component
- `frontend/src/components/AnalysisIssuesWarning.vue` - Uses tooltip
- `frontend/src/components/__tests__/AnalysisIssuesWarning.spec.ts` - New tests

### Docs
- `docs/OPERATIONS.md` - Analysis troubleshooting section

---

## Garbage Image Filtering - Context for Brainstorming

### Current System (in `app/services/eval_generation.py`)
- Detection happens during Eval Runbook generation only
- Uses Claude Vision with prompt (lines 268-306)
- `delete_unrelated_images()` in `app/services/image_cleanup.py` handles deletion
- Prompt is condition-focused with garbage detection buried in middle

### User's Design Preference
1. **Dedicated garbage detection call** - Separate focused Claude call JUST for filtering
2. **Prompts in S3** - User suggests storing prompts as S3 objects for adjustment without code releases, with versioning

### Questions to Explore in Brainstorming
1. Should we add a dedicated pre-analysis garbage detection step?
2. Should prompts live in S3 vs code? (latency, drift, troubleshooting implications)
3. Where should this detection run? (scrape time vs before analysis vs both)
4. How to make prompt more comprehensive (catch "not a book" objects)?

### Technical Context
- Prompts currently embedded in Python code in `backend/app/services/`
- S3 bucket available: `bluemoxon-images-staging` / `bluemoxon-images`
- Could use SSM Parameter Store as alternative to S3 for prompts

---

## Listing Re-extracted for Testing

eBay item 397448193086 re-scraped to `listings/397448193086/` in S3:
- 24 images extracted
- Book not yet re-created in database (was deleted for debugging)
- Ready for fresh import to test garbage detection changes
