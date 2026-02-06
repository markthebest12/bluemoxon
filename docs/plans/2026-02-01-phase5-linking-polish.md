# Entity Profiles Phase 5 — Linking, Polish & Enrichment

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the entity profile experience by fixing linking bugs, adding missing click interactions, wiring analytics, and preparing for content enrichment. Three sub-phases: immediate fixes, near-term interactivity, and future brainstorming items.

**Architecture:** Phase 5A tasks have zero file overlap and run fully in parallel. Phase 5B adds analytics and stats. Phase 5C requires brainstorming sessions before implementation.

**Tech Stack:** Vue 3/TypeScript (frontend), Python/FastAPI (backend), Vitest (unit tests), Playwright (E2E)

---

## Phase Overview

| Sub-Phase | Scope | Issues | Effort |
|-----------|-------|--------|--------|
| **5A** | Linking & display fixes | #1615, #1616, #1617, #1620 | Small — all frontend, parallel |
| **5B** | Analytics & stats | #1621, new backend stats | Medium — frontend + backend |
| **5C** | Content enrichment | #1618, #1619, portraits, thumbnails | Needs brainstorming first |

---

## Phase 5A — Linking & Display Fixes (Immediate)

All 4 tasks touch different files — run fully in parallel across 4 worktrees.

### Parallel Execution Strategy

| Lane | Worktree | Branch | Issue | File |
|------|----------|--------|-------|------|
| A | `.tmp/worktrees/fix-condition` | `fix/ep-condition-labels` | #1617 | `EntityBooks.vue` |
| B | `.tmp/worktrees/fix-shared-books` | `fix/ep-shared-book-links` | #1615 | `KeyConnections.vue` |
| C | `.tmp/worktrees/fix-timeline-click` | `fix/ep-timeline-click` | #1620 | `PublicationTimeline.vue` |
| D | `.tmp/worktrees/fix-ego-click` | `fix/ep-ego-network-click` | #1616 | `EgoNetwork.vue` |

---

### Task 1: Fix condition label display in EntityBooks (#1617)

**Lane:** A
**Branch:** `fix/ep-condition-labels`

**Files:**
- Modify: `frontend/src/components/entityprofile/EntityBooks.vue:33`
- Test: `frontend/src/components/entityprofile/__tests__/EntityBooks.test.ts` (create if needed)

**Context:** EntityBooks displays `book.condition` raw (e.g., `NEAR_FINE`). The utility `formatConditionGrade()` in `frontend/src/utils/format.ts:23-55` already handles this — it maps enum values to human-readable labels using `CONDITION_GRADE_OPTIONS` from `frontend/src/constants/index.ts:77-88`.

**Step 1: Write the failing test**

Create `frontend/src/components/entityprofile/__tests__/EntityBooks.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import EntityBooks from "../EntityBooks.vue";

const mockBooks = [
  { id: 1, title: "Aurora Leigh", year: 1856, condition: "NEAR_FINE", edition: "First" },
  { id: 2, title: "Sonnets", year: 1850, condition: "VERY_GOOD", edition: null },
  { id: 3, title: "Poems", year: 1844, condition: null, edition: null },
];

describe("EntityBooks", () => {
  it("formats condition labels as human-readable text", () => {
    const wrapper = mount(EntityBooks, {
      props: { books: mockBooks },
      global: { stubs: { "router-link": { template: "<a><slot /></a>", props: ["to"] } } },
    });
    expect(wrapper.text()).toContain("Near Fine");
    expect(wrapper.text()).not.toContain("NEAR_FINE");
    expect(wrapper.text()).toContain("Very Good");
    expect(wrapper.text()).not.toContain("VERY_GOOD");
  });

  it("handles null condition gracefully", () => {
    const wrapper = mount(EntityBooks, {
      props: { books: [{ id: 3, title: "Poems", year: 1844, condition: null, edition: null }] },
      global: { stubs: { "router-link": { template: "<a><slot /></a>", props: ["to"] } } },
    });
    expect(wrapper.text()).not.toContain("null");
  });
});
```

**Step 2: Run test to verify it fails**

```bash
npm run --prefix frontend test -- --run src/components/entityprofile/__tests__/EntityBooks.test.ts
```

Expected: FAIL — currently renders raw `NEAR_FINE`.

**Step 3: Write the implementation**

In `frontend/src/components/entityprofile/EntityBooks.vue`, add the import in the `<script setup>` section:

```typescript
import { formatConditionGrade } from "@/utils/format";
```

Then change line 33 from:

```vue
<span v-if="book.condition" class="entity-books__condition">{{ book.condition }}</span>
```

To:

