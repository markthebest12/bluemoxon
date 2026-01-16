# Session: Dashboard Tooltip Enhancements

**Date:** 2026-01-12 to 2026-01-13
**Branch:** `feat/tooltip-improvements`, `fix/binder-schema-dashboard-fields`
**PRs:** #1099, #1100, #1101
**Status:** MERGED TO PRODUCTION

## Background

After PR #1098 (tooltip clipping fixes), additional tooltip enhancements were requested:

1. **Tooltip cuts off on left edge** - When trigger element is near left viewport edge
2. **"ON_HAND" text** - Should display as "On Hand" in tooltip descriptions
3. **Binder tooltips incomplete** - Only showed full_name, needed operation dates and book list
4. **Author/Publisher chart tooltips** - Work on bar hover, user expected label tooltips too

## Changes Made

### Frontend

1. **BaseTooltip.vue** - Added viewport boundary clamping
   - Added `tooltipRef` and `tooltipOffset` refs
   - Added `clampToViewport()` function called after render
   - Applied offset to prevent left/right edge clipping

2. **constants/index.ts** - Changed "ON_HAND" to "On Hand" in descriptions

3. **chartHelpers.ts** - NEW: Y-axis label tooltip plugin
   - `yAxisLabelTooltipPlugin` - Chart.js plugin that detects hover over Y-axis labels
   - Shows custom tooltip with entity metadata (era, dates, descriptions)
   - Works for both author and publisher horizontal bar charts

4. **StatisticsDashboard.vue** - Enhanced tooltips
   - Added `formatBinderYears()` helper for operation dates
   - Added `formatBinderTooltip()` helper showing: full name, operation years, book count, sample titles
   - Added `formatAuthorLabelTooltip()` for author axis labels
   - Added `formatPublisherLabelTooltip()` for publisher axis labels
   - Registered `yAxisLabelTooltipPlugin` with Chart.js
   - Added `labelTooltips` to author and publisher chart options

5. **types/dashboard.ts** - Added to BinderData:
   - `founded_year?: number | null`
   - `closed_year?: number | null`
   - `sample_titles?: string[]`
   - `has_more?: boolean`

6. **types/admin.ts** - Added to BinderEntity:
   - `founded_year?: number | null`
   - `closed_year?: number | null`

### Backend

1. **app/api/v1/stats.py**
   - Added `batch_fetch_sample_titles()` helper function (reduces code duplication)
   - Refactored `query_by_author()` to use helper
   - Refactored `query_bindings()` to use helper with additional filter

2. **app/models/binder.py** - Added columns:

   ```python
   founded_year: Mapped[int | None] = mapped_column(Integer)
   closed_year: Mapped[int | None] = mapped_column(Integer)
   ```

3. **alembic/versions/z2012345ghij_add_binder_operation_years.py** - Migration

4. **tests/test_stats.py** - Added 6 new binder tests:
   - `test_bindings_includes_founded_and_closed_year`
   - `test_bindings_handles_null_founded_and_closed_year`
   - `test_bindings_sample_titles_limit`
   - `test_bindings_has_more_flag`
   - `test_bindings_multiple_binders_sample_titles`

## Verification

- Frontend: All 564 tests pass, lint/type-check clean
- Backend: All 72 stats tests pass, ruff check/format clean

---

## Code Review Round 2 (2026-01-12)

### Issues Identified

| Priority | Issue | Verdict |
|----------|-------|---------|
| P0-1 | Memory leak in Y-axis tooltip plugin | VALID - Fixed |
| P0-2 | Event listener stacking in BaseTooltip | INVALID - Browsers deduplicate |
| P1-3 | Hit detection assumes uniform label spacing | VALID - Fixed |
| P1-4 | Race condition in clampToViewport RAF | INVALID - show() resets offset |
| P1-5 | Inconsistent has_more logic | INVALID - Filters consistent |
| P2-6 | ERA_DEFINITIONS dead code | VALID - Removed |
| P2-7 | Default days changed 30→90 | VALID - Documented |
| P2-8 | Bar/label tooltips show same info | VALID - Differentiated |
| P3-9 | Missing type on fk_column | VALID - Added |
| P3-10 | Test order assumption | INVALID - Uses membership check |
| P3-11 | beforeDestroy naming | INVALID - Chart.js API, not Vue |

### Fixes Applied

1. **P0-1: Memory Leak** (`chartHelpers.ts`)
   - Added `activeChartCount` to track charts using the tooltip
   - Added `removeTooltip()` function to properly remove from DOM
   - `afterInit` increments counter, `beforeDestroy` decrements
   - Tooltip only removed when last chart is destroyed

2. **P1-3: Hit Detection** (`chartHelpers.ts`)
   - Changed from `yScale.height / labels.length` (uniform assumption)
   - Now uses actual `getPixelForTick(i-1)` and `getPixelForTick(i+1)`
   - Hit box calculated from midpoints between adjacent ticks

3. **P2-6: Dead Code** (`constants/index.ts`)
   - Removed `ERA_DEFINITIONS` and `EraDefinition` type
   - Added comment: era definitions now served by API

