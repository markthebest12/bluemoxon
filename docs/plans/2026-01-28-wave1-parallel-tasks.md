# Parallel Task Specifications

**Date:** 2026-01-28
**Wave 1:** 45 independent tasks (new files only)
**Wave 2:** 12 integration + E2E tasks

## Closed Issues (Skip)
- ~~#1366~~ HoveredEdgeData duplication - closed by PR #1396
- ~~#1387~~ TIER_MAP satisfies - closed by PR #1396
- ~~#1409, #1412, #1414~~ - auto-closed

## Issues Covered
| Issue | Title | Tasks |
|-------|-------|-------|
| #1324 | Search | C1, C10, F1, T1 |
| #1325 | Statistics panel | C2, C12, F2, T2 |
| #1326 | Degrees of separation | C4, C11, F3, T3 |
| #1327 | Mobile optimization | C13, C14, F8, W2-1 |
| #1335 | Test coverage | T1-T18 |
| #1336 | Analytics | F6, T6 |
| #1342 | Layout switcher | C3, F7, T7 |
| #1343 | Find Similar | C5, F4, T4 |
| #1344 | Keyboard shortcuts | C9 |
| #1345 | Filter badges | C7 |
| #1346 | Mini-map | C6, F5, T5 |
| #1347 | Timeline markers | C8 |
| #1356 | Backend caching | B1-B4 |

---

---

## Backend Tasks (Python)

### TASK-B1: Performance Benchmark Script

**File:** `backend/scripts/benchmark_social_circles.py`
**Issue:** #1356
**Effort:** Small

**Description:**
Create a benchmark script to measure social circles endpoint performance under load.

**Requirements:**
- Measure `/api/v1/social-circles` response time
- Test with varying `max_books` parameter (100, 500, 1000, 5000)
- Output timing metrics: min, max, avg, p95, p99
- Test against staging environment
- Use `httpx` for async requests

**Acceptance Criteria:**
- [ ] Script runnable via `python backend/scripts/benchmark_social_circles.py`
- [ ] Outputs JSON with timing metrics
- [ ] Supports `--iterations` flag (default 10)
- [ ] Supports `--env staging|prod` flag
- [ ] Documents baseline performance in output

**Example Output:**
```json
{
  "endpoint": "/api/v1/social-circles",
  "max_books": 1000,
  "iterations": 10,
  "metrics": {
    "min_ms": 120,
    "max_ms": 450,
    "avg_ms": 230,
    "p95_ms": 380,
    "p99_ms": 420
  }
}
```

---

### TASK-B2: Redis Caching Service

**File:** `backend/app/services/social_circles_cache.py`
**Issue:** #1356
**Effort:** Medium

**Description:**
Implement Redis caching for social circles graph data to avoid recomputation.

**Requirements:**
- Cache key: `social_circles:graph:{hash_of_params}`
- TTL: 5 minutes (configurable)
- Serialize/deserialize `SocialCirclesResponse` with msgpack or JSON
- Graceful fallback if Redis unavailable
- Add `X-Cache: HIT|MISS` response header

**Implementation:**
```python
# backend/app/services/social_circles_cache.py

from typing import Optional
import hashlib
import json
from app.schemas.social_circles import SocialCirclesResponse
from app.core.config import settings

CACHE_TTL_SECONDS = 300  # 5 minutes

def get_cache_key(include_binders: bool, min_book_count: int, max_books: int) -> str:
    """Generate deterministic cache key from parameters."""
    params = f"{include_binders}:{min_book_count}:{max_books}"
    return f"social_circles:graph:{hashlib.md5(params.encode()).hexdigest()}"

async def get_cached_graph(cache_key: str) -> Optional[SocialCirclesResponse]:
    """Retrieve cached graph if available."""
    # Implementation with Redis client
    pass

async def set_cached_graph(cache_key: str, response: SocialCirclesResponse) -> None:
    """Cache graph response."""
    pass

def invalidate_cache() -> None:
    """Invalidate all social circles cache entries."""
    # Called when books are added/modified
    pass
```

**Acceptance Criteria:**
- [ ] Cache hit returns data without DB query
- [ ] Cache miss populates cache after DB query
- [ ] Cache invalidation clears all graph caches
- [ ] Redis connection failure doesn't break endpoint
- [ ] Logging for cache hits/misses

---

### TASK-B3: Cache Invalidation Hook

**File:** `backend/app/services/social_circles_cache.py` (extends B2)
**Depends On:** TASK-B2
**Effort:** Small

**Description:**
Add cache invalidation when books are created, updated, or deleted.

**Requirements:**
- Hook into book create/update/delete operations
- Call `invalidate_cache()` on relevant changes
- Only invalidate on status changes to/from OWNED_STATUSES

**Integration Points:**
- `backend/app/api/v1/books.py` - POST, PATCH, DELETE endpoints
- `backend/app/services/book_service.py` - if exists

**Acceptance Criteria:**
- [ ] Creating a book invalidates cache
- [ ] Updating book status invalidates cache
- [ ] Deleting a book invalidates cache
- [ ] Non-status updates don't invalidate (optimization)

---

### TASK-B4: Backend Cache Tests

**File:** `backend/tests/test_social_circles_cache.py`
**Depends On:** TASK-B2
**Effort:** Small

**Description:**
Unit tests for the caching service.

**Test Cases:**
```python
def test_cache_key_deterministic():
    """Same params produce same cache key."""

def test_cache_key_varies_with_params():
    """Different params produce different keys."""

def test_cache_hit_returns_data():
    """Cached data is returned on hit."""

def test_cache_miss_returns_none():
    """None returned when not cached."""

def test_invalidate_clears_all():
    """All cache entries cleared on invalidate."""

def test_redis_failure_graceful():
    """Redis unavailable doesn't raise exception."""
```

**Acceptance Criteria:**
- [ ] All test cases pass
- [ ] Mocks Redis client appropriately
- [ ] Tests are isolated (no shared state)

---

## Frontend - New Components

### TASK-C1: SearchInput Component

**File:** `frontend/src/components/socialcircles/SearchInput.vue`
**Issue:** #1324
**Effort:** Medium

**Description:**
Type-ahead search input for finding people in the graph.

**Props:**
```typescript
interface Props {
  nodes: ApiNode[];
  modelValue: string;
  placeholder?: string;
}
```

**Emits:**
```typescript
interface Emits {
  (e: 'update:modelValue', value: string): void;
  (e: 'select', node: ApiNode): void;
}
```