```vue
<span v-if="book.condition" class="entity-books__condition">{{ formatConditionGrade(book.condition) }}</span>
```

**Step 4: Run test to verify it passes**

```bash
npm run --prefix frontend test -- --run src/components/entityprofile/__tests__/EntityBooks.test.ts
```

Expected: PASS

**Step 5: Lint and commit**

```bash
npm run --prefix frontend lint
npm run --prefix frontend format
git add frontend/src/components/entityprofile/EntityBooks.vue frontend/src/components/entityprofile/__tests__/EntityBooks.test.ts
git commit -m "fix: display human-readable condition labels in EntityBooks (#1617)"
```

---

### Task 2: Add book detail links to shared books in KeyConnections (#1615)

**Lane:** B
**Branch:** `fix/ep-shared-book-links`

**Files:**
- Modify: `frontend/src/components/entityprofile/KeyConnections.vue:51-55`
- Test: `frontend/src/components/entityprofile/__tests__/KeyConnections.test.ts` (existing file)

**Context:** Shared books in KeyConnections connection cards are displayed as plain `<li>` text. Book objects have `id`, `title`, and `year` properties. The `book-detail` route is defined at `/books/:id` with name `"book-detail"`.

**Step 1: Write the failing test**

Add to existing `frontend/src/components/entityprofile/__tests__/KeyConnections.test.ts`:

```typescript
it("renders shared books as links to book detail", () => {
  // Use a connection fixture that has shared_books
  const wrapper = mount(KeyConnections, {
    props: {
      connections: [
        {
          entity: { id: 31, type: "author", name: "EBB" },
          connection_type: "shared_publisher",
          strength: 5,
          shared_book_count: 1,
          shared_books: [{ id: 57, title: "Poetical Works", year: 1904 }],
          narrative: null,
          narrative_trigger: null,
          is_key: true,
          relationship_story: null,
        },
      ],
    },
    global: {
      stubs: {
        "router-link": {
          template: '<a :data-to="JSON.stringify(to)"><slot /></a>',
          props: ["to"],
        },
      },
    },
  });

  const bookLinks = wrapper.findAll(".key-connections__book-link");
  expect(bookLinks.length).toBe(1);
  const to = JSON.parse(bookLinks[0].attributes("data-to")!);
  expect(to.name).toBe("book-detail");
  expect(to.params.id).toBe(57);
});
```

**Step 2: Run test to verify it fails**

```bash
npm run --prefix frontend test -- --run src/components/entityprofile/__tests__/KeyConnections.test.ts
```

Expected: FAIL — no `.key-connections__book-link` elements exist.

**Step 3: Write the implementation**

In `frontend/src/components/entityprofile/KeyConnections.vue`, change the shared books list at lines 51-55 from:

```vue
<ul v-if="conn.shared_books.length" class="key-connections__books">
  <li v-for="book in conn.shared_books" :key="book.id">
    {{ book.title }}<span v-if="book.year"> ({{ book.year }})</span>
  </li>
</ul>
```

To:

```vue
<ul v-if="conn.shared_books.length" class="key-connections__books">
  <li v-for="book in conn.shared_books" :key="book.id">
    <router-link
      :to="{ name: 'book-detail', params: { id: book.id } }"
      class="key-connections__book-link"
    >
      {{ book.title }}
    </router-link>
    <span v-if="book.year"> ({{ book.year }})</span>
  </li>
</ul>
```

Add CSS in the `<style scoped>` section:

```css
.key-connections__book-link {
  color: var(--color-accent-gold, #b8860b);
  text-decoration: none;
}

.key-connections__book-link:hover {
  text-decoration: underline;
}
```

**Step 4: Run test to verify it passes**

```bash
npm run --prefix frontend test -- --run src/components/entityprofile/__tests__/KeyConnections.test.ts
```

Expected: PASS

**Step 5: Also format the condition in shared books**

The shared books also show `book.condition` if present. Apply `formatConditionGrade()` here too if condition is displayed. Check the template — if condition appears, import and use the formatter.

**Step 6: Lint and commit**

```bash
npm run --prefix frontend lint
npm run --prefix frontend format
git add frontend/src/components/entityprofile/KeyConnections.vue frontend/src/components/entityprofile/__tests__/KeyConnections.test.ts
git commit -m "fix: link shared books to book detail pages in KeyConnections (#1615)"
```

---

### Task 3: Add click-to-navigate on PublicationTimeline dots (#1620)

**Lane:** C
**Branch:** `fix/ep-timeline-click`

**Files:**
- Modify: `frontend/src/components/entityprofile/PublicationTimeline.vue:61-70`
- Test: `frontend/src/components/entityprofile/__tests__/PublicationTimeline.test.ts` (create if needed)

