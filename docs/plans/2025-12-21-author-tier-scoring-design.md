# Author Tier Scoring Design

**Issue:** #528
**Date:** 2025-12-21
**Status:** Approved

---

## Problem

Book 521 (Darwin's "Power of Movement in Plants") shows "Charles Darwin - not a priority author" despite Darwin being a TOP PRIORITY for 2026 acquisition goals.

**Root cause:** All authors have `priority_score: 0` - no author priorities configured.

---

## Solution

Add author tier system matching existing publisher/binder pattern.

### Author Tiers

| Tier | Authors | Bonus | Rationale |
|------|---------|-------|-----------|
| TIER_1 | Darwin, Lyell | +15 | Victorian Science - strategic dimension |
| TIER_2 | Dickens, Collins | +10 | Victorian Novelists - established collecting |
| TIER_3 | Ruskin | +5 | Art Criticism - developing interest |

### Scoring Integration

- Author tier bonus adds to strategic_fit score
- Stacks with publisher tier (Darwin + John Murray = +15 + +15 = +30)
- Stacks with binder tier (Darwin + Murray + Rivière = +30 + +20 = +50)

### Display Change

Book detail shows "Charles Darwin - Tier 1 author" instead of "not a priority author"

---

## Data Changes

### Authors to Update (5)

| Author | ID | Tier |
|--------|-----|------|
| Charles Darwin | 34 | TIER_1 |
| Charles Lyell | (create) | TIER_1 |
| Charles Dickens | 250 | TIER_2 |
| W. Wilkie Collins | 335 | TIER_2 |
| John Ruskin | 260 | TIER_3 |

### Publishers to Update (2)

| Publisher | ID | Tier |
|-----------|-----|------|
| Chatto and Windus | 193 | TIER_2 |
| George Allen | 197 | TIER_2 |

### Binders to Update (3)

| Binder | ID | Tier |
|--------|-----|------|
| Bayntun | 4 | TIER_1 (upgrade from TIER_2) |
| Leighton, Son & Hodge | 27 | TIER_1 (from null) |
| Hayday | (create) | TIER_1 |

---

## Implementation

1. **Schema:** Add `tier` enum field to authors table
2. **Scoring:** Update `backend/app/services/scoring.py` to include author tier bonus
3. **Frontend:** Update book detail to display author tier
4. **Data:** Apply tier updates via migration

---

## Effect on Book 521

Before:
- Author: "Charles Darwin - not a priority author" (+0)
- Publisher: D. Appleton (null) (+0)
- Strategic fit: 50

After:
- Author: "Charles Darwin - Tier 1 author" (+15)
- Publisher: D. Appleton (null) (+0)
- Strategic fit: 65

---

## References

- Acquisition guide: `~/projects/book-collection/documentation/Victorian_Book_Acquisition_Guide.md`
- January targets: `~/projects/book-collection/documentation/January_2026_Acquisition_Targets.md`
