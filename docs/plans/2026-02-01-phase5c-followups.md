# Phase 5C Follow-ups Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> to implement this plan task-by-task.

**Goal:** Fix 3 post-review issues from Phase 5C and add hub mode E2E
test coverage.

**Architecture:** 4 independent tracks — one backend fix, two frontend
fixes, one E2E test suite. All can run in parallel with separate
worktrees.

**Tech Stack:** Python/FastAPI (backend), Vue 3/TypeScript (frontend),
Playwright (E2E)

---

## Track 1: Cap Connection List Size (#1654)

### Task 1: Add connection cap with test

**Files:**

- Modify: `backend/app/services/entity_profile.py:395-415`
- Test: `backend/tests/test_entity_profile.py` (add test)

**Context:** `generate_and_cache_profile()` builds `connection_list`
from all `connected_edges` and passes it to every AI call via the
`connections` parameter. Hub entities with 50+ connections produce
expensive prompts. We cap the prompt list at 15 (strongest first) while
keeping the full list for marker validation.

**Step 1: Write the failing test**

In `backend/tests/test_entity_profile.py`, add a test that verifies
connection_list is capped. Since `generate_and_cache_profile` is
tightly integrated with DB and Bedrock, test `_format_connection_instructions`
directly — it's the function that receives the connection list. The cap
should happen *before* this function is called.

Actually, the cap logic will be in `entity_profile.py`, not in the AI
generator. Add a unit test for the new constant and the slicing behavior.

Create test in `backend/tests/test_entity_profile_connections.py`:

```python
"""Tests for connection list capping in AI prompt generation."""

from app.services.entity_profile import _MAX_PROMPT_CONNECTIONS


def test_max_prompt_connections_is_15():
    """Cap should be 15 to balance prompt quality vs token cost."""
    assert _MAX_PROMPT_CONNECTIONS == 15
```

**Step 2: Run test to verify it fails**

Run: `poetry run pytest backend/tests/test_entity_profile_connections.py -v`
Expected: FAIL — `_MAX_PROMPT_CONNECTIONS` not defined

**Step 3: Implement the connection cap**

In `backend/app/services/entity_profile.py`, add the constant near the
top of file (after imports):

```python
_MAX_PROMPT_CONNECTIONS = 15
```

Then modify `generate_and_cache_profile()` — the section at lines
395-424. Change from:

```python
    connection_list = []
    for edge in connected_edges:
        other_id = edge.target if edge.source == node_id else edge.source
        other = node_map.get(other_id)
        if other:
            other_type = other.type.value if hasattr(other.type, "value") else str(other.type)
            connection_list.append(
                {
                    "entity_type": other_type,
                    "entity_id": other.entity_id,
                    "name": other.name,
                }
            )
    valid_entity_ids = {f"{c['entity_type']}:{c['entity_id']}" for c in connection_list}
```

To:

```python
    # Sort edges by strength so prompt gets strongest connections first
    connected_edges = sorted(connected_edges, key=lambda e: e.strength, reverse=True)

    connection_list = []
    for edge in connected_edges:
        other_id = edge.target if edge.source == node_id else edge.source
        other = node_map.get(other_id)
        if other:
            other_type = other.type.value if hasattr(other.type, "value") else str(other.type)
            connection_list.append(
                {
                    "entity_type": other_type,
                    "entity_id": other.entity_id,
                    "name": other.name,
                }
            )
    # Full set for marker validation (any connection marker is valid)
    valid_entity_ids = {f"{c['entity_type']}:{c['entity_id']}" for c in connection_list}

    # Cap connections in AI prompts to control token cost (#1654)
    prompt_connections = connection_list[:_MAX_PROMPT_CONNECTIONS]
```

Then update the three AI calls to use `prompt_connections` instead of
`connection_list`:

1. Line ~423: `connections=connection_list` → `connections=prompt_connections`
   (in `generate_bio_and_stories` call)
2. Line ~480: `connections=connection_list` → `connections=prompt_connections`
   (in `generate_relationship_story` call)
3. Line ~502: `connections=connection_list` → `connections=prompt_connections`
   (in `generate_connection_narrative` call)

**Step 4: Run tests**

Run: `poetry run pytest backend/tests/test_entity_profile_connections.py -v`
Expected: PASS

Run: `poetry run pytest backend/ -v`
Expected: All existing tests pass

**Step 5: Lint**

Run: `poetry run ruff check backend/`
Run: `poetry run ruff format --check backend/`

**Step 6: Commit**

```bash
git add backend/app/services/entity_profile.py backend/tests/test_entity_profile_connections.py
git commit -m "fix: cap connection list at 15 in AI prompts (#1654)"
```

---

## Track 2: Wire ExpandBadge via Cytoscape Labels (#1655)

### Task 2: Add hiddenCount to Cytoscape node data

**Files:**

- Modify: `frontend/src/composables/socialcircles/useSocialCircles.ts:265-280`

