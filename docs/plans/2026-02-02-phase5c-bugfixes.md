# Phase 5C Bugfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> to implement this plan task-by-task.

**Goal:** Fix 3 regressions from Phase 5C UI fixes — graph too small,
slider-vs-marker label overlap, and Show Less generating new layout.

**Architecture:** 3 independent tracks with minimal file overlap.
Track 1 reverts over-aggressive padding. Track 2 adds slider-aware
label suppression. Track 3 adds position caching for subset layouts.

**Tech Stack:** Vue 3/TypeScript, Cytoscape.js, Vitest, Playwright

---

## Track 1: Fix Graph Too Small (#1667 regression)

### Task 1: Revert layout padding to 30, fitToView to 50

**Files:**

- Modify: `frontend/src/constants/socialCircles.ts:149,164,171,183`
- Modify: `frontend/src/utils/socialCircles/layoutConfigs.ts:20,40,51,65`
- Modify: `frontend/src/components/socialcircles/NetworkGraph.vue:321`
- Modify: `frontend/src/composables/socialcircles/useSocialCircles.ts:260`
- Modify: `frontend/src/utils/socialCircles/__tests__/layoutConfigs.test.ts:127-131`

**Step 1: Update layout config padding in constants**

In `constants/socialCircles.ts`, change all 4 `padding: 80` to
`padding: 30` (lines 149, 164, 171, 183).

**Step 2: Update layout config padding in layoutConfigs.ts**

In `utils/socialCircles/layoutConfigs.ts`, change all 4 `padding: 80`
to `padding: 30` (lines 20, 40, 51, 65).

**Step 3: Update fitToView in NetworkGraph.vue**

Line 321, change:

```typescript
  fitToView: () => cy.value?.fit(undefined, 80),
```

To:

```typescript
  fitToView: () => cy.value?.fit(undefined, 50),
```

**Step 4: Update fitToView in useSocialCircles.ts**

Line 260, change:

```typescript
      cytoscapeInstance.value.fit(undefined, 80);
```

To:

```typescript
      cytoscapeInstance.value.fit(undefined, 50);
```

**Step 5: Update test assertion**

In `layoutConfigs.test.ts`, line 127, change:

```typescript
        "%s layout has padding of 80",
```

To:

```typescript
        "%s layout has padding of 30",
```

And line 130, change:

```typescript
          expect(config.padding).toBe(80);
```

To:

```typescript
          expect(config.padding).toBe(30);
```

**Step 6: Run tests**

Run: `npm run --prefix frontend test -- --run src/utils/socialCircles/__tests__/layoutConfigs.test.ts`
Expected: ALL PASS

**Step 7: Lint + type-check**

Run: `npm run --prefix frontend lint`
Run: `npm run --prefix frontend type-check`

**Step 8: Commit**

```bash
git add frontend/src/constants/socialCircles.ts \
        frontend/src/utils/socialCircles/layoutConfigs.ts \
        frontend/src/components/socialcircles/NetworkGraph.vue \
        frontend/src/composables/socialcircles/useSocialCircles.ts \
        frontend/src/utils/socialCircles/__tests__/layoutConfigs.test.ts
git commit -m "fix: revert padding to 30/50 — graph was too small (#1667)"
```

---

## Track 2: Fix Slider-vs-Marker Label Overlap (#1668 regression)

### Task 2: Add sliderYear prop to TimelineMarkers

**Files:**

- Modify: `frontend/src/components/socialcircles/TimelineMarkers.vue:19-27,44-69`
- Modify: `frontend/src/components/socialcircles/TimelineSlider.vue:123`
- Test: `frontend/src/components/socialcircles/__tests__/TimelineMarkers.test.ts`

**Step 1: Write the failing test**

