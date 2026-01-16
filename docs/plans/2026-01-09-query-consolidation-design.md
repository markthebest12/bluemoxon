# Query Consolidation Design (#1001)

**Date:** 2026-01-09
**Issue:** #1001 - Consolidate dashboard stats queries with GROUPING SETS
**Status:** Approved

## Summary

Reduce dashboard database queries from 14 to 7 by consolidating simple aggregations using PostgreSQL GROUPING SETS and conditional aggregation.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Scope | Moderate consolidation | 57% query reduction, keeps complex queries separate |
| Code structure | Dashboard-only | Hot path optimization, no API breaking changes |
| Testing | Parallel execution | Gold standard correctness during refactor |

## Query Consolidation Strategy

### GROUPING SETS for Dimensions

Consolidate `by_condition`, `by_category`, and `by_era` into one query:

```sql
SELECT
    condition_grade,
    category,
    CASE WHEN COALESCE(year_start, year_end) BETWEEN 1837 AND 1901 THEN 'Victorian' ... END as era,
    GROUPING(condition_grade) as g_condition,
    GROUPING(category) as g_category,
    COUNT(*) as count,
    SUM(value_mid) as value
FROM books
WHERE inventory_type = 'PRIMARY'
GROUP BY GROUPING SETS (
    (condition_grade),
    (category),
    (era_case)
)
```

### Conditional Aggregation for Overview

Consolidate 6 overview queries into 1:

```sql
SELECT
    COUNT(*) FILTER (WHERE status = 'ON_HAND') as on_hand_count,
    COUNT(*) FILTER (WHERE status = 'IN_TRANSIT') as in_transit_count,
    SUM(value_mid) FILTER (WHERE status = 'ON_HAND') as on_hand_value,
    SUM(value_low) FILTER (WHERE status = 'ON_HAND') as on_hand_value_low,
    SUM(value_high) FILTER (WHERE status = 'ON_HAND') as on_hand_value_high,
    SUM(volumes) FILTER (WHERE status = 'ON_HAND') as on_hand_volumes,
    COUNT(*) FILTER (WHERE binding_authenticated AND status = 'ON_HAND') as authenticated_count,
    COUNT(*) FILTER (WHERE purchase_date >= :week_ago AND status = 'ON_HAND') as week_count,
    SUM(value_mid) FILTER (WHERE purchase_date >= :week_ago AND status = 'ON_HAND') as week_value,
    SUM(volumes) FILTER (WHERE purchase_date >= :week_ago AND status = 'ON_HAND') as week_volumes,
    COUNT(*) FILTER (WHERE binding_authenticated AND purchase_date >= :week_ago AND status = 'ON_HAND') as week_authenticated
FROM books
WHERE inventory_type = 'PRIMARY'
```

## Code Architecture

### New Module

```text
backend/app/services/
└── dashboard_stats.py    # Consolidated query functions
```

### Functions

```python
def get_dimension_stats(db: Session) -> dict:
    """Single GROUPING SETS query for condition/category/era."""
    # Returns: {"by_condition": [...], "by_category": [...], "by_era": [...]}

def get_overview_stats(db: Session) -> dict:
    """Single query for all overview counts/values."""
    # Returns: {"primary": {...}, "extended": {...}, "week_delta": {...}, ...}

def get_dashboard_optimized(db: Session, reference_date, days) -> DashboardResponse:
    """Main entry point - 7 queries total."""
```

### Endpoint Change

```python
# stats.py
@router.get("/dashboard")
def get_dashboard(...):
    return get_dashboard_optimized(db, reference_date, days)
```

## Testing Strategy

### Phase 1: Parallel Comparison (during refactor)

```python
def test_dimension_stats_matches_individual_endpoints(db_with_books):
    old_condition = get_by_condition(db)
    consolidated = get_dimension_stats(db)
    assert consolidated["by_condition"] == old_condition
```

### Phase 2: Property Tests (kept after refactor)

```python
def test_dimension_counts_sum_to_total(db_with_books):
    stats = get_dimension_stats(db)
    total = sum(item["count"] for item in stats["by_condition"])
    assert total == get_primary_book_count(db)
```

## Query Count

| Before | After |
|--------|-------|
| get_overview: ~6 | get_overview_stats: 1 |
| by_condition: 1 | get_dimension_stats: 1 |
| by_category: 1 | (included above) |
| by_era: 1 | (included above) |
| bindings: 1 | bindings: 1 |
| by_publisher: 1 | by_publisher: 1 |
| by_author: 2 | by_author: 2 |
| acquisitions_daily: 1 | acquisitions_daily: 1 |
| **Total: 14** | **Total: 7** |

## Implementation Steps

1. Create git worktree for isolated work
2. TDD: Write failing parallel comparison tests
3. Implement `get_dimension_stats()` with GROUPING SETS
4. Implement `get_overview_stats()` with FILTER clauses
5. Wire up `get_dashboard_optimized()`
6. Remove parallel tests, keep property tests
7. Create PR targeting staging

## Related

- Issue: #1001
- Follow-up: #1002 (caching layer - after this is merged)
