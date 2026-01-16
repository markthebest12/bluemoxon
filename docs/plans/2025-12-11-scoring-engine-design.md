# Scoring Engine Design

**Goal:** Add automated scoring to help prioritize book acquisitions and analyze the collection.

**Key Decisions:**

- Three component scores + overall composite score
- Auto-calculate on create, on-demand refresh for existing
- Author priorities stored in database (editable)
- Fuzzy title matching for duplicate detection
- Scores visible for all book statuses

---

## Data Model

### Books Table (new fields)

```sql
-- Component scores (0-100 each, collection_impact can go negative)
investment_grade      INTEGER  -- Discount-based tiered score
strategic_fit         INTEGER  -- Publisher tier + era + author priority
collection_impact     INTEGER  -- Duplicate penalty, author gap bonus, set completion

-- Overall composite score
overall_score         INTEGER  -- Sum of components (0-300+, bonuses can exceed)

-- Metadata
scores_calculated_at  TIMESTAMP  -- When scores were last computed
```

### Authors Table (new field)

```sql
priority_score        INTEGER DEFAULT 0  -- Bonus points (Hardy=50, Darwin=50, etc.)
```

---

## Scoring Algorithms

### Investment Grade (0-100)

Based on discount percentage: `discount = (value_mid - purchase_price) / value_mid * 100`

| Discount | Points | Rationale |
|----------|--------|-----------|
| 70%+ | 100 | Exceptional deal |
| 60-69% | 85 | Strong buy |
| 50-59% | 70 | Good value |
| 40-49% | 55 | Meets minimum threshold |
| 30-39% | 35 | Below target |
| 20-29% | 20 | Marginal |
| <20% | 5 | Poor investment |
| No price data | 0 | Cannot calculate |

### Strategic Fit (0-100+)

| Factor | Points | Source |
|--------|--------|--------|
| Tier 1 Publisher | 35 | `publishers.tier` |
| Tier 2 Publisher | 15 | `publishers.tier` |
| Victorian/Romantic Era (1800-1901) | 20 | `publication_date` |
| Complete Set | 15 | `volumes` field or `is_complete` |
| Condition Good+ | 15 | `condition` field |
| Author Priority | 0-50 | `authors.priority_score` |

### Collection Impact (0-100, can go negative)

| Factor | Points | Detection |
|--------|--------|-----------|
| New author to collection | +30 | 0 existing books by author |
| Fills author gap | +15 | 1 existing book by author |
| Duplicate title detected | -40 | Fuzzy match >= 80% |
| Completes incomplete set | +25 | Manual flag or future detection |
| Large set penalty (5+ vols) | -20 | `volumes >= 5` |

### Overall Score

```
overall_score = investment_grade + strategic_fit + collection_impact
```

**Decision thresholds:**

- 160+: STRONG BUY (green)
- 120-159: BUY (yellow)
- 80-119: CONDITIONAL (orange)
- <80: PASS (red)

---

## API Endpoints

### New Endpoints

```
POST /books/{id}/scores/calculate
  - Recalculates all scores for a single book
  - Returns: { investment_grade, strategic_fit, collection_impact, overall_score }
  - Called: on-demand via UI button

POST /books/scores/calculate-all
  - Batch recalculates scores for all books (admin only)
  - Returns: { updated_count, errors[] }
  - Called: manual trigger
```

### Modified Endpoints

```
POST /books
  - Auto-calculates scores after book creation
  - Returns book with scores populated

GET /books
  - Scores included in response
  - New query params: ?min_score=120&sort_by=overall_score

GET /books/{id}
  - Scores included in response
```

---

## Frontend - Acquisitions Dashboard

### EVALUATING Cards (full breakdown)

```
┌─────────────────────────────────────────┐
│ Felix Holt, the Radical                 │
│ George Eliot • 3 vols • $701            │
├─────────────────────────────────────────┤
│ SCORE: 185  ████████████░░ STRONG BUY   │
├─────────────────────────────────────────┤
│ Investment    65  ██████░░░░  (52% off) │
│ Strategic     70  ███████░░░  Tier 1    │
│ Collection    50  █████░░░░░  New author│
├─────────────────────────────────────────┤
│ [⚡ Analysis] [📊 Recalc] [✓ Acquire]   │
└─────────────────────────────────────────┘
```

### Score Badge Colors

| Score | Color | Label |
|-------|-------|-------|
| 160+ | Green | STRONG BUY |
| 120-159 | Yellow | BUY |
| 80-119 | Orange | CONDITIONAL |
| <80 | Red | PASS |

### IN_TRANSIT and ON_HAND Columns

Compact display: badge + number only (decision already made).

---

## Duplicate Detection

### Fuzzy Title Matching

```python
def is_duplicate(new_book, existing_books):
    """Check if new_book duplicates any existing book by same author."""
    same_author = [b for b in existing_books if b.author_id == new_book.author_id]

    for existing in same_author:
        similarity = fuzzy_match(normalize(new_book.title), normalize(existing.title))
        if similarity >= 0.8:  # 80% threshold
            return True, existing.id

    return False, None

def normalize(title):
    """Normalize for comparison: lowercase, remove articles, punctuation."""
    return title.lower().strip()
           .replace("the ", "").replace("a ", "")
           .replace("'s", "").replace(":", "")
```

### Author Gap Detection

```python
def get_author_book_count(author_id, exclude_book_id=None):
    """Count how many books we have by this author."""
    # Returns 0 = new author (+30 pts)
    # Returns 1 = fills gap (+15 pts)
    # Returns 2+ = no bonus
```

---

## Initial Author Priority Data

Based on ACQUISITION_EVALUATION_PROTOCOL.md bonus modifiers:

| Author | Priority Score |
|--------|---------------|
| Thomas Hardy | 50 |
| Charles Darwin | 50 |
| Charles Lyell | 40 |
| James Clerk Maxwell | 40 |
| Charles Dickens | 30 |
| Thomas Carlyle | 25 |
| John Ruskin | 25 |
| Wilkie Collins | 20 |

---

## Implementation Notes

1. **Migration:** Add new columns to books and authors tables
2. **Backfill:** Run calculate-all to score existing books
3. **Testing:** Unit tests for each scoring component
4. **Performance:** Duplicate detection queries should be indexed on author_id
