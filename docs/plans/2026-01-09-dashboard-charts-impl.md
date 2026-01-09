# Dashboard Charts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add "Books by Condition Grade" and "Books by Category" doughnut charts to the dashboard.

**Architecture:** Backend adds `/stats/by-condition` endpoint and includes both `by_condition` and `by_category` in the dashboard batch response. Frontend adds two new doughnut charts using existing chart patterns.

**Tech Stack:** Python/FastAPI, SQLAlchemy, Pydantic (backend); Vue 3, TypeScript, Chart.js (frontend)

---

## Task 1: Backend - Add ConditionData Schema

**Files:**
- Modify: `backend/app/schemas/stats.py:96` (before DashboardResponse)

**Step 1: Add ConditionData and CategoryData models**

Add after `AcquisitionDay` class (line 94), before `DashboardResponse`:

```python
class ConditionData(BaseModel):
    """Books grouped by condition grade."""

    condition: str
    count: int
    value: float


class CategoryData(BaseModel):
    """Books grouped by category."""

    category: str
    count: int
    value: float
```

**Step 2: Update DashboardResponse to include new fields**

Modify `DashboardResponse` class to add:

```python
class DashboardResponse(BaseModel):
    """Complete dashboard statistics response."""

    overview: OverviewStats
    bindings: list[BinderData]
    by_era: list[EraData]
    by_publisher: list[PublisherData]
    by_author: list[AuthorData]
    acquisitions_daily: list[AcquisitionDay]
    by_condition: list[ConditionData]
    by_category: list[CategoryData]
```

**Step 3: Run type check**

Run: `cd backend && poetry run python -c "from app.schemas.stats import DashboardResponse, ConditionData, CategoryData; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add backend/app/schemas/stats.py
git commit -m "feat(backend): add ConditionData and CategoryData schemas"
```

---

## Task 2: Backend - Write Failing Test for by-condition Endpoint

**Files:**
- Modify: `backend/tests/test_stats.py` (add new test class after TestStatsByCategory)

**Step 1: Write failing test class**

Add after `TestStatsByCategory` class (around line 501):

```python
class TestStatsByCondition:
    """Tests for GET /api/v1/stats/by-condition."""

    def test_by_condition_empty(self, client):
        """Test with no books returns empty list."""
        response = client.get("/api/v1/stats/by-condition")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_by_condition_groups_by_grade(self, client):
        """Test condition grade distribution."""
        client.post(
            "/api/v1/books",
            json={"title": "Fine Book 1", "condition_grade": "Fine"},
        )
        client.post(
            "/api/v1/books",
            json={"title": "Fine Book 2", "condition_grade": "Fine"},
        )
        client.post(
            "/api/v1/books",
            json={"title": "Good Book", "condition_grade": "Good"},
        )

        response = client.get("/api/v1/stats/by-condition")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        fine = next((c for c in data if c["condition"] == "Fine"), None)
        assert fine is not None
        assert fine["count"] == 2

        good = next((c for c in data if c["condition"] == "Good"), None)
        assert good is not None
        assert good["count"] == 1

    def test_by_condition_null_becomes_ungraded(self, client):
        """Test null condition_grade shows as Ungraded."""
        client.post(
            "/api/v1/books",
            json={"title": "Ungraded Book"},
        )

        response = client.get("/api/v1/stats/by-condition")
        assert response.status_code == 200
        data = response.json()

        ungraded = next((c for c in data if c["condition"] == "Ungraded"), None)
        assert ungraded is not None
        assert ungraded["count"] == 1

    def test_by_condition_includes_value(self, client):
        """Test response includes value sum."""
        client.post(
            "/api/v1/books",
            json={"title": "Valued Book", "condition_grade": "VG", "value_mid": 150.00},
        )

        response = client.get("/api/v1/stats/by-condition")
        assert response.status_code == 200
        data = response.json()

        vg = next((c for c in data if c["condition"] == "VG"), None)
        assert vg is not None
        assert vg["value"] == 150.00
```

**Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/test_stats.py::TestStatsByCondition -v`
Expected: FAIL with "404 Not Found" (endpoint doesn't exist yet)

**Step 3: Commit failing test**

```bash
git add backend/tests/test_stats.py
git commit -m "test(backend): add failing tests for by-condition endpoint"
```

---

## Task 3: Backend - Implement by-condition Endpoint

**Files:**
- Modify: `backend/app/api/v1/stats.py` (add new endpoint after get_by_category)

**Step 1: Add get_by_condition endpoint**

Add after `get_by_category` function (around line 221):

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

**Step 2: Run tests to verify they pass**

Run: `cd backend && poetry run pytest tests/test_stats.py::TestStatsByCondition -v`
Expected: 4 passed

**Step 3: Commit implementation**

```bash
git add backend/app/api/v1/stats.py
git commit -m "feat(backend): add /stats/by-condition endpoint"
```

---

## Task 4: Backend - Write Failing Test for Dashboard Batch Update

**Files:**
- Modify: `backend/tests/test_stats.py` (add test for dashboard including new fields)

**Step 1: Find or create TestDashboard class, add test**

If `TestDashboard` class exists, add to it. Otherwise create it:

```python
class TestDashboard:
    """Tests for GET /api/v1/stats/dashboard."""

    def test_dashboard_includes_condition_and_category(self, client):
        """Test dashboard batch includes by_condition and by_category."""
        client.post(
            "/api/v1/books",
            json={
                "title": "Test Book",
                "condition_grade": "Fine",
                "category": "Victorian Poetry",
            },
        )

        response = client.get("/api/v1/stats/dashboard")
        assert response.status_code == 200
        data = response.json()

        # Check new fields exist
        assert "by_condition" in data
        assert "by_category" in data

        # Check condition data
        assert len(data["by_condition"]) >= 1
        fine = next((c for c in data["by_condition"] if c["condition"] == "Fine"), None)
        assert fine is not None

        # Check category data
        assert len(data["by_category"]) >= 1
        poetry = next(
            (c for c in data["by_category"] if c["category"] == "Victorian Poetry"), None
        )
        assert poetry is not None
```

**Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/test_stats.py::TestDashboard::test_dashboard_includes_condition_and_category -v`
Expected: FAIL with KeyError or missing field

**Step 3: Commit failing test**

```bash
git add backend/tests/test_stats.py
git commit -m "test(backend): add failing test for dashboard batch with condition/category"
```

---

## Task 5: Backend - Update Dashboard Batch Endpoint

**Files:**
- Modify: `backend/app/api/v1/stats.py:587-616` (get_dashboard function)

**Step 1: Update get_dashboard to include new data**

Modify the `get_dashboard` function to call and return the new data:

```python
@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    reference_date: str = Query(
        default=None,
        description="Reference date in YYYY-MM-DD format (defaults to today UTC)",
    ),
    days: int = Query(default=30, ge=7, le=90, description="Number of days for acquisitions"),
) -> DashboardResponse:
    """Get all dashboard statistics in a single request.

    Combines: overview, bindings, by-era, by-publisher, by-author, acquisitions-daily,
    by-condition, by-category.
    This reduces API calls for the dashboard.
    """
    # Reuse existing endpoint logic
    overview = get_overview(db)
    bindings = get_bindings(db)
    by_era = get_by_era(db)
    by_publisher = get_by_publisher(db)
    by_author = get_by_author(db)
    acquisitions_daily = get_acquisitions_daily(db, reference_date, days)
    by_condition = get_by_condition(db)
    by_category = get_by_category(db)

    return {
        "overview": overview,
        "bindings": bindings,
        "by_era": by_era,
        "by_publisher": by_publisher,
        "by_author": by_author,
        "acquisitions_daily": acquisitions_daily,
        "by_condition": by_condition,
        "by_category": by_category,
    }
```

**Step 2: Run tests to verify they pass**

Run: `cd backend && poetry run pytest tests/test_stats.py::TestDashboard -v`
Expected: PASS

**Step 3: Run all stats tests**

Run: `cd backend && poetry run pytest tests/test_stats.py -v --tb=short`
Expected: All tests pass

**Step 4: Commit**

```bash
git add backend/app/api/v1/stats.py
git commit -m "feat(backend): include by_condition and by_category in dashboard batch"
```

---

## Task 6: Frontend - Add TypeScript Types

**Files:**
- Modify: `frontend/src/types/dashboard.ts`

**Step 1: Add ConditionData interface**

