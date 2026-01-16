# Session Log: Binder Proliferation Fix

**Date:** 2026-01-02
**Issue:** Proliferation of "Unidentified" binder variants in production
**PR:** #759 (targeting staging)

---

## Problem Summary

The BlueMoxon database had accumulated 34+ duplicate "Unidentified" binder variants, each slightly different:

- "Unidentified (no signature visible)"
- "Unidentified (Publisher's Trade Binding)"
- "UNIDENTIFIED (no signature or stamp visible)"
- "Unknown (commercial trade binding)"
- etc.

These variants were being created because:

1. AI (Napoleon prompt) generates descriptive "Unidentified" names with parenthetical explanations
2. The extraction prompt's structured data included these descriptive names
3. Existing filtering only matched EXACT strings ("unidentified", "unknown", "none")
4. `normalize_binder_name()` passed unknown names through unchanged
5. `get_or_create_binder()` created new records for each unique string

## Root Cause Analysis

**Flow:**

```text
AI generates "Unidentified (no signature visible)"
    → Extraction prompt extracts to binder_identified field
    → Markdown parser merges to binder_identification["name"]
    → normalize_binder_name() returns ("Unidentified (no signature visible)", None)
    → get_or_create_binder() creates NEW binder record
```

**Key files:**

- `backend/app/services/reference.py` - `normalize_binder_name()`, `get_or_create_binder()`
- `backend/app/utils/markdown_parser.py` - `_parse_binder_identification()`, structured data merge
- S3 prompts: `prompts/napoleon-framework/v3.md`, `prompts/extraction/structured-data.md`

## Solution Implemented

### Code Changes

1. **`normalize_binder_name()`** - Returns `(None, None)` for names starting with "unidentified", "unknown", or "none"

2. **`get_or_create_binder()`** - Returns `None` when canonical_name is `None`

3. **Markdown parser** - Changed from exact match to `startswith()` filtering in both:
   - `_parse_binder_identification()` (line 309)
   - Structured data merge (line 415)

4. **Tests** - Updated `test_unknown_binder_returns_none()` and added `test_unidentified_variants_return_none()`

### Prompt Updates (S3 - both staging and prod)

- **napoleon-v3.md**: Changed "Unidentified" to "UNKNOWN", added note about no descriptions
- **structured-data.md**: Clarified "set to `null` (not 'Unknown', 'Unidentified', or any variant)"

### Production Cleanup

- Deleted 4 binders with 0 books directly
- Cleared `binder_id` from 54 books via API
- Deleted 34 "Unidentified" binder variants
- **Zero Unidentified binders remain**

## Next Steps

1. **Monitor PR #759** - Wait for CI to pass
2. **Merge to staging** - After CI passes
3. **Verify in staging** - Test that new analyses don't create Unidentified binders
4. **Promote to production** - Create PR from staging to main

---

## CRITICAL REMINDERS FOR FUTURE SESSIONS

### 1. ALWAYS USE SUPERPOWERS SKILLS

**If there is even a 1% chance a skill might apply, INVOKE IT FIRST.**

Relevant skills for this type of work:

- `superpowers:systematic-debugging` - Before proposing fixes
- `superpowers:verification-before-completion` - Before claiming work is done
- `superpowers:requesting-code-review` - After completing significant changes

### 2. BASH COMMAND RULES - NEVER USE THESE

These trigger permission prompts that cannot be auto-approved:

```bash
# NEVER USE:
# comment lines before commands          ❌
command1 \                               ❌ backslash continuations
  --option value
$(command)                               ❌ command substitution
$((1 + 2))                               ❌ arithmetic substitution
cmd1 && cmd2                             ❌ && chaining
cmd1 || cmd2                             ❌ || chaining
--password 'Test1234!'                   ❌ ! in quoted strings
```

### 3. BASH COMMAND RULES - ALWAYS USE THESE

```bash
# ALWAYS USE:
# Simple single-line commands
curl -s https://api.example.com/health

# Separate sequential Bash tool calls instead of &&
# (Make multiple Bash tool calls, not one chained command)

# bmx-api for all BlueMoxon API calls (no permission prompts)
bmx-api GET /books
bmx-api --prod GET /binders
bmx-api --prod PUT /books/123 '{"binder_id": null}'
bmx-api --prod DELETE /binders/456
```

### 4. BMX-API USAGE

```bash
bmx-api GET /endpoint                    # Staging (default)
bmx-api --prod GET /endpoint             # Production
bmx-api POST /endpoint '{"key":"value"}' # With JSON body
bmx-api PUT /endpoint '{"key":"value"}'  # Update
bmx-api PATCH /endpoint '{"key":"value"}'# Partial update
bmx-api DELETE /endpoint                 # Delete
```

---

## Files Modified

| File | Lines Changed |
|------|---------------|
| `backend/app/services/reference.py` | +13, -2 |
| `backend/app/utils/markdown_parser.py` | +15, -8 |
| `backend/tests/test_reference_service.py` | +27, -2 |

## Commit

```text
40fe866 fix: Prevent proliferation of Unidentified binder variants
```
