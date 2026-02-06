# Wave 3: BMX 3.0 Closeout - Subagent Dispatch Plan

**Date:** 2026-01-28
**Status:** Wave 1 (new files) complete. Wave 2 (integration) pending.
**Goal:** Close ALL remaining bmx 3.0 issues via parallel subagents.

## Remaining Open Issues (17)

| # | Title | Type | Area |
|---|-------|------|------|
| #1426 | API 307 redirect trailing slash | bug fix | frontend |
| #1425 | Keyboard shortcuts ? key not working | bug fix | frontend |
| #1423 | Phase 2.0 low-pri code review (4 items) | chore | mixed |
| #1421 | CORS Authorization header | bug fix | backend |
| #1356 | Optimize O(n²) edge generation | optimization | backend |
| #1347 | Timeline historical event markers | integration | frontend |
| #1346 | Mini-map navigation overlay | integration | frontend |
| #1345 | Filter count badges | integration | frontend |
| #1344 | Keyboard shortcuts help modal | integration | frontend |
| #1343 | Find Similar in bio panel | integration | frontend |
| #1342 | Layout mode switcher | integration | frontend |
| #1336 | Analytics tracking | integration | frontend |
| #1335 | Unit and E2E test coverage | tests | frontend |
| #1327 | Mobile optimization | integration | frontend |
| #1326 | Degrees of separation | integration | frontend |
| #1325 | Statistics panel | integration | frontend |
| #1324 | Search to find person in graph | integration | frontend |
| #1316 | Parent umbrella (close last) | - | - |

## Wave 1 Status: COMPLETE

All standalone files exist:
- 14 components, 8 composables, 2 backend files
- 24+ test files (composables, components, backend)
- Composable index.ts already exports everything

## File Conflict Map

Critical shared files and which tasks touch them:

```
SocialCirclesView.vue  ← Search, Stats, PathFinder, FindSimilar, Keyboard, Analytics, Mobile
NetworkGraph.vue       ← LayoutSwitcher, MiniMap, Mobile
useSocialCircles.ts    ← centerOnNode, highlightPath (Search, PathFinder integrations)
useUrlState.ts         ← layout param (LayoutSwitcher)
useNetworkKeyboard.ts  ← ? key handler (Keyboard)
NodeFloatingCard.vue   ← FindSimilar button
FilterPanel.vue        ← FilterBadges, Mobile
TimelineSlider.vue     ← TimelineMarkers
backend/app/main.py    ← CORS fix
```

---

## Dispatch Plan

### WAVE A: 15 parallel subagents (no file conflicts)

#### Independent Bug Fixes (4 subagents)

**A1: CORS Authorization Header**
- Branch: `fix/cors-authorization-header`
- File: `backend/app/main.py`
- Closes: #1421
- Work: Replace `allow_headers=["*"]` with explicit list `["Authorization", "Content-Type", "X-API-Key", "X-Requested-With"]`
- Validate: `poetry run ruff check backend/` and `poetry run ruff format --check backend/`

**A2: Trailing Slash Fix**
- Branch: `fix/social-circles-trailing-slash`
- File: `frontend/src/composables/socialcircles/useNetworkData.ts` (or wherever API URL is constructed)
- Closes: #1426
- Work: Add trailing slash to social-circles API endpoint URL
- Validate: `npm run --prefix frontend lint` and `npm run --prefix frontend type-check`

**A3: Backend O(n²) Optimization**
- Branch: `fix/social-circles-edge-optimization`
- File: `backend/app/services/social_circles.py`
- Closes: #1356
- Work: Optimize shared_publisher edge generation. Current approach iterates all author pairs per publisher. Use adjacency sets or pre-computed edge index to avoid O(n²).
- Validate: `poetry run ruff check backend/` and `poetry run pytest backend/tests/api/v1/test_social_circles.py`

**A4: Benchmark Concurrent Mode**
- Branch: `fix/benchmark-concurrent-mode`
- File: `backend/scripts/benchmark_social_circles.py`
- Partially closes: #1423
- Work: Add `--concurrent` flag using `asyncio.gather` for load testing
- Validate: `poetry run ruff check backend/`

#### Code Review Fixes (3 subagents)

**A5: KeyboardShortcutsModal Focus Trap**
- Branch: `fix/keyboard-modal-focus-trap`
- File: `frontend/src/components/socialcircles/KeyboardShortcutsModal.vue`
- Partially closes: #1423
- Work: Consolidate keydown listener and focus trap into a single watcher on `isOpen`
- Validate: `npm run --prefix frontend lint` and `npm run --prefix frontend type-check`

