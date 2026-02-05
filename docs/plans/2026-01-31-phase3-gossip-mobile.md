# Entity Profiles Phase 3: Gossip Panel + Mobile + E2E

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add inline gossip panel (relationship stories) to KeyConnections cards, optimize all entity profile components for mobile viewports, and add E2E test coverage.

**Architecture:** Frontend-only changes. The `relationship_story` data already flows from the backend (`ProfileConnection.relationship_story: RelationshipNarrative | null`) but is not rendered. We extract a shared `useToneStyle()` composable, create a `ConnectionGossipPanel` component with style-adaptive rendering (prose/bullets/timeline), wire it into KeyConnections as an accordion, add responsive CSS at 768px/480px breakpoints, and replace EgoNetwork with a text-based ConnectionSummary on mobile. E2E tests validate the full flow.

**Tech Stack:** Vue 3, TypeScript, Playwright, Vitest, @vue/test-utils

**Worktrees:** Three parallel worktrees from `staging` (see Parallel Execution Strategy below).

---

## Parallel Execution Strategy

### Setup — 3 Worktrees

```bash
git worktree add .tmp/worktrees/phase3-gossip -b feat/ep-phase3-gossip staging
git worktree add .tmp/worktrees/phase3-mobile -b feat/ep-phase3-mobile staging
git worktree add .tmp/worktrees/phase3-e2e -b feat/ep-phase3-e2e staging
```

### Wave 1 — 3 Parallel Subagents

| Subagent | Worktree | Tasks | Files Created/Modified |
|----------|----------|-------|----------------------|
| A: Gossip | `.tmp/worktrees/phase3-gossip` | 1 → 2 → 3 (sequential) | useToneStyle.ts, ConnectionGossipPanel.vue, KeyConnections.vue, ProfileHero.vue (script+template) |
| B: Mobile | `.tmp/worktrees/phase3-mobile` | 4 (independent pieces only) | ConnectionSummary.vue, useMediaQuery.ts, EntityProfileView.vue, CollectionStats.vue (CSS), PublicationTimeline.vue (CSS), ProfileHero.vue (CSS only) |
| C: E2E | `.tmp/worktrees/phase3-e2e` | 5 (write test file) | entity-profile.spec.ts |

**Important for Subagent B:** Do NOT touch `KeyConnections.vue` — its mobile CSS depends on Task 3's toggle button which is in Subagent A. That CSS gets applied in Wave 2.

### Wave 2 — Merge + Fixup (sequential)