**Requirements:**
- Debounced input (300ms)
- Fuzzy search on node names
- Results grouped by type (Authors, Publishers, Binders)
- Max 10 results shown
- Keyboard navigation (↑↓ to navigate, Enter to select, Esc to close)
- Victorian-styled input with ornamental border
- "No results" state

**Template Structure:**
```vue
<template>
  <div class="search-input">
    <input
      type="text"
      v-model="query"
      @keydown="handleKeydown"
      placeholder="Search people..."
    />
    <div v-if="showResults" class="search-results">
      <div v-for="group in groupedResults" :key="group.type">
        <div class="group-header">{{ group.label }}</div>
        <div
          v-for="(node, idx) in group.nodes"
          :key="node.id"
          :class="{ active: idx === activeIndex }"
          @click="selectNode(node)"
        >
          {{ node.name }}
        </div>
      </div>
      <div v-if="noResults" class="no-results">
        No matches found
      </div>
    </div>
  </div>
</template>
```

**Acceptance Criteria:**
- [ ] Typing filters results in real-time
- [ ] Results grouped by node type
- [ ] Keyboard navigation works
- [ ] Selecting result emits `select` event
- [ ] Victorian styling matches existing components
- [ ] Accessible (ARIA labels)

---

### TASK-C2: StatsPanel Component

**File:** `frontend/src/components/socialcircles/StatsPanel.vue`
**Issue:** #1325
**Effort:** Medium

**Description:**
Collapsible panel showing network statistics.

**Props:**
```typescript
interface Props {
  nodes: ApiNode[];
  edges: ApiEdge[];
  meta: SocialCirclesMeta;
  isCollapsed?: boolean;
}
```

**Emits:**
```typescript
interface Emits {
  (e: 'toggle'): void;
}
```

**Statistics to Display:**
- Total nodes (X authors, Y publishers, Z binders)
- Total connections
- Most connected author (with degree)
- Most prolific publisher (by book count)
- Network density percentage
- Average connections per node

**Template Structure:**
```vue
<template>
  <div class="stats-panel" :class="{ collapsed: isCollapsed }">
    <button class="toggle-btn" @click="$emit('toggle')">
      <span>Statistics</span>
      <ChevronIcon :direction="isCollapsed ? 'down' : 'up'" />
    </button>
    <div v-if="!isCollapsed" class="stats-content">
      <StatCard label="Total People" :value="stats.totalNodes" />
      <StatCard label="Connections" :value="stats.totalEdges" />
      <StatCard label="Most Connected" :value="stats.mostConnected.name" :sublabel="stats.mostConnected.degree + ' connections'" />
      <StatCard label="Network Density" :value="formatPercent(stats.density)" />
    </div>
  </div>
</template>
```

**Acceptance Criteria:**
- [ ] Shows all required statistics
- [ ] Collapses/expands on click
- [ ] Updates when filters change
- [ ] Victorian typography
- [ ] Responsive layout

---

### TASK-C3: LayoutSwitcher Component

**File:** `frontend/src/components/socialcircles/LayoutSwitcher.vue`
**Issue:** #1342
**Effort:** Small

**Description:**
Button group to switch between graph layout modes.

**Props:**
```typescript
interface Props {
  modelValue: LayoutMode;
  disabled?: boolean;
}
```

**Emits:**
```typescript
interface Emits {
  (e: 'update:modelValue', mode: LayoutMode): void;
}
```

**Layout Modes:** `force`, `circle`, `grid`, `hierarchical`

**Template Structure:**
```vue
<template>
  <div class="layout-switcher">
    <button
      v-for="mode in AVAILABLE_LAYOUTS"
      :key="mode"
      :class="{ active: modelValue === mode }"
      :disabled="disabled"
      @click="$emit('update:modelValue', mode)"
      :title="LAYOUT_MODE_DESCRIPTIONS[mode]"
    >
      <LayoutIcon :mode="mode" />
      <span class="sr-only">{{ LAYOUT_MODE_LABELS[mode] }}</span>
    </button>
  </div>
</template>
```

**Acceptance Criteria:**
- [ ] Four layout buttons displayed
- [ ] Active mode visually highlighted
- [ ] Tooltip shows layout description
- [ ] Disabled state styling
- [ ] Victorian button styling

---

### TASK-C4: PathFinderPanel Component

**File:** `frontend/src/components/socialcircles/PathFinderPanel.vue`
**Issue:** #1326
**Effort:** Medium

**Description:**
UI for finding shortest path between two people.

**Props:**
```typescript
interface Props {
  nodes: ApiNode[];
  path: NodeId[] | null;
  isCalculating: boolean;
}
```

**Emits:**
```typescript
interface Emits {
  (e: 'find-path', start: NodeId, end: NodeId): void;
  (e: 'clear'): void;
}
```

**Requirements:**
- Two search inputs (start person, end person)
- "Find Path" button
- Path result display with narrative
- "Clear" button to reset
- Handle "no path exists" gracefully

**Template Structure:**
```vue
<template>
  <div class="path-finder-panel">
    <h3>Degrees of Separation</h3>
    <div class="inputs">
      <SearchInput v-model="startQuery" :nodes="nodes" @select="setStart" placeholder="Start person..." />
      <span class="connector">to</span>
      <SearchInput v-model="endQuery" :nodes="nodes" @select="setEnd" placeholder="End person..." />
    </div>
    <div class="actions">
      <button @click="findPath" :disabled="!canFind || isCalculating">
        {{ isCalculating ? 'Finding...' : 'Find Path' }}
      </button>
      <button @click="$emit('clear')" :disabled="!path">Clear</button>
    </div>
    <PathNarrative v-if="path" :path="path" :nodes="nodes" />
    <div v-else-if="noPathFound" class="no-path">
      No connection found between these people.
    </div>
  </div>
</template>
```

**Acceptance Criteria:**
- [ ] Can select two people via search
- [ ] Find Path calculates shortest path
- [ ] Path displayed as narrative
- [ ] "No path" state handled
- [ ] Loading state during calculation

---

### TASK-C5: FindSimilarButton Component

**File:** `frontend/src/components/socialcircles/FindSimilarButton.vue`
**Issue:** #1343
**Effort:** Small

**Description:**
Button that finds nodes with similar connections to the selected node.

**Props:**
```typescript
interface Props {
  nodeId: NodeId;
  disabled?: boolean;
}
```

**Emits:**
```typescript
interface Emits {
  (e: 'find-similar', nodeId: NodeId): void;
}
```

