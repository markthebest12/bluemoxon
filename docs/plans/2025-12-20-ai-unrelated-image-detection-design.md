# AI-Powered Unrelated Image Detection Design

**Issue:** #487 - Non-related images from eBay listings imported into book carousel
**Date:** 2025-12-20
**Status:** Approved

## Problem

The aspect-ratio banner filter (PR #488) only catches wide banners (>2:1 ratio). Seller content with normal aspect ratios still gets through:

- **Seller logos** (square): "MIDTOWN SCHOLAR BOOKSTORE"
- **Different books** (portrait): Edward Gibbon Folio Society set in a Seven Lamps listing
- **Store promotional images** (portrait): "Visit My eBay Store!"

**Example:** Book 506 has images 17-23 that are all unrelated to the actual book, but only the wide ones would be caught by aspect ratio filtering.

## Solution: Leverage Existing AI Analysis

Claude Vision already analyzes book images during eval runbook generation (`_analyze_images_with_claude()`). We extend this prompt to also identify which images are NOT of the listed book.

### Why Eval Runbook (not Napoleon)

| Factor | Eval Runbook | Napoleon |
|--------|--------------|----------|
| Model | Sonnet (cheaper) | Sonnet |
| Timing | During acquisition eval | Later analysis phase |
| Images analyzed | Up to 15 | Up to 15 |
| **Decision** | **Earlier = prevents bad data** | Later = already stored |

## Decision: Block Automatically

Consistent with the aspect-ratio banner filtering design:

- **Cost of false positive** (missing one book photo): Low - user can manually upload
- **Cost of false negative** (ads in carousel): High - degrades collection quality
- **Implementation**: Simple - no UI changes needed

## Detection Logic

Add to existing Claude Vision prompt:

```
For each image, determine if it shows the listed book or is unrelated content:
- Unrelated: seller logos, store banners, different books, promotional material
- Related: the actual book being sold (cover, spine, pages, condition details)

Return image indices that are UNRELATED to the listing.
```

### Response Format

Add to existing response structure:
```json
{
  "condition_grade": "Good",
  "binding_analysis": {...},
  "unrelated_images": [17, 18, 19, 20, 21, 22, 23],
  "unrelated_reasons": {
    "17": "Shows different book (Edward Gibbon set)",
    "20": "Seller store logo",
    "23": "Promotional banner for seller's eBay store"
  }
}
```

### Action on Detection

When `unrelated_images` is non-empty:
1. Log identified unrelated images with reasons
2. Mark images for deletion from book's carousel
3. Delete the S3 objects
4. Update book's image metadata

## Implementation Location

**File:** `backend/app/services/eval_generation.py`

**Function:** `_analyze_images_with_claude()`

**Changes:**
1. Extend prompt to ask about image relevance
2. Parse `unrelated_images` from response
3. Return unrelated indices to caller
4. Caller handles S3 deletion

## Edge Cases

- **Single image listings:** Still analyze - might be only a seller logo
- **All images unrelated:** Log warning, keep at least first image
- **Claude uncertain:** Fail open (keep image) - Claude will say "possibly" which we ignore
- **Analysis failure:** Keep all images, log error

## Testing

**Unit tests:**
- Mock Claude response with unrelated_images field
- Verify parsing extracts indices correctly
- Verify empty array when all images related

**Integration tests:**
- Book 506 should identify images 17-23 as unrelated
- Book 515 should identify image 17 as unrelated

## Rollout

1. Deploy to staging
2. Re-run eval on book 506, verify unrelated images identified
3. Check CloudWatch logs for detection messages
4. Deploy to production

## Future Enhancements

- Add "unrelated_images" to book metadata for audit trail
- Dashboard showing detected unrelated content
- User override to restore incorrectly-filtered images