**Context:** Timeline dots have `cursor: pointer` CSS (line 114) but no `@click` handler. Each dot's `book` object has an `id` property. The `book-detail` route is at `/books/:id`.

**Step 1: Write the failing test**

Create `frontend/src/components/entityprofile/__tests__/PublicationTimeline.test.ts`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import PublicationTimeline from "../PublicationTimeline.vue";

const mockRouter = { push: vi.fn() };

vi.mock("vue-router", () => ({
  useRouter: () => mockRouter,
}));

const mockBooks = [
  { id: 57, title: "Poetical Works", year: 1904, condition: "VERY_GOOD", edition: "Oxford" },
  { id: 59, title: "Aurora Leigh", year: 1877, condition: "NEAR_FINE", edition: "Reprint" },
];

describe("PublicationTimeline", () => {
  it("navigates to book detail on dot click", async () => {
    const wrapper = mount(PublicationTimeline, {
      props: { books: mockBooks },
    });

    const dots = wrapper.findAll(".publication-timeline__dot");
    if (dots.length > 0) {
      await dots[0].trigger("click");
      expect(mockRouter.push).toHaveBeenCalledWith({
        name: "book-detail",
        params: { id: expect.any(Number) },
      });
    }
  });
});
```

**Step 2: Run test to verify it fails**

```bash
npm run --prefix frontend test -- --run src/components/entityprofile/__tests__/PublicationTimeline.test.ts
```

Expected: FAIL — no router.push call on click.

**Step 3: Write the implementation**

In `frontend/src/components/entityprofile/PublicationTimeline.vue`, add the router import in `<script setup>`:

```typescript
import { useRouter } from "vue-router";

const router = useRouter();
```

Then add a click handler function:

```typescript
function navigateToBook(bookId: number) {
  void router.push({ name: "book-detail", params: { id: bookId } });
}
```

On the dot element (around line 61-70), add `@click`:

Change from whatever the current dot element is to include:

```vue
@click="navigateToBook(book.id)"
```

The dot element should have both the existing `@mouseenter`/`@mouseleave` AND the new `@click`.

**Step 4: Run test to verify it passes**

```bash
npm run --prefix frontend test -- --run src/components/entityprofile/__tests__/PublicationTimeline.test.ts
```

Expected: PASS

**Step 5: Lint and commit**

```bash
npm run --prefix frontend lint
npm run --prefix frontend format
git add frontend/src/components/entityprofile/PublicationTimeline.vue frontend/src/components/entityprofile/__tests__/PublicationTimeline.test.ts
git commit -m "feat: navigate to book detail on PublicationTimeline dot click (#1620)"
```

---

### Task 4: Add click navigation to EgoNetwork nodes (#1616)

**Lane:** D
**Branch:** `fix/ep-ego-network-click`

**Files:**
- Modify: `frontend/src/components/entityprofile/EgoNetwork.vue` (Cytoscape event handlers, ~line 125)
- Test: `frontend/src/components/entityprofile/__tests__/EgoNetwork.test.ts` (create if needed)

**Context:** EgoNetwork uses Cytoscape.js with concentric layout. All user interaction is disabled (`userZoomingEnabled: false`, `userPanningEnabled: false`, `boxSelectionEnabled: false`). Nodes have entity data (type, entity_id) stored in Cytoscape node data. Clicking a node should navigate to that entity's profile.

**Step 1: Add Cytoscape tap handler**

In the `<script setup>` section of `EgoNetwork.vue`, import the router:

```typescript
import { useRouter } from "vue-router";

