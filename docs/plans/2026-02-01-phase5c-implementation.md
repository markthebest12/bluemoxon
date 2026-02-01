# Phase 5C Implementation Plan — AI Cross-Links + Progressive Disclosure

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add clickable entity cross-links in AI-generated stories (#1618) and progressive disclosure hub mode to the social circles landing page (#1619).

**Architecture:** Three parallel lanes with zero file overlap. Lane A modifies backend AI prompts to emit inline `{{entity:TYPE:ID|Name}}` markers. Lane B builds the frontend marker parser, a shared `EntityLinkedText` component, and integrates it into ProfileHero and ConnectionGossipPanel. Lane C adds a hub mode composable to useSocialCircles with expand-in-place, "+N more" badges, and a "Show more" button. After all lanes merge, regenerate all entity profiles.

**Tech Stack:** FastAPI, Python, Vue 3, TypeScript, Cytoscape.js, Vitest, Pytest

---

## Parallel Lane Map

```
Lane A (backend)           Lane B (frontend cross-links)    Lane C (hub mode)
═══════════════            ══════════════════════════        ═════════════════
ai_profile_generator.py    entityMarkers.ts (new)           useHubMode.ts (new)
entity_profile.py          entityMarkers.test.ts (new)      useHubMode.test.ts (new)
test_ai_profile_gen.py     EntityLinkedText.vue (new)       ShowMoreButton.vue (new)
                           EntityLinkedText.test.ts (new)   ExpandBadge.vue (new)
                           ProfileHero.vue                  useSocialCircles.ts
                           ProfileHero.test.ts              SocialCirclesView.vue
                           ConnectionGossipPanel.vue
                           ConnectionGossipPanel.test.ts

Zero file overlap ✓
```

After all 3 lanes merge → Task 10: Regenerate profiles on staging.

---

## Lane A: Backend Prompt Enrichment (#1618)

### Task 1: Add connection list parameter to all generation functions

**Files:**
- Modify: `backend/app/services/ai_profile_generator.py:109-252`
- Test: `backend/tests/test_ai_profile_generator.py`

**Step 1: Write the failing tests**

Add to `backend/tests/test_ai_profile_generator.py`:

```python
class TestGenerateBioWithConnections:
    """Tests for bio generation with entity cross-link markers."""

    @patch("app.services.ai_profile_generator._invoke")
    def test_connections_included_in_prompt(self, mock_invoke):
        mock_invoke.return_value = '{"biography": "Bio.", "personal_stories": []}'
        connections = [
            {"entity_type": "author", "entity_id": 32, "name": "Robert Browning"},
            {"entity_type": "publisher", "entity_id": 7, "name": "Chapman & Hall"},
        ]
        generate_bio_and_stories(
            "Elizabeth Barrett Browning", "author",
            birth_year=1806, death_year=1861,
            connections=connections,
        )
        prompt_arg = mock_invoke.call_args.args[1]
        assert "author:32" in prompt_arg
        assert "Robert Browning" in prompt_arg
        assert "publisher:7" in prompt_arg
        assert "{{entity:" in prompt_arg  # marker format in instructions

    @patch("app.services.ai_profile_generator._invoke")
    def test_no_connections_omits_marker_instructions(self, mock_invoke):
        mock_invoke.return_value = '{"biography": "Bio.", "personal_stories": []}'
        generate_bio_and_stories("Test", "author")
        prompt_arg = mock_invoke.call_args.args[1]
        assert "{{entity:" not in prompt_arg


class TestGenerateNarrativeWithConnections:
    """Tests for connection narrative with entity cross-link markers."""

    @patch("app.services.ai_profile_generator._invoke")
    def test_connections_included_in_narrative_prompt(self, mock_invoke):
        mock_invoke.return_value = "A narrative about {{entity:author:32|Robert Browning}}."
        connections = [
            {"entity_type": "author", "entity_id": 32, "name": "Robert Browning"},
        ]
        generate_connection_narrative(
            "EBB", "author", "Robert Browning", "author",
            "shared_publisher", ["Sonnets"],
            connections=connections,
        )
        prompt_arg = mock_invoke.call_args.args[1]
        assert "author:32" in prompt_arg


class TestGenerateRelationshipStoryWithConnections:
    """Tests for relationship story with entity cross-link markers."""

    @patch("app.services.ai_profile_generator._invoke")
    def test_connections_included_in_story_prompt(self, mock_invoke):
        mock_invoke.return_value = json.dumps({
            "summary": "A story about {{entity:publisher:7|Chapman & Hall}}.",
            "details": [],
            "narrative_style": "prose-paragraph",
        })
        connections = [
            {"entity_type": "publisher", "entity_id": 7, "name": "Chapman & Hall"},
        ]
        generate_relationship_story(
            "Dickens", "author", "1812-1870",
            "Chapman & Hall", "publisher", "1830-1900",
            "publisher", ["Pickwick Papers"], "hub_figure",
            connections=connections,
        )
        prompt_arg = mock_invoke.call_args.args[1]
        assert "publisher:7" in prompt_arg
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/mark/projects/bluemoxon && poetry run pytest backend/tests/test_ai_profile_generator.py -v -k "Connections" --no-header`
Expected: FAIL (unexpected keyword argument `connections`)

**Step 3: Implement the connection list parameter**

Modify `backend/app/services/ai_profile_generator.py`:

Add a helper function after `_strip_markdown_fences` (after line 87):

```python
def _format_connection_instructions(connections: list[dict] | None) -> str:
    """Format entity cross-link instructions for AI prompts."""
    if not connections:
        return ""
    conn_lines = "\n".join(
        f'- {c["entity_type"]}:{c["entity_id"]} "{c["name"]}"'
        for c in connections
    )
    return f"""

When mentioning any of these connected entities by name, wrap them in markers like this:
{{{{entity:author:32|Robert Browning}}}}

Connection list (ONLY use markers for entities in this list — never invent IDs):
{conn_lines}"""
```

Update `generate_bio_and_stories` signature (line 109) to accept `connections: list[dict] | None = None`:

```python
def generate_bio_and_stories(
    name: str,
    entity_type: str,
    birth_year: int | None = None,
    death_year: int | None = None,
    founded_year: int | None = None,
    book_titles: list[str] | None = None,
    connections: list[dict] | None = None,
) -> dict:
```

Append `_format_connection_instructions(connections)` to the end of `user_prompt` (before the closing `"""`), at line 150:

```python
    user_prompt = f"""Given this entity from a rare book collection:
  ...existing prompt...

Return ONLY valid JSON: {{"biography": "...", "personal_stories": [...]}}
If the entity is obscure, provide what is known and note the obscurity.{_format_connection_instructions(connections)}"""
```

Update `generate_connection_narrative` signature (line 170) to accept `connections: list[dict] | None = None`:

```python
def generate_connection_narrative(
    entity1_name: str,
    entity1_type: str,
    entity2_name: str,
    entity2_type: str,
    connection_type: str,
    shared_book_titles: list[str],
    connections: list[dict] | None = None,
) -> str | None:
```

Append to its user_prompt (before `Return ONLY the single sentence`):

```python
    conn_instructions = _format_connection_instructions(connections)
    user_prompt = f"""Describe this connection in one sentence for a rare book collector:
  {entity1_name} ({entity1_type}) connected to {entity2_name} ({entity2_type})
  Connection: {connection_type}
  Shared works: {books_str}{conn_instructions}

Return ONLY the single sentence, no quotes."""
```

Update `generate_relationship_story` signature (line 198) to accept `connections: list[dict] | None = None`:

```python
def generate_relationship_story(
    entity1_name: str,
    entity1_type: str,
    entity1_dates: str,
    entity2_name: str,
    entity2_type: str,
    entity2_dates: str,
    connection_type: str,
    shared_book_titles: list[str],
    trigger_type: str,
    connections: list[dict] | None = None,
) -> dict | None:
```

Append to its user_prompt (before `Return ONLY valid JSON`):

```python
    conn_instructions = _format_connection_instructions(connections)
    user_prompt = f"""Given this connection between two entities in a rare book collection:
  ...existing prompt...

Return ONLY valid JSON: {{"summary": "...", "details": [...], "narrative_style": "..."}}{conn_instructions}"""
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/mark/projects/bluemoxon && poetry run pytest backend/tests/test_ai_profile_generator.py -v --no-header`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add backend/app/services/ai_profile_generator.py backend/tests/test_ai_profile_generator.py
git commit -m "feat: add connection list to AI prompts for entity cross-link markers (#1618)"
```

---

### Task 2: Add marker validation and wire connections into generation pipeline

**Files:**
- Modify: `backend/app/services/ai_profile_generator.py` (add validation)
- Modify: `backend/app/services/entity_profile.py:374-514` (pass connections)
- Test: `backend/tests/test_ai_profile_generator.py`

**Step 1: Write the failing tests for marker validation**

Add to `backend/tests/test_ai_profile_generator.py`:

```python
from app.services.ai_profile_generator import strip_invalid_markers


class TestStripInvalidMarkers:
    """Tests for stripping hallucinated entity markers."""

    def test_valid_markers_preserved(self):
        text = "Met {{entity:author:32|Robert Browning}} at a salon."
        valid_ids = {"author:32"}
        assert strip_invalid_markers(text, valid_ids) == text

    def test_invalid_markers_stripped_to_display_name(self):
        text = "Met {{entity:author:999|Fake Person}} at a salon."
        valid_ids = {"author:32"}
        assert strip_invalid_markers(text, valid_ids) == "Met Fake Person at a salon."

    def test_mixed_valid_and_invalid(self):
        text = "{{entity:author:32|Robert}} met {{entity:author:999|Fake}}."
        valid_ids = {"author:32"}
        assert strip_invalid_markers(text, valid_ids) == "{{entity:author:32|Robert}} met Fake."

    def test_no_markers_unchanged(self):
        text = "Plain text with no markers."
        assert strip_invalid_markers(text, set()) == text

    def test_empty_text(self):
        assert strip_invalid_markers("", set()) == ""

    def test_multiple_markers_same_entity(self):
        text = "{{entity:author:32|RB}} and {{entity:author:32|Robert Browning}}."
        valid_ids = {"author:32"}
        assert strip_invalid_markers(text, valid_ids) == text
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/mark/projects/bluemoxon && poetry run pytest backend/tests/test_ai_profile_generator.py::TestStripInvalidMarkers -v --no-header`
Expected: FAIL (cannot import `strip_invalid_markers`)

**Step 3: Implement marker validation**

Add to `backend/app/services/ai_profile_generator.py` after `_format_connection_instructions`:

```python
import re

_ENTITY_MARKER_RE = re.compile(r"\{\{entity:(\w+):(\d+)\|([^}]+)\}\}")


def strip_invalid_markers(text: str, valid_entity_ids: set[str]) -> str:
    """Strip entity markers whose IDs are not in the valid set.

    Valid markers are preserved. Invalid markers are replaced with just
    the display name (graceful degradation).
    """
    def _replace(match: re.Match) -> str:
        entity_type = match.group(1)
        entity_id = match.group(2)
        display_name = match.group(3)
        key = f"{entity_type}:{entity_id}"
        if key in valid_entity_ids:
            return match.group(0)  # preserve valid marker
        return display_name  # strip to plain text

    return _ENTITY_MARKER_RE.sub(_replace, text)
```

**Step 4: Run validation tests**

Run: `cd /Users/mark/projects/bluemoxon && poetry run pytest backend/tests/test_ai_profile_generator.py::TestStripInvalidMarkers -v --no-header`
Expected: ALL PASS

**Step 5: Wire connections into `generate_and_cache_profile`**

Modify `backend/app/services/entity_profile.py:374-514`. In `generate_and_cache_profile()`, build a connection list from the graph before calling generation functions:

After line 407 (`source_connection_count = len(connected_edges)`), add:

```python
    # Build connection list for cross-link markers
    connection_list = []
    for edge in connected_edges:
        other_id = edge.target if edge.source == node_id else edge.source
        other = node_map.get(other_id)
        if other:
            other_type = other.type.value if hasattr(other.type, "value") else str(other.type)
            connection_list.append({
                "entity_type": other_type,
                "entity_id": other.entity_id,
                "name": other.name,
            })
    valid_entity_ids = {f'{c["entity_type"]}:{c["entity_id"]}' for c in connection_list}
```

Update the `generate_bio_and_stories` call (line 391) to pass connections:

```python
    bio_data = generate_bio_and_stories(
        name=entity.name,
        entity_type=entity_type,
        birth_year=getattr(entity, "birth_year", None),
        death_year=getattr(entity, "death_year", None),
        founded_year=getattr(entity, "founded_year", None),
        book_titles=book_titles,
        connections=connection_list,
    )
```

Update the `generate_relationship_story` call (line 445) to pass connections:

```python
            story = generate_relationship_story(
                entity1_name=entity.name,
                entity1_type=entity_type,
                entity1_dates=_format_entity_dates(source_node) if source_node else "dates unknown",
                entity2_name=other_node.name,
                entity2_type=other_type_str,
                entity2_dates=_format_entity_dates(other_node),
                connection_type=conn_type_str,
                shared_book_titles=shared_titles,
                trigger_type=trigger,
                connections=connection_list,
            )
```

Update the `generate_connection_narrative` call (line 463) to pass connections:

```python
            narrative = generate_connection_narrative(
                entity1_name=entity.name,
                entity1_type=entity_type,
                entity2_name=other_node.name,
                entity2_type=other_type_str,
                connection_type=conn_type_str,
                shared_book_titles=shared_titles,
                connections=connection_list,
            )
```

Add marker validation after bio generation (after `bio_data = generate_bio_and_stories(...)`) and add import at top:

```python
from app.services.ai_profile_generator import strip_invalid_markers
```

After bio_data is obtained, validate markers in personal stories:

```python
    # Validate cross-link markers in bio and stories
    if bio_data.get("biography"):
        bio_data["biography"] = strip_invalid_markers(bio_data["biography"], valid_entity_ids)
    for story in bio_data.get("personal_stories", []):
        if story.get("text"):
            story["text"] = strip_invalid_markers(story["text"], valid_entity_ids)
```

Similarly, after each narrative/story is generated, validate markers:

For narratives (after line 472 `narratives[key] = narrative`):
```python
                narratives[key] = strip_invalid_markers(narrative, valid_entity_ids)
```

For relationship stories (after `rel_stories[key] = story`):
```python
            if story:
                # Validate markers in story text
                if story.get("summary"):
                    story["summary"] = strip_invalid_markers(story["summary"], valid_entity_ids)
                for detail in story.get("details", []):
                    if detail.get("text"):
                        detail["text"] = strip_invalid_markers(detail["text"], valid_entity_ids)
                rel_stories[key] = story
```

**Step 6: Run all backend tests**

Run: `cd /Users/mark/projects/bluemoxon && poetry run pytest backend/tests/test_ai_profile_generator.py -v --no-header`
Expected: ALL PASS

**Step 7: Run linting**

Run: `cd /Users/mark/projects/bluemoxon && poetry run ruff check backend/ && poetry run ruff format --check backend/`
Expected: PASS

**Step 8: Commit**

```bash
git add backend/app/services/ai_profile_generator.py backend/app/services/entity_profile.py backend/tests/test_ai_profile_generator.py
git commit -m "feat: validate cross-link markers and wire connections into generation pipeline (#1618)"
```

---

## Lane B: Frontend Marker Parser + Component Integration (#1618)

### Task 3: Create `parseEntityMarkers` utility

**Files:**
- Create: `frontend/src/utils/entityMarkers.ts`
- Create: `frontend/src/utils/__tests__/entityMarkers.test.ts`

**Step 1: Write the failing tests**

Create `frontend/src/utils/__tests__/entityMarkers.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { parseEntityMarkers, type Segment } from "@/utils/entityMarkers";

describe("parseEntityMarkers", () => {
  it("returns single text segment for plain text", () => {
    const result = parseEntityMarkers("Hello world");
    expect(result).toEqual([{ type: "text", content: "Hello world" }]);
  });

  it("parses a single marker", () => {
    const result = parseEntityMarkers(
      "Met {{entity:author:32|Robert Browning}} at a salon."
    );
    expect(result).toEqual([
      { type: "text", content: "Met " },
      { type: "link", entityType: "author", entityId: 32, displayName: "Robert Browning" },
      { type: "text", content: " at a salon." },
    ]);
  });

  it("parses multiple markers", () => {
    const result = parseEntityMarkers(
      "{{entity:author:32|Robert Browning}} published with {{entity:publisher:7|Chapman & Hall}}."
    );
    expect(result).toHaveLength(4);
    expect(result[0]).toEqual({
      type: "link", entityType: "author", entityId: 32, displayName: "Robert Browning",
    });
    expect(result[1]).toEqual({ type: "text", content: " published with " });
    expect(result[2]).toEqual({
      type: "link", entityType: "publisher", entityId: 7, displayName: "Chapman & Hall",
    });
    expect(result[3]).toEqual({ type: "text", content: "." });
  });

  it("returns single text segment for empty string", () => {
    expect(parseEntityMarkers("")).toEqual([{ type: "text", content: "" }]);
  });

  it("handles adjacent markers with no text between", () => {
    const result = parseEntityMarkers(
      "{{entity:author:1|Alice}}{{entity:author:2|Bob}}"
    );
    expect(result).toEqual([
      { type: "link", entityType: "author", entityId: 1, displayName: "Alice" },
      { type: "link", entityType: "author", entityId: 2, displayName: "Bob" },
    ]);
  });

  it("handles malformed markers as plain text", () => {
    const result = parseEntityMarkers("Text with {{entity:broken marker here.");
    expect(result).toEqual([
      { type: "text", content: "Text with {{entity:broken marker here." },
    ]);
  });

  it("handles marker with special characters in display name", () => {
    const result = parseEntityMarkers(
      "Published by {{entity:publisher:7|Smith, Elder & Co.}}."
    );
    expect(result[0]).toEqual({
      type: "link", entityType: "publisher", entityId: 7, displayName: "Smith, Elder & Co.",
    });
  });

  it("filters empty text segments between adjacent markers", () => {
    const result = parseEntityMarkers(
      "{{entity:author:1|A}}{{entity:author:2|B}}"
    );
    // Should not have empty text segments between markers
    expect(result.every((s) => s.type === "link" || s.content !== "")).toBe(true);
  });
});
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/mark/projects/bluemoxon/frontend && npx vitest run src/utils/__tests__/entityMarkers.test.ts`
Expected: FAIL (cannot find module)

**Step 3: Implement the parser**

Create `frontend/src/utils/entityMarkers.ts`:

```typescript
/**
 * Parser for AI-generated entity cross-link markers.
 *
 * Markers follow the format: {{entity:TYPE:ID|Display Name}}
 * Example: {{entity:author:32|Robert Browning}}
 */

export type TextSegment = { type: "text"; content: string };
export type LinkSegment = {
  type: "link";
  entityType: string;
  entityId: number;
  displayName: string;
};
export type Segment = TextSegment | LinkSegment;

const MARKER_RE = /\{\{entity:(\w+):(\d+)\|([^}]+)\}\}/g;