**Template:**
```vue
<template>
  <button
    class="find-similar-btn"
    :disabled="disabled"
    @click="$emit('find-similar', nodeId)"
    title="Find people with similar connections"
  >
    <SimilarIcon />
    Find Similar
  </button>
</template>
```

**Acceptance Criteria:**
- [ ] Button triggers find-similar event
- [ ] Disabled state works
- [ ] Victorian styling
- [ ] Tooltip explains function

---

### TASK-C6: MiniMap Component

**File:** `frontend/src/components/socialcircles/MiniMap.vue`
**Issue:** #1346
**Effort:** Medium

**Description:**
Small overview map showing entire graph with viewport indicator.

**Props:**
```typescript
interface Props {
  cy: cytoscape.Core | null;
  width?: number;
  height?: number;
}
```

**Requirements:**
- Shows miniaturized version of entire graph
- Rectangle indicates current viewport
- Click to pan main view
- Drag rectangle to pan
- Toggle visibility

**Implementation Notes:**
- Use Cytoscape's `cy.png()` or render simplified nodes
- Update viewport rectangle on pan/zoom
- Sync clicks back to main graph

**Acceptance Criteria:**
- [ ] Shows overview of entire graph
- [ ] Viewport rectangle visible
- [ ] Click pans main view
- [ ] Updates on zoom/pan
- [ ] Can be hidden/shown

---

### TASK-C7: FilterBadges Component

**File:** `frontend/src/components/socialcircles/FilterBadges.vue`
**Issue:** #1345
**Effort:** Small

**Description:**
Badges showing count of items for each filter option.

**Props:**
```typescript
interface Props {
  nodes: ApiNode[];
  filterState: FilterState;
}
```

**Requirements:**
- Badge next to each filter checkbox showing count
- Count updates based on other active filters
- Dim badge when filter would result in 0 items

**Template:**
```vue
<template>
  <span class="filter-badge" :class="{ empty: count === 0 }">
    {{ count }}
  </span>
</template>
```

**Acceptance Criteria:**
- [ ] Shows accurate counts
- [ ] Updates when filters change
- [ ] Empty state styling
- [ ] Compact size

---

### TASK-C8: TimelineMarkers Component

**File:** `frontend/src/components/socialcircles/TimelineMarkers.vue`
**Issue:** #1347
**Effort:** Small

**Description:**
Historical event markers on the timeline slider.

**Props:**
```typescript
interface Props {
  minYear: number;
  maxYear: number;
  events?: HistoricalEvent[];
}

interface HistoricalEvent {
  year: number;
  label: string;
  type: 'political' | 'literary' | 'cultural';
}
```

**Default Events:**
```typescript
const VICTORIAN_EVENTS: HistoricalEvent[] = [
  { year: 1837, label: "Victoria's Coronation", type: 'political' },
  { year: 1851, label: "Great Exhibition", type: 'cultural' },
  { year: 1859, label: "Origin of Species", type: 'literary' },
  { year: 1901, label: "Victoria Dies", type: 'political' },
];
```

**Template:**
```vue
<template>
  <div class="timeline-markers">
    <div
      v-for="event in visibleEvents"
      :key="event.year"
      class="marker"
      :style="{ left: getPosition(event.year) }"
      :title="event.label"
    >
      <div class="marker-line" />
      <span class="marker-label">{{ event.year }}</span>
    </div>
  </div>
</template>
```

**Acceptance Criteria:**
- [ ] Markers positioned correctly on timeline
- [ ] Tooltip shows event name
- [ ] Only shows events within visible range
- [ ] Victorian styling

---

### TASK-C9: KeyboardShortcutsModal Component

**File:** `frontend/src/components/socialcircles/KeyboardShortcutsModal.vue`
**Issue:** #1344
**Effort:** Small

**Description:**
Modal showing available keyboard shortcuts.

**Props:**
```typescript
interface Props {
  isOpen: boolean;
}
```

**Emits:**
```typescript
interface Emits {
  (e: 'close'): void;
}
```

**Shortcuts to Document:**
```typescript
const SHORTCUTS = [
  { key: '?', description: 'Show this help' },
  { key: 'Esc', description: 'Close panel / Clear selection' },
  { key: 'F', description: 'Toggle filter panel' },
  { key: 'L', description: 'Cycle layout modes' },
  { key: 'R', description: 'Reset view' },
  { key: '+/-', description: 'Zoom in/out' },
  { key: 'Space', description: 'Play/pause timeline' },
  { key: '←/→', description: 'Step timeline' },
];
```

**Acceptance Criteria:**
- [ ] Modal opens with `?` key
- [ ] Shows all shortcuts in organized list
- [ ] Closes on Esc or backdrop click
- [ ] Victorian modal styling

---

### TASK-C10: SearchResults Component

**File:** `frontend/src/components/socialcircles/SearchResults.vue`
**Issue:** #1324
**Effort:** Small

**Description:**
Dropdown showing grouped search results.

**Props:**
```typescript
interface Props {
  results: ApiNode[];
  activeIndex: number;
  query: string;
}
```

**Emits:**
```typescript
interface Emits {
  (e: 'select', node: ApiNode): void;
  (e: 'hover', index: number): void;
}
```

**Requirements:**
- Group results by node type
- Highlight matching text in names
- Show node metadata (birth year, book count)
- Keyboard-navigable

**Acceptance Criteria:**
- [ ] Results grouped by type
- [ ] Query highlighted in names
- [ ] Hover/active states work
- [ ] Accessible

---

### TASK-C11: PathNarrative Component

**File:** `frontend/src/components/socialcircles/PathNarrative.vue`
**Issue:** #1326
**Effort:** Small

**Description:**
Human-readable narrative of a path between people.

**Props:**
```typescript
interface Props {
  path: NodeId[];
  nodes: ApiNode[];
  edges: ApiEdge[];
}
```

**Example Output:**
```
Lord Byron → John Murray (publisher) → Charles Darwin
"Byron is 2 degrees from Darwin via John Murray"
```

**Requirements:**
- Show each step in the path
- Include relationship type (published by, shared publisher with)
- Final summary sentence
- Clickable nodes to select them

**Acceptance Criteria:**
- [ ] Shows step-by-step path
- [ ] Includes relationship context
- [ ] Summary with degree count
- [ ] Nodes are clickable

---

### TASK-C12: StatCard Component

**File:** `frontend/src/components/socialcircles/StatCard.vue`
**Issue:** #1325
**Effort:** Small

**Description:**
Individual statistic display card.

