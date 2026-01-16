# Session: Dashboard Chart Improvements

**Date:** 2026-01-12
**Issue:** #1093
**Branch:** TBD

## Summary

Improve dashboard charts:

1. Human-readable condition labels (NEAR_FINE → "Near Fine")
2. Extend value growth chart from 30 days to 3 months (90 days)

## Findings from Codebase Search

### Condition Labels

- **Frontend constants**: `frontend/src/constants/index.ts` lines 62-90
  - `CONDITION_GRADES` enum and `CONDITION_GRADE_OPTIONS` with display labels
- **Backend stats**: `backend/app/services/dashboard_stats.py` lines 77-84
  - Condition grade display formatting, NULL → "Ungraded"
- **Dashboard chart**: `frontend/src/components/dashboard/StatisticsDashboard.vue`
  - Lines 353-365: `conditionChartData` computed property
  - Lines 323-347: Color mappings for each condition

### Value Growth Chart

- **Backend API**: `backend/app/api/v1/stats.py` line 612
  - `days: int = Query(default=30, ge=7, le=90...)` - hardcoded default
- **Dashboard service**: `backend/app/services/dashboard_stats.py` line 214
  - `get_dashboard_optimized()` with `days: int = 30`
- **Frontend**: `StatisticsDashboard.vue` lines 262-277, 588-603
  - Title: "Est. Value Growth (Last 30 Days)"

### Existing Formatting Utilities

- `frontend/src/utils/format.ts` - formatBytes, formatCost
- `frontend/src/composables/useFormatters.ts` - formatAnalysisIssues
- `frontend/src/constants/index.ts` - CONDITION_GRADE_OPTIONS has label property

## Implementation Plan

1. **Centralize condition label formatting** in `frontend/src/utils/format.ts`
   - Create `formatConditionGrade(grade: string): string` function
   - Use existing `CONDITION_GRADE_OPTIONS` labels or generate from enum

2. **Update dashboard chart** to use formatted labels
   - Modify `conditionChartData` computed property

3. **Change value growth to 90 days**
   - Backend: Change default in `dashboard_stats.py` and `stats.py`
   - Frontend: Update chart title

## TDD Approach

Write tests first for:

- [ ] `formatConditionGrade()` utility function
- [ ] Backend 90-day default change

## Progress

- [x] Created GitHub issue #1093
- [x] Create feature branch `fix/chart-improvements-1093`
- [x] Write failing tests (TDD RED phase)
  - `frontend/src/utils/format.test.ts` - 9 tests for formatConditionGrade()
  - `backend/tests/test_stats.py::TestAcquisitionsDailyDefaults` - 2 tests for 90-day default
- [x] Implement changes (TDD GREEN phase)
  - `frontend/src/utils/format.ts` - Added formatConditionGrade() function
  - `backend/app/services/dashboard_stats.py` - Changed default from 30 to 90 days
  - `backend/app/api/v1/stats.py` - Changed default from 30 to 90 days, extended le from 90 to 180
- [x] All tests pass (553 frontend + 2 backend)
- [x] Update frontend chart
  - `StatisticsDashboard.vue` - Use formatConditionGrade() for labels
  - `StatisticsDashboard.vue` - Change title to "Last 3 Months"
- [ ] PR to staging (user review)
- [ ] Merge to staging
- [ ] PR to main (user review)
- [ ] Deploy to production

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/utils/format.ts` | Added `formatConditionGrade()` function |
| `frontend/src/utils/format.test.ts` | NEW - 9 tests for formatConditionGrade() |
| `frontend/src/components/dashboard/StatisticsDashboard.vue` | Import formatter, use for labels, update title |
| `backend/app/services/dashboard_stats.py` | `days: int = 90` (was 30) |
| `backend/app/api/v1/stats.py` | `days: int = Query(default=90, ge=7, le=180...)` |
| `backend/tests/test_stats.py` | Added TestAcquisitionsDailyDefaults class |