/**
 * Parse text containing entity markers into an array of segments.
 *
 * Plain text becomes TextSegment, markers become LinkSegment.
 * Malformed markers are left as plain text.
 */
export function parseEntityMarkers(text: string): Segment[] {
  const segments: Segment[] = [];
  let lastIndex = 0;

  for (const match of text.matchAll(MARKER_RE)) {
    const matchStart = match.index!;

    // Add text before this marker (if any)
    if (matchStart > lastIndex) {
      segments.push({ type: "text", content: text.slice(lastIndex, matchStart) });
    }

    segments.push({
      type: "link",
      entityType: match[1],
      entityId: parseInt(match[2], 10),
      displayName: match[3],
    });

    lastIndex = matchStart + match[0].length;
  }

  // Add remaining text after last marker
  if (lastIndex <= text.length) {
    const remaining = text.slice(lastIndex);
    if (remaining || segments.length === 0) {
      segments.push({ type: "text", content: remaining });
    }
  }

  return segments;
}
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/mark/projects/bluemoxon/frontend && npx vitest run src/utils/__tests__/entityMarkers.test.ts`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add frontend/src/utils/entityMarkers.ts frontend/src/utils/__tests__/entityMarkers.test.ts
git commit -m "feat: add parseEntityMarkers utility for AI cross-link markers (#1618)"
```

