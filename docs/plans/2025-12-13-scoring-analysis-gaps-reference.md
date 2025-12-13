# Scoring & Analysis Flow Gaps Analysis

**Date:** December 12, 2025
**Books Compared:** #489 (exemplar - manual flow) vs #501 (automated flow)
**Reference:** `example_quality_acquisition_flow.md`

---

## Executive Summary

The automated acquisition flow (book 501) produces detailed analysis but:
1. Valuation data doesn't get extracted to book record
2. Scoring methodology doesn't match the exemplar strategic fit scoring
3. Key book fields (notes, provenance, condition_grade) aren't populated
4. Investment grade = 0 because FMV data doesn't flow through

---

## Problem 1: Valuation Data Format Mismatch

### Current Parser Expects:
```markdown
| Low | $450 |
| Mid | $550 |
| High | $650 |
```

Pattern in `markdown_parser.py:160-171`:
```python
low_match = re.search(r"Low\s*\|?\s*\$?([\d,]+)", text)
mid_match = re.search(r"Mid\s*\|?\s*\$?([\d,]+)", text)
high_match = re.search(r"High\s*\|?\s*\$?([\d,]+)", text)
```

### Automated Analysis Generates:
```markdown
**Retail Value Range:** $650-$900
**Most Likely Market Value:** $725-$800
```

### Fix Required:
Enhance parser to extract from multiple formats:
```python
# Also match range formats
range_match = re.search(r"Retail Value Range[:\s]*\$?([\d,]+)[–-]\$?([\d,]+)", text)
if range_match:
    result["valuation"]["low"] = int(range_match.group(1).replace(",", ""))
    result["valuation"]["high"] = int(range_match.group(2).replace(",", ""))
    # Calculate mid from range
    result["valuation"]["mid"] = (result["valuation"]["low"] + result["valuation"]["high"]) // 2

# Also match "Most Likely Market Value"
likely_match = re.search(r"Most Likely Market Value[:\s]*\$?([\d,]+)[–-]?\$?([\d,]+)?", text)
```

---

## Problem 2: Scoring Methodology Gaps

### Exemplar Strategic Fit (200 point max):

| Component | Points | Description |
|-----------|--------|-------------|
| Authenticated Binder | +40 | Tier 1 binder (Zaehnsdorf, Riviere, etc.) |
| Tier 1 Publisher | +35 | Macmillan, Smith Elder, etc. |
| Tier 2 Publisher | +15 | |
| Victorian Era (1837-1901) | +20 | |
| Romantic Era (1800-1836) | +20 | |
| Complete Set | +15 | |
| Good+ Condition | +15 | |
| New Author | +30 | First work by author in collection |
| 4+ Volumes | -10 | Storage consideration |
| 5+ Volumes | -20 | (current code) |
| **DOUBLE TIER 1 Bonus** | +15 | Tier 1 Publisher + Tier 1 Binder |

### Current Code Missing:

1. **Binder Tier scoring** - NOT IMPLEMENTED
   - Needs `binder_tier` field on book or lookup from binder relationship
   - Add to `calculate_strategic_fit()`:
     ```python
     if binder_tier == "TIER_1":
         score += 40
     elif binder_tier == "TIER_2":
         score += 20
     ```

2. **DOUBLE TIER 1 bonus** - NOT IMPLEMENTED
   - When both publisher AND binder are Tier 1
   - Add to scoring:
     ```python
     if publisher_tier == "TIER_1" and binder_tier == "TIER_1":
         score += 15  # DOUBLE TIER 1 bonus
     ```

3. **Volume penalty scale** - PARTIAL
   - Current: -20 for 5+ volumes
   - Exemplar: -10 for 4 volumes
   - Consider graduated scale

### Book 501 Score Breakdown:

| Component | Current | Should Be | Gap |
|-----------|---------|-----------|-----|
| investment_grade | 0 | ~70 (50% discount) | -70 (no FMV data) |
| strategic_fit | 70 | 115+ | -45 (missing binder) |
| collection_impact | 30 | 30 | ✓ |
| **overall_score** | **100** | **~215** | **-115** |

---

## Problem 3: Book Fields Not Populated

### Book 501 Current State:
```json
{
  "notes": null,
  "provenance": null,
  "category": null,
  "condition_grade": null,
  "binding_description": null,
  "value_low": null,
  "value_mid": null,
  "value_high": null
}
```

### Data Available in Analysis:
- **Condition Grade:** "Good+ to Very Good-"
- **Binding:** "Half leather (niger morocco spine, blue buckram boards)"
- **Notes:** Key points from executive summary
- **Provenance:** Legal motto panel suggests institutional origin

### Fix Required:
Either enhance parser or add dedicated extraction step after analysis generation:
```python
# In books.py after analysis generation
if parsed.condition_assessment:
    if "condition_grade" in parsed.condition_assessment:
        book.condition_grade = parsed.condition_assessment["condition_grade"]
    if "binding_type" in parsed.condition_assessment:
        book.binding_description = parsed.condition_assessment["binding_type"]
```

---

## Problem 4: Investment Grade = 0

### Root Cause:
```python
# scoring.py:55-56
if purchase_price is None or value_mid is None:
    return 0
```

Book 501:
- `purchase_price = 502.05` ✓
- `value_mid = null` ✗ → Returns 0

### Actual Value (from analysis):
- Retail Value Range: $650-$900
- Most Likely Market Value: $725-$800
- **Discount:** ($750 - $502) / $750 = 33% → Should be ~35 points

---

## Recommended Implementation Order

### Phase 1: Parser Enhancement (Quick Win)
1. Add multi-format valuation extraction to `markdown_parser.py`
2. Test with book 501 analysis
3. Re-run `/books/501/analysis/reparse` to populate FMV

### Phase 2: Scoring Enhancement
1. Add `binder_tier` field to Book model (or lookup from Binder)
2. Add binder scoring to `calculate_strategic_fit()`
3. Add DOUBLE TIER 1 bonus logic
4. Update tests

### Phase 3: Prompt Enhancement
1. Update napoleon-framework prompt to require parseable valuation format
2. Add sections for extractable book fields
3. Test with fresh analysis generation

### Phase 4: Field Extraction
1. Extract condition_grade from condition assessment
2. Extract binding_description
3. Generate notes from executive summary key points

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/utils/markdown_parser.py` | Add multi-format valuation extraction |
| `backend/app/services/scoring.py` | Add binder_tier, DOUBLE TIER 1 bonus |
| `backend/app/api/v1/books.py` | Populate book fields from parsed analysis |
| `infrastructure/prompts/napoleon-framework/v1.md` | Require parseable format |
| `backend/tests/test_scoring.py` | Add binder tier tests |

---

## Comparison: Book 489 vs 501

| Aspect | Book 489 (Exemplar) | Book 501 (Automated) |
|--------|---------------------|---------------------|
| Value Low | $450 | null |
| Value Mid | $550 | null |
| Value High | $650 | null |
| Condition Grade | VG | null |
| Notes | Populated | null |
| Provenance | Populated | null |
| Investment Grade | 70 | 0 |
| Strategic Fit | 85 | 70 |
| Collection Impact | 30 | 30 |
| **Overall Score** | **185** | **100** |

Both are the same book (J.R. Green, Zaehnsdorf binding) - the gap is entirely due to data extraction failures.