1. Create integration branch: `git checkout -b feat/ep-phase3-gossip-mobile staging`
2. Merge gossip: `git merge feat/ep-phase3-gossip`
3. Merge mobile: `git merge feat/ep-phase3-mobile` (ProfileHero.vue: script vs CSS — should auto-merge)
4. Merge e2e: `git merge feat/ep-phase3-e2e`
5. **Fixup commit:** Add KeyConnections.vue mobile CSS (the one piece that depends on Task 3's toggle)
6. Run full unit tests: `npm run --prefix frontend test:unit`
7. Run lint + type-check: `npm run --prefix frontend lint` then `npm run --prefix frontend type-check`

### Wave 3 — Review

Use `/bmx-review-changes` to spawn a code review subagent, then `/bmx-apply-review-feedback` for fixes.

### Wave 4 — Ship

1. PR `feat/ep-phase3-gossip-mobile` → `staging`
2. Merge (squash)
3. Watch deploy
4. Run E2E: `/bmx-e2e-validation`
5. If green: promote staging → main

### Skills for Implementation Session

- `superpowers:subagent-driven-development` — orchestrate the parallel subagents
- `superpowers:test-driven-development` — each subagent follows TDD per task steps
- `superpowers:verification-before-completion` — run tests before claiming done
- `/bmx-review-changes` — code review after merge
- `/bmx-apply-review-feedback` — apply review fixes
- `/bmx-e2e-validation` — post-deploy validation
- Sequential-Thinking MCP — for complex merge conflict resolution if needed

---

## Task 1: Extract `useToneStyle` Composable

**Lane A** — runs in `.tmp/worktrees/phase3-gossip`, step 1 of 3.

**Files:**
- Create: `frontend/src/composables/entityprofile/useToneStyle.ts`
- Create: `frontend/src/composables/entityprofile/__tests__/useToneStyle.test.ts`
- Modify: `frontend/src/components/entityprofile/ProfileHero.vue:51` (use composable instead of inline class)

**Context:** ProfileHero currently applies `:class="\`--${story.tone}\`"` at line 51 but has no tone-specific CSS. The composable defines the tone-to-color mapping and both ProfileHero and ConnectionGossipPanel (Task 2) will consume it.

### Step 1: Write the failing test

Create `frontend/src/composables/entityprofile/__tests__/useToneStyle.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { useToneStyle } from "../useToneStyle";
import type { Tone } from "@/types/entityProfile";

describe("useToneStyle", () => {
  const ALL_TONES: Tone[] = ["dramatic", "scandalous", "tragic", "intellectual", "triumphant"];

  it("returns a className and color for each tone", () => {
    for (const tone of ALL_TONES) {
      const style = useToneStyle(tone);
      expect(style.className).toBe(`tone--${tone}`);
      expect(style.color).toBeTruthy();
    }
  });

  it("returns distinct colors for each tone", () => {
    const colors = ALL_TONES.map((t) => useToneStyle(t).color);
    expect(new Set(colors).size).toBe(ALL_TONES.length);
  });

  it("returns fallback for unknown tone", () => {
    const style = useToneStyle("unknown" as Tone);
    expect(style.className).toBe("tone--unknown");
    expect(style.color).toBeTruthy();
  });
});
```

### Step 2: Run test to verify it fails

Run: `npm run --prefix frontend test:unit -- --run src/composables/entityprofile/__tests__/useToneStyle.test.ts`

Expected: FAIL — module `../useToneStyle` not found.

### Step 3: Write minimal implementation

Create `frontend/src/composables/entityprofile/useToneStyle.ts`:

```typescript
import type { Tone } from "@/types/entityProfile";

export interface ToneStyle {
  className: string;
  color: string;
}

const TONE_COLORS: Record<string, string> = {
  dramatic: "#c0392b",
  scandalous: "#e74c3c",
  tragic: "#7f8c8d",
  intellectual: "#2c3e50",
  triumphant: "#d4a017",
};

const FALLBACK_COLOR = "#b8860b";

export function useToneStyle(tone: Tone): ToneStyle {
  return {
    className: `tone--${tone}`,
    color: TONE_COLORS[tone] ?? FALLBACK_COLOR,
  };
}
```

### Step 4: Run test to verify it passes

Run: `npm run --prefix frontend test:unit -- --run src/composables/entityprofile/__tests__/useToneStyle.test.ts`

Expected: 3 tests PASS.

### Step 5: Wire into ProfileHero

Modify `frontend/src/components/entityprofile/ProfileHero.vue`:

In `<script setup>`, add import:
```typescript
import { useToneStyle } from "@/composables/entityprofile/useToneStyle";
```

Change line 51 from:
```html
:class="`--${story.tone}`"
```
to:
```html
:class="useToneStyle(story.tone).className"
:style="{ borderLeftColor: useToneStyle(story.tone).color }"
```

### Step 6: Run existing ProfileHero tests

Run: `npm run --prefix frontend test:unit -- --run src/components/entityprofile/__tests__/ProfileHero.test.ts`

Expected: All 7 tests PASS (no functional change, just CSS).

### Step 7: Commit

```
git add frontend/src/composables/entityprofile/useToneStyle.ts frontend/src/composables/entityprofile/__tests__/useToneStyle.test.ts frontend/src/components/entityprofile/ProfileHero.vue
git commit -m "feat(ep): extract useToneStyle composable from ProfileHero"
```

---

## Task 2: Create `ConnectionGossipPanel` Component

**Lane A** — runs in `.tmp/worktrees/phase3-gossip`, step 2 of 3. Depends on Task 1.

**Files:**
- Create: `frontend/src/components/entityprofile/ConnectionGossipPanel.vue`
- Create: `frontend/src/components/entityprofile/__tests__/ConnectionGossipPanel.test.ts`

**Context:** Receives a `RelationshipNarrative` prop and optional `NarrativeTrigger`. Renders differently based on `narrative_style`: prose-paragraph shows flowing text, bullet-facts shows a bullet list, timeline-events shows year-badged entries. Each `BiographicalFact` gets tone-colored border from `useToneStyle`. A trigger badge pill appears at the top when present.

### Step 1: Write the failing test

Create `frontend/src/components/entityprofile/__tests__/ConnectionGossipPanel.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ConnectionGossipPanel from "../ConnectionGossipPanel.vue";
import type { RelationshipNarrative, NarrativeTrigger } from "@/types/entityProfile";

const proseNarrative: RelationshipNarrative = {
  summary: "A dramatic literary friendship.",
  details: [
    {
      text: "They exchanged passionate letters for years before meeting.",
      year: 1845,
      significance: "revelation",
      tone: "dramatic",
      display_in: ["connection-detail"],
    },
    {
      text: "Their correspondence influenced major poetic works.",
      significance: "notable",
      tone: "intellectual",
      display_in: ["connection-detail"],
    },
  ],
  narrative_style: "prose-paragraph",
};

const bulletNarrative: RelationshipNarrative = {
  summary: "Shared publishing connections.",
  details: [
    {
      text: "Both published with Smith, Elder & Co.",
      year: 1847,
      significance: "context",
      tone: "intellectual",
      display_in: ["connection-detail"],
    },
  ],
  narrative_style: "bullet-facts",
};

const timelineNarrative: RelationshipNarrative = {
  summary: "A timeline of influence.",
  details: [
    {
      text: "First meeting at a literary salon.",
      year: 1840,
      significance: "notable",
      tone: "triumphant",
      display_in: ["connection-detail"],
    },
    {
      text: "Published joint anthology.",
      year: 1852,
      significance: "revelation",
      tone: "intellectual",
      display_in: ["connection-detail"],
    },
  ],
  narrative_style: "timeline-events",
};

describe("ConnectionGossipPanel", () => {
  it("renders summary text", () => {
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: proseNarrative, trigger: null },
    });
    expect(wrapper.text()).toContain("A dramatic literary friendship.");
  });

  it("renders detail facts", () => {
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: proseNarrative, trigger: null },
    });
    expect(wrapper.text()).toContain("exchanged passionate letters");
  });

  it("renders year badge on dated facts", () => {
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: proseNarrative, trigger: null },
    });
    expect(wrapper.text()).toContain("1845");
  });

  it("renders trigger badge when present", () => {
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: proseNarrative, trigger: "cross_era_bridge" as NarrativeTrigger },
    });
    expect(wrapper.text()).toContain("Cross-Era Bridge");
  });

  it("does not render trigger badge when null", () => {
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: proseNarrative, trigger: null },
    });
    expect(wrapper.find(".gossip-panel__trigger").exists()).toBe(false);
  });

  it("applies prose-paragraph render mode", () => {
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: proseNarrative, trigger: null },
    });
    expect(wrapper.find(".gossip-panel--prose-paragraph").exists()).toBe(true);
  });

  it("applies bullet-facts render mode", () => {
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: bulletNarrative, trigger: null },
    });
    expect(wrapper.find(".gossip-panel--bullet-facts").exists()).toBe(true);
  });

  it("applies timeline-events render mode", () => {
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: timelineNarrative, trigger: null },
    });
    expect(wrapper.find(".gossip-panel--timeline-events").exists()).toBe(true);
  });

  it("renders timeline years in order", () => {
    const wrapper = mount(ConnectionGossipPanel, {
      props: { narrative: timelineNarrative, trigger: null },
    });
    const text = wrapper.text();
    expect(text.indexOf("1840")).toBeLessThan(text.indexOf("1852"));
  });
});
```

### Step 2: Run test to verify it fails

Run: `npm run --prefix frontend test:unit -- --run src/components/entityprofile/__tests__/ConnectionGossipPanel.test.ts`

Expected: FAIL — module `../ConnectionGossipPanel.vue` not found.

### Step 3: Write the component

Create `frontend/src/components/entityprofile/ConnectionGossipPanel.vue`:

```vue
<script setup lang="ts">
import type { RelationshipNarrative, NarrativeTrigger } from "@/types/entityProfile";
import { useToneStyle } from "@/composables/entityprofile/useToneStyle";

const props = defineProps<{
  narrative: RelationshipNarrative;
  trigger: NarrativeTrigger;
}>();

const TRIGGER_LABELS: Record<string, string> = {
  cross_era_bridge: "Cross-Era Bridge",
  social_circle: "Social Circle",
  hub_figure: "Hub Figure",
  influence_chain: "Influence Chain",
};
</script>

<template>
  <div class="gossip-panel" :class="`gossip-panel--${narrative.narrative_style}`">
    <span v-if="trigger" class="gossip-panel__trigger">
      {{ TRIGGER_LABELS[trigger] ?? trigger }}
    </span>

    <p class="gossip-panel__summary">{{ narrative.summary }}</p>

    <!-- Prose paragraph mode -->
    <div v-if="narrative.narrative_style === 'prose-paragraph'" class="gossip-panel__prose">
      <p
        v-for="(fact, i) in narrative.details"
        :key="i"
        class="gossip-panel__fact"
        :style="{ borderLeftColor: useToneStyle(fact.tone).color }"
      >
        <span v-if="fact.year" class="gossip-panel__year">{{ fact.year }}</span>
        {{ fact.text }}
      </p>
    </div>

    <!-- Bullet facts mode -->
    <ul v-else-if="narrative.narrative_style === 'bullet-facts'" class="gossip-panel__bullets">
      <li
        v-for="(fact, i) in narrative.details"
        :key="i"
        :style="{ borderLeftColor: useToneStyle(fact.tone).color }"
      >
        <span v-if="fact.year" class="gossip-panel__year">{{ fact.year }}</span>
        {{ fact.text }}
      </li>
    </ul>

    <!-- Timeline events mode -->
    <div v-else class="gossip-panel__timeline">
      <div
        v-for="(fact, i) in narrative.details"
        :key="i"
        class="gossip-panel__event"
        :style="{ borderLeftColor: useToneStyle(fact.tone).color }"
      >
        <span v-if="fact.year" class="gossip-panel__year gossip-panel__year--badge">
          {{ fact.year }}
        </span>
        <span class="gossip-panel__event-text">{{ fact.text }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.gossip-panel {
  padding: 12px 0 0;
}

.gossip-panel__trigger {
  display: inline-block;
  padding: 2px 10px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--color-accent-gold, #b8860b);
  background: color-mix(in srgb, var(--color-accent-gold, #b8860b) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-accent-gold, #b8860b) 30%, transparent);
  border-radius: 12px;
  margin-bottom: 8px;
}

.gossip-panel__summary {
  font-size: 14px;
  line-height: 1.5;
  font-style: italic;
  color: var(--color-text, #2c2420);
  margin: 8px 0;
}

.gossip-panel__fact,
.gossip-panel__bullets li,
.gossip-panel__event {
  padding: 8px 12px;
  border-left: 3px solid var(--color-accent-gold, #b8860b);
  margin-bottom: 8px;
  font-size: 13px;
  line-height: 1.5;
}

.gossip-panel__year {
  font-weight: 600;
  margin-right: 6px;
  color: var(--color-text-muted, #8b8579);
}

.gossip-panel__year--badge {
  display: inline-block;
  padding: 1px 6px;
  background: var(--color-surface, #faf8f5);
  border: 1px solid var(--color-border, #e8e4de);
  border-radius: 4px;
  font-size: 11px;
}

.gossip-panel__bullets {
  list-style: none;
  padding: 0;
  margin: 0;
}

.gossip-panel__timeline {
  position: relative;
}

.gossip-panel__event {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.gossip-panel__event-text {
  flex: 1;
}
</style>
```

### Step 4: Run tests to verify they pass

Run: `npm run --prefix frontend test:unit -- --run src/components/entityprofile/__tests__/ConnectionGossipPanel.test.ts`

Expected: All 9 tests PASS.

### Step 5: Commit

```
git add frontend/src/components/entityprofile/ConnectionGossipPanel.vue frontend/src/components/entityprofile/__tests__/ConnectionGossipPanel.test.ts
git commit -m "feat(ep): add ConnectionGossipPanel with style-adaptive rendering"
```

---

## Task 3: Wire Gossip Panel into KeyConnections (Accordion)

**Lane A** — runs in `.tmp/worktrees/phase3-gossip`, step 3 of 3. Depends on Task 2.

**Files:**
- Modify: `frontend/src/components/entityprofile/KeyConnections.vue`
- Create: `frontend/src/components/entityprofile/__tests__/KeyConnections.test.ts`

**Context:** Add a "View full story" button to each connection card that has `relationship_story`. Track open/closed state with a `Set<string>`. Render `ConnectionGossipPanel` inside the expanded card with smooth CSS transition.

### Step 1: Write the failing test

Create `frontend/src/components/entityprofile/__tests__/KeyConnections.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import KeyConnections from "../KeyConnections.vue";
import type { ProfileConnection } from "@/types/entityProfile";

const connWithStory: ProfileConnection = {
  entity: { id: 31, type: "author", name: "Elizabeth Barrett Browning" },
  connection_type: "literary_associate",
  strength: 8,
  shared_book_count: 3,
  shared_books: [{ id: 1, title: "Aurora Leigh", year: 1856 }],
  narrative: "Close literary associates.",
  narrative_trigger: "cross_era_bridge",
  is_key: true,
  relationship_story: {
    summary: "A dramatic literary friendship.",
    details: [
      {
        text: "They exchanged passionate letters.",
        year: 1845,
        significance: "revelation",
        tone: "dramatic",
        display_in: ["connection-detail"],
      },
    ],
    narrative_style: "prose-paragraph",
  },
};

const connWithoutStory: ProfileConnection = {
  entity: { id: 7, type: "publisher", name: "Smith, Elder & Co." },
  connection_type: "publisher",
  strength: 6,
  shared_book_count: 5,
  shared_books: [],
  narrative: "Published several works.",
  narrative_trigger: null,
  is_key: true,
  relationship_story: null,
};

// Stub router-link to avoid router dependency in unit tests
const stubs = {
  "router-link": {
    template: "<a><slot /></a>",
    props: ["to"],
  },
};

describe("KeyConnections", () => {
  it("renders connection names", () => {
    const wrapper = mount(KeyConnections, {
      props: { connections: [connWithStory, connWithoutStory] },
      global: { stubs },
    });
    expect(wrapper.text()).toContain("Elizabeth Barrett Browning");
    expect(wrapper.text()).toContain("Smith, Elder & Co.");
  });

  it("shows 'View full story' button only when relationship_story exists", () => {
    const wrapper = mount(KeyConnections, {
      props: { connections: [connWithStory, connWithoutStory] },
      global: { stubs },
    });
    const buttons = wrapper.findAll(".key-connections__story-toggle");
    expect(buttons).toHaveLength(1);
  });

  it("expands gossip panel on button click", async () => {
    const wrapper = mount(KeyConnections, {
      props: { connections: [connWithStory] },
      global: { stubs },
    });
    expect(wrapper.find(".gossip-panel").exists()).toBe(false);
    await wrapper.find(".key-connections__story-toggle").trigger("click");
    expect(wrapper.find(".gossip-panel").exists()).toBe(true);
  });

  it("collapses gossip panel on second click", async () => {
    const wrapper = mount(KeyConnections, {
      props: { connections: [connWithStory] },
      global: { stubs },
    });
    const btn = wrapper.find(".key-connections__story-toggle");
    await btn.trigger("click");
    expect(wrapper.find(".gossip-panel").exists()).toBe(true);
    await btn.trigger("click");
    expect(wrapper.find(".gossip-panel").exists()).toBe(false);
  });

  it("renders gossip panel content when expanded", async () => {
    const wrapper = mount(KeyConnections, {
      props: { connections: [connWithStory] },
      global: { stubs },
    });
    await wrapper.find(".key-connections__story-toggle").trigger("click");
    expect(wrapper.text()).toContain("A dramatic literary friendship.");
    expect(wrapper.text()).toContain("exchanged passionate letters");
  });
});
```

### Step 2: Run test to verify it fails

Run: `npm run --prefix frontend test:unit -- --run src/components/entityprofile/__tests__/KeyConnections.test.ts`

Expected: FAIL — no `.key-connections__story-toggle` element found.

### Step 3: Modify KeyConnections.vue

Update `frontend/src/components/entityprofile/KeyConnections.vue`:

**Script section** — add imports and expand state:

```vue
<script setup lang="ts">
import { ref } from "vue";
import type { ProfileConnection } from "@/types/entityProfile";
import ConnectionGossipPanel from "./ConnectionGossipPanel.vue";

defineProps<{
  connections: ProfileConnection[];
}>();

const expandedCards = ref(new Set<string>());

function toggleCard(conn: ProfileConnection) {
  const key = `${conn.entity.type}:${conn.entity.id}`;
  if (expandedCards.value.has(key)) {
    expandedCards.value.delete(key);
  } else {
    expandedCards.value.add(key);
  }
  // Trigger reactivity on Set mutation
  expandedCards.value = new Set(expandedCards.value);
}

function isExpanded(conn: ProfileConnection): boolean {
  return expandedCards.value.has(`${conn.entity.type}:${conn.entity.id}`);
}
</script>
```

**Template** — after the `.key-connections__meta` div (line 52), before the closing `</div>` of the card (line 53), add:

```html
        <button
          v-if="conn.relationship_story"
          class="key-connections__story-toggle"
          @click="toggleCard(conn)"
        >
          {{ isExpanded(conn) ? "Hide story" : "View full story" }}
        </button>
        <ConnectionGossipPanel
          v-if="conn.relationship_story && isExpanded(conn)"
          :narrative="conn.relationship_story"
          :trigger="conn.narrative_trigger"
        />
```

**Style section** — add at end:

```css
.key-connections__story-toggle {
  display: inline-block;
  margin-top: 8px;
  padding: 4px 12px;
  font-size: 12px;
  color: var(--color-accent-gold, #b8860b);
  background: none;
  border: 1px solid var(--color-accent-gold, #b8860b);
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 150ms;
}

.key-connections__story-toggle:hover {
  background: color-mix(in srgb, var(--color-accent-gold, #b8860b) 10%, transparent);
}
```

### Step 4: Run tests to verify they pass

Run: `npm run --prefix frontend test:unit -- --run src/components/entityprofile/__tests__/KeyConnections.test.ts`

Expected: All 5 tests PASS.

### Step 5: Run all entity profile tests

Run: `npm run --prefix frontend test:unit -- --run src/components/entityprofile/__tests__/`

Expected: All entity profile tests PASS (ProfileHero, CollectionStats, EntityBooks, ConnectionGossipPanel, KeyConnections).

### Step 6: Commit

```
git add frontend/src/components/entityprofile/KeyConnections.vue frontend/src/components/entityprofile/__tests__/KeyConnections.test.ts
git commit -m "feat(ep): wire gossip panel accordion into KeyConnections"
```

---

## Task 4: Mobile Optimization

**Parallel lane B** — runs in `.tmp/worktrees/phase3-mobile`, independent of gossip chain.

**Files (Lane B — parallel safe):**
- Create: `frontend/src/components/entityprofile/ConnectionSummary.vue`
- Create: `frontend/src/components/entityprofile/__tests__/ConnectionSummary.test.ts`
- Create: `frontend/src/composables/entityprofile/useMediaQuery.ts`
- Modify: `frontend/src/views/EntityProfileView.vue` (EgoNetwork/ConnectionSummary swap + breakpoints)
- Modify: `frontend/src/components/entityprofile/ProfileHero.vue` (append mobile CSS to `<style>` only)
- Modify: `frontend/src/components/entityprofile/CollectionStats.vue` (append mobile CSS)
- Modify: `frontend/src/components/entityprofile/PublicationTimeline.vue` (append mobile CSS)

**Files (Post-merge fixup — depends on Task 3):**
- Modify: `frontend/src/components/entityprofile/KeyConnections.vue` (append mobile CSS for toggle button)

**Context:** Three breakpoints: 1024px (existing tablet, 2→1 column), 768px (mobile: smaller type, swap EgoNetwork for ConnectionSummary, larger touch targets), 480px (small mobile: single-column stats). ConnectionSummary is a text-only replacement for EgoNetwork showing "Connected to N figures including X, Y, and Z."

### Step 1: Write ConnectionSummary test

Create `frontend/src/components/entityprofile/__tests__/ConnectionSummary.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ConnectionSummary from "../ConnectionSummary.vue";
import type { ProfileConnection } from "@/types/entityProfile";

function makeConn(name: string, isKey: boolean): ProfileConnection {
  return {
    entity: { id: 1, type: "author", name },
    connection_type: "associate",
    strength: 5,
    shared_book_count: 1,
    shared_books: [],
    narrative: null,
    narrative_trigger: null,
    is_key: isKey,
    relationship_story: null,
  };
}

describe("ConnectionSummary", () => {
  it("renders total connection count", () => {
    const conns = [makeConn("Alice", true), makeConn("Bob", true), makeConn("Carol", false)];
    const wrapper = mount(ConnectionSummary, { props: { connections: conns } });
    expect(wrapper.text()).toContain("3");
  });

  it("lists key connection names", () => {
    const conns = [makeConn("Dickens", true), makeConn("Morris", true), makeConn("Other", false)];
    const wrapper = mount(ConnectionSummary, { props: { connections: conns } });
    expect(wrapper.text()).toContain("Dickens");
    expect(wrapper.text()).toContain("Morris");
  });

  it("limits displayed names to 3", () => {
    const conns = [
      makeConn("A", true),
      makeConn("B", true),
      makeConn("C", true),
      makeConn("D", true),
      makeConn("E", false),
    ];
    const wrapper = mount(ConnectionSummary, { props: { connections: conns } });
    // Should show first 3 key names then "and 2 others"
    expect(wrapper.text()).toContain("and 2 others");
  });

  it("renders nothing when no connections", () => {
    const wrapper = mount(ConnectionSummary, { props: { connections: [] } });
    expect(wrapper.text()).toBe("");
  });
});
```

### Step 2: Run test to verify it fails

Run: `npm run --prefix frontend test:unit -- --run src/components/entityprofile/__tests__/ConnectionSummary.test.ts`

Expected: FAIL — module not found.

### Step 3: Create ConnectionSummary component

Create `frontend/src/components/entityprofile/ConnectionSummary.vue`:

```vue
<script setup lang="ts">
import { computed } from "vue";
import type { ProfileConnection } from "@/types/entityProfile";

const MAX_NAMES = 3;

const props = defineProps<{
  connections: ProfileConnection[];
}>();

const keyNames = computed(() =>
  props.connections.filter((c) => c.is_key).map((c) => c.entity.name)
);

const displayNames = computed(() => keyNames.value.slice(0, MAX_NAMES));

const remaining = computed(() => props.connections.length - displayNames.value.length);
</script>

<template>
  <section v-if="connections.length > 0" class="connection-summary">
    <h2 class="connection-summary__title">Network</h2>
    <p class="connection-summary__text">
      Connected to {{ connections.length }}
      {{ connections.length === 1 ? "figure" : "figures" }}
      <template v-if="displayNames.length > 0">
        including {{ displayNames.join(", ") }}
        <template v-if="remaining > 0">
          and {{ remaining }} {{ remaining === 1 ? "other" : "others" }}
        </template>
      </template>
    </p>
  </section>
</template>

<style scoped>
.connection-summary__title {
  font-size: 20px;
  margin: 0 0 8px;
}

.connection-summary__text {
  font-size: 14px;
  line-height: 1.5;
  color: var(--color-text-muted, #8b8579);
}
</style>
```

### Step 4: Run ConnectionSummary tests

Run: `npm run --prefix frontend test:unit -- --run src/components/entityprofile/__tests__/ConnectionSummary.test.ts`

Expected: All 4 tests PASS.

### Step 5: Commit ConnectionSummary

```
git add frontend/src/components/entityprofile/ConnectionSummary.vue frontend/src/components/entityprofile/__tests__/ConnectionSummary.test.ts
git commit -m "feat(ep): add ConnectionSummary text component for mobile"
```

### Step 6: Modify EntityProfileView for mobile swap

Update `frontend/src/views/EntityProfileView.vue`:

**Script** — add import and media query ref:

After the existing imports (line 13), add:
```typescript
import ConnectionSummary from "@/components/entityprofile/ConnectionSummary.vue";
import { useMediaQuery } from "@/composables/entityprofile/useMediaQuery";

const isMobile = useMediaQuery("(max-width: 767px)");
```

**Note:** If `useMediaQuery` does not exist, create a minimal version — see substep below.

**Template** — replace the EgoNetwork block (lines 89-95) with:

```html
      <EgoNetwork
        v-if="connections.length > 0 && !isMobile"
        :entity-id="entity.id"
        :entity-type="entity.type"
        :entity-name="entity.name"
        :connections="connections"
      />
      <ConnectionSummary
        v-if="connections.length > 0 && isMobile"
        :connections="connections"
      />
```

**Style** — add after the existing 1024px media query (line 154-158):

```css
@media (max-width: 768px) {
  .entity-profile-view {
    padding: 16px;
  }

  .entity-profile-view__back {
    font-size: 16px;
    padding: 8px 0;
  }
}
```

### Step 6a: Create useMediaQuery composable (if needed)

Check if `frontend/src/composables/entityprofile/useMediaQuery.ts` exists. If not, create it:

```typescript
import { onMounted, onUnmounted, ref } from "vue";

export function useMediaQuery(query: string) {
  const matches = ref(false);
  let mql: MediaQueryList | null = null;

  function update() {
    matches.value = mql?.matches ?? false;
  }

  onMounted(() => {
    mql = window.matchMedia(query);
    mql.addEventListener("change", update);
    update();
  });

  onUnmounted(() => {
    mql?.removeEventListener("change", update);
  });

  return matches;
}
```

### Step 7: Add mobile CSS to ProfileHero

Append to `frontend/src/components/entityprofile/ProfileHero.vue` `<style>` section:

```css
@media (max-width: 768px) {
  .profile-hero {
    padding: 20px;
  }

  .profile-hero__name {
    font-size: 22px;
  }

  .profile-hero__bio {
    font-size: 15px;
  }
}
```

### Step 8: Add mobile CSS to KeyConnections

Append to `frontend/src/components/entityprofile/KeyConnections.vue` `<style>` section:

```css
@media (max-width: 768px) {
  .key-connections__card {
    padding: 12px;
  }

  .key-connections__story-toggle {
    padding: 6px 14px;
    font-size: 13px;
  }
}
```

### Step 9: Add mobile CSS to CollectionStats

Append to `frontend/src/components/entityprofile/CollectionStats.vue` `<style>` section:

```css
@media (max-width: 480px) {
  .collection-stats__grid {
    grid-template-columns: 1fr;
  }
}
```

### Step 10: Add mobile CSS to PublicationTimeline

Append to `frontend/src/components/entityprofile/PublicationTimeline.vue` `<style>` section:

```css
@media (max-width: 768px) {
  .publication-timeline__dot {
    width: 16px;
    height: 16px;
  }
}
```

### Step 11: Run all entity profile unit tests

Run: `npm run --prefix frontend test:unit -- --run src/components/entityprofile/__tests__/`

Expected: All tests PASS.

### Step 12: Run lint and type-check

Run: `npm run --prefix frontend lint`
Run: `npm run --prefix frontend type-check`

Expected: No errors.

### Step 13: Commit

```
git add frontend/src/views/EntityProfileView.vue frontend/src/components/entityprofile/ProfileHero.vue frontend/src/components/entityprofile/KeyConnections.vue frontend/src/components/entityprofile/CollectionStats.vue frontend/src/components/entityprofile/PublicationTimeline.vue frontend/src/composables/entityprofile/useMediaQuery.ts
git commit -m "feat(ep): mobile optimization with 768px/480px breakpoints"
```

---

## Task 5: E2E Tests

**Lane C** — runs in `.tmp/worktrees/phase3-e2e`, fully independent (write file only, run after deploy).

**Files:**
- Create: `frontend/e2e/entity-profile.spec.ts`

**Context:** E2E tests run against staging (`https://staging.app.bluemoxon.com`) with viewer auth from `.auth/viewer.json`. Tests cover: profile page load, gossip panel expand/collapse, mobile viewport layout, and navigation between profiles via connection links.

**Important:** These tests target staging with real data. The test needs a known entity to navigate to. Use the social circles page to find and click into a profile, or navigate directly to a known author profile URL.

### Step 1: Write E2E test file

Create `frontend/e2e/entity-profile.spec.ts`:

```typescript
import { test, expect } from "@playwright/test";

test.describe("Entity Profile", () => {
  // Navigate to a profile by going through social circles
  // This ensures the route works end-to-end
  test.beforeEach(async ({ page }) => {
    // Go to social circles and click into the first available profile
    await page.goto("/social-circles");
    await expect(page.locator("text=Social Circles")).toBeVisible({ timeout: 15000 });

    // Click the first node card or entity link that appears
    const profileLink = page.locator("a[href*='/entity/']").first();
    await expect(profileLink).toBeVisible({ timeout: 10000 });
    await profileLink.click();
    await expect(page.locator(".profile-hero")).toBeVisible({ timeout: 10000 });
  });

  test("displays profile hero with entity name", async ({ page }) => {
    await expect(page.locator(".profile-hero__name")).toBeVisible();
    const name = await page.locator(".profile-hero__name").textContent();
    expect(name?.trim().length).toBeGreaterThan(0);
  });

  test("displays key connections section", async ({ page }) => {
    // Key connections may or may not exist depending on the entity
    const connections = page.locator(".key-connections");
    const hasConnections = await connections.isVisible().catch(() => false);
    if (hasConnections) {
      await expect(page.locator(".key-connections__card").first()).toBeVisible();
    }
  });

  test("displays collection stats", async ({ page }) => {
    const stats = page.locator(".collection-stats");
    const hasStats = await stats.isVisible().catch(() => false);
    if (hasStats) {
      await expect(page.locator("text=Total Books")).toBeVisible();
    }
  });

  test("gossip panel expands and collapses", async ({ page }) => {
    const toggle = page.locator(".key-connections__story-toggle").first();
    const hasToggle = await toggle.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasToggle) {
      // Expand
      await toggle.click();
      await expect(page.locator(".gossip-panel").first()).toBeVisible();
      await expect(page.locator(".gossip-panel__summary").first()).toBeVisible();

      // Collapse
      await toggle.click();
      await expect(page.locator(".gossip-panel").first()).not.toBeVisible();
    }
  });

  test("navigate between profiles via connection link", async ({ page }) => {
    const firstLink = page.locator(".key-connections__name").first();
    const hasLink = await firstLink.isVisible({ timeout: 3000 }).catch(() => false);

    if (hasLink) {
      const targetName = await firstLink.textContent();
      await firstLink.click();

      // Should navigate to new profile
      await expect(page.locator(".profile-hero")).toBeVisible({ timeout: 10000 });
      const heroName = await page.locator(".profile-hero__name").textContent();
      expect(heroName?.trim()).toBe(targetName?.trim());
    }
  });

  test("back link returns to social circles", async ({ page }) => {
    await page.locator(".entity-profile-view__back").click();
    await expect(page).toHaveURL(/\/social-circles/);
  });
});

test.describe("Entity Profile - Mobile", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test.beforeEach(async ({ page }) => {
    await page.goto("/social-circles");
    await expect(page.locator("text=Social Circles")).toBeVisible({ timeout: 15000 });

    const profileLink = page.locator("a[href*='/entity/']").first();
    await expect(profileLink).toBeVisible({ timeout: 10000 });
    await profileLink.click();
    await expect(page.locator(".profile-hero")).toBeVisible({ timeout: 10000 });
  });

  test("hides EgoNetwork on mobile viewport", async ({ page }) => {
    // EgoNetwork canvas should not be visible at mobile width
    const egoNetwork = page.locator(".ego-network");
    await expect(egoNetwork).not.toBeVisible();
  });

  test("shows ConnectionSummary on mobile viewport", async ({ page }) => {
    const summary = page.locator(".connection-summary");
    const hasSummary = await summary.isVisible({ timeout: 3000 }).catch(() => false);
    if (hasSummary) {
      await expect(page.locator(".connection-summary__text")).toBeVisible();
      await expect(page.locator("text=Connected to")).toBeVisible();
    }
  });

  test("profile layout is single column on mobile", async ({ page }) => {
    const content = page.locator(".entity-profile-view__content");
    const hasContent = await content.isVisible({ timeout: 3000 }).catch(() => false);
    if (hasContent) {
      const box = await content.boundingBox();
      // Single column should be less than viewport width with padding
      expect(box?.width).toBeLessThanOrEqual(375);
    }
  });
});
```

### Step 2: Run E2E tests locally to verify

Run: `npm run --prefix frontend test:e2e -- --project=chromium --grep "Entity Profile"`

Expected: All desktop tests PASS. Mobile tests PASS (EgoNetwork hidden, ConnectionSummary visible).

**Note:** If some tests fail because the staging entity doesn't have gossip data (no `relationship_story`), the tests are written to handle this gracefully with `isVisible().catch(() => false)` guards.

### Step 3: Run E2E on mobile project

Run: `npm run --prefix frontend test:e2e -- --project="Mobile Chrome" --grep "Entity Profile - Mobile"`

Expected: Mobile-specific tests PASS.

### Step 4: Commit

```
git add frontend/e2e/entity-profile.spec.ts
git commit -m "test(ep): add E2E tests for profile, gossip panel, and mobile"
```

---

## Dependency Graph

```
Task 1 (useToneStyle) ──→ Task 2 (GossipPanel) ──→ Task 3 (KeyConnections)
                                                          │
Task 4a (ConnectionSummary + mobile CSS) ─────────────────┤ ← merge point
                                                          │
Task 4b (KeyConnections mobile CSS) ──────────────────────┘ ← fixup after merge
                                                          │
Task 5 (E2E test file) ──────────────────────────────────→ run after deploy
```

**Parallel lanes:**
- Lane A: Tasks 1 → 2 → 3 (gossip chain)
- Lane B: Task 4a (mobile, independent pieces)
- Lane C: Task 5 (E2E file, write-only)

**Merge order:** A first, B second (auto-merge expected), C third, then fixup commit for Task 4b.

**PR:** Single PR `feat/ep-phase3-gossip-mobile` → `staging` after merge.