**Context:** `getCytoscapeElements()` transforms filtered nodes/edges
into Cytoscape `ElementDefinition[]`. We need to add a precomputed
`label` property that includes `" +N"` when the node has hidden
neighbors, and a `hiddenCount` data property for styling.

**Step 1: Modify getCytoscapeElements**

In `useSocialCircles.ts`, change `getCytoscapeElements()` from:

```typescript
  function getCytoscapeElements() {
    const m = meta.value;
    return transformToCytoscapeElements({
      nodes: [...filteredNodes.value] as ApiNode[],
      edges: [...filteredEdges.value] as ApiEdge[],
      meta: {
        total_books: m?.total_books ?? 0,
        ...
      },
    });
  }
```

To:

```typescript
  function getCytoscapeElements() {
    const m = meta.value;
    const elements = transformToCytoscapeElements({
      nodes: [...filteredNodes.value] as ApiNode[],
      edges: [...filteredEdges.value] as ApiEdge[],
      meta: {
        total_books: m?.total_books ?? 0,
        total_authors: m?.total_authors ?? 0,
        total_publishers: m?.total_publishers ?? 0,
        total_binders: m?.total_binders ?? 0,
        date_range: m?.date_range ? ([...m.date_range] as [number, number]) : [1800, 1900],
        generated_at: m?.generated_at ?? new Date().toISOString(),
        truncated: m?.truncated ?? false,
      },
    });

    // Inject hub mode badge data into node elements (#1655)
    if (!hubMode.isFullyExpanded.value) {
      for (const el of elements) {
        if (el.group === "nodes" && el.data?.id) {
          const hidden = hubMode.hiddenNeighborCount(el.data.id as NodeId);
          el.data.hiddenCount = hidden;
          el.data.label = hidden > 0 ? `${el.data.name}  +${hidden}` : el.data.name;
        }
      }
    } else {
      for (const el of elements) {
        if (el.group === "nodes") {
          el.data.hiddenCount = 0;
          el.data.label = el.data.name;
        }
      }
    }

    return elements;
  }
```

**Step 2: Run type-check**

Run: `npm run --prefix frontend type-check`
Expected: PASS (ElementDefinition data accepts arbitrary keys)

### Task 3: Update Cytoscape stylesheet to use label data

**Files:**

- Modify: `frontend/src/components/socialcircles/NetworkGraph.vue:90`

**Context:** Currently `label: "data(name)"`. Change to use
precomputed `label` field that includes "+N" badge text.

**Step 1: Update stylesheet**

In `NetworkGraph.vue`, line 90, change:

```typescript
        label: "data(name)",
```

To:

```typescript
        label: "data(label)",
```

Then add a new selector for badge-bearing nodes after the `node`
selector (after line 103):

```typescript
    {
      selector: "node[hiddenCount > 0]",
      style: {
        "font-size": "9px",
        "text-wrap": "wrap",
        "text-max-width": "100px",
      },
    },
```

**Step 2: Run lint + type-check**

Run: `npm run --prefix frontend lint`
Run: `npm run --prefix frontend type-check`

**Step 3: Commit**

```bash
git add frontend/src/composables/socialcircles/useSocialCircles.ts \
        frontend/src/components/socialcircles/NetworkGraph.vue
git commit -m "feat: show +N hidden count on Cytoscape node labels (#1655)"
```

---

## Track 3: Fix Double showMore() Overshoot (#1656)

### Task 4: Fix search auto-reveal logic

**Files:**

- Modify: `frontend/src/views/SocialCirclesView.vue:221-224`

**Context:** When a searched node isn't visible, the code calls
`showMore()` twice unconditionally, jumping from compact to full and
skipping medium. Fix: check visibility between calls.

**Step 1: Fix the code**

In `SocialCirclesView.vue`, change lines 221-224 from:

```typescript
      if (!filteredNodes.value.some((n) => n.id === node.id)) {
        hubMode.showMore();
        hubMode.showMore(); // Jump to full if needed
      }
```

To:

```typescript
      if (!filteredNodes.value.some((n) => n.id === node.id)) {
        hubMode.showMore();
        // Only escalate to full if node still not visible after first expansion
        if (!filteredNodes.value.some((n) => n.id === node.id)) {
          hubMode.showMore();
        }
      }
```

**Step 2: Lint + type-check**

Run: `npm run --prefix frontend lint`
Run: `npm run --prefix frontend format`
Run: `npm run --prefix frontend type-check`

**Step 3: Commit**

```bash
git add frontend/src/views/SocialCirclesView.vue
git commit -m "fix: check visibility between showMore() calls in search (#1656)"
```

---

## Track 4: Hub Mode E2E Tests

### Task 5: Create hub mode E2E test spec

**Files:**

- Create: `frontend/e2e/socialcircles-hub-mode.spec.ts`

**Context:** No E2E coverage exists for hub mode progressive
disclosure. Tests run against staging where Phase 5C is deployed.
Follow patterns from existing `socialcircles-search.spec.ts`.

