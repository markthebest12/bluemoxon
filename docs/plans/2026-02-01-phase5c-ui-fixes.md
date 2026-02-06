# Phase 5C UI Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> to implement this plan task-by-task.

**Goal:** Fix 4 Social Circles UI issues — graph centering, timeline
label overlap, Show Less button, and node click race condition.

**Architecture:** 3 parallel tracks with no file overlap. Track 1 is a
one-line padding fix, Track 2 is a constant bump, Track 3 combines the
hub mode interaction fixes (Show Less + node click bug).

**Tech Stack:** Vue 3/TypeScript, Cytoscape.js, Vitest, Playwright

---

## Track 1: Fix Graph Centering (#1662)

### Task 1: Increase fit() padding

**Files:**

- Modify: `frontend/src/components/socialcircles/NetworkGraph.vue:321`

**Step 1: Change fit padding**

In `NetworkGraph.vue`, line 321, change:

```typescript
  fitToView: () => cy.value?.fit(undefined, 50),
```

To:

```typescript
  fitToView: () => cy.value?.fit(undefined, 80),
```

Also find the layout `run()` calls — the layout options likely pass a
`padding` value. Search for `padding` in the file and update any layout
padding values from 50 to 80 as well.

**Step 2: Lint + type-check**

Run: `npm run --prefix frontend lint`
Run: `npm run --prefix frontend type-check`

**Step 3: Commit**

```bash
git add frontend/src/components/socialcircles/NetworkGraph.vue
git commit -m "fix: increase graph fit padding to clear overlay controls (#1662)"
```

---

## Track 2: Fix Timeline Label Overlap (#1663)

### Task 2: Increase MIN_LABEL_SPACING

**Files:**

- Modify: `frontend/src/components/socialcircles/TimelineMarkers.vue:46`

**Step 1: Update the spacing constant**

In `TimelineMarkers.vue`, line 46, change:

```typescript
const MIN_LABEL_SPACING = 4;
```

To:

```typescript
const MIN_LABEL_SPACING = 8;
```

This gives ~80px clearance at 1000px timeline width — enough for two
4-digit year labels with buffer.

**Step 2: Lint + type-check**

Run: `npm run --prefix frontend lint`
Run: `npm run --prefix frontend type-check`

**Step 3: Commit**

```bash
git add frontend/src/components/socialcircles/TimelineMarkers.vue
git commit -m "fix: increase timeline label spacing to prevent year overlap (#1663)"
```

---

## Track 3: Hub Mode Interaction Fixes (#1664 + #1665)

### Task 3: Fix node click race condition (#1665)

**Files:**

- Modify: `frontend/src/views/SocialCirclesView.vue:482-497`

**Context:** `handleNodeSelect()` calls both `hubMode.expandNode()`
and `toggleSelectNode()` synchronously. The `expandNode()` triggers a
reactive cascade that changes the visible node set before the selection
panel opens — causing the graph to "jump" to a different set of nodes
instead of showing the detail modal.

**Fix:** Remove `expandNode()` from the click handler. Node clicks
should only open the detail panel. Expansion stays available via the
Show More button.

**Step 1: Remove expandNode from handleNodeSelect**

In `SocialCirclesView.vue`, change lines 482-497 from:

```typescript
function handleNodeSelect(nodeId: string | null) {
  if (nodeId) {
    // Expand hub neighborhood on node click for progressive disclosure
    if (!hubMode.isFullyExpanded.value) {
      hubMode.expandNode(nodeId as NodeId);
    }
    toggleSelectNode(nodeId);
    // Only track if the panel was opened (not toggled closed)
    if (isPanelOpen.value) {
      const node = nodeMap.value.get(nodeId);
      if (node) analytics.trackNodeSelect(node as ApiNode);
    }
  } else {
    clearSelection();
  }
}
```

To:

```typescript
function handleNodeSelect(nodeId: string | null) {
  if (nodeId) {
    toggleSelectNode(nodeId);
    // Only track if the panel was opened (not toggled closed)
    if (isPanelOpen.value) {
      const node = nodeMap.value.get(nodeId);
      if (node) analytics.trackNodeSelect(node as ApiNode);
    }
  } else {
    clearSelection();
  }
}
```

**Step 2: Lint + type-check**

Run: `npm run --prefix frontend lint`
Run: `npm run --prefix frontend type-check`

**Step 3: Commit**

```bash
git add frontend/src/views/SocialCirclesView.vue
git commit -m "fix: remove expandNode from click handler to prevent graph jump (#1665)"
```