**Props:**
```typescript
interface Props {
  label: string;
  value: string | number;
  sublabel?: string;
  icon?: string;
}
```

**Template:**
```vue
<template>
  <div class="stat-card">
    <div class="stat-value">{{ value }}</div>
    <div class="stat-label">{{ label }}</div>
    <div v-if="sublabel" class="stat-sublabel">{{ sublabel }}</div>
  </div>
</template>
```

**Acceptance Criteria:**
- [ ] Displays value prominently
- [ ] Label below value
- [ ] Optional sublabel
- [ ] Victorian typography

---

### TASK-C13: BottomSheet Component

**File:** `frontend/src/components/socialcircles/BottomSheet.vue`
**Issue:** #1327
**Effort:** Medium

**Description:**
Mobile-friendly bottom sheet drawer for panels.

**Props:**
```typescript
interface Props {
  modelValue: boolean;
  title?: string;
  maxHeight?: string;
}
```

**Emits:**
```typescript
interface Emits {
  (e: 'update:modelValue', value: boolean): void;
}
```

**Requirements:**
- Slides up from bottom of screen
- Backdrop closes sheet
- Swipe down to close
- Handles safe area insets (iOS notch)
- Transition animation

**Template Structure:**
```vue
<template>
  <Teleport to="body">
    <Transition name="bottom-sheet">
      <div v-if="modelValue" class="bottom-sheet-overlay" @click="close">
        <div
          class="bottom-sheet"
          @click.stop
          @touchstart="handleTouchStart"
          @touchmove="handleTouchMove"
          @touchend="handleTouchEnd"
        >
          <div class="bottom-sheet-handle" />
          <div v-if="title" class="bottom-sheet-header">
            <h3>{{ title }}</h3>
            <button @click="close">×</button>
          </div>
          <div class="bottom-sheet-content">
            <slot />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
```

**Acceptance Criteria:**
- [ ] Opens/closes with v-model
- [ ] Backdrop click closes
- [ ] Swipe gesture works
- [ ] Smooth animation
- [ ] Safe area handled

---

### TASK-C14: MobileFilterFab Component

**File:** `frontend/src/components/socialcircles/MobileFilterFab.vue`
**Issue:** #1327
**Effort:** Small

**Description:**
Floating action button to open filters on mobile.

**Props:**
```typescript
interface Props {
  activeFilterCount?: number;
}
```

**Emits:**
```typescript
interface Emits {
  (e: 'click'): void;
}
```

**Template:**
```vue
<template>
  <button class="mobile-filter-fab" @click="$emit('click')">
    <FilterIcon />
    <span v-if="activeFilterCount" class="badge">{{ activeFilterCount }}</span>
  </button>
</template>
```

**Acceptance Criteria:**
- [ ] Positioned bottom-right
- [ ] Shows active filter count badge
- [ ] Touch-friendly size (48px minimum)
- [ ] Victorian styling

---

## Frontend - New Composables

### TASK-F1: useSearch Composable

**File:** `frontend/src/composables/socialcircles/useSearch.ts`
**Issue:** #1324
**Effort:** Medium

**Description:**
Composable for searching nodes with fuzzy matching.

**Interface:**
```typescript
export function useSearch(nodes: Ref<ApiNode[]>) {
  const query = ref('');
  const results = computed<ApiNode[]>(() => /* fuzzy search */);
  const groupedResults = computed<GroupedResults>(() => /* group by type */);
  const activeIndex = ref(0);

  function selectResult(index: number): ApiNode | null;
  function navigateUp(): void;
  function navigateDown(): void;
  function clearSearch(): void;

  return {
    query,
    results,
    groupedResults,
    activeIndex,
    selectResult,
    navigateUp,
    navigateDown,
    clearSearch,
  };
}
```

**Requirements:**
- Fuzzy search using simple includes or Fuse.js
- Debounce search (300ms)
- Group results by node type
- Limit to 10 results
- Keyboard navigation state

**Acceptance Criteria:**
- [ ] Fuzzy search works
- [ ] Results debounced
- [ ] Grouped by type
- [ ] Navigation state managed

---

### TASK-F2: useNetworkStats Composable

**File:** `frontend/src/composables/socialcircles/useNetworkStats.ts`
**Issue:** #1325
**Effort:** Small

**Description:**
Composable for computing network statistics.

**Interface:**
```typescript
export function useNetworkStats(
  nodes: Ref<ApiNode[]>,
  edges: Ref<ApiEdge[]>
) {
  const stats = computed(() => ({
    totalNodes: number,
    totalEdges: number,
    nodesByType: { author: number, publisher: number, binder: number },
    mostConnected: { node: ApiNode, degree: number } | null,
    mostProlific: { node: ApiNode, bookCount: number } | null,
    avgDegree: number,
    density: number,
  }));

  return { stats };
}
```

**Implementation:**
Use existing `calculateGraphStats`, `findHubs` from `graphAlgorithms.ts`.

**Acceptance Criteria:**
- [ ] All stats computed correctly
- [ ] Reactive to node/edge changes
- [ ] Uses existing graph algorithm utils

---

### TASK-F3: usePathFinder Composable

**File:** `frontend/src/composables/socialcircles/usePathFinder.ts`
**Issue:** #1326
**Effort:** Medium

**Description:**
Composable for finding shortest paths between nodes.

**Interface:**
```typescript
export function usePathFinder(
  nodes: Ref<ApiNode[]>,
  edges: Ref<ApiEdge[]>
) {
  const startNode = ref<NodeId | null>(null);
  const endNode = ref<NodeId | null>(null);
  const path = ref<NodeId[] | null>(null);
  const isCalculating = ref(false);
  const noPathFound = ref(false);

  function findPath(): void;
  function clear(): void;
  function setStart(nodeId: NodeId): void;
  function setEnd(nodeId: NodeId): void;

  return {
    startNode,
    endNode,
    path,
    isCalculating,
    noPathFound,
    findPath,
    clear,
    setStart,
    setEnd,
  };
}
```

**Implementation:**
Use `buildAdjacencyList` and `findShortestPath` from `graphAlgorithms.ts`.

**Acceptance Criteria:**
- [ ] Path finding works
- [ ] Loading state during calculation
- [ ] No-path state handled
- [ ] Clear resets all state

---

### TASK-F4: useFindSimilar Composable

**File:** `frontend/src/composables/socialcircles/useFindSimilar.ts`
**Issue:** #1343
**Effort:** Small

**Description:**
Composable for finding nodes similar to a selected node.