**Step 1: Write the E2E spec**

```typescript
import { test, expect } from "@playwright/test";

/**
 * Social Circles Hub Mode E2E Tests
 *
 * Tests progressive disclosure: initial compact view (25 nodes),
 * ShowMoreButton expansion, and full graph reveal.
 */

test.describe("Social Circles Hub Mode", () => {
  test.beforeEach(async ({ page }) => {
    const viewport = page.viewportSize();
    test.skip(
      !!viewport && viewport.width <= 768,
      "Hub mode controls require desktop viewport"
    );

    await page.goto("/social-circles");
    await expect(page.getByTestId("network-graph")).toBeVisible({
      timeout: 15000,
    });
  });

  test("ShowMoreButton is visible on initial load", async ({ page }) => {
    const btn = page.getByTestId("show-more-btn");
    await expect(btn).toBeVisible({ timeout: 5000 });
    await expect(btn).toContainText(/Showing \d+ of \d+/);
    await expect(btn).toContainText("Show more");
  });

  test("clicking ShowMoreButton expands node count", async ({ page }) => {
    const btn = page.getByTestId("show-more-btn");
    await expect(btn).toBeVisible({ timeout: 5000 });

    // Capture initial count text
    const initialText = await btn.textContent();

    // Click to expand (compact → medium)
    await btn.click();

    // Button should still be visible with updated count (medium level)
    // or may have disappeared if total nodes < 50
    const stillVisible = await btn.isVisible().catch(() => false);
    if (stillVisible) {
      const updatedText = await btn.textContent();
      // Count should have increased
      expect(updatedText).not.toBe(initialText);
    }
  });

  test("two clicks reveals all nodes and hides button", async ({
    page,
  }) => {
    const btn = page.getByTestId("show-more-btn");
    await expect(btn).toBeVisible({ timeout: 5000 });

    // Click twice: compact → medium → full
    await btn.click();
    // Small delay for reactivity
    await page.waitForTimeout(300);

    const stillVisible = await btn.isVisible().catch(() => false);
    if (stillVisible) {
      await btn.click();
      // After full expansion, button should disappear
      await expect(btn).not.toBeVisible({ timeout: 3000 });
    }
  });

  test("graph renders without errors at each hub level", async ({
    page,
  }) => {
    // Verify no console errors during expansion
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));

    const btn = page.getByTestId("show-more-btn");
    await expect(btn).toBeVisible({ timeout: 5000 });

    // Expand through levels
    await btn.click();
    await page.waitForTimeout(500);

    const stillVisible = await btn.isVisible().catch(() => false);
    if (stillVisible) {
      await btn.click();
      await page.waitForTimeout(500);
    }

    // No JS errors during expansion
    expect(errors).toHaveLength(0);
  });

  test("search auto-reveal works after hub mode expansion", async ({
    page,
  }) => {
    // Find the search input
    const searchInput = page.getByTestId("search-input");
    test.skip(
      !(await searchInput.isVisible()),
      "SearchInput component not rendered"
    );

    const inputField = searchInput.locator("input");
    await inputField.fill("Charles");

    // Wait for dropdown
    const dropdown = searchInput.getByTestId("search-dropdown");
    await expect(dropdown).toBeVisible({ timeout: 5000 });

    // Select first result
    const firstResult = dropdown.getByTestId("search-item").first();
    await expect(firstResult).toBeVisible();
    await firstResult.click();

    // Graph should center on the node (no toast error)
    // If the node was hidden, hub mode should have auto-expanded
    const toast = page.locator(".toast-message, [role='alert']");
    await expect(toast).not.toBeVisible({ timeout: 2000 }).catch(() => {
      // Toast may not exist at all — that's fine
    });
  });
});
```

**Step 2: Run locally to verify**

Run: `npx playwright test frontend/e2e/socialcircles-hub-mode.spec.ts --project=chromium`

Note: This runs against staging. Verify tests pass.

**Step 3: Commit**

```bash
git add frontend/e2e/socialcircles-hub-mode.spec.ts
git commit -m "test: add hub mode E2E tests for progressive disclosure"
```

---

## Parallelization Strategy

| Track | Branch | Worktree | Files |
|-------|--------|----------|-------|
| 1 (#1654) | `fix/cap-connections` | `.worktrees/cap-connections` | `backend/` only |
| 2 (#1655) | `feat/expand-badge-labels` | `.worktrees/expand-badge` | `frontend/src/` |
| 3 (#1656) | `fix/showmore-overshoot` | `.worktrees/showmore-fix` | `frontend/src/views/` |
| 4 (E2E) | `test/hub-mode-e2e` | `.worktrees/hub-mode-e2e` | `frontend/e2e/` |

**No file overlap** between any tracks — safe to parallelize fully.

Tracks 2 and 3 both touch `frontend/src/` but different files:

- Track 2: `useSocialCircles.ts`, `NetworkGraph.vue`
- Track 3: `SocialCirclesView.vue`
