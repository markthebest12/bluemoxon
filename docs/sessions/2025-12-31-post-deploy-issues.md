# Session Log: Post-Deploy Issues (#715, #717, #729)

**Date:** 2025-12-31
**Status:** ✅ COMPLETE - Deployed to Production
**Version:** `2025.12.31-8cb057c`

---

## SUMMARY FOR NEXT SESSION

### Background

PR #727 deployed issues #715 (model version tracking) and #717 (volume extraction) to production. Post-deploy verification revealed three issues:

1. **Model ID not showing in UI** - Frontend wasn't displaying the `model_id` field
2. **Title extraction wrong** - Prompt stripped author name, returning "10 Vol Set" instead of "Works of Charles Dickens"
3. **FMV Pricing empty** - Bad title caused no comparables (separate issue, not fixed here)

### What Was Fixed (PR #730 → #731)

| Issue | Fix |
|-------|-----|
| Model ID display | Added to `AnalysisViewer.vue` footer with `formatModelId()` function |
| Title extraction | Updated `EXTRACTION_PROMPT` to guide "Works of [Author]" for collected works |
| UI separator | Changed from pipe `\|` to middle dot `·` |
| Test coverage | Behavioral mock test for collected works title extraction |

### Production State

- **API health:** healthy
- **Frontend:** Working, displays "· Claude Sonnet 4.5" for new analyses
- **Older analyses:** Show timestamp only (model_id is null, handled gracefully)

### Outstanding Issue: FMV Still Empty (#729 partial)

Even with corrected title "Works of Charles Dickens", FMV lookup returns no comparables. This is a **SEPARATE issue** - search query may need different terms for eBay/AbeBooks to find matches.

---

## CRITICAL REMINDERS FOR CONTINUATION

### 1. ALWAYS USE SUPERPOWERS SKILLS - MANDATORY AT ALL STAGES

**IF A SKILL APPLIES, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.**

| When | Skill |
|------|-------|
| Starting ANY task | `superpowers:using-superpowers` |
| Creative/feature work | `superpowers:brainstorming` |
| ANY implementation | `superpowers:test-driven-development` (failing test FIRST) |
| ANY bug/issue | `superpowers:systematic-debugging` (root cause FIRST) |
| Claiming done | `superpowers:verification-before-completion` |
| Creating PRs | `superpowers:requesting-code-review` |
| Receiving feedback | `superpowers:receiving-code-review` (verify, no performative agreement) |

### 2. BASH COMMAND RULES - NEVER USE (triggers permission prompts)

- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` or `$((...))` command substitution
- `||` or `&&` chaining
- `!` in quoted strings (bash history expansion)

### 3. BASH COMMAND RULES - ALWAYS USE

- Simple single-line commands
- Separate sequential Bash tool calls instead of `&&`
- `git -C /path/to/repo` instead of `cd path && git`
- `bmx-api` for all BlueMoxon API calls (no permission prompts)

---

## NEXT STEPS (if continuing this work)

1. **Create GitHub issue for FMV search problem** - "Works of Charles Dickens" query returns no comparables
2. **Investigate FMV search logic** - May need author-only search fallback or different query terms
3. **Consider regenerating analysis** for books 539/558 to populate model_id field

---

## Related Issues/PRs

- Issue #729 - Title extraction for collected works
- PR #730 - Code review fixes → staging
- PR #731 - Promote staging → production
- PR #727 - Deployed #715, #717
- Issue #715 - Model version tracking
- Issue #717 - Volume extraction

---

## Key Files Modified

| File | Changes |
|------|---------|
| `backend/app/services/listing.py:235` | EXTRACTION_PROMPT - guides "Works of [Author]" |
| `backend/tests/test_listing_extraction.py` | Behavioral mock test for collected works |
| `frontend/src/components/books/AnalysisViewer.vue` | `formatModelId()` + model display in footer |

---

## Design Document

See: `docs/plans/2025-12-31-title-extraction-fix-design.md`