const router = useRouter();
```

After the Cytoscape instance is initialized (after the `cy = cytoscape({...})` call), add a tap event handler:

```typescript
cy.on("tap", "node", (evt) => {
  const node = evt.target;
  const entityType = node.data("entityType");
  const entityId = node.data("entityId");
  // Don't navigate to self (the center node is the current entity)
  if (entityType && entityId && entityId !== props.entityId) {
    void router.push({
      name: "entity-profile",
      params: { type: entityType, id: String(entityId) },
    });
  }
});
```

**Step 2: Verify node data includes entity info**

Check how nodes are created in the component. Each node needs `entityType` and `entityId` in its Cytoscape data. The component receives `connections` as a prop — each connection has `entity.type` and `entity.id`. Verify these are passed to Cytoscape node data when building the graph elements.

If they're not in the data already, add them when constructing the Cytoscape elements array:

```typescript
{
  data: {
    id: `${conn.entity.type}:${conn.entity.id}`,
    label: conn.entity.name,
    entityType: conn.entity.type,
    entityId: conn.entity.id,
  },
}
```

**Step 3: Add visual feedback**

Add a hover style change to show nodes are clickable. In the Cytoscape stylesheet array, add:

```typescript
{
  selector: "node:active",
  style: {
    "overlay-opacity": 0.1,
  },
},
```

Also consider adding `cursor: pointer` handling — Cytoscape manages cursor separately from CSS.

**Step 4: Enable pointer cursor on nodes**

After Cytoscape initialization:

```typescript
cy.on("mouseover", "node", () => {
  document.body.style.cursor = "pointer";
});
cy.on("mouseout", "node", () => {
  document.body.style.cursor = "default";
});
```

**Step 5: Type-check and lint**

```bash
npm run --prefix frontend type-check
npm run --prefix frontend lint
npm run --prefix frontend format
```

**Step 6: Commit**

```bash
git add frontend/src/components/entityprofile/EgoNetwork.vue
git commit -m "feat: navigate to entity profile on EgoNetwork node click (#1616)"
```

---

### Phase 5A Merge

After all 4 lanes complete:

```bash
gh pr create --base staging --head fix/ep-condition-labels --title "fix: human-readable condition labels in EntityBooks (#1617)"
gh pr create --base staging --head fix/ep-shared-book-links --title "fix: link shared books to book detail pages (#1615)"
gh pr create --base staging --head fix/ep-timeline-click --title "feat: PublicationTimeline dot click navigates to book (#1620)"
gh pr create --base staging --head fix/ep-ego-network-click --title "feat: EgoNetwork node click navigates to entity profile (#1616)"
```

Merge each with `--squash`. Run full test suite on staging. Promote to main.

---

## Phase 5B — Analytics & Stats (Near-term)

### Task 5: Wire analytics into entity profile views (#1621)

**Files:**
- Modify: `frontend/src/views/EntityProfileView.vue`
- Modify: `frontend/src/components/entityprofile/KeyConnections.vue`
- Modify: `frontend/src/composables/socialcircles/useAnalytics.ts` (add new tracking functions)
- Test: `frontend/src/composables/socialcircles/__tests__/useAnalytics.test.ts` (existing, add new tests)

**Context:** useAnalytics is a singleton composable with dev console logging and prod stub. Currently has 9 tracking functions for social circles. Needs 5 new functions for entity profiles.

**Step 1: Add new tracking functions to useAnalytics**

In `frontend/src/composables/socialcircles/useAnalytics.ts`, add:

```typescript
trackProfileView(entity: { type: string; id: number; name: string; tier?: string }) {
  track("profile_viewed", {
    entityType: entity.type,
    entityId: entity.id,
    entityName: entity.name,
    tier: entity.tier,
  });
},

trackConnectionClick(source: { type: string; id: number }, target: { type: string; id: number }) {
  track("connection_clicked", {
    sourceType: source.type,
    sourceId: source.id,
    targetType: target.type,
    targetId: target.id,
  });
},

trackGossipExpand(entityType: string, entityId: number, connectionEntityId: number) {
  track("gossip_expanded", { entityType, entityId, connectionEntityId });
},

trackBookClick(bookId: number, source: string) {
  track("book_clicked", { bookId, source });
},

trackProfileRegenerate(entityType: string, entityId: number) {
  track("profile_regenerated", { entityType, entityId });
},
```

**Step 2: Write tests for new functions**

Add to existing `useAnalytics.test.ts`:

```typescript
it("tracks profile view", () => {
  const { trackProfileView } = useAnalytics();
  trackProfileView({ type: "author", id: 31, name: "EBB", tier: "TIER_1" });
  // Verify no throw; in dev mode, check console.log was called
});

it("tracks gossip expand", () => {
  const { trackGossipExpand } = useAnalytics();
  trackGossipExpand("author", 31, 245);
});
```

**Step 3: Wire into EntityProfileView**

In `EntityProfileView.vue`, import and call:

```typescript
import { useAnalytics } from "@/composables/socialcircles/useAnalytics";

const analytics = useAnalytics();