**A6: MiniMap Layoutstop Cleanup**
- Branch: `fix/minimap-layoutstop-cleanup`
- File: `frontend/src/components/socialcircles/MiniMap.vue`
- Partially closes: #1423
- Work: Store layoutstop handler reference, remove specifically instead of `cy.off("layoutstop")`
- Validate: `npm run --prefix frontend lint` and `npm run --prefix frontend type-check`

**A7: PathFinderPanel Filtering Perf**
- Branch: `fix/pathfinder-filtering-perf`
- File: `frontend/src/components/socialcircles/PathFinderPanel.vue`
- Partially closes: #1423
- Work: Optimize computed filtering for large node lists - early termination, limit upstream
- Validate: `npm run --prefix frontend lint` and `npm run --prefix frontend type-check`

#### Missing Utils Tests (4 subagents)

**A8: graphAlgorithms Tests**
- Branch: `test/graph-algorithms`
- File: `frontend/src/utils/socialcircles/__tests__/graphAlgorithms.test.ts`
- Partially closes: #1335
- Work: Test `findShortestPath`, `buildAdjacencyList`, `calculateGraphStats`, `findHubs`, `findSimilarNodes`. Read the source at `frontend/src/utils/socialcircles/graphAlgorithms.ts` first.
- Validate: `npm run --prefix frontend test -- --run --reporter=verbose src/utils/socialcircles/__tests__/graphAlgorithms.test.ts`

**A9: layoutConfigs Tests**
- Branch: `test/layout-configs`
- File: `frontend/src/utils/socialcircles/__tests__/layoutConfigs.test.ts`
- Partially closes: #1335
- Work: Test `getLayoutConfig` for all modes, `LAYOUT_MODE_LABELS`, `AVAILABLE_LAYOUTS`. Read the source at `frontend/src/utils/socialcircles/layoutConfigs.ts` first.
- Validate: `npm run --prefix frontend test -- --run --reporter=verbose src/utils/socialcircles/__tests__/layoutConfigs.test.ts`

**A10: colorPalettes Tests**
- Branch: `test/color-palettes`
- File: `frontend/src/utils/socialcircles/__tests__/colorPalettes.test.ts`
- Partially closes: #1335
- Work: Test all exports from `frontend/src/utils/socialcircles/colorPalettes.ts`. Read the source first.
- Validate: `npm run --prefix frontend test -- --run --reporter=verbose src/utils/socialcircles/__tests__/colorPalettes.test.ts`

**A11: dataTransformers Tests**
- Branch: `test/data-transformers`
- File: `frontend/src/utils/socialcircles/__tests__/dataTransformers.test.ts`
- Partially closes: #1335
- Work: Test all exports from `frontend/src/utils/socialcircles/dataTransformers.ts`. Read the source first.
- Validate: `npm run --prefix frontend test -- --run --reporter=verbose src/utils/socialcircles/__tests__/dataTransformers.test.ts`

#### Feature Integration Bundles (4 subagents, each owns distinct files)

**A12: SocialCirclesView Integration (MEGA)**
- Branch: `feat/social-circles-view-integration`
- Files OWNED (only this subagent touches):
  - `frontend/src/views/SocialCirclesView.vue` (primary)
  - `frontend/src/composables/socialcircles/useSocialCircles.ts`
