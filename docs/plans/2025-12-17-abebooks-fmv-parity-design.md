# AbeBooks FMV Parity Design

**Date:** 2025-12-17
**Issue:** #379
**Status:** Approved

## Overview

Bring AbeBooks FMV lookup to parity with eBay's implementation.

## Problem

1. Claude prompt asks for "sold listings" but AbeBooks shows active listings - Claude refuses to extract
2. AbeBooks uses simple query (title + author) while eBay uses context-aware query (volumes, binding, etc.)
3. Result: AbeBooks returns 0 comparables, reducing FMV accuracy

## Solution

### Scope

**In scope:**
- Fix prompt to say "active listings" for AbeBooks
- Add context-aware query support (volumes, binding, binder, edition)
- Verify direct HTTP still works

**Out of scope:**
- Price weighting between sources (treat equally)
- Scraper Lambda integration (test first, add later if needed)
- AbeBooks-specific search syntax tuning

### Implementation

**Change 1: Update `_extract_comparables_with_claude()` prompt**

Conditional prompt text based on source:
- eBay: "sold book listings"
- AbeBooks: "book listings currently for sale"

**Change 2: Update `lookup_abebooks_comparables()` signature**

Add parameters: `volumes`, `binding_type`, `binder`, `edition`

**Change 3: Use context-aware query in AbeBooks**

Use `_build_context_aware_query()` when metadata is available.

**Change 4: Update `lookup_fmv()` caller**

Pass new parameters to `lookup_abebooks_comparables()`.

### Files to Modify

- `backend/app/services/fmv_lookup.py` - Main changes
- `backend/tests/test_fmv_lookup.py` - Add tests

## Testing

**Unit Tests:**
1. `test_abebooks_uses_context_aware_query()` - Verify volumes/binding in query
2. `test_extract_comparables_prompt_varies_by_source()` - Verify prompt wording

**Manual Validation:**
1. Trigger runbook for multi-volume book
2. Check CloudWatch logs for AbeBooks URL (should include "7 volumes")
3. Check Claude extraction response (should find listings)
4. Verify `abebooks_comparables` populated in runbook

## Success Criteria

- AbeBooks returns >0 comparables where listings exist
- Context-aware terms appear in search URL
- No regression in eBay functionality

## Risk & Rollback

**Risk level:** Low - isolated changes, no database/infrastructure changes

**Rollback:** Revert PR if AbeBooks fails. Worst case is 0 results (current state).