4. **P2-7: Default Days** (`stores/dashboard.ts`)
   - Added comment explaining 90-day default (was 30)
   - Documents this was intentional UX change in PR #1099

5. **P2-8: Tooltip Differentiation** (`StatisticsDashboard.vue`)
   - **Bar tooltip**: Now shows only count ("15 books across 3 titles")
   - **Label tooltip**: Shows full context (era, lifespan, sample titles)
   - Removed dead code: `TOOLTIP_LINE_LENGTH`, `TOOLTIP_WRAP_THRESHOLD`

6. **P3-9: Type Annotation** (`stats.py`)
   - Added `InstrumentedAttribute[int | None]` type to `fk_column` parameter
   - Added import from `sqlalchemy.orm.attributes`

### Invalid Issues (Pushed Back)

- **P0-2 (Event listeners)**: Browsers deduplicate identical addEventListener calls per MDN
- **P1-4 (RAF race)**: `show()` resets `tooltipOffset.value.x = 0` before making visible
- **P1-5 (has_more)**: Both queries use identical filters, counts match
- **P3-10 (Test order)**: Tests use `in` operator (membership), not list comparison
- **P3-11 (beforeDestroy)**: This is Chart.js plugin API, not Vue lifecycle

---

## Post-Merge Bug Fix (PR #1100)

### Issue Discovered

After PR #1099 was merged to staging, testing revealed binder tooltips were NOT showing sample titles. The API returned bindings without `founded_year`, `closed_year`, `sample_titles`, `has_more` fields.

### Root Cause (Systematic Debugging)

**Data Flow Traced:**

1. `/stats/bindings` endpoint → Returns all fields ✓
2. `/stats/dashboard` endpoint → Missing fields ✗
3. Traced to `DashboardResponse` schema using `list[BinderData]`
4. `BinderData` Pydantic schema was missing 4 fields

**Root Cause:** `query_bindings()` returned all fields, but Pydantic silently dropped them during serialization because `BinderData` schema didn't define them.

### Fix (TDD)

1. **RED:** Wrote failing test `test_dashboard_bindings_include_enhanced_fields`
2. **GREEN:** Added missing fields to `BinderData` schema:

   ```python
   founded_year: int | None = None
   closed_year: int | None = None
   sample_titles: list[str] = Field(default_factory=list)
   has_more: bool = False
   ```

3. **VERIFY:** All 73 stats tests pass

### Lesson Learned

**Tests weren't written when features were added.** If PR #1099 had included a test verifying "dashboard endpoint returns binder sample_titles", this bug would have been caught before merge.

---

## Production Promotion (PR #1101)

- PR #1099 + #1100 merged to staging
- Migration verified on staging
- Binder tooltips verified working in browser
- Promoted to production via PR #1101

## Files Modified

### Initial Implementation

```text
frontend/src/components/BaseTooltip.vue
frontend/src/components/dashboard/StatisticsDashboard.vue
frontend/src/components/dashboard/chartHelpers.ts
frontend/src/constants/index.ts
frontend/src/types/admin.ts
frontend/src/types/dashboard.ts
backend/app/api/v1/stats.py
backend/app/models/binder.py
backend/alembic/versions/z2012345ghij_add_binder_operation_years.py
backend/tests/test_stats.py
```

### Code Review Round 2 Fixes

```text
frontend/src/components/dashboard/chartHelpers.ts  # Memory leak, hit detection
frontend/src/components/dashboard/StatisticsDashboard.vue  # Tooltip differentiation
frontend/src/constants/index.ts  # Removed ERA_DEFINITIONS dead code
frontend/src/stores/dashboard.ts  # Document 90-day default
backend/app/api/v1/stats.py  # Type annotation
```

---

## CRITICAL REMINDERS FOR NEXT SESSION

### 1. ALWAYS Use Superpowers Skills

Invoke relevant skills BEFORE any response or action:

- `superpowers:brainstorming` - Before any creative/feature work
- `superpowers:systematic-debugging` - For ANY bug/test failure
- `superpowers:test-driven-development` - Before writing implementation code
- `superpowers:verification-before-completion` - Before claiming work is done
- `superpowers:receiving-code-review` - When getting PR feedback

**If a skill might apply (even 1% chance), invoke it.**

### 2. NEVER Use These Bash Patterns (Permission Prompts)

```bash
# BAD - triggers permission prompts:
# Comment lines before commands
command1 \
  --with-continuation
$(command substitution)
command1 && command2
command1 || command2
password='Test1234!'  # ! gets expanded
```

### 3. ALWAYS Use These Patterns

```bash
# GOOD - no permission prompts:
simple-single-line-command --flag value
```

For sequential operations, use **separate Bash tool calls** instead of `&&`.

For API calls, use `bmx-api`:

```bash
bmx-api GET /books
bmx-api --prod GET /books/123
```

### 4. Git Commands

```bash
# Stage files
git add file1 file2

# Commit with HEREDOC (separate call)
git commit -m "$(cat <<'EOF'
Message here

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"

# Push (separate call)
git push -u origin branch-name
```