---

### Task 4: Create `EntityLinkedText` component

**Files:**
- Create: `frontend/src/components/entityprofile/EntityLinkedText.vue`
- Create: `frontend/src/components/entityprofile/__tests__/EntityLinkedText.test.ts`

**Step 1: Write the failing tests**

Create `frontend/src/components/entityprofile/__tests__/EntityLinkedText.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { mount, RouterLinkStub } from "@vue/test-utils";
import EntityLinkedText from "../EntityLinkedText.vue";
import type { ProfileConnection } from "@/types/entityProfile";

const mockConnections: ProfileConnection[] = [
  {
    entity: { id: 32, type: "author", name: "Robert Browning" },
    connection_type: "shared_publisher",
    strength: 5,
    shared_book_count: 2,
    shared_books: [],
    narrative: null,
    narrative_trigger: null,
    is_key: true,
    relationship_story: null,
  },
];

describe("EntityLinkedText", () => {
  it("renders plain text when no markers", () => {
    const wrapper = mount(EntityLinkedText, {
      props: { text: "Plain text here.", connections: [] },
      global: { stubs: { RouterLink: RouterLinkStub } },
    });
    expect(wrapper.text()).toBe("Plain text here.");
    expect(wrapper.findAllComponents(RouterLinkStub)).toHaveLength(0);
  });

  it("renders link for valid marker with matching connection", () => {
    const wrapper = mount(EntityLinkedText, {
      props: {
        text: "Met {{entity:author:32|Robert Browning}} at a salon.",
        connections: mockConnections,
      },
      global: { stubs: { RouterLink: RouterLinkStub } },
    });
    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links).toHaveLength(1);
    expect(links[0].text()).toBe("Robert Browning");
  });

  it("renders plain text for marker with no matching connection (stale)", () => {
    const wrapper = mount(EntityLinkedText, {
      props: {
        text: "Met {{entity:author:999|Ghost Person}} at a salon.",
        connections: mockConnections,
      },
      global: { stubs: { RouterLink: RouterLinkStub } },
    });
    expect(wrapper.text()).toContain("Ghost Person");
    expect(wrapper.findAllComponents(RouterLinkStub)).toHaveLength(0);
  });

  it("renders link with correct route params", () => {
    const wrapper = mount(EntityLinkedText, {
      props: {
        text: "{{entity:author:32|Robert Browning}}",
        connections: mockConnections,
      },
      global: { stubs: { RouterLink: RouterLinkStub } },
    });
    const link = wrapper.findComponent(RouterLinkStub);
    const to = JSON.parse(link.attributes("to") || "{}");
    expect(to.name).toBe("entity-profile");
    expect(to.params.entityType).toBe("author");
    expect(to.params.entityId).toBe("32");
  });

  it("applies entity-link class to links", () => {
    const wrapper = mount(EntityLinkedText, {
      props: {
        text: "{{entity:author:32|Robert Browning}}",
        connections: mockConnections,
      },
      global: { stubs: { RouterLink: RouterLinkStub } },
    });
    const link = wrapper.findComponent(RouterLinkStub);
    expect(link.classes()).toContain("entity-linked-text__link");
  });
});
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/mark/projects/bluemoxon/frontend && npx vitest run src/components/entityprofile/__tests__/EntityLinkedText.test.ts`
Expected: FAIL (cannot find module)

