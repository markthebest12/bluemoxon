# Design: Data Normalization + Clickable Chart Links

**Date:** 2026-01-09
**Issues:** #1006, #1008
**Status:** Approved

## Summary

Two related improvements to the dashboard:

1. **#1006:** Normalize `condition_grade` data to eliminate case inconsistencies
2. **#1008:** Make all dashboard charts clickable, navigating to filtered book lists

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Normalization method | DB Migration | One-time fix, no runtime overhead |
| Chart scope | All 8 charts | Complete user experience |
| Acquisitions click | Filter by date | Requires new `date_acquired` filter |

## Part 1: Data Normalization (#1006)

### Problem

The `condition_grade` field has mixed casing: "Good" vs "GOOD", "Fair" vs "FAIR".

### Solution

New Alembic migration with idempotent SQL:

```sql
UPDATE books
SET condition_grade = UPPER(condition_grade)
WHERE condition_grade IS NOT NULL
  AND condition_grade != UPPER(condition_grade);
```

### Files

- `backend/alembic/versions/xxxx_normalize_condition_grade_casing.py`

## Part 2: Clickable Charts (#1008)

### Chart → Filter Mapping

| Chart | Type | Click Target | Filter Param |
|-------|------|--------------|--------------|
| Condition | Doughnut | Slice label | `condition_grade=GOOD` |
| Category | Doughnut | Slice label | `category=Victorian Poetry` |
| Era | Bar | Bar label | `era=Victorian` |
| Bindings | Bar | Binder name | `binder_id=123` |
| Authors | Bar | Author name | `author_id=456` |
| Publishers | Bar | Publisher name | `publisher_id=789` |
| Acquisitions | Line | Date point | `date_acquired=2026-01-05` |

### Backend Changes

**New filter param** in `BookListParams`:

```python
date_acquired: date | None = None
```

**Query filter** in books endpoint:

```python
if params.date_acquired:
    query = query.filter(func.date(Book.date_acquired) == params.date_acquired)
```

### Frontend Changes

**1. Extend URL sync** (`BooksView.vue`):
Add these filters to `updateUrlWithFilters()`:

- `condition_grade`
- `category`
- `era`
- `binder_id`
- `binding_authenticated`
- `author_id`
- `publisher_id`
- `date_acquired`

**2. Add click handlers** (`StatisticsDashboard.vue`):

```typescript
onClick: (event, elements) => {
  if (elements.length > 0) {
    const label = chartData.labels[elements[0].index];
    router.push({ path: '/books', query: { filter_param: label } });
  }
}
```

### Files to Modify

- `backend/app/schemas/book.py` - add date_acquired param
- `backend/app/api/v1/books.py` - add date filter logic
- `frontend/src/stores/books.ts` - add date_acquired to Filters
- `frontend/src/views/BooksView.vue` - extend URL sync
- `frontend/src/components/dashboard/StatisticsDashboard.vue` - add click handlers

## Implementation Plan

| Branch | Scope |
|--------|-------|
| `fix/1006-condition-normalization` | Migration only |
| `feat/1008-clickable-charts` | Backend filter + frontend changes |

## Testing

### Backend

- Migration: verify idempotent, normalizes all variants
- API: `date_acquired` filter returns correct books

### Frontend

- Chart clicks navigate with correct query params
- URL sync round-trips all filter params
- Back button restores filters correctly
