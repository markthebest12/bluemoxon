# Score Transparency Design

**Goal:** Add visibility into why a book scored the way it did, with inline warnings for issues like duplicates.

**Problem:** The scoring engine works correctly, but when a book scores low (e.g., 15 PASS), the UI doesn't explain why. A duplicate penalty of -40 points isn't visible without digging into the data.

---

## Solution Summary

1. **API returns score breakdown** — The calculate endpoint returns detailed factors for each score component
2. **Tooltip breakdowns** — Hover on each score row to see what contributed
3. **Inline warnings** — Subtle text warning when issues like duplicates are detected

---

## API Changes

### Modified Endpoint: `POST /books/{id}/scores/calculate`

Returns expanded response with `details` object:

```json
{
  "investment_grade": 35,
  "strategic_fit": 55,
  "collection_impact": 15,
  "overall_score": 105,
  "details": {
    "investment": {
      "discount_percent": 33.2,
      "purchase_price": 701.25,
      "value_mid": 1050.00,
      "tier": "30-39%",
      "points": 35
    },
    "strategic": {
      "factors": [
        {"name": "publisher_tier", "label": "Tier 1 Publisher (Blackwood)", "points": 35},
        {"name": "era", "label": "Victorian Era (1866)", "points": 20},
        {"name": "condition", "label": "Condition (not set)", "points": 0},
        {"name": "complete_set", "label": "Complete Set (not set)", "points": 0},
        {"name": "author_priority", "label": "Author Priority (not seeded)", "points": 0}
      ],
      "points": 55
    },
    "collection": {
      "factors": [
        {"name": "author_gap", "label": "Fills author gap (1 existing)", "points": 15}
      ],
      "warnings": [],
      "points": 15
    }
  }
}
```

### When duplicate detected:

```json
"collection": {
  "factors": [
    {"name": "author_gap", "label": "Fills author gap (1 existing)", "points": 15},
    {"name": "duplicate", "label": "Duplicate: Felix Holt (ID: 498)", "points": -40}
  ],
  "warnings": ["duplicate"],
  "points": -25
}
```

### Details returned on demand only

- `GET /books` and `GET /books/{id}` return scores but NOT details (keeps payloads small)
- Details only returned from `POST /books/{id}/scores/calculate`
- Frontend caches details after recalculate call

---

## Frontend UI

### Score Card with Tooltips

```
┌─────────────────────────────────────────┐
│ Felix Holt, the Radical                 │
│ George Eliot • 3 vols • $701            │
│ FMV: $1,050                             │
├─────────────────────────────────────────┤
│ SCORE: 105        ████████░░ CONDITIONAL│
├─────────────────────────────────────────┤
│ Investment  [████░░░░░░]  35  (i)       │  ← hover shows discount breakdown
│ Strategic   [█████░░░░░]  55  (i)       │  ← hover shows factor list
│ Collection  [██░░░░░░░░]  15  (i)       │  ← hover shows author/duplicate info
├─────────────────────────────────────────┤
│ ⚠️ Duplicate detected                   │  ← only shows when warning present
├─────────────────────────────────────────┤
│ [Recalculate]              [Acquire]    │
└─────────────────────────────────────────┘
```

### Tooltip Content

**Investment Grade:**
```
33% discount ($701 / $1,050 FMV)
→ 35 points (30-39% tier)
```

**Strategic Fit:**
```
+35  Tier 1 Publisher (Blackwood)
+20  Victorian Era (1866)
 +0  Condition (not set)
 +0  Complete Set (not set)
 +0  Author Priority (not seeded)
───
 55  total
```

**Collection Impact:**
```
+15  Fills author gap (1 existing)
-40  Duplicate: "Felix Holt" (ID: 498)
───
-25  total
```

### Styling

- Zero-point factors: muted gray text
- Negative factors: red text
- Warning line: small muted text, only visible when `warnings` array is non-empty

---

## Implementation

### Backend Changes

1. Modify `scoring.py` functions to return breakdown alongside scores:
   - `calculate_investment_grade()` → returns `{points, discount_percent, tier}`
   - `calculate_strategic_fit()` → returns `{points, factors[]}`
   - `calculate_collection_impact()` → returns `{points, factors[], warnings[], duplicate_book_id?}`

2. Modify `books.py` endpoint to include `details` in calculate response

3. Track duplicate book ID when detected for inclusion in label

### Frontend Changes

1. Add tooltip component to score rows (hover/tap to show)
2. Add conditional warning line below scores
3. Cache score details in component state after recalculate
4. Style factors by point value (gray for 0, red for negative)

### No Database Changes

The breakdown is computed on-the-fly from existing book/author/publisher data.

---

## Warning Types

| Warning Key | Trigger | Display Text |
|-------------|---------|--------------|
| `duplicate` | Duplicate title detected | "Duplicate detected" |
| `missing_valuation` | `value_mid` is null | "Missing valuation data" |
| `missing_condition` | `condition` is null | "Condition not set" |

Only `duplicate` warning implemented initially. Others can be added later if useful.