**Step 3: Implement the component**

Create `frontend/src/components/entityprofile/EntityLinkedText.vue`:

```vue
<script setup lang="ts">
import { computed } from "vue";
import { parseEntityMarkers } from "@/utils/entityMarkers";
import type { ProfileConnection } from "@/types/entityProfile";

const props = defineProps<{
  text: string;
  connections: ProfileConnection[];
}>();

// Build a Set of valid entity keys for O(1) lookup
const validEntityKeys = computed(() => {
  const keys = new Set<string>();
  for (const conn of props.connections) {
    keys.add(`${conn.entity.type}:${conn.entity.id}`);
  }
  return keys;
});

const segments = computed(() => parseEntityMarkers(props.text));

function isValidLink(entityType: string, entityId: number): boolean {
  return validEntityKeys.value.has(`${entityType}:${entityId}`);
}
</script>

<template>
  <span class="entity-linked-text">
    <template v-for="(seg, i) in segments" :key="i">
      <router-link
        v-if="seg.type === 'link' && isValidLink(seg.entityType, seg.entityId)"
        :to="{
          name: 'entity-profile',
          params: { entityType: seg.entityType, entityId: String(seg.entityId) },
        }"
        class="entity-linked-text__link"
      >
        {{ seg.displayName }}
      </router-link>
      <template v-else-if="seg.type === 'link'">{{ seg.displayName }}</template>
      <template v-else>{{ seg.content }}</template>
    </template>
  </span>
</template>

<style scoped>
.entity-linked-text__link {
  color: inherit;
  text-decoration: underline dotted;
  text-underline-offset: 2px;
  cursor: pointer;
  transition:
    text-decoration-style 0.15s ease,
    color 0.15s ease;
}

.entity-linked-text__link:hover {
  text-decoration-style: solid;
  color: var(--color-accent-gold, #b8860b);
}
</style>
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/mark/projects/bluemoxon/frontend && npx vitest run src/components/entityprofile/__tests__/EntityLinkedText.test.ts`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add frontend/src/components/entityprofile/EntityLinkedText.vue frontend/src/components/entityprofile/__tests__/EntityLinkedText.test.ts
git commit -m "feat: add EntityLinkedText component for AI cross-link rendering (#1618)"
```

---

### Task 5: Integrate EntityLinkedText into ProfileHero and ConnectionGossipPanel

**Files:**
- Modify: `frontend/src/components/entityprofile/ProfileHero.vue`
- Modify: `frontend/src/components/entityprofile/ConnectionGossipPanel.vue`
- Modify: `frontend/src/components/entityprofile/__tests__/ProfileHero.test.ts`
- Modify: `frontend/src/components/entityprofile/__tests__/ConnectionGossipPanel.test.ts`

**Step 1: Write the failing tests for ProfileHero**

Add to `frontend/src/components/entityprofile/__tests__/ProfileHero.test.ts`:

```typescript
import { RouterLinkStub } from "@vue/test-utils";
import type { ProfileConnection } from "@/types/entityProfile";