**Interface:**
```typescript
export function useFindSimilar(
  nodes: Ref<ApiNode[]>,
  edges: Ref<ApiEdge[]>
) {
  const similarNodes = ref<{ node: ApiNode; sharedConnections: number }[]>([]);

  function findSimilar(nodeId: NodeId, limit?: number): void;
  function clear(): void;

  return {
    similarNodes,
    findSimilar,
    clear,
  };
}
```

**Implementation:**
Use `findSimilarNodes` from `graphAlgorithms.ts`.

**Acceptance Criteria:**
- [ ] Similar nodes found correctly
- [ ] Sorted by shared connections
- [ ] Clear resets state

---

### TASK-F5: useMiniMap Composable

**File:** `frontend/src/composables/socialcircles/useMiniMap.ts`
**Issue:** #1346
**Effort:** Medium

**Description:**
Composable for managing mini-map state and interactions.

**Interface:**
```typescript
export function useMiniMap(cy: Ref<cytoscape.Core | null>) {
  const isVisible = ref(true);
  const viewportBounds = ref<{ x: number, y: number, w: number, h: number } | null>(null);
  const graphBounds = ref<{ x: number, y: number, w: number, h: number } | null>(null);

  function updateViewport(): void;
  function panTo(x: number, y: number): void;
  function toggle(): void;

  // Auto-update on cy viewport changes

  return {
    isVisible,
    viewportBounds,
    graphBounds,
    updateViewport,
    panTo,
    toggle,
  };
}
```

**Acceptance Criteria:**
- [ ] Tracks viewport position
- [ ] Tracks graph bounds
- [ ] Pan-to-click works
- [ ] Visibility toggle works

---

### TASK-F6: useAnalytics Composable

**File:** `frontend/src/composables/socialcircles/useAnalytics.ts`
**Issue:** #1336
**Effort:** Small

**Description:**
Composable for tracking user interactions.

**Interface:**
```typescript
export function useAnalytics() {
  function trackEvent(event: AnalyticsEvent): void;
  function trackNodeSelect(node: ApiNode): void;
  function trackEdgeSelect(edge: ApiEdge): void;
  function trackFilterChange(filter: string, value: unknown): void;
  function trackLayoutChange(mode: LayoutMode): void;
  function trackSearch(query: string, resultCount: number): void;
  function trackExport(format: 'png' | 'json' | 'url'): void;

  return {
    trackEvent,
    trackNodeSelect,
    trackEdgeSelect,
    trackFilterChange,
    trackLayoutChange,
    trackSearch,
    trackExport,
  };
}
```

**Implementation:**
- Use existing analytics service if available
- Or stub for future integration
- Console log in development