// In onMounted or after fetchProfile succeeds:
watch(entity, (newEntity) => {
  if (newEntity) {
    analytics.trackProfileView({
      type: newEntity.type,
      id: newEntity.id,
      name: newEntity.name,
      tier: newEntity.tier,
    });
  }
});
```

**Step 4: Wire into KeyConnections (gossip expand)**

In `KeyConnections.vue`, when the gossip toggle is clicked, call:

```typescript
analytics.trackGossipExpand(/* pass entity context */);
```

**Step 5: Wire into handleRegenerate**

In `EntityProfileView.vue`, add tracking to `handleRegenerate()`:

```typescript
async function handleRegenerate() {
  if (!entity.value) return;
  analytics.trackProfileRegenerate(entity.value.type, entity.value.id);
  // ... existing regenerate logic
}
```

**Step 6: Test, lint, commit**

```bash
npm run --prefix frontend test -- --run
npm run --prefix frontend lint
npm run --prefix frontend format
git add -A
git commit -m "feat: wire analytics tracking into entity profile views (#1621)"
```

---

### Task 6: Add condition breakdown to CollectionStats (new issue needed)

**Files:**
- Modify: `backend/app/schemas/entity_profile.py:86-92` (add `condition_breakdown` field to ProfileStats)
- Modify: `backend/app/services/entity_profile.py` (compute condition counts)
- Modify: `frontend/src/components/entityprofile/CollectionStats.vue`
- Test: Backend + frontend tests

**Context:** ProfileStats currently has 4 fields. The books data already includes condition values. The backend needs to aggregate `condition` values across the entity's books and return a breakdown dict like `{"NEAR_FINE": 1, "VERY_GOOD": 2}`.

**Step 1: Add field to ProfileStats schema**

```python
class ProfileStats(BaseModel):
    total_books: int = 0
    total_estimated_value: float | None = None
    first_editions: int = 0
    date_range: list[int] = Field(default_factory=list)
    condition_breakdown: dict[str, int] = Field(default_factory=dict)
```

**Step 2: Compute in backend service**

Where ProfileStats is built (in the entity profile service), add:

```python
from collections import Counter

condition_counts = Counter(b.condition_grade for b in books if b.condition_grade)
stats.condition_breakdown = dict(condition_counts)
```

**Step 3: Display in CollectionStats.vue**

Add a condition breakdown section after the existing stats grid:

```vue
<div v-if="Object.keys(stats.condition_breakdown ?? {}).length > 0" class="collection-stats__item collection-stats__item--wide">
  <dt>Condition</dt>
  <dd class="collection-stats__breakdown">
    <span v-for="(count, grade) in stats.condition_breakdown" :key="grade" class="collection-stats__grade">
      {{ formatConditionGrade(grade) }}: {{ count }}
    </span>
  </dd>
</div>
```

**Step 4: Test, lint, commit**

Backend and frontend tests, then commit.

---

## Phase 5C — Content Enrichment (Requires Brainstorming)

These items need brainstorming sessions before implementation plans can be written. Create a brainstorming session for each when ready.

### #1618: AI-generated stories should create entity cross-links

**Brainstorming questions:**
- Frontend auto-linking (pattern match entity names in text)?
- Backend enrichment (Bedrock returns entity references)?
- Hybrid approach?
- How to handle ambiguous names?
- Performance impact of text scanning?

**Recommended approach to explore:** Backend enrichment — have the AI generation prompt request structured entity references alongside narrative text. Frontend renders links from the structured data. This avoids fragile text pattern matching.

### #1619: Social circles landing page — improve default view

**Brainstorming questions:**
- Smart initial zoom vs progressive disclosure vs search-first?
- How to pick a "featured" cluster algorithmically?
- Should the default change on each visit?
- Mobile considerations (dense graph on small screen)?

### Portrait/Placeholder Images in ProfileHero

**Brainstorming questions:**
- Source: public domain historical portraits? AI-generated? Placeholder silhouettes?
- Storage: S3 images bucket? CDN?
- Fallback: entity type icon (author/publisher/binder)?
- Integration with existing getPlaceholderImage() in social circles?

### Book Thumbnails in EntityBooks

**Brainstorming questions:**
- Source: existing book images from S3? Cover scan pipeline?
- Thumbnail sizing and lazy loading?
- Fallback for books without images?

---

## Issue Tracker

| # | Title | Phase | Status |
|---|-------|-------|--------|
| #1615 | Shared books don't link to book entity | 5A | Open |
| #1616 | Network connections don't link to other entities | 5A | Open |
| #1617 | Book quality fields show raw DB enum values | 5A | Open |
| #1618 | AI-generated stories should create entity cross-links | 5C | Open (brainstorm) |
| #1619 | Social circles landing page — improve default view | 5C | Open (brainstorm) |
| #1620 | PublicationTimeline dots should navigate to book detail | 5A | Open |
| #1621 | Wire analytics tracking into entity profile views | 5B | Open |
| TBD | Condition breakdown in CollectionStats | 5B | Needs issue |
| TBD | Portrait/placeholder images in ProfileHero | 5C | Needs brainstorming |
| TBD | Book thumbnails in EntityBooks | 5C | Needs brainstorming |
