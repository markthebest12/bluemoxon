# Batch Re-Extraction Continuation Notes

**Date:** 2025-12-21 (Session Complete)
**Session:** Full format analysis and processing

## SESSION SUMMARY

### Completed Work

| Category | Count | Status |
|----------|-------|--------|
| Degraded books (re-extract) | 26 | ✅ All successful |
| Stale books with good format (re-extract) | 35 | ✅ All successful |
| OLD format books (full regen) | 5 | ✅ All completed |
| **Total** | **66** | **100% complete** |

### Degraded Books (26) - All Re-Extracted

59, 21, 401, 56, 22, 395, 60, 512, 399, 389, 62, 57, 390, 2, 393, 24, 4, 391, 67, 509, 47, 63, 64, 66, 374, 25

### Stale Books with Good Format (35) - All Re-Extracted

343, 396, 489, 350, 336, 372, 383, 384, 400, 385, 352, 392, 405, 339, 27, 402, 397, 367, 382, 398, 347, 346, 335, 380, 3, 387, 379, 394, 345, 41, 381, 348, 388, 356, 337

### OLD Format Books (5) - Full Regeneration Complete

| Book ID | Title | Format After Regen |
|---------|-------|-------------------|
| 378 | Court and Times of James I | ✅ NEW: `# Professional Valuation Report:` |
| 403 | Life of John Sterling | ✅ NEW: `# Professional Valuation Analysis:` |
| 68 | Felix Holt, the Radical | ✅ NEW: `# Professional Valuation Report:` |
| 351 | Fielding Select Works | ⚠️ `## Executive Summary` (no H1) |
| 51 | Works of William Shakespeare | ⚠️ `## 1. Executive Summary` (no H1) |

**Note:** Books 351 and 51 regenerated but still have non-standard format (starts with ## instead of #). The Napoleon prompt generates inconsistent formats.

## EXCLUDED

- **Book 373** - User explicitly excluded, DO NOT TOUCH

## ROOT CAUSE ANALYSIS COMPLETE (2025-12-21)

### Issue: Book 351 Missing Provenance Detection - RESOLVED

**Problem:** User reports provenance visible in book 351 images, but AI analysis states:
> "Provenance evidence: No bookplates, ownership signatures, or institutional stamps visible in provided images."

### Investigation Findings

**Phase 1 - Evidence Found:**
Image 8 (`351_e22a77b0040441d0bb5fb27fcead5303.jpg`) clearly shows:

1. **Ex Libris bookplate** for "CAROL KANNER" on front pastedown
2. **Ownership signature** "Gertrude Conant" on front free endpaper
3. Additional period signatures at top of page

**Phase 2 - Root Cause Identified:**
The Napoleon prompt (`backend/prompts/napoleon-framework/v2.md`) Section 2 (Condition Assessment) was missing explicit instructions to look for provenance markers.

Original:

```
- **Endpapers:** original/replaced, marbling condition, hinges
```

The AI was never told WHERE to look for provenance or WHAT markers to detect.

**Phase 3 - Determination:**
This is a **systematic prompt issue**, not a one-off. Could affect other books.

### Fixes Applied

**1. Napoleon Prompt Updated** (`v2.md` Section 2):

```markdown
- **Provenance Markers (EXAMINE CAREFULLY):**
  - **Front paste-down:** Look for bookplates ("Ex Libris" labels)
  - **Front free endpaper:** Look for ownership signatures, inscriptions, gift dedications
  - **Title page:** Look for signatures, stamps, or ownership inscriptions
  - **Throughout:** Look for institutional stamps, library markings, or collector blind stamps
  - If ANY ownership evidence is found, document it specifically
```

**2. Book 351 Manually Updated:**

```json
{
  "has_provenance": true,
  "provenance": "Ex Libris bookplate of Carol Kanner on front pastedown; ownership signature of Gertrude Conant on front free endpaper; additional period signatures visible",
  "provenance_tier": "Tier 3"
}
```

### Status: COMPLETE

- ✅ Root cause identified (prompt gap)
- ✅ Code fix applied (prompt enhanced)
- ✅ Book 351 data corrected manually in prod
- ✅ Prompt change merged to staging (PR #496)
- ✅ Staging deployed with new code (version 2025.12.21-9024a28)
- ✅ Prompt uploaded to staging S3 (`s3://bluemoxon-images-staging/prompts/napoleon-framework/v2.md`)
- ⚠️ Production prompt NOT updated (user requested testing without prod changes)

## CRITICAL FINDING: Image Database Linkage Issue (2025-12-21)

**Problem:** Images exist in S3 but are NOT linked in the database.

**Evidence:**

```bash
# S3 has images for book 351:
AWS_PROFILE=bmx-prod aws s3 ls s3://bluemoxon-images/books/ | grep "351_" | wc -l
# Output: 20+ images

# But API shows no images:
bmx-api --prod GET '/books/351' | jq '.images'
# Output: null

# Same for ALL books - images are null:
bmx-api --prod GET '/books/59' | jq '{has_images, images}'
# Output: {"has_images": null, "images": null}
```

**Impact:**

- The analysis worker gets 0 images when processing books
- AI cannot detect provenance because it has no images to examine
- The prompt fix is working correctly (explicitly looks for provenance markers)
- But without images, there's nothing to analyze

**Root Cause:** Unknown - needs investigation. Possible causes:

1. Images were uploaded to S3 but never linked to database records
2. Database migration removed image linkage
3. Image upload process has bug that skips database linking

**Action Required:**

1. Investigate why book images are not linked in database
2. Create database records linking books to their S3 images
3. Re-test provenance detection after images are linked

## Testing the Prompt Fix

**Staging test (2025-12-21):**

- Triggered analysis for book 351 in staging
- Prompt correctly includes "Provenance Markers (EXAMINE CAREFULLY)" section
- Analysis explicitly states: "Front Pastedown: Examined - no bookplates... visible"
- The AI IS following the prompt instructions - but there are no images to examine

**To properly test the prompt:**

1. Fix the image database linkage issue
2. Trigger analysis for a book with known provenance (e.g., book 351)
3. Verify provenance is detected

## Prompt Location (Important)

The Napoleon prompt is loaded from S3, NOT from the Lambda package:

```python
PROMPTS_BUCKET = os.environ.get("PROMPTS_BUCKET", settings.images_bucket)
PROMPT_KEY = "prompts/napoleon-framework/v2.md"
```

**Current S3 locations:**

- Staging: `s3://bluemoxon-images-staging/prompts/napoleon-framework/v2.md` (UPDATED)
- Production: `s3://bluemoxon-images/prompts/napoleon-framework/v2.md` (NOT UPDATED)

## OLD Format Detection Pattern (Reference)

**OLD format indicators:**

1. Empty code blocks at start: ` ```\n``` `
2. Starts with `## 1. Executive Summary` (no H1 title)
3. All-caps header: `# PROFESSIONAL VALUATION`

**NEW format:**

- Starts with `# Professional Valuation Report: [Title]` or similar H1 header

## Commands Reference

```bash
# Check extraction status
bmx-api --prod GET '/books/{id}/analysis' | jq '{id: .book_id, status: .extraction_status}'

# Check format type
bmx-api --prod GET '/books/{id}/analysis/raw' | head -c 60

# Full regeneration (async)
bmx-api --prod POST '/books/{id}/analysis/generate-async'

# Re-extract only (Stage 2)
bmx-api --prod POST '/books/{id}/re-extract'

# Check provenance fields
bmx-api --prod GET '/books/{id}' | jq '{has_provenance, provenance, provenance_tier}'
```