### Task 4: Add showLess() to useHubMode

**Files:**

- Modify: `frontend/src/composables/socialcircles/useHubMode.ts:167-174`
- Test: `frontend/src/composables/socialcircles/__tests__/useHubMode.test.ts`

**Context:** The `showMore()` function transitions compact → medium →
full. We need `showLess()` to reverse: full → medium → compact. When
stepping down, clear `manuallyAddedNodes` so the user gets the exact
same node set as that level originally showed (deterministic).

**Step 1: Write the failing test**

In `useHubMode.test.ts`, add after the existing "transitions hub
levels" test:

```typescript
  it("transitions hub levels backwards: full → medium → compact", () => {
    const nodes = ref<ApiNode[]>(
      Array.from({ length: 100 }, (_, i) => makeNode(`author:${i}`, "author"))
    );
    const edges = ref<ApiEdge[]>([]);

    const hub = useHubMode(nodes, edges);
    hub.initializeHubs();

    // Go to full
    hub.showMore();
    hub.showMore();
    expect(hub.hubLevel.value).toBe("full");

    hub.showLess();
    expect(hub.hubLevel.value).toBe("medium");
    expect(hub.visibleNodes.value.length).toBeLessThanOrEqual(50);

    hub.showLess();
    expect(hub.hubLevel.value).toBe("compact");
    expect(hub.visibleNodes.value.length).toBeLessThanOrEqual(25);
  });

  it("showLess clears manuallyAddedNodes for deterministic reversal", () => {
    const hub_node = makeNode("author:0", "author");
    const neighbors = Array.from({ length: 25 }, (_, i) => makeNode(`publisher:${i}`, "publisher"));
    const extraAuthors = Array.from({ length: 20 }, (_, i) =>
      makeNode(`author:${i + 1}`, "author")
    );
    const nodes = ref<ApiNode[]>([hub_node, ...neighbors, ...extraAuthors]);
    const edges = ref<ApiEdge[]>(neighbors.map((n, i) => makeEdge("author:0", n.id, 25 - i)));

    const hub = useHubMode(nodes, edges);
    hub.initializeHubs();

    const compactCount = hub.visibleNodes.value.length;

    // Expand some nodes manually
    hub.expandNode("author:0" as NodeId);
    expect(hub.visibleNodes.value.length).toBeGreaterThan(compactCount);

    // Show less should return to exact compact set
    hub.showLess();
    expect(hub.hubLevel.value).toBe("compact");
    expect(hub.visibleNodes.value.length).toBe(compactCount);
  });

  it("showLess does nothing at compact level", () => {
    const nodes = ref<ApiNode[]>(
      Array.from({ length: 100 }, (_, i) => makeNode(`author:${i}`, "author"))
    );
    const edges = ref<ApiEdge[]>([]);

    const hub = useHubMode(nodes, edges);
    hub.initializeHubs();

    expect(hub.hubLevel.value).toBe("compact");
    hub.showLess();
    expect(hub.hubLevel.value).toBe("compact");
  });
```

**Step 2: Run test to verify it fails**

Run: `npm run --prefix frontend test -- --run src/composables/socialcircles/__tests__/useHubMode.test.ts`
Expected: FAIL — `hub.showLess is not a function`

**Step 3: Implement showLess()**

In `useHubMode.ts`, add after the `showMore()` function (after line
174):

```typescript
  // "Show less" level transition (deterministic reversal)
  function showLess() {
    if (hubLevel.value === "full") {
      hubLevel.value = "medium";
    } else if (hubLevel.value === "medium") {
      hubLevel.value = "compact";
    }
    // Clear manually expanded nodes so user gets the exact hub set for this level
    manuallyAddedNodes.value = new Set();
    expandedNodes.value = new Set();
  }
```

Add `showLess` to the return object (after `showMore` on line 206):

```typescript
    showLess,
```

**Step 4: Run tests**

Run: `npm run --prefix frontend test -- --run src/composables/socialcircles/__tests__/useHubMode.test.ts`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add frontend/src/composables/socialcircles/useHubMode.ts \
        frontend/src/composables/socialcircles/__tests__/useHubMode.test.ts
git commit -m "feat: add showLess() for deterministic hub level reversal (#1664)"
```

### Task 5: Update ShowMoreButton to support Show Less

**Files:**

- Modify: `frontend/src/components/socialcircles/ShowMoreButton.vue`
- Modify: `frontend/src/views/SocialCirclesView.vue:707-713,822-831`

**Step 1: Update ShowMoreButton component**

Replace the entire `ShowMoreButton.vue` with:

```vue
<script setup lang="ts">
defineProps<{
  statusText: string | null;
  isFullyExpanded: boolean;
  canShowLess: boolean;
}>();

