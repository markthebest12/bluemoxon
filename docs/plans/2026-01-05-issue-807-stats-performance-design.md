# Design: Stats Endpoint Performance Optimization (Issue #807)

**Date:** 2026-01-05
**Issue:** #807 - perf: get_collection_metrics loads ALL books into memory

## Problem

Several stats endpoints load all books into memory and iterate in Python, causing:
1. Memory usage scales with collection size
2. Python loops slower than SQL aggregation
3. Unnecessary - all calculations can be done in SQL

## Affected Endpoints

| Endpoint | Issue | Location |
|----------|-------|----------|
| `get_collection_metrics` | `.all()` + Python loops | stats.py:117-179 |
| `get_by_era` | `.all()` + Python loops | stats.py:323-366 |
| `get_overview` | `week_arrivals.all()` + loops | stats.py:75-88 |
| `get_by_author` | N+1 query for sample titles | stats.py:262-274 |

## Solution

Replace Python iteration with SQL aggregation using `func.count()`, `func.sum()`, `func.avg()`, and SQL `CASE` expressions.

### 1. `get_collection_metrics`

**Before:** Load all books, iterate for Victorian count, averages, totals.

**After:** Single aggregation query:

```python
from sqlalchemy import case

victorian_case = case(
    (
        (Book.year_start.between(1800, 1901)) |
        (Book.year_end.between(1800, 1901)),
        1
    ),
    else_=0
)

result = db.query(
    func.count(Book.id).label("total"),
    func.sum(victorian_case).label("victorian_count"),
    func.avg(Book.discount_pct).label("avg_discount"),
    func.avg(Book.roi_pct).label("avg_roi"),
    func.sum(Book.purchase_price).label("total_purchase"),
    func.sum(Book.value_mid).label("total_value"),
).filter(Book.inventory_type == "PRIMARY").first()
```

### 2. `get_by_era`

**Before:** Load all books, categorize by year in Python loop.

**After:** SQL CASE with GROUP BY:

```python
year_col = func.coalesce(Book.year_start, Book.year_end)

era_case = case(
    (year_col.is_(None), literal("Unknown")),
    (year_col < 1800, literal("Pre-Romantic (before 1800)")),
    (year_col.between(1800, 1836), literal("Romantic (1800-1837)")),
    (year_col.between(1837, 1901), literal("Victorian (1837-1901)")),
    (year_col.between(1902, 1910), literal("Edwardian (1901-1910)")),
    else_=literal("Post-1910")
).label("era")

results = db.query(
    era_case,
    func.count(Book.id).label("count"),
    func.sum(Book.value_mid).label("value"),
).filter(Book.inventory_type == "PRIMARY").group_by(era_case).all()
```

**Bug fix included:** Pre-1800 books now get "Pre-Romantic" category instead of being mislabeled as "Post-1910".

### 3. `get_overview` Week Deltas

**Before:** `week_arrivals.all()` then Python loops.

**After:** Single aggregation:

```python
week_delta = db.query(
    func.count(Book.id).label("count"),
    func.coalesce(func.sum(Book.volumes), func.count(Book.id)).label("volumes"),
    func.coalesce(func.sum(Book.value_mid), 0).label("value"),
    func.sum(case((Book.binding_authenticated.is_(True), 1), else_=0)).label("authenticated"),
).filter(
    on_hand_filter,
    Book.purchase_date >= one_week_ago,
).first()
```

### 4. `get_by_author` N+1 Fix

**Before:** Main query + N separate queries for sample titles.

**After:** Two-query batch approach:

```python
# Query 1: Aggregation (unchanged)
results = db.query(...).group_by(Author.id).all()
author_ids = [row[0] for row in results]

# Query 2: Batch fetch sample titles using window function
subq = db.query(
    Book.author_id,
    Book.title,
    func.row_number().over(partition_by=Book.author_id).label("rn")
).filter(
    Book.author_id.in_(author_ids),
    Book.inventory_type == "PRIMARY"
).subquery()

sample_titles_rows = db.query(
    subq.c.author_id,
    subq.c.title
).filter(subq.c.rn <= 5).all()

# Build lookup dict
titles_by_author = defaultdict(list)
for author_id, title in sample_titles_rows:
    titles_by_author[author_id].append(title)
```

## Testing Strategy

**Existing tests:** All 4 endpoints have tests verifying response structure/values - serve as regression tests.

**New tests to add:**
1. `test_metrics_victorian_year_end_fallback` - Books with only year_end in Victorian range
2. `test_by_era_pre_romantic` - Verify pre-1800 books get correct category
3. `test_by_author_sample_titles_batch` - Verify batch query populates correctly

**TDD approach:**
1. Write failing tests for edge cases first
2. Refactor endpoint implementations
3. Verify existing tests still pass

## API Compatibility

**No breaking changes.** Response schemas remain identical - pure internal optimization.

## Compatibility

All SQL must work with both:
- PostgreSQL (production)
- SQLite (tests)

Window functions (`ROW_NUMBER()`) are supported by both.
