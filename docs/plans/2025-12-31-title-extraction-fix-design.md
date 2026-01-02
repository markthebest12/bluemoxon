# Title Extraction Fix for Collected Works (#729)

**Date:** 2025-12-31
**Status:** Approved
**Issue:** #729

## Problem

The listing extraction prompt strips author/publisher from eBay titles, leaving only volume info for collected works:

- eBay title: `"Charles Dickens 10 Vol Set (1860s) Chapman & Hall"`
- Extracted: `"10 Vol Set"` (wrong)
- Expected: `"Works of Charles Dickens"`

This causes FMV lookup to fail (no comparables found for "10 Vol Set").

## Solution

### 1. Update EXTRACTION_PROMPT (Issue 2)

**File:** `backend/app/services/listing.py:235`

**Before:**
```python
"title": "book title only, no author/publisher/binder in title",
```

**After:**
```python
"title": "book title only (for collected works/sets without a specific title, use 'Works of [Author]' or 'Collected Works')",
```

### 2. Add Test for model_id Persistence (Issue 1)

**File:** `backend/tests/test_generate_analysis.py`

Add test verifying `model_id` is saved to database during AI generation (not just present in response).

### 3. Add Test for Collected Works Title

**File:** `backend/tests/test_listing_extraction.py`

Add test verifying collected works titles extract correctly.

### 4. Data Fix for Existing Books (Issue 3)

```bash
# Fix titles
bmx-api --prod PATCH /books/558 '{"title": "Works of Charles Dickens"}'
bmx-api PATCH /books/539 '{"title": "Works of Charles Dickens"}'

# Re-run eval to get FMV data
bmx-api --prod POST /books/558/eval
bmx-api POST /books/539/eval
```

## Testing

1. Test collected works title extraction with mock eBay HTML
2. Test model_id saved during generation
3. Verify FMV lookup works with corrected title

## Files Modified

- `backend/app/services/listing.py` - Prompt update
- `backend/tests/test_generate_analysis.py` - model_id test
- `backend/tests/test_listing_extraction.py` - Title extraction test