const mockConnections: ProfileConnection[] = [
  {
    entity: { id: 32, type: "author", name: "Robert Browning" },
    connection_type: "shared_publisher",
    strength: 5,
    shared_book_count: 2,
    shared_books: [],
    narrative: null,
    narrative_trigger: null,
    is_key: true,
    relationship_story: null,
  },
];

// Add new tests to existing describe block:

  it("renders cross-linked entity names in bio summary", () => {
    const profileWithMarkers: ProfileData = {
      ...mockProfile,
      bio_summary: "She married {{entity:author:32|Robert Browning}} in 1846.",
    };
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: profileWithMarkers, connections: mockConnections },
      global: { stubs: { RouterLink: RouterLinkStub } },
    });
    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links.length).toBeGreaterThanOrEqual(1);
    expect(wrapper.text()).toContain("Robert Browning");
  });

  it("renders cross-linked entity names in personal stories", () => {
    const profileWithMarkers: ProfileData = {
      ...mockProfile,
      personal_stories: [
        {
          text: "Met {{entity:author:32|Robert Browning}} through correspondence.",
          year: 1845,
          significance: "revelation",
          tone: "dramatic",
          display_in: ["hero-bio"],
        },
      ],
    };
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: profileWithMarkers, connections: mockConnections },
      global: { stubs: { RouterLink: RouterLinkStub } },
    });
    const links = wrapper.findAllComponents(RouterLinkStub);
    expect(links.length).toBeGreaterThanOrEqual(1);
  });

  it("renders without connections prop (backward compatible)", () => {
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: mockProfile },
    });
    expect(wrapper.text()).toContain("Elizabeth Barrett Browning");
  });
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/mark/projects/bluemoxon/frontend && npx vitest run src/components/entityprofile/__tests__/ProfileHero.test.ts`
Expected: FAIL (connections prop not accepted)

**Step 3: Modify ProfileHero.vue to use EntityLinkedText**

Update `frontend/src/components/entityprofile/ProfileHero.vue`:

Add import and props change:

```vue
<script setup lang="ts">
import { computed } from "vue";
import type { ProfileEntity, ProfileData, ProfileConnection } from "@/types/entityProfile";
import { formatTier } from "@/utils/socialCircles/formatters";
import { getToneStyle } from "@/composables/entityprofile/getToneStyle";
import EntityLinkedText from "./EntityLinkedText.vue";

const props = defineProps<{
  entity: ProfileEntity;
  profile: ProfileData | null;
  connections?: ProfileConnection[];
}>();
```

Replace the bio_summary rendering (line 40-42):
```vue
      <p v-if="profile?.bio_summary" class="profile-hero__bio">
        <EntityLinkedText :text="profile.bio_summary" :connections="connections ?? []" />
      </p>
```

Replace the story text rendering (line 54-55):
```vue
          <span v-if="story.year" class="profile-hero__story-year">{{ story.year }}</span>
          <EntityLinkedText :text="story.text" :connections="connections ?? []" />
```

**Step 4: Modify ConnectionGossipPanel.vue to use EntityLinkedText**

Update `frontend/src/components/entityprofile/ConnectionGossipPanel.vue`:

Add import and props change:

```vue
<script setup lang="ts">
import type { RelationshipNarrative, NarrativeTrigger, ProfileConnection } from "@/types/entityProfile";
import { getToneStyle } from "@/composables/entityprofile/getToneStyle";
import EntityLinkedText from "./EntityLinkedText.vue";

defineProps<{
  narrative: RelationshipNarrative;
  trigger: NarrativeTrigger;
  connections?: ProfileConnection[];
}>();
```

Replace `{{ narrative.summary }}` (line 24):
```vue
    <p class="gossip-panel__summary">
      <EntityLinkedText :text="narrative.summary" :connections="connections ?? []" />
    </p>
```

Replace `{{ fact.text }}` in prose-paragraph mode (line 38-39):
```vue
        <span v-if="fact.year" class="gossip-panel__year">{{ fact.year }}</span>
        <EntityLinkedText :text="fact.text" :connections="connections ?? []" />
```

Replace `{{ fact.text }}` in bullet-facts mode (line 52-53):
```vue
        <span v-if="fact.year" class="gossip-panel__year">{{ fact.year }}</span>
        <EntityLinkedText :text="fact.text" :connections="connections ?? []" />
```

Replace `{{ fact.text }}` in timeline-events mode (line 68):
```vue
        <span class="gossip-panel__event-text">
          <EntityLinkedText :text="fact.text" :connections="connections ?? []" />
        </span>
```

**Step 5: Run all entity profile component tests**

Run: `cd /Users/mark/projects/bluemoxon/frontend && npx vitest run src/components/entityprofile/__tests__/`
Expected: ALL PASS

**Step 6: Run linting**

Run: `cd /Users/mark/projects/bluemoxon/frontend && npm run lint && npm run format && npm run type-check`
Expected: PASS

**Step 7: Commit**

```bash
git add frontend/src/components/entityprofile/ProfileHero.vue frontend/src/components/entityprofile/ConnectionGossipPanel.vue frontend/src/components/entityprofile/__tests__/ProfileHero.test.ts frontend/src/components/entityprofile/__tests__/ConnectionGossipPanel.test.ts
git commit -m "feat: integrate EntityLinkedText into ProfileHero and ConnectionGossipPanel (#1618)"
```

---

### Task 6: Pass connections to ProfileHero and ConnectionGossipPanel from parent

**Files:**
- Modify: `frontend/src/views/EntityProfileView.vue` (or wherever ProfileHero/ConnectionGossipPanel are used)

**Step 1: Find where ProfileHero and ConnectionGossipPanel are rendered**

Run: `grep -rn "ProfileHero\|ConnectionGossipPanel" frontend/src/views/ frontend/src/components/entityprofile/`

Pass the `connections` array from `useEntityProfile` composable down to ProfileHero and ConnectionGossipPanel. The `connections` computed property is already available from the composable. Add `:connections="connections"` to each usage.

Example for ProfileHero:
```vue
<ProfileHero :entity="entity" :profile="profile" :connections="connections" />
```

Example for ConnectionGossipPanel (in KeyConnections.vue):
```vue
<ConnectionGossipPanel
  :narrative="conn.relationship_story"
  :trigger="conn.narrative_trigger"
  :connections="connections"
/>
```

**Step 2: Run all frontend tests**

Run: `cd /Users/mark/projects/bluemoxon/frontend && npx vitest run`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: wire connections prop through to EntityLinkedText components (#1618)"
```

---

## Lane C: Progressive Disclosure Hub Mode (#1619)

### Task 7: Create `useHubMode` composable

**Files:**
- Create: `frontend/src/composables/socialcircles/useHubMode.ts`
- Create: `frontend/src/composables/socialcircles/__tests__/useHubMode.test.ts`