- Closes: #1324, #1325, #1326, #1336, #1343, #1344, #1425
- Work:
  1. Import and wire SearchInput into toolbar area (#1324)
  2. Import and wire StatsPanel, collapsed state (#1325)
  3. Import and wire PathFinderPanel with path highlighting (#1326)
  4. Import FindSimilarButton into NodeFloatingCard event handler (#1343)
  5. Import and wire KeyboardShortcutsModal + fix ? key (#1344, #1425)
  6. Wire useAnalytics into event handlers (#1336)
  7. Add `centerOnNode(nodeId)` to useSocialCircles.ts
  8. Add `highlightPath(path)` to useSocialCircles.ts
- Validate: `npm run --prefix frontend lint` and `npm run --prefix frontend type-check`
- NOTE: Do NOT touch NetworkGraph.vue, FilterPanel.vue, or TimelineSlider.vue

**A13: NetworkGraph Integration**
- Branch: `feat/network-graph-integration`
- Files OWNED (only this subagent touches):
  - `frontend/src/components/socialcircles/NetworkGraph.vue`
  - `frontend/src/composables/socialcircles/useUrlState.ts`
- Closes: #1342, #1346
- Work:
  1. Import LayoutSwitcher, add to controls area (#1342)
  2. Import MiniMap, add toggleable overlay (#1346)
  3. Wire useLayoutMode to apply layout on mode change
  4. Add `layout` parameter to useUrlState.ts
- Validate: `npm run --prefix frontend lint` and `npm run --prefix frontend type-check`
- NOTE: Do NOT touch SocialCirclesView.vue

**A14: FilterPanel Integration**
- Branch: `feat/filter-badges`
- Files OWNED:
  - `frontend/src/components/socialcircles/FilterPanel.vue`
- Closes: #1345
- Work: Import FilterBadges component, add count badges next to each filter checkbox. Pass node counts as props.
- Validate: `npm run --prefix frontend lint` and `npm run --prefix frontend type-check`
- NOTE: Do NOT touch SocialCirclesView.vue or NetworkGraph.vue

**A15: Timeline Markers Integration**
- Branch: `feat/timeline-markers`
- Files OWNED:
  - `frontend/src/components/socialcircles/TimelineSlider.vue`
- Closes: #1347
- Work: Import TimelineMarkers component, add historical event markers to timeline track. Position markers based on year range.
- Validate: `npm run --prefix frontend lint` and `npm run --prefix frontend type-check`
- NOTE: Do NOT touch SocialCirclesView.vue

---

### WAVE B: 6 parallel subagents (after Wave A merges)

**B1: FindSimilar NodeFloatingCard Integration**
- Branch: `feat/find-similar-integration`
- Files OWNED:
  - `frontend/src/components/socialcircles/NodeFloatingCard.vue`
- Closes: #1343 (completes what A12 started - A12 wires the handler, B1 adds the button)
- Work: Import FindSimilarButton, add to card actions area, emit `find-similar` event
- Validate: `npm run --prefix frontend lint`

**B2: Mobile Responsive Integration**
- Branch: `feat/mobile-optimization`
- Files modified:
  - `frontend/src/views/SocialCirclesView.vue`
  - `frontend/src/components/socialcircles/FilterPanel.vue`
  - `frontend/src/components/socialcircles/NetworkGraph.vue`
- Closes: #1327
- Work:
  1. Add responsive layout to SocialCirclesView (desktop vs mobile)
  2. Wire BottomSheet + MobileFilterFab for mobile filter access
  3. Adjust node size on mobile for touch targets
  4. Adjust FilterPanel for vertical stacking on narrow screens
- Validate: `npm run --prefix frontend lint` and `npm run --prefix frontend type-check`

**B3-B6: E2E Tests (4 parallel)**

**B3: Search E2E**
- Branch: `test/e2e-search`
- File: `frontend/tests/e2e/socialcircles-search.spec.ts`
- Partially closes: #1335
- Tests: search input visible, typing shows results, selecting centers graph, keyboard nav, no results state

**B4: Layout E2E**
- Branch: `test/e2e-layout`
- File: `frontend/tests/e2e/socialcircles-layout.spec.ts`
- Partially closes: #1335
- Tests: switcher visible, clicking changes layout, URL persistence, keyboard shortcut L

**B5: Statistics E2E**
- Branch: `test/e2e-stats`
- File: `frontend/tests/e2e/socialcircles-stats.spec.ts`
- Partially closes: #1335
- Tests: panel shows counts, stats update with filters, collapse/expand

**B6: Path Finder E2E**
- Branch: `test/e2e-path`
- File: `frontend/tests/e2e/socialcircles-path.spec.ts`
- Partially closes: #1335
- Tests: panel accessible, node selection, path highlights, narrative display, no-path state

---

### WAVE C: Final (after Wave B merges)

**C1: Close Umbrella Issue**
- Close #1316 (parent issue) once all child issues are closed
- Close #1423 once all 4 sub-items are addressed (A4, A5, A6, A7)
- Close #1335 once sufficient test coverage is confirmed

---

## Issue Closure Map

| Issue | Closed By | Wave |
|-------|-----------|------|
| #1421 | A1 | A |
| #1426 | A2 | A |
| #1356 | A3 | A |
| #1423 | A4 + A5 + A6 + A7 | A |
| #1324 | A12 | A |
| #1325 | A12 | A |
| #1326 | A12 | A |
| #1336 | A12 | A |
| #1344 | A12 | A |
| #1425 | A12 | A |
| #1342 | A13 | A |
| #1346 | A13 | A |
| #1345 | A14 | A |
| #1347 | A15 | A |
| #1343 | A12 + B1 | A+B |
| #1327 | B2 | B |
| #1335 | A8-A11 + B3-B6 | A+B |
| #1316 | C1 (umbrella) | C |

## Execution Summary

| Wave | Subagents | Parallel? | Prerequisite |
|------|-----------|-----------|-------------|
| A | 15 | All parallel | None |
| B | 6 | All parallel | Wave A merged to staging |
| C | 1 | N/A | Wave B merged |

**Total: 22 subagent tasks → closes 17 issues → completes bmx 3.0**

## PR Strategy

Each subagent branch PRs to staging with squash merge.
After all Wave A branches merge, create Wave B branches from updated staging.
After all merged: promote staging → main with merge commit.

PR title format: `<type>(<scope>): <description> (#issue)`
PR body should include `Closes #XXXX` for auto-closure.
