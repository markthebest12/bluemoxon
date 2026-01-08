# Session Log: Issue #904 - Trend Chart "Today" Bug

**Date:** 2026-01-08
**Issue:** [#904](https://github.com/bluemoxon/bluemoxon/issues/904)
**Type:** Bug fix (frontend)

## Problem Statement

When hovering over the trend chart (Est. Value Growth chart), the tooltip always says "Added today:" regardless of which day's data point is being hovered.

## Root Cause Analysis

**File:** `frontend/src/components/dashboard/StatisticsDashboard.vue`
**Line:** 74

```typescript
// Current (buggy)
return [
  `Total: $${day.cumulative_value.toLocaleString()}`,
  `Added today: ${day.count} items ($${day.value.toLocaleString()})`,  // BUG
];
```

The string `"Added today:"` is hardcoded. The `AcquisitionDay` interface has a `label` property that contains the actual formatted date label (e.g., "Jan 5", "Dec 31").

## Solution

Use `day.label` instead of hardcoded "today":

```typescript
// Fixed
return [
  `Total: $${day.cumulative_value.toLocaleString()}`,
  `Added ${day.label}: ${day.count} items ($${day.value.toLocaleString()})`,
];
```

## Implementation Plan

1. Create failing test for tooltip callback
2. Fix the bug
3. Verify test passes
4. Run full lint/type-check
5. Create PR to staging

## Progress

- [x] Root cause identified
- [x] Failing test written (`StatisticsDashboard.spec.ts`)
- [x] Bug fixed (extracted `formatAcquisitionTooltip` to `chartHelpers.ts`)
- [x] Tests pass (348 tests)
- [x] Lint/type-check pass
- [ ] PR created