defineEmits<{
  showMore: [];
  showLess: [];
}>();
</script>

<template>
  <div v-if="statusText" class="show-more-controls" data-testid="show-more-controls">
    <button
      v-if="canShowLess"
      class="show-more-btn"
      data-testid="show-less-btn"
      @click="$emit('showLess')"
    >
      <span class="show-more-btn__action">Show less</span>
    </button>
    <button
      v-if="!isFullyExpanded"
      class="show-more-btn"
      data-testid="show-more-btn"
      @click="$emit('showMore')"
    >
      {{ statusText }} — <span class="show-more-btn__action">Show more</span>
    </button>
    <span v-if="isFullyExpanded && canShowLess" class="show-more-status">
      {{ statusText }}
    </span>
  </div>
</template>

<style scoped>
.show-more-controls {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.show-more-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.75rem;
  background: var(--color-victorian-paper-white, #fdfcfa);
  border: 1px solid var(--color-victorian-paper-aged, #e8e1d5);
  border-radius: 4px;
  font-size: 0.8125rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.show-more-btn:hover {
  background: var(--color-victorian-paper-cream, #f5f0e6);
}

.show-more-btn__action {
  font-weight: 600;
  color: var(--color-victorian-hunter-600, #2f5a4b);
}

.show-more-status {
  font-size: 0.8125rem;
  color: var(--color-victorian-ink-muted, #5c5c58);
}
</style>
```

**Step 2: Add canShowLess computed to useHubMode**

In `useHubMode.ts`, add after the `isFullyExpanded` computed (after
line 191):

```typescript
  const canShowLess = computed(() => hubLevel.value !== "compact");
```

Add `canShowLess` to the return object.

**Step 3: Wire up in SocialCirclesView**

In `SocialCirclesView.vue`, update the desktop ShowMoreButton (lines
707-713) from:

```html
          <div v-show="!showDetailPanel" class="show-more-container">
            <ShowMoreButton
              :status-text="hubMode.statusText.value"
              :is-fully-expanded="hubMode.isFullyExpanded.value"
              @show-more="hubMode.showMore"
            />
          </div>
```

To:

```html
          <div v-show="!showDetailPanel" class="show-more-container">
            <ShowMoreButton
              :status-text="hubMode.statusText.value"
              :is-fully-expanded="hubMode.isFullyExpanded.value"
              :can-show-less="hubMode.canShowLess.value"
              @show-more="hubMode.showMore"
              @show-less="hubMode.showLess"
            />
          </div>
```

Update the mobile ShowMoreButton (lines 826-830) the same way — add
`:can-show-less` and `@show-less` props.

Also update the `v-if` visibility: the old component hid itself when
fully expanded. The new component stays visible when fully expanded
AND canShowLess is true, so update the container `v-show` conditions.

Desktop container (line 707): change from:

```html
          <div v-show="!showDetailPanel" class="show-more-container">
```

To:

```html
          <div v-show="!showDetailPanel && (hubMode.statusText.value || hubMode.canShowLess.value)" class="show-more-container">
```

Mobile container (line 822-824): apply same pattern.

**Step 4: Lint + type-check**

Run: `npm run --prefix frontend lint`
Run: `npm run --prefix frontend format`
Run: `npm run --prefix frontend type-check`

**Step 5: Commit**

```bash
git add frontend/src/components/socialcircles/ShowMoreButton.vue \
        frontend/src/composables/socialcircles/useHubMode.ts \
        frontend/src/views/SocialCirclesView.vue
git commit -m "feat: add Show Less button for hub mode reversal (#1664)"
```

---

## Parallelization Strategy

| Track | Branch | Worktree | Files |
|-------|--------|----------|-------|
| 1 (#1662) | `fix/graph-centering` | `.worktrees/graph-centering` | `NetworkGraph.vue` |
| 2 (#1663) | `fix/timeline-labels` | `.worktrees/timeline-labels` | `TimelineMarkers.vue` |
| 3 (#1664+#1665) | `fix/hub-mode-interaction` | `.worktrees/hub-interaction` | `useHubMode.ts`, `ShowMoreButton.vue`, `SocialCirclesView.vue` |

**No file overlap** between tracks — safe to parallelize fully.