**Step 1: Write the failing tests**

Create `frontend/src/composables/socialcircles/__tests__/useHubMode.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { ref } from "vue";
import { useHubMode } from "../useHubMode";
import type { ApiNode, ApiEdge, NodeId, EdgeId, BookId } from "@/types/socialCircles";

function makeNode(id: string, type: "author" | "publisher" | "binder", edgeCount = 0): ApiNode {
  return {
    id: id as NodeId,
    entity_id: parseInt(id.split(":")[1]),
    name: `Node ${id}`,
    type,
    book_count: 1,
    book_ids: [1 as BookId],
  };
}

function makeEdge(source: string, target: string, strength = 5): ApiEdge {
  return {
    id: `e:${source}:${target}` as EdgeId,
    source: source as NodeId,
    target: target as NodeId,
    type: "publisher",
    strength,
  };
}

describe("useHubMode", () => {
  it("selects top nodes by type with diversity ratio", () => {
    const nodes = ref<ApiNode[]>([
      // 20 authors, 10 publishers, 5 binders
      ...Array.from({ length: 20 }, (_, i) => makeNode(`author:${i}`, "author")),
      ...Array.from({ length: 10 }, (_, i) => makeNode(`publisher:${i}`, "publisher")),
      ...Array.from({ length: 5 }, (_, i) => makeNode(`binder:${i}`, "binder")),
    ]);
    const edges = ref<ApiEdge[]>(
      // Give each node varying edge counts by creating edges
      Array.from({ length: 20 }, (_, i) =>
        makeEdge(`author:${i}`, `publisher:${i % 10}`, 10 - (i % 10))
      )
    );

    const hub = useHubMode(nodes, edges);
    const visible = hub.visibleNodes.value;

    // Should have at most 25 nodes
    expect(visible.length).toBeLessThanOrEqual(25);
    // Should include authors, publishers, and binders
    expect(visible.some((n) => n.type === "author")).toBe(true);
    expect(visible.some((n) => n.type === "publisher")).toBe(true);
  });

  it("expands a node adding up to 10 neighbors", () => {
    const hub_node = makeNode("author:0", "author");
    const neighbors = Array.from({ length: 15 }, (_, i) =>
      makeNode(`publisher:${i}`, "publisher")
    );
    const nodes = ref<ApiNode[]>([hub_node, ...neighbors]);
    const edges = ref<ApiEdge[]>(
      neighbors.map((n, i) => makeEdge("author:0", n.id, 10 - i))
    );

    const hub = useHubMode(nodes, edges);
    // Start with hub visible
    hub.initializeHubs();

    const beforeCount = hub.visibleNodes.value.length;
    hub.expandNode("author:0" as NodeId);
    const afterCount = hub.visibleNodes.value.length;

    // Should add up to 10 neighbors
    expect(afterCount - beforeCount).toBeLessThanOrEqual(10);
    expect(hub.isExpanded("author:0" as NodeId)).toBe(true);
  });

  it("reports remaining hidden neighbors count", () => {
    const hub_node = makeNode("author:0", "author");
    const neighbors = Array.from({ length: 15 }, (_, i) =>
      makeNode(`publisher:${i}`, "publisher")
    );
    const nodes = ref<ApiNode[]>([hub_node, ...neighbors]);
    const edges = ref<ApiEdge[]>(
      neighbors.map((n, i) => makeEdge("author:0", n.id, 10 - i))
    );

    const hub = useHubMode(nodes, edges);
    hub.initializeHubs();
    hub.expandNode("author:0" as NodeId);

    const remaining = hub.hiddenNeighborCount("author:0" as NodeId);
    expect(remaining).toBe(5); // 15 total - 10 expanded
  });

  it("transitions hub levels: compact → medium → full", () => {
    const nodes = ref<ApiNode[]>(
      Array.from({ length: 100 }, (_, i) => makeNode(`author:${i}`, "author"))
    );
    const edges = ref<ApiEdge[]>([]);

    const hub = useHubMode(nodes, edges);
    hub.initializeHubs();

    expect(hub.hubLevel.value).toBe("compact");
    expect(hub.visibleNodes.value.length).toBeLessThanOrEqual(25);

    hub.showMore();
    expect(hub.hubLevel.value).toBe("medium");
    expect(hub.visibleNodes.value.length).toBeLessThanOrEqual(50);

    hub.showMore();
    expect(hub.hubLevel.value).toBe("full");
    expect(hub.visibleNodes.value.length).toBe(100);
  });

  it("does not duplicate already-visible nodes on expand", () => {
    const nodes = ref<ApiNode[]>([
      makeNode("author:0", "author"),
      makeNode("author:1", "author"),
      makeNode("publisher:0", "publisher"),
    ]);
    const edges = ref<ApiEdge[]>([
      makeEdge("author:0", "publisher:0"),
      makeEdge("author:1", "publisher:0"),
    ]);

    const hub = useHubMode(nodes, edges);
    hub.initializeHubs();

    // Both authors and publisher should be hubs in a 3-node graph
    const before = hub.visibleNodes.value.length;
    hub.expandNode("author:0" as NodeId);
    const after = hub.visibleNodes.value.length;

    // publisher:0 was already visible — no duplicate
    expect(after).toBe(before);
  });

  it("edges are filtered to only visible endpoints", () => {
    const nodes = ref<ApiNode[]>([
      makeNode("author:0", "author"),
      makeNode("publisher:0", "publisher"),
      makeNode("publisher:1", "publisher"),
    ]);
    const edges = ref<ApiEdge[]>([
      makeEdge("author:0", "publisher:0"),
      makeEdge("author:0", "publisher:1"),
    ]);

    const hub = useHubMode(nodes, edges);
    hub.initializeHubs();

    // Only edges where both endpoints are visible should appear
    for (const edge of hub.visibleEdges.value) {
      const nodeIds = new Set(hub.visibleNodes.value.map((n) => n.id));
      expect(nodeIds.has(edge.source)).toBe(true);
      expect(nodeIds.has(edge.target)).toBe(true);
    }
  });
});
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/mark/projects/bluemoxon/frontend && npx vitest run src/composables/socialcircles/__tests__/useHubMode.test.ts`
Expected: FAIL (cannot find module)

**Step 3: Implement the composable**

Create `frontend/src/composables/socialcircles/useHubMode.ts`:

```typescript
/**
 * useHubMode - Progressive disclosure for social circles landing.
 *
 * Shows top N nodes by connection count (with type diversity),
 * supports expand-in-place and "show more" level transitions.
 */

import { computed, ref, type Ref } from "vue";
import type { ApiNode, ApiEdge, NodeId } from "@/types/socialCircles";

type HubLevel = "compact" | "medium" | "full";

const HUB_COUNTS: Record<HubLevel, number | null> = {
  compact: 25,
  medium: 50,
  full: null, // show all
};

// Type diversity ratio (proportional allocation)
const TYPE_RATIOS: Record<string, number> = {
  author: 0.6,
  publisher: 0.32,
  binder: 0.08,
};

const EXPAND_BATCH_SIZE = 10;

export function useHubMode(
  allNodes: Ref<ApiNode[]>,
  allEdges: Ref<ApiEdge[]>,
) {
  const hubLevel = ref<HubLevel>("compact");
  const expandedNodes = ref(new Set<NodeId>());
  const manuallyAddedNodes = ref(new Set<NodeId>());

  // Precompute edge count per node for hub ranking
  const edgeCountMap = computed(() => {
    const counts = new Map<NodeId, number>();
    for (const edge of allEdges.value) {
      counts.set(edge.source, (counts.get(edge.source) ?? 0) + 1);
      counts.set(edge.target, (counts.get(edge.target) ?? 0) + 1);
    }
    return counts;
  });

  // Select top N hubs with type diversity
  function selectHubs(count: number): Set<NodeId> {
    const byType = new Map<string, ApiNode[]>();
    for (const node of allNodes.value) {
      const list = byType.get(node.type) ?? [];
      list.push(node);
      byType.set(node.type, list);
    }

    // Sort each type by edge count descending
    const edgeCounts = edgeCountMap.value;
    for (const [, list] of byType) {
      list.sort((a, b) => (edgeCounts.get(b.id) ?? 0) - (edgeCounts.get(a.id) ?? 0));
    }

    const selected = new Set<NodeId>();

    // First pass: allocate by ratio
    for (const [type, ratio] of Object.entries(TYPE_RATIOS)) {
      const available = byType.get(type) ?? [];
      const quota = Math.round(count * ratio);
      for (let i = 0; i < Math.min(quota, available.length); i++) {
        selected.add(available[i].id);
      }
    }

    // Second pass: fill remaining slots from any type (by edge count)
    if (selected.size < count) {
      const allSorted = [...allNodes.value].sort(
        (a, b) => (edgeCounts.get(b.id) ?? 0) - (edgeCounts.get(a.id) ?? 0)
      );
      for (const node of allSorted) {
        if (selected.size >= count) break;
        selected.add(node.id);
      }
    }

    return selected;
  }

  // Hub node IDs based on current level
  const hubNodeIds = computed(() => {
    const limit = HUB_COUNTS[hubLevel.value];
    if (limit === null) {
      return new Set(allNodes.value.map((n) => n.id));
    }
    return selectHubs(limit);
  });

  // All visible node IDs = hubs + manually expanded
  const visibleNodeIds = computed(() => {
    const ids = new Set(hubNodeIds.value);
    for (const id of manuallyAddedNodes.value) {
      ids.add(id);
    }
    return ids;
  });

  // Visible nodes and edges
  const visibleNodes = computed(() =>
    allNodes.value.filter((n) => visibleNodeIds.value.has(n.id))
  );

  const visibleEdges = computed(() =>
    allEdges.value.filter(
      (e) => visibleNodeIds.value.has(e.source) && visibleNodeIds.value.has(e.target)
    )
  );

  // Expand a node's neighborhood
  function expandNode(nodeId: NodeId) {
    const neighbors = allEdges.value
      .filter((e) => e.source === nodeId || e.target === nodeId)
      .map((e) => ({ nodeId: e.source === nodeId ? e.target : e.source, strength: e.strength }))
      .filter((n) => !visibleNodeIds.value.has(n.nodeId))
      .sort((a, b) => b.strength - a.strength)
      .slice(0, EXPAND_BATCH_SIZE);

    for (const n of neighbors) {
      manuallyAddedNodes.value.add(n.nodeId);
    }
    expandedNodes.value.add(nodeId);

    // Trigger reactivity
    manuallyAddedNodes.value = new Set(manuallyAddedNodes.value);
    expandedNodes.value = new Set(expandedNodes.value);
  }

  // Expand next batch for a node ("+N more")
  function expandMore(nodeId: NodeId) {
    expandNode(nodeId);
  }

  // Count hidden neighbors for "+N more" badge
  function hiddenNeighborCount(nodeId: NodeId): number {
    return allEdges.value
      .filter((e) => e.source === nodeId || e.target === nodeId)
      .map((e) => (e.source === nodeId ? e.target : e.source))
      .filter((id) => !visibleNodeIds.value.has(id)).length;
  }

  function isExpanded(nodeId: NodeId): boolean {
    return expandedNodes.value.has(nodeId);
  }

  // "Show more" level transition
  function showMore() {
    if (hubLevel.value === "compact") {
      hubLevel.value = "medium";
    } else if (hubLevel.value === "medium") {
      hubLevel.value = "full";
    }
  }

  // Initialize (called on mount)
  function initializeHubs() {
    hubLevel.value = "compact";
    expandedNodes.value = new Set();
    manuallyAddedNodes.value = new Set();
  }

  // Status text for "Show more" button
  const statusText = computed(() => {
    const visible = visibleNodes.value.length;
    const total = allNodes.value.length;
    if (hubLevel.value === "full" && manuallyAddedNodes.value.size === 0) return null;
    return `Showing ${visible} of ${total}`;
  });

  const isFullyExpanded = computed(() => hubLevel.value === "full");

  return {
    // State
    hubLevel,
    visibleNodes,
    visibleEdges,
    visibleNodeIds,
    statusText,
    isFullyExpanded,

    // Actions
    initializeHubs,
    expandNode,
    expandMore,
    showMore,
    hiddenNeighborCount,
    isExpanded,
  };
}
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/mark/projects/bluemoxon/frontend && npx vitest run src/composables/socialcircles/__tests__/useHubMode.test.ts`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add frontend/src/composables/socialcircles/useHubMode.ts frontend/src/composables/socialcircles/__tests__/useHubMode.test.ts
git commit -m "feat: add useHubMode composable for progressive disclosure landing (#1619)"
```

---

### Task 8: Create ShowMoreButton and ExpandBadge components

**Files:**
- Create: `frontend/src/components/socialcircles/ShowMoreButton.vue`
- Create: `frontend/src/components/socialcircles/ExpandBadge.vue`

**Step 1: Implement ShowMoreButton**

Create `frontend/src/components/socialcircles/ShowMoreButton.vue`:

```vue
<script setup lang="ts">
defineProps<{
  statusText: string | null;
  isFullyExpanded: boolean;
}>();

defineEmits<{
  showMore: [];
}>();
</script>

<template>
  <button
    v-if="statusText && !isFullyExpanded"
    class="show-more-btn"
    data-testid="show-more-btn"
    @click="$emit('showMore')"
  >
    {{ statusText }} — <span class="show-more-btn__action">Show more</span>
  </button>
