# Dashboard Charts: Condition Grade & Category

**Date:** 2026-01-09
**Issue:** #965
**Status:** Approved

## Summary

Add two doughnut charts to the dashboard: "Books by Condition Grade" and "Books by Category".

## Architecture

```text
Backend                          Frontend
────────────────────────────────────────────────────
/stats/by-condition (NEW)   →   ConditionData[]
/stats/by-category (EXISTS) →   CategoryData[]
        ↓
/stats/dashboard (UPDATE)   →   DashboardStats (extended)
        ↓
StatisticsDashboard.vue     →   Two new <Doughnut> components
```

## Backend Changes

### New Endpoint: `/stats/by-condition`

```python
@router.get("/by-condition")
def get_by_condition(db: Session = Depends(get_db)):
    """Get counts by condition grade."""
    results = (
        db.query(
            Book.condition_grade,
            func.count(Book.id),
            func.sum(Book.value_mid),
        )
        .filter(Book.inventory_type == "PRIMARY")
        .group_by(Book.condition_grade)
        .all()
    )

    return [
        {
            "condition": row[0] or "Ungraded",
            "count": row[1],
            "value": safe_float(row[2]),
        }
        for row in results
    ]
```

### Update `/stats/dashboard`

Add to batch response:

- `by_condition`: from `get_by_condition(db)`
- `by_category`: from `get_by_category(db)` (already exists)

### Schema Updates (`schemas/stats.py`)

```python
class ConditionData(BaseModel):
    condition: str
    count: int
    value: float

class CategoryData(BaseModel):
    category: str
    count: int
    value: float

class DashboardResponse(BaseModel):
    # ...existing fields...
    by_condition: list[ConditionData]
    by_category: list[CategoryData]
```

## Frontend Changes

### Type Updates (`types/dashboard.ts`)

```typescript
export interface ConditionData {
  condition: string;
  count: number;
  value: number;
}

export interface CategoryData {
  category: string;
  count: number;
  value: number;
}

export interface DashboardStats {
  // ...existing fields...
  by_condition: ConditionData[];
  by_category: CategoryData[];
}
```

### Chart Components (`StatisticsDashboard.vue`)

Two new doughnut charts using existing `doughnutOptions`:

```typescript
const conditionChartData = computed(() => ({
  labels: props.data.by_condition.map((d) => d.condition),
  datasets: [{
    data: props.data.by_condition.map((d) => d.count),
    backgroundColor: [
      chartColors.primary,      // Fine
      chartColors.hunter700,    // Very Good
      chartColors.gold,         // Good
      chartColors.goldMuted,    // Fair
      chartColors.burgundy,     // Poor
      chartColors.inkMuted,     // Ungraded
    ],
    borderWidth: 0,
  }],
}));

const categoryChartData = computed(() => ({
  labels: props.data.by_category.map((d) => d.category),
  datasets: [{
    data: props.data.by_category.map((d) => d.count),
    backgroundColor: [/* rotating Victorian colors */],
    borderWidth: 0,
  }],
}));
```

### Grid Placement

Insert after "Top Tier 1 Publishers", before "Est. Value Growth":

- Books by Condition Grade (left column)
- Books by Category (right column)

## Testing

### Backend Tests

```python
def test_get_by_condition(client, db_session):
    """Test condition grade distribution endpoint."""
    # Create books with different conditions
    # Verify counts and null handling ("Ungraded")

def test_dashboard_includes_condition_and_category(client, db_session):
    """Test dashboard batch includes new fields."""
    # Verify by_condition and by_category in response
```

### Frontend Behavior

- Charts render with data
- Empty state shows appropriate message
- Tooltip shows count and percentage

## Edge Cases

- All books have null condition → single "Ungraded" slice
- All books in one category → single slice
- No books at all → "No data available" message

## Acceptance Criteria

- [ ] Books by Condition Grade chart displays on dashboard
- [ ] Books by Category chart displays on dashboard
- [ ] Charts handle empty/null values gracefully
- [ ] Charts follow existing Victorian design system colors

## Out of Scope

Per issue #965, these are lower priority and not included:

- First Editions Count
- Provenance Breakdown
- Acquisition Spend