Add after `AuthorData` interface (around line 53):

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
```

**Step 2: Update DashboardStats interface**

Modify `DashboardStats` to include new fields:

```typescript
export interface DashboardStats {
  overview: OverviewStats;
  bindings: BinderData[];
  by_era: EraData[];
  by_publisher: PublisherData[];
  by_author: AuthorData[];
  acquisitions_daily: AcquisitionDay[];
  by_condition: ConditionData[];
  by_category: CategoryData[];
}
```

**Step 3: Run type check**

Run: `cd frontend && npm run type-check`
Expected: Error - StatisticsDashboard.vue doesn't handle new fields yet (this is expected)

**Step 4: Commit**

```bash
git add frontend/src/types/dashboard.ts
git commit -m "feat(frontend): add ConditionData and CategoryData types"
```

---

## Task 7: Frontend - Add Condition Grade Chart

**Files:**
- Modify: `frontend/src/components/dashboard/StatisticsDashboard.vue`

**Step 1: Add conditionChartData computed property**

Add after `publisherChartData` computed (around line 212):

```typescript
const conditionChartData = computed(() => ({
  labels: props.data.by_condition.map((d) => d.condition),
  datasets: [
    {
      data: props.data.by_condition.map((d) => d.count),
      backgroundColor: [
        chartColors.primary,
        chartColors.hunter700,
        chartColors.gold,
        chartColors.goldMuted,
        chartColors.burgundy,
        chartColors.burgundyLight,
        chartColors.inkMuted,
      ],
      borderWidth: 0,
    },
  ],
}));
```

**Step 2: Add chart template**

Add after "Top Tier 1 Publishers" div (around line 360), before the value growth chart:

```vue
<!-- Condition Grade Distribution -->
<div class="card-static p-4!">
  <h3 class="text-sm font-medium text-victorian-ink-muted uppercase tracking-wider mb-3">
    Books by Condition
  </h3>
  <div class="h-48 md:h-56">
    <Doughnut
      v-if="props.data.by_condition.length > 0"
      :data="conditionChartData"
      :options="doughnutOptions"
    />
    <p v-else class="text-victorian-ink-muted text-sm text-center py-8">
      No condition data available
    </p>
  </div>
</div>
```

**Step 3: Run type check**

Run: `cd frontend && npm run type-check`
Expected: Still error for by_category (expected)

**Step 4: Commit**

```bash
git add frontend/src/components/dashboard/StatisticsDashboard.vue
git commit -m "feat(frontend): add condition grade doughnut chart"
```

---

## Task 8: Frontend - Add Category Chart

**Files:**
- Modify: `frontend/src/components/dashboard/StatisticsDashboard.vue`

**Step 1: Add categoryChartData computed property**

Add after `conditionChartData`:

```typescript
const categoryChartData = computed(() => ({
  labels: props.data.by_category.map((d) => d.category),
  datasets: [
    {
      data: props.data.by_category.map((d) => d.count),
      backgroundColor: [
        chartColors.burgundy,
        chartColors.gold,
        chartColors.primary,
        chartColors.hunter700,
        chartColors.goldMuted,
        chartColors.burgundyLight,
        chartColors.inkMuted,
        chartColors.paperAntique,
      ],
      borderWidth: 0,
    },
  ],
}));
```

**Step 2: Add chart template**

Add after "Books by Condition" div:

```vue
<!-- Category Distribution -->
<div class="card-static p-4!">
  <h3 class="text-sm font-medium text-victorian-ink-muted uppercase tracking-wider mb-3">
    Books by Category
  </h3>
  <div class="h-48 md:h-56">
    <Doughnut
      v-if="props.data.by_category.length > 0"
      :data="categoryChartData"
      :options="doughnutOptions"
    />
    <p v-else class="text-victorian-ink-muted text-sm text-center py-8">
      No category data available
    </p>
  </div>
</div>
```

**Step 3: Run type check**

Run: `cd frontend && npm run type-check`
Expected: PASS (no errors)

**Step 4: Commit**

```bash
git add frontend/src/components/dashboard/StatisticsDashboard.vue
git commit -m "feat(frontend): add category doughnut chart"
```

---

## Task 9: Verify All Tests and Linting

**Step 1: Run backend tests**

Run: `cd backend && poetry run pytest tests/test_stats.py -v --tb=short`
Expected: All tests pass

**Step 2: Run backend linting**

Run: `cd backend && poetry run ruff check .`
Expected: No errors

Run: `cd backend && poetry run ruff format --check .`
Expected: No formatting issues

**Step 3: Run frontend linting**

Run: `cd frontend && npm run lint`
Expected: No errors

Run: `cd frontend && npm run format`
Expected: Formats any needed files

Run: `cd frontend && npm run type-check`
Expected: No errors

**Step 4: Commit any format fixes**

```bash
git add -A
git commit -m "style: format code" --allow-empty
```

---

## Task 10: Create PR to Staging

**Step 1: Push branch**

Run: `git push -u origin feat/965-dashboard-charts`

**Step 2: Create PR**

Run:
```bash
gh pr create --base staging --title "feat: Add condition and category charts to dashboard (#965)" --body "$(cat <<'EOF'
## Summary
- Add Books by Condition Grade doughnut chart
- Add Books by Category doughnut chart
- Backend: new `/stats/by-condition` endpoint
- Backend: updated dashboard batch to include both datasets
- Frontend: two new doughnut chart components

Closes #965

## Test Plan
- [ ] Backend tests pass
- [ ] Frontend type-check passes
- [ ] Charts display correctly on dashboard
- [ ] Empty states show appropriate messages

Generated with [Claude Code](https://claude.ai/code)
EOF
)"
```

**Step 3: Note PR number for review**

Record PR URL for user review before merging to staging.