In `TimelineMarkers.test.ts`, add a new test after the existing label
spacing tests (after the "shows first label even when all events are
clustered" test):

```typescript
  it("hides marker label when too close to slider position", () => {
    // Range 1700-1967 = 267 years. Slider at 1850.
    // Event at 1851: (1851-1700)/267 = 56.55%
    // Slider at 1850: (1850-1700)/267 = 56.18%
    // Gap: 0.37% — well under MIN_LABEL_SPACING (4%)
    const wrapper = mountMarkers({
      minYear: 1700,
      maxYear: 1967,
      sliderYear: 1850,
      events: [
        { year: 1837, label: "Victoria's Coronation", type: "political" },
        { year: 1851, label: "Great Exhibition", type: "cultural" },
        { year: 1901, label: "Victoria Dies", type: "political" },
      ],
    });
    const yearLabels = wrapper.findAll(".timeline-markers__year");
    expect(yearLabels).toHaveLength(3);
    // 1837 visible (far from slider)
    expect(yearLabels[0].isVisible()).toBe(true);
    // 1851 hidden (too close to slider at 1850)
    expect(yearLabels[1].isVisible()).toBe(false);
    // 1901 visible (far from slider)
    expect(yearLabels[2].isVisible()).toBe(true);
  });

  it("shows all markers when sliderYear is not provided", () => {
    // No sliderYear — same as before, only marker-to-marker spacing applies
    const wrapper = mountMarkers({
      minYear: 1837,
      maxYear: 1901,
      events: [
        { year: 1837, label: "Victoria's Coronation", type: "political" },
        { year: 1870, label: "Education Act", type: "cultural" },
        { year: 1901, label: "Victoria Dies", type: "political" },
      ],
    });
    const yearLabels = wrapper.findAll(".timeline-markers__year");
    expect(yearLabels).toHaveLength(3);
    expect(yearLabels[0].isVisible()).toBe(true);
    expect(yearLabels[1].isVisible()).toBe(true);
    expect(yearLabels[2].isVisible()).toBe(true);
  });

  it("updates label visibility reactively when slider moves", async () => {
    // Event at 1870 is initially far from slider at 1837
    const wrapper = mountMarkers({
      minYear: 1837,
      maxYear: 1901,
      sliderYear: 1837,
      events: [
        { year: 1870, label: "Education Act", type: "cultural" },
      ],
    });
    let yearLabels = wrapper.findAll(".timeline-markers__year");
    expect(yearLabels[0].isVisible()).toBe(true);

    // Move slider close to 1870
    await wrapper.setProps({ sliderYear: 1869 });
    yearLabels = wrapper.findAll(".timeline-markers__year");
    expect(yearLabels[0].isVisible()).toBe(false);
  });
```

Note: The `mountMarkers` helper needs to accept `sliderYear` in its
props object. If it uses a typed interface, add `sliderYear?: number`
to match the new prop.

**Step 2: Run test to verify it fails**

Run: `npm run --prefix frontend test -- --run src/components/socialcircles/__tests__/TimelineMarkers.test.ts`
Expected: FAIL — `sliderYear` is not a recognized prop

**Step 3: Revert MIN_LABEL_SPACING and add sliderYear prop**

In `TimelineMarkers.vue`, change the Props interface (lines 19-23):

```typescript
interface Props {
  minYear: number;
  maxYear: number;
  sliderYear?: number;
  events?: readonly HistoricalEvent[];
}
```

Update withDefaults (lines 25-27):

```typescript
const props = withDefaults(defineProps<Props>(), {
  sliderYear: undefined,
  events: () => VICTORIAN_EVENTS,
});
```

Revert `MIN_LABEL_SPACING` from 8 back to 4 (line 46):

```typescript
const MIN_LABEL_SPACING = 4;
```

Update the `visibleEvents` computed (lines 53-71) to account for
slider proximity:

```typescript
const visibleEvents = computed<EnrichedEvent[]>(() => {
  if (props.maxYear < props.minYear) return [];
  const filtered = props.events
    .filter((event) => event.year >= props.minYear && event.year <= props.maxYear)
    .map((e) => ({ ...e, _id: getEventId(e), _showLabel: false }));

  // Sort by year to evaluate label spacing left-to-right
  filtered.sort((a, b) => a.year - b.year);

  const sliderPercent =
    props.sliderYear !== undefined ? getPositionPercent(props.sliderYear) : null;

  let lastShownPercent = -Infinity;
  for (const event of filtered) {
    const percent = getPositionPercent(event.year);
    const tooCloseToSlider =
      sliderPercent !== null && Math.abs(percent - sliderPercent) < MIN_LABEL_SPACING;
    if (
      !tooCloseToSlider &&
      percent - lastShownPercent >= MIN_LABEL_SPACING - EPSILON
    ) {
      event._showLabel = true;
      lastShownPercent = percent;
    }
  }

  return filtered;
});
```

**Step 4: Pass sliderYear from TimelineSlider**

In `TimelineSlider.vue`, line 123, change:

```html
        <TimelineMarkers :min-year="minYear" :max-year="maxYear" />
```

To:

```html
        <TimelineMarkers :min-year="minYear" :max-year="maxYear" :slider-year="localYear" />
```

**Step 5: Run tests**

Run: `npm run --prefix frontend test -- --run src/components/socialcircles/__tests__/TimelineMarkers.test.ts`
Expected: ALL PASS

**Step 6: Update stale test comments**

In `TimelineMarkers.test.ts`, update any comments that reference "8%"
back to "4%" (lines 599, 644, 682 — these were changed in the
previous fix). The comments should read "4%" since MIN_LABEL_SPACING
is being reverted to 4.

**Step 7: Lint + type-check**

Run: `npm run --prefix frontend lint`
Run: `npm run --prefix frontend format`
Run: `npm run --prefix frontend type-check`

**Step 8: Commit**

```bash
git add frontend/src/components/socialcircles/TimelineMarkers.vue \
        frontend/src/components/socialcircles/TimelineSlider.vue \
        frontend/src/components/socialcircles/__tests__/TimelineMarkers.test.ts
git commit -m "fix: hide marker labels near slider position (#1668)"
```

---

## Track 3: Fix Show Less Layout Reset (#1669 regression)

### Task 3: Add position caching for subset layouts

**Files:**

- Modify: `frontend/src/components/socialcircles/NetworkGraph.vue:238-269`

**Step 1: Implement position caching in the element watch**

In `NetworkGraph.vue`, replace the element watch block (lines 238-269)
with:

```typescript
// Track element IDs to avoid unnecessary re-layouts (using Set for O(n) lookup)
let lastElementIds = new Set<string>();

// Cache node positions before re-layout for "show less" restoration
let positionCache = new Map<string, { x: number; y: number }>();

// Watch elements for filter changes - only re-layout if elements actually changed
watch(
  () => props.elements,
  (newElements) => {
    if (!cy.value) return;

    // Use Set for O(n) comparison instead of O(n log n) sorting
    // Filter out falsy IDs to prevent undefined/null from collapsing into single "" entry
    const newIdSet = new Set<string>(
      newElements.map((e) => e.data?.id).filter((id): id is NonNullable<typeof id> => Boolean(id))
    );
    // Check if any new ID wasn't in the old set (more intuitive: "what appeared?")
    const idsChanged =
      newIdSet.size !== lastElementIds.size || [...newIdSet].some((id) => !lastElementIds.has(id));

    if (!idsChanged) return; // Skip if same elements

    // Cache current positions before removing elements
    if (cy.value.nodes().length > 0) {
      positionCache = new Map(
        cy.value.nodes().map((n) => [n.id(), { ...n.position() }])
      );
    }

    // Check if new elements are a subset of old (shrink = show less)
    const isSubset =
      newIdSet.size < lastElementIds.size &&
      [...newIdSet].every((id) => lastElementIds.has(id));

    lastElementIds = newIdSet;

    cy.value.batch(() => {
      cy.value!.elements().remove();
      cy.value!.add(newElements);
    });

    if (isSubset && positionCache.size > 0) {
      // Restore cached positions for remaining nodes (deterministic reversal)
      cy.value
        .layout({
          name: "preset",
          positions: (node: { id: () => string }) => positionCache.get(node.id()),
          fit: true,
          padding: 50,
        } as LayoutOptions)
        .run();
    } else {
      cy.value.layout(LAYOUT_CONFIGS.force as LayoutOptions).run();
    }
  },
  // flush: "post" ensures DOM is ready; deep: true is defensive in case elements
  // are ever mutated in-place (currently they're replaced via computed)
  { deep: true, flush: "post" }
);
```

**Step 2: Lint + type-check**

Run: `npm run --prefix frontend lint`
Run: `npm run --prefix frontend type-check`

**Step 3: Run existing tests**

Run: `npm run --prefix frontend test -- --run`
Expected: ALL PASS (no unit test changes needed — the behavior is
internal to the Cytoscape integration which is tested via E2E)

**Step 4: Commit**

```bash
git add frontend/src/components/socialcircles/NetworkGraph.vue
git commit -m "fix: cache positions for subset layouts — show less preserves arrangement (#1669)"
```

---

## Parallelization Strategy

| Track | Branch | Worktree | Files |
|-------|--------|----------|-------|
| 1 (#1667) | `fix/graph-padding-revert` | `.worktrees/graph-padding` | constants, layoutConfigs, NetworkGraph, useSocialCircles, test |
| 2 (#1668) | `fix/slider-label-overlap` | `.worktrees/slider-labels` | TimelineMarkers, TimelineSlider, test |
| 3 (#1669) | `fix/showless-positions` | `.worktrees/showless-cache` | NetworkGraph |

**File overlap:** Tracks 1 and 3 both touch `NetworkGraph.vue` but at
different locations (line 321 vs lines 238-269). Safe to parallelize
if merged sequentially (Track 1 first, Track 3 rebases).

**Recommended merge order:** Track 2 first (no overlap), then Track 1,
then Track 3 (rebases on NetworkGraph changes).