**Acceptance Criteria:**
- [ ] Track functions defined
- [ ] Events logged in dev mode
- [ ] Non-blocking (errors don't break UI)

---

### TASK-F7: useLayoutMode Composable

**File:** `frontend/src/composables/socialcircles/useLayoutMode.ts`
**Issue:** #1342
**Effort:** Small

**Description:**
Composable for managing graph layout mode.

**Interface:**
```typescript
export function useLayoutMode(cy: Ref<cytoscape.Core | null>) {
  const currentMode = ref<LayoutMode>('force');
  const isAnimating = ref(false);

  function setMode(mode: LayoutMode): void;
  function cycleMode(): void;

  return {
    currentMode,
    isAnimating,
    setMode,
    cycleMode,
  };
}
```

**Implementation:**
Use `getLayoutConfig` from `layoutConfigs.ts` and call `cy.layout(config).run()`.

**Acceptance Criteria:**
- [ ] Mode changes update graph layout
- [ ] Animation state tracked
- [ ] Cycle through modes works

---

### TASK-F8: useMobile Composable

**File:** `frontend/src/composables/socialcircles/useMobile.ts`
**Issue:** #1327
**Effort:** Small

**Description:**
Composable for mobile-specific state and behavior.

**Interface:**
```typescript
export function useMobile() {
  const isMobile = useMediaQuery('(max-width: 768px)');
  const isTablet = useMediaQuery('(min-width: 769px) and (max-width: 1024px)');
  const isTouch = ref(false);
  const isFiltersOpen = ref(false);

  // Detect touch capability
  onMounted(() => {
    isTouch.value = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
  });

  function openFilters(): void;
  function closeFilters(): void;
  function toggleFilters(): void;

  return {
    isMobile,
    isTablet,
    isTouch,
    isFiltersOpen,
    openFilters,
    closeFilters,
    toggleFilters,
  };
}
```

**Usage:**
```typescript
const { isMobile, isFiltersOpen, toggleFilters } = useMobile();
```

**Acceptance Criteria:**
- [ ] Detects mobile viewport
- [ ] Detects touch capability
- [ ] Manages filter panel state
- [ ] Works with SSR (guards window access)

---

## Frontend - Unit Tests

### TASK-T1 through TASK-T18: Unit Test Files

Each test file is independent. Follow this pattern:

**File Pattern:** `frontend/src/{path}/__tests__/{name}.test.ts`

| Task | File | Tests For |
|------|------|-----------|
| T1 | `composables/socialcircles/__tests__/useSearch.test.ts` | TASK-F1 |
| T2 | `composables/socialcircles/__tests__/useNetworkStats.test.ts` | TASK-F2 |
| T3 | `composables/socialcircles/__tests__/usePathFinder.test.ts` | TASK-F3 |
| T4 | `composables/socialcircles/__tests__/useFindSimilar.test.ts` | TASK-F4 |
| T5 | `composables/socialcircles/__tests__/useMiniMap.test.ts` | TASK-F5 |
| T6 | `composables/socialcircles/__tests__/useAnalytics.test.ts` | TASK-F6 |
| T7 | `composables/socialcircles/__tests__/useLayoutMode.test.ts` | TASK-F7 |
| T8 | `composables/socialcircles/__tests__/useMobile.test.ts` | TASK-F8 |
| T9 | `composables/socialcircles/__tests__/useNetworkData.test.ts` | existing |
| T10 | `composables/socialcircles/__tests__/useNetworkFilters.test.ts` | existing |
| T11 | `composables/socialcircles/__tests__/useNetworkTimeline.test.ts` | existing |
| T12 | `composables/socialcircles/__tests__/useNetworkKeyboard.test.ts` | existing |
| T13 | `utils/socialcircles/__tests__/graphAlgorithms.test.ts` | existing |
| T14 | `utils/socialcircles/__tests__/layoutConfigs.test.ts` | existing |
| T15 | `utils/socialcircles/__tests__/colorPalettes.test.ts` | existing |
| T16 | `utils/socialcircles/__tests__/dataTransformers.test.ts` | existing |
| T17 | `components/socialcircles/__tests__/FilterPanel.test.ts` | existing |
| T18 | `components/socialcircles/__tests__/NetworkLegend.test.ts` | existing |
| T19 | `components/socialcircles/__tests__/ZoomControls.test.ts` | existing |

**Test Template:**
```typescript
import { describe, it, expect, vi } from 'vitest';
import { ref } from 'vue';
import { useXxx } from '../useXxx';

describe('useXxx', () => {
  it('should do something', () => {
    // Arrange
    const input = ref([]);

    // Act
    const { result } = useXxx(input);

    // Assert
    expect(result.value).toBe(expected);
  });
});
```

**Acceptance Criteria (each):**
- [ ] Tests cover happy path
- [ ] Tests cover edge cases (empty input, null, etc.)
- [ ] Tests are isolated (no shared state)
- [ ] Mocks external dependencies appropriately

---

## Wave 1 Summary

**Total Independent Tasks:** 45

| Category | Count |
|----------|-------|
| Backend | 4 |
| Components | 14 |
| Composables | 8 |
| Unit Tests | 19 |

**Execution:**
All 43 tasks can run in parallel with no file conflicts. Each creates a new file.

---

# Wave 2: Integration & E2E Tasks

**Prerequisites:** Wave 1 complete
**Total Tasks:** 12
**Parallelization:** Some tasks can run in parallel within groups

---

## E2E Tests (4 tasks - can run in parallel)

### TASK-E1: Search E2E Tests

**File:** `frontend/tests/e2e/socialcircles-search.spec.ts`
**Issue:** #1324, #1335
**Depends On:** Wave 1 complete

**Test Scenarios:**
```typescript
import { test, expect } from '@playwright/test';

test.describe('Social Circles - Search', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/socialcircles');
    await page.waitForSelector('.network-graph');
  });

  test('search input is visible', async ({ page }) => {
    await expect(page.locator('.search-input')).toBeVisible();
  });

  test('typing shows results dropdown', async ({ page }) => {
    await page.fill('.search-input input', 'Byron');
    await expect(page.locator('.search-results')).toBeVisible();
  });

  test('selecting result centers graph on node', async ({ page }) => {
    await page.fill('.search-input input', 'Byron');
    await page.click('.search-results .result-item:first-child');
    // Verify node is selected
    await expect(page.locator('[data-selected="true"]')).toBeVisible();
  });

  test('keyboard navigation works', async ({ page }) => {
    await page.fill('.search-input input', 'John');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Enter');
    await expect(page.locator('[data-selected="true"]')).toBeVisible();
  });

  test('no results shows empty state', async ({ page }) => {
    await page.fill('.search-input input', 'xyznonexistent');
    await expect(page.locator('.no-results')).toBeVisible();
  });
});
```

**Acceptance Criteria:**
- [ ] All test scenarios pass
- [ ] Tests run in CI
- [ ] Screenshots on failure

---

### TASK-E2: Layout Switching E2E Tests

**File:** `frontend/tests/e2e/socialcircles-layout.spec.ts`
**Issue:** #1342, #1335
**Depends On:** Wave 1 complete

**Test Scenarios:**
```typescript
test.describe('Social Circles - Layout', () => {
  test('layout switcher is visible', async ({ page }) => {
    await page.goto('/socialcircles');
    await expect(page.locator('.layout-switcher')).toBeVisible();
  });

  test('clicking layout button changes graph layout', async ({ page }) => {
    await page.goto('/socialcircles');
    await page.click('[data-layout="circle"]');
    // Wait for animation
    await page.waitForTimeout(1000);
    // Verify URL updated
    await expect(page).toHaveURL(/layout=circle/);
  });

  test('layout persists on page reload', async ({ page }) => {
    await page.goto('/socialcircles?layout=grid');
    await expect(page.locator('[data-layout="grid"].active')).toBeVisible();
  });

  test('keyboard shortcut L cycles layouts', async ({ page }) => {
    await page.goto('/socialcircles');
    await page.keyboard.press('l');
    await expect(page).toHaveURL(/layout=circle/);
  });
});
```

**Acceptance Criteria:**
- [ ] All test scenarios pass
- [ ] Layout transitions are smooth
- [ ] URL state persists

---

### TASK-E3: Statistics Panel E2E Tests

**File:** `frontend/tests/e2e/socialcircles-stats.spec.ts`
**Issue:** #1325, #1335
**Depends On:** Wave 1 complete

**Test Scenarios:**
```typescript
test.describe('Social Circles - Statistics', () => {
  test('stats panel shows correct counts', async ({ page }) => {
    await page.goto('/socialcircles');
    await expect(page.locator('.stats-panel')).toBeVisible();
    // Verify counts match meta data
    const authorCount = await page.locator('[data-stat="authors"]').textContent();
    expect(parseInt(authorCount)).toBeGreaterThan(0);
  });

  test('stats update when filters applied', async ({ page }) => {
    await page.goto('/socialcircles');
    const initialCount = await page.locator('[data-stat="total"]').textContent();
    // Apply filter
    await page.click('[data-filter="showPublishers"]');
    const newCount = await page.locator('[data-stat="total"]').textContent();
    expect(parseInt(newCount)).toBeLessThan(parseInt(initialCount));
  });

  test('panel collapses and expands', async ({ page }) => {
    await page.goto('/socialcircles');
    await page.click('.stats-panel .toggle-btn');
    await expect(page.locator('.stats-panel.collapsed')).toBeVisible();
    await page.click('.stats-panel .toggle-btn');
    await expect(page.locator('.stats-panel:not(.collapsed)')).toBeVisible();
  });
});
```

**Acceptance Criteria:**
- [ ] Stats display correctly
- [ ] Stats update reactively
- [ ] Collapse/expand works

---

### TASK-E4: Path Finder E2E Tests

**File:** `frontend/tests/e2e/socialcircles-path.spec.ts`
**Issue:** #1326, #1335
**Depends On:** Wave 1 complete

**Test Scenarios:**
```typescript
test.describe('Social Circles - Path Finder', () => {
  test('path finder panel is accessible', async ({ page }) => {
    await page.goto('/socialcircles');
    await expect(page.locator('.path-finder-panel')).toBeVisible();
  });

  test('can select start and end nodes', async ({ page }) => {
    await page.goto('/socialcircles');
    await page.fill('.path-finder-panel .start-input', 'Byron');
    await page.click('.search-results .result-item:first-child');
    await page.fill('.path-finder-panel .end-input', 'Darwin');
    await page.click('.search-results .result-item:first-child');
    await expect(page.locator('.path-finder-panel .find-btn:not([disabled])')).toBeVisible();
  });

  test('finding path highlights nodes', async ({ page }) => {
    await page.goto('/socialcircles');
    // Select nodes and find path
    // ... setup
    await page.click('.find-btn');
    await expect(page.locator('.path-highlight')).toHaveCount({ greaterThan: 0 });
  });

  test('path narrative displays correctly', async ({ page }) => {
    // ... setup and find path
    await expect(page.locator('.path-narrative')).toBeVisible();
    await expect(page.locator('.path-narrative')).toContainText('degrees');
  });

  test('no path state handled', async ({ page }) => {
    // Select disconnected nodes
    // ... setup
    await page.click('.find-btn');
    await expect(page.locator('.no-path-message')).toBeVisible();
  });
});
```

**Acceptance Criteria:**
- [ ] Path finding works end-to-end
- [ ] Path visualization correct
- [ ] Edge cases handled

---

## Integration Tasks (8 tasks)

### TASK-W2-1: Mobile Responsive Integration

**Files Modified:**
- `frontend/src/views/SocialCirclesView.vue`
- `frontend/src/components/socialcircles/FilterPanel.vue`
- `frontend/src/components/socialcircles/NetworkGraph.vue`

**Issue:** #1327
**Depends On:** C13 (BottomSheet), C14 (MobileFilterFab), F8 (useMobile)
**Effort:** Medium

**Description:**
Integrate mobile components and make existing components responsive.

**Changes to SocialCirclesView.vue:**
```vue
<script setup>
import { useMobile } from '@/composables/socialcircles/useMobile';
import BottomSheet from '@/components/socialcircles/BottomSheet.vue';
import MobileFilterFab from '@/components/socialcircles/MobileFilterFab.vue';

const { isMobile, isFiltersOpen, toggleFilters } = useMobile();
</script>

<template>
  <!-- Desktop layout -->
  <div v-if="!isMobile" class="desktop-layout">
    <FilterPanel class="sidebar" />
    <NetworkGraph class="main" />
  </div>

  <!-- Mobile layout -->
  <div v-else class="mobile-layout">
    <NetworkGraph class="full-width" />
    <MobileFilterFab @click="toggleFilters" :activeFilterCount="activeFilters.length" />
    <BottomSheet v-model="isFiltersOpen" title="Filters">
      <FilterPanel />
    </BottomSheet>
  </div>
</template>
```

**Changes to NetworkGraph.vue:**
- Increase node size on mobile (minTouchTarget: 44px)
- Adjust pan/zoom sensitivity for touch

**Changes to FilterPanel.vue:**
- Remove fixed positioning on mobile (handled by BottomSheet)
- Stack filters vertically on narrow screens

**Acceptance Criteria:**
- [ ] Mobile layout activates below 768px
- [ ] Filter FAB visible on mobile
- [ ] Bottom sheet opens/closes
- [ ] Touch gestures work on graph
- [ ] No horizontal scroll on mobile

---

### TASK-W2-2: Search Integration

**Files Modified:**
- `frontend/src/views/SocialCirclesView.vue`
- `frontend/src/composables/socialcircles/useSocialCircles.ts`
- `frontend/src/composables/socialcircles/index.ts`

**Issue:** #1324
**Depends On:** C1 (SearchInput), F1 (useSearch)
**Effort:** Small

**Description:**
Wire SearchInput component into the main view.

**Changes to SocialCirclesView.vue:**
```vue
<template>
  <header class="toolbar">
    <SearchInput
      :nodes="nodes"
      v-model="searchQuery"
      @select="handleSearchSelect"
    />
    <!-- existing toolbar items -->
  </header>
</template>

<script setup>
function handleSearchSelect(node: ApiNode) {
  selectNode(node.id);
  // Center graph on node
  cy.value?.center(cy.value.$id(node.id));
}
</script>
```

**Changes to useSocialCircles.ts:**
- Expose search-related state
- Add `centerOnNode(nodeId)` function

**Changes to index.ts:**
- Export useSearch

**Acceptance Criteria:**
- [ ] Search input visible in toolbar
- [ ] Selecting result selects node
- [ ] Graph centers on selected node
- [ ] Search state in URL (optional)

---

### TASK-W2-3: Statistics Panel Integration

**Files Modified:**
- `frontend/src/views/SocialCirclesView.vue`
- `frontend/src/composables/socialcircles/index.ts`

**Issue:** #1325
**Depends On:** C2 (StatsPanel), C12 (StatCard), F2 (useNetworkStats)
**Effort:** Small

**Description:**
Wire StatsPanel into the main view.

**Changes to SocialCirclesView.vue:**
```vue
<template>
  <div class="view-container">
    <StatsPanel
      :nodes="filteredNodes"
      :edges="filteredEdges"
      :meta="meta"
      v-model:collapsed="statsCollapsed"
    />
    <!-- existing content -->
  </div>
</template>
```

**Positioning:**
- Desktop: Bottom-left, above legend
- Mobile: Collapsed by default, in bottom sheet

**Acceptance Criteria:**
- [ ] Stats panel visible
- [ ] Stats update with filters
- [ ] Collapse state persists
- [ ] Mobile positioning works

---

### TASK-W2-4: Layout Switcher Integration

**Files Modified:**
- `frontend/src/components/socialcircles/NetworkGraph.vue`
- `frontend/src/composables/socialcircles/useUrlState.ts`
- `frontend/src/composables/socialcircles/index.ts`

**Issue:** #1342
**Depends On:** C3 (LayoutSwitcher), F7 (useLayoutMode)
**Effort:** Small

**Description:**
Wire LayoutSwitcher into NetworkGraph.

**Changes to NetworkGraph.vue:**
```vue
<template>
  <div class="network-graph">
    <div class="graph-container" ref="graphContainer" />
    <div class="controls-bottom-right">
      <LayoutSwitcher v-model="layoutMode" :disabled="isAnimating" />
      <ZoomControls />
    </div>
  </div>
</template>

<script setup>
import { useLayoutMode } from '@/composables/socialcircles/useLayoutMode';

const { currentMode: layoutMode, isAnimating, setMode } = useLayoutMode(cy);

// Watch for mode changes
watch(layoutMode, (mode) => {
  const config = getLayoutConfig(mode);
  cy.value?.layout(config).run();
});
</script>
```

**Changes to useUrlState.ts:**
- Add `layout` parameter to URL state
- Default: 'force'

**Acceptance Criteria:**
- [ ] Layout buttons visible
- [ ] Clicking changes layout
- [ ] Layout persists in URL
- [ ] Keyboard shortcut 'L' works

---

### TASK-W2-5: Path Finder Integration

**Files Modified:**
- `frontend/src/views/SocialCirclesView.vue`
- `frontend/src/composables/socialcircles/useSocialCircles.ts`

**Issue:** #1326
**Depends On:** C4 (PathFinderPanel), C11 (PathNarrative), F3 (usePathFinder)
**Effort:** Medium

**Description:**
Wire PathFinderPanel into the view and add path highlighting.

**Changes to SocialCirclesView.vue:**
```vue
<template>
  <aside class="sidebar-right">
    <PathFinderPanel
      :nodes="nodes"
      :path="pathState.path"
      :isCalculating="pathState.isCalculating"
      @find-path="handleFindPath"
      @clear="handleClearPath"
    />
  </aside>
</template>
```

**Changes to useSocialCircles.ts:**
```typescript
// Add path highlighting
function highlightPath(path: NodeId[]) {
  clearSelection();
  path.forEach(nodeId => {
    highlightedNodes.value.add(nodeId);
  });
  // Highlight edges between consecutive nodes
  for (let i = 0; i < path.length - 1; i++) {
    const edgeId = findEdgeBetween(path[i], path[i+1]);
    if (edgeId) highlightedEdges.value.add(edgeId);
  }
}
```

**Acceptance Criteria:**
- [ ] Path finder panel accessible
- [ ] Path calculated correctly
- [ ] Path nodes/edges highlighted
- [ ] Narrative displayed

---

### TASK-W2-6: Find Similar Integration

**Files Modified:**
- `frontend/src/components/socialcircles/NodeFloatingCard.vue`
- `frontend/src/views/SocialCirclesView.vue`

**Issue:** #1343
**Depends On:** C5 (FindSimilarButton), F4 (useFindSimilar)
**Effort:** Small

**Description:**
Add Find Similar button to node detail card.

**Changes to NodeFloatingCard.vue:**
```vue
<template>
  <div class="node-card">
    <!-- existing content -->
    <div class="actions">
      <FindSimilarButton
        :nodeId="node.id"
        @find-similar="$emit('find-similar', $event)"
      />
    </div>
  </div>
</template>
```

**Changes to SocialCirclesView.vue:**
```vue
<NodeFloatingCard
  @find-similar="handleFindSimilar"
/>

<script setup>
const { similarNodes, findSimilar, clear: clearSimilar } = useFindSimilar(nodes, edges);

function handleFindSimilar(nodeId: NodeId) {
  findSimilar(nodeId);
  // Highlight similar nodes
  similarNodes.value.forEach(({ node }) => {
    highlightedNodes.value.add(node.id);
  });
}
</script>
```

**Acceptance Criteria:**
- [ ] Button visible in node card
- [ ] Similar nodes highlighted on click
- [ ] Similar nodes listed somewhere

---

### TASK-W2-7: Mini-map Integration

**Files Modified:**
- `frontend/src/components/socialcircles/NetworkGraph.vue`

**Issue:** #1346
**Depends On:** C6 (MiniMap), F5 (useMiniMap)
**Effort:** Small

**Description:**
Add mini-map overlay to NetworkGraph.

**Changes to NetworkGraph.vue:**
```vue
<template>
  <div class="network-graph">
    <div class="graph-container" ref="graphContainer" />
    <MiniMap
      v-if="showMiniMap"
      :cy="cy"
      class="mini-map-overlay"
    />
    <button @click="showMiniMap = !showMiniMap" class="mini-map-toggle">
      {{ showMiniMap ? 'Hide' : 'Show' }} Map
    </button>
  </div>
</template>
```

**Acceptance Criteria:**
- [ ] Mini-map visible (toggleable)
- [ ] Shows viewport rectangle
- [ ] Click-to-pan works
- [ ] Updates on zoom/pan

---

### TASK-W2-8: Keyboard Shortcuts Integration

**Files Modified:**
- `frontend/src/views/SocialCirclesView.vue`
- `frontend/src/composables/socialcircles/useNetworkKeyboard.ts`

**Issue:** #1344
**Depends On:** C9 (KeyboardShortcutsModal)
**Effort:** Small

**Description:**
Add `?` shortcut and integrate modal.

**Changes to SocialCirclesView.vue:**
```vue
<template>
  <KeyboardShortcutsModal
    v-model:open="showShortcuts"
  />
</template>
```

**Changes to useNetworkKeyboard.ts:**
```typescript
// Add ? handler
useEventListener(document, 'keydown', (e) => {
  if (e.key === '?' && !isInputFocused()) {
    showShortcuts.value = true;
  }
});
```

**Acceptance Criteria:**
- [ ] `?` opens modal
- [ ] Modal shows all shortcuts
- [ ] Esc closes modal

---

## Wave 2 Execution Order

```
E2E Tests (parallel):     E1 ─┬─ E2 ─┬─ E3 ─┬─ E4
                              │      │      │
Integration (staged):         ▼      ▼      ▼
  Group A (parallel):    W2-2 ── W2-3 ── W2-4 ── W2-8
                              │
  Group B (after A):     W2-5 ── W2-6 ── W2-7
                              │
  Group C (after B):          W2-1 (mobile - touches many files)
```

**Rationale:**
- E2E tests can run in parallel (separate test files)
- Group A: Simple integrations that add new components without conflicts
- Group B: Features that build on Group A (path finder needs search)
- Group C: Mobile touches multiple files, run last to avoid conflicts

---

## Complete Task Summary

| Wave | Category | Tasks | Parallel? |
|------|----------|-------|-----------|
| 1 | Backend | B1-B4 | Yes (all 4) |
| 1 | Components | C1-C14 | Yes (all 14) |
| 1 | Composables | F1-F8 | Yes (all 8) |
| 1 | Unit Tests | T1-T19 | Yes (all 19) |
| 2 | E2E Tests | E1-E4 | Yes (all 4) |
| 2 | Integration A | W2-2,3,4,8 | Yes (4) |
| 2 | Integration B | W2-5,6,7 | Yes (3) |
| 2 | Integration C | W2-1 | Sequential |

**Total: 57 tasks**
- Wave 1: 45 fully parallel
- Wave 2: 12 tasks (staged parallelism)