</template>

<style scoped>
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
</style>
```

**Step 2: Implement ExpandBadge**

Create `frontend/src/components/socialcircles/ExpandBadge.vue`:

```vue
<script setup lang="ts">
defineProps<{
  count: number;
}>();

defineEmits<{
  expand: [];
}>();
</script>

<template>
  <button
    v-if="count > 0"
    class="expand-badge"
    data-testid="expand-badge"
    :title="`Show ${count} more connections`"
    @click.stop="$emit('expand')"
  >
    +{{ count }}
  </button>
</template>

<style scoped>
.expand-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 20px;
  padding: 0 6px;
  background: var(--color-accent-gold, #b8860b);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.15s ease;
  position: absolute;
  top: -8px;
  right: -8px;
}

.expand-badge:hover {
  background: color-mix(in srgb, var(--color-accent-gold, #b8860b) 85%, black);
}
</style>
```

**Step 3: Commit**

```bash
git add frontend/src/components/socialcircles/ShowMoreButton.vue frontend/src/components/socialcircles/ExpandBadge.vue
git commit -m "feat: add ShowMoreButton and ExpandBadge UI components (#1619)"
```

---

### Task 9: Integrate hub mode into useSocialCircles and SocialCirclesView

**Files:**
- Modify: `frontend/src/composables/socialcircles/useSocialCircles.ts`
- Modify: `frontend/src/views/SocialCirclesView.vue`

**Step 1: Wire useHubMode into useSocialCircles**

In `frontend/src/composables/socialcircles/useSocialCircles.ts`:

Import useHubMode:
```typescript
import { useHubMode } from "./useHubMode";
```

After `const timeline = useNetworkTimeline();` (line 32), add:
```typescript
const hubMode = useHubMode(
  computed(() => nodes.value as ApiNode[]),
  computed(() => edges.value as ApiEdge[]),
);
```

Modify `filteredNodes` (line 45) to apply hub mode filter AFTER existing filters:

Replace the existing `filteredNodes` computed with a two-stage pipeline:

```typescript
  // Stage 1: Apply user filters (type, era, search, timeline)
  const filterPassedNodes = computed(() => {
    // ... (move existing filteredNodes logic here, unchanged)
  });

  // Stage 2: Apply hub mode on top of filter results
  const filteredNodes = computed(() => {
    const filtered = filterPassedNodes.value;
    if (hubMode.isFullyExpanded.value) return filtered;
    const visibleIds = hubMode.visibleNodeIds.value;
    return filtered.filter((n) => visibleIds.has(n.id));
  });
```

In `initialize()` (line 348), after `networkData.fetchData()` completes, add:
```typescript
    hubMode.initializeHubs();
```

In the search handler integration: when a searched node is not in the visible set, auto-expand it. This happens in `SocialCirclesView.vue`, not in the composable.

Expose hub mode in the return object:
```typescript
    // Hub mode
    hubMode: {
      statusText: hubMode.statusText,
      isFullyExpanded: hubMode.isFullyExpanded,
      expandNode: hubMode.expandNode,
      expandMore: hubMode.expandMore,
      showMore: hubMode.showMore,
      hiddenNeighborCount: hubMode.hiddenNeighborCount,
      isExpanded: hubMode.isExpanded,
      hubLevel: hubMode.hubLevel,
    },
```

**Step 2: Wire into SocialCirclesView**

In `frontend/src/views/SocialCirclesView.vue`:

Import the new components:
```typescript
import ShowMoreButton from "@/components/socialcircles/ShowMoreButton.vue";
```

Destructure hub mode from socialCircles:
```typescript
const { hubMode } = socialCircles;
```

In the template toolbar area (near LayoutSwitcher), add ShowMoreButton:
```vue
<ShowMoreButton
  :status-text="hubMode.statusText.value"
  :is-fully-expanded="hubMode.isFullyExpanded.value"
  @show-more="hubMode.showMore"
/>
```

Modify `handleSearchSelect` to auto-expand searched nodes that aren't visible:
```typescript
  // Auto-expand neighborhood if node not in hub view
  const nodeInView = filteredNodes.value.some((n) => n.id === node.id);
  if (!nodeInView && !hubMode.isFullyExpanded.value) {
    // Find a visible neighbor and expand it, or add the node directly
    hubMode.expandNode(node.id as NodeId);
  }
```

In `handleNodeClick` (or wherever node tap is handled), trigger expansion:
```typescript
  if (!hubMode.isFullyExpanded.value) {
    hubMode.expandNode(nodeId);
  }
```

**Step 3: Run all frontend tests**

Run: `cd /Users/mark/projects/bluemoxon/frontend && npx vitest run`
Expected: ALL PASS

**Step 4: Run linting**

Run: `cd /Users/mark/projects/bluemoxon/frontend && npm run lint && npm run format && npm run type-check`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/composables/socialcircles/useSocialCircles.ts frontend/src/views/SocialCirclesView.vue
git commit -m "feat: integrate hub mode into social circles for progressive disclosure landing (#1619)"
```

---

## Post-Merge: Profile Regeneration

### Task 10: Regenerate all entity profiles with cross-link markers

**Prerequisites:** Lanes A + B merged to staging and deployed.

**Step 1: Verify backend is deployed to staging**

```bash
curl -s https://staging.api.bluemoxon.com/api/v1/health/version | jq
```

**Step 2: Trigger profile regeneration**

```bash
bmx-api POST /entity/profiles/generate-all
```

**Step 3: Monitor progress**

```bash
# Get job ID from the response above, then:
bmx-api GET /entity/profiles/generate-all/status/<JOB_ID>
```

Wait for `status: "completed"`. Takes ~15 minutes for 264 entities.

**Step 4: Verify cross-links appear in a profile**

```bash
bmx-api GET /entity/author/31/profile | jq '.profile.bio_summary'
```

Look for `{{entity:...}}` markers in the bio and story text.

**Step 5: Run E2E smoke test**

Run: @bmx-e2e-validation (smoke + entity-profile suites)

---

## Lane Summary

| Lane | Branch | Issues | Files (no overlap) |
|------|--------|--------|--------------------|
| A | `feat/cross-link-backend` | #1618 | `ai_profile_generator.py`, `entity_profile.py`, `test_ai_profile_generator.py` |
| B | `feat/cross-link-frontend` | #1618 | `entityMarkers.ts`, `EntityLinkedText.vue`, `ProfileHero.vue`, `ConnectionGossipPanel.vue`, + tests |
| C | `feat/hub-mode` | #1619 | `useHubMode.ts`, `ShowMoreButton.vue`, `ExpandBadge.vue`, `useSocialCircles.ts`, `SocialCirclesView.vue`, + tests |

After all merge → Task 10: regenerate profiles.
