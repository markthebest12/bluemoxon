# Phase 5C Design: AI Cross-Links + Progressive Disclosure Landing

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:writing-plans to create the implementation plan from this design.

**Goal:** Two features that transform entity profiles and social circles from static displays into an interconnected, explorable experience.

**Architecture:** Backend prompt enrichment for cross-links (requires profile regeneration); client-side progressive disclosure for the landing page (no backend changes).

**Tech Stack:** Vue 3, TypeScript, Cytoscape.js, AWS Bedrock (Claude Haiku), FastAPI

---

## Feature 1: AI Entity Cross-Links (#1618)

### Overview

Make entity names in AI-generated stories clickable links to their profile pages. The AI returns inline markers like `{{entity:author:32|Robert Browning}}` in story text. The frontend parses markers and renders subtle inline links.

### Backend Changes

#### Prompt Modifications

All three generation functions in `backend/app/services/ai_profile_generator.py` receive the connection list (entity type, ID, name) as context:

- `generate_bio_and_stories()` (lines 109-167)
- `generate_connection_narrative()` (lines 170-195)
- `generate_relationship_story()` (lines 198-252)

The system prompt instructs the AI to wrap entity mentions in `{{entity:TYPE:ID|Display Name}}` markers. Only entities from the provided connection list may be linked — the AI must never invent IDs.

Example prompt addition:
```
When mentioning entities from the connection list below, wrap their names in markers:
{{entity:author:32|Robert Browning}}

Connection list:
- author:32 "Robert Browning"
- publisher:7 "Chapman & Hall"

Only use markers for entities in this list. Never invent entity IDs.
```

#### Validation

After parsing the AI JSON response, a validation step strips any markers whose entity IDs are not in the provided connection list. This guards against hallucinated IDs.

#### Scope

- Personal stories (bio facts): yes, cross-link mentions
- Relationship stories (connection narratives): yes, cross-link mentions
- Both `narrative` (one-liners) and `relationship_story.details` (full stories)

#### Profile Regeneration

All ~264 entity profiles must be regenerated after prompt changes. This is a one-time cost using the existing `POST /profiles/generate-all` endpoint.

### Frontend Changes

#### Marker Parser

New utility: `frontend/src/utils/entityMarkers.ts`

```typescript
type TextSegment = { type: 'text'; content: string }
type LinkSegment = { type: 'link'; entityType: string; entityId: number; displayName: string }
type Segment = TextSegment | LinkSegment

function parseEntityMarkers(text: string): Segment[]
```

Splits text on the regex pattern `\{\{entity:(\w+):(\d+)\|([^}]+)\}\}`, returning an array of text and link segments.

#### Component Integration

Components that render story text use the parser:

- **ProfileHero.vue** — personal stories in the hero bio section
- **ConnectionGossipPanel.vue** — relationship story details (prose-paragraph, bullet-facts, timeline-events modes)

A shared render helper (component or composable) takes a string, parses it, and renders `<span>` for text and `<router-link>` for links.

#### Link Styling

Subtle inline — designed not to break narrative reading flow:

- Same text color as surrounding prose
- Dotted underline (`text-decoration: underline dotted`)
- `cursor: pointer`
- On hover: underline becomes solid, slight color shift toward `--color-accent-gold`
- No bold, no badges, no icons

#### Stale Marker Handling

The frontend checks each marker's `entityType:entityId` against the `connections` array in the current API response. If the entity is missing (deleted, connection removed), the marker renders as plain text — just the display name with no link. This is graceful degradation; stale markers self-heal on next profile regeneration.

---

## Feature 2: Progressive Disclosure Landing (#1619)

### Overview

Replace the all-nodes-at-once landing with a curated hub view. On load, show 25 hub nodes selected by connection count with type diversity. Users expand neighborhoods by clicking. Each expansion reveals up to 10 connections. Recursive expansion allows deep exploration.

### Hub Selection

New computed property in `frontend/src/composables/socialcircles/useSocialCircles.ts`:

1. Sort all nodes by connection count (edge count) within each type
2. Select top N per type with ratio: 15 authors, 8 publishers, 2 binders (25 total)
3. Include edges only where both endpoints are in the visible set
4. If fewer nodes exist for a type than its quota, redistribute slots to other types

This is a client-side view filter. The API still returns the full graph. The existing `filteredNodes` / `filteredEdges` pipeline gains a `hubMode` boolean and a `visibleNodeIds: Set<NodeId>` that controls initial visibility.

### Hub Mode State

```typescript
interface HubState {
  enabled: boolean                    // true on initial load
  visibleNodeIds: Set<NodeId>         // starts with 25 hubs
  expandedNodes: Set<NodeId>          // tracks which nodes have been expanded
  hubLevel: 'compact' | 'medium' | 'full'  // 25 → 50 → all
}
```

### Expand Mechanic

Clicking a node in hub mode:
1. Shows the floating card (existing behavior)
2. Expands the node's neighborhood:
   - Sort connected edges by strength (descending)
   - Add top 10 target nodes to `visibleNodeIds`
   - Add the corresponding edges
   - Mark node as expanded in `expandedNodes`
3. Force-directed layout recalculates with animation
4. Newly added nodes fade in (brief opacity transition)

If the node has more than 10 hidden connections, a "+N more" badge appears on or near the node. Clicking the badge reveals the next batch of 10.

### "Show More" Button

Toolbar button near the layout switcher:

- Text: "Showing 25 of 224 — Show more"
- First click: jumps to 50 hubs (recalculates with same type-diversity ratio)
- Second click: shows all nodes (full graph, hub mode effectively off)
- At "all": button disappears, graph behaves as it does today

### Interaction with Existing Features

| Feature | Behavior in Hub Mode |
|---------|---------------------|
| **Node type toggles** | Filter applies on top of hub set (publishers off = publisher hubs hidden) |
| **Era filter** | Filters hub nodes by era |
| **Timeline slider** | Filters hub nodes as usual |
| **Search** | Centers on match; auto-expands its neighborhood if not yet visible |
| **Clear filters** | Resets to 25-hub default, not to all nodes |
| **Layout switcher** | Works normally on visible nodes |
| **Path finder** | If either endpoint is hidden, auto-expand to reveal the path |

### Edge Cases

- Entity with 0 connections: never selected as hub, can appear via expansion of a connected hub
- All hubs of one type filtered out: remaining types fill the gap proportionally
- Expansion reveals an already-visible node: no duplicate, just the edge is added
- Disconnected components: hubs from different components both appear, maintaining graph structure

---

## Testing

### #1618 Tests

**Unit:**
- `parseEntityMarkers()`: valid markers, malformed markers (missing pipe, wrong format), empty text, text with no markers, adjacent markers, nested markers
- Backend validation: strip markers with IDs not in connection list
- Component tests: ProfileHero and ConnectionGossipPanel render links for valid markers, plain text for stale/missing entities

**E2E:**
- Navigate to a profile with cross-links, click a linked entity name, verify navigation to correct profile page

### #1619 Tests

**Unit:**
- Hub selection: correct count per type, sorted by connection count, handles fewer-than-quota types
- Expansion: adds top 10 by strength, tracks expanded state, "+N more" calculates remaining
- Composable: `hubMode` filters correctly, expansion updates visible set, "Show more" transitions levels

**E2E:**
- Landing page shows ~25 nodes (not 224+)
- Click a hub, new nodes appear
- "+N more" badge appears on dense hubs
- "Show more" button increases node count
- Search auto-expands target neighborhood
- Filters work within hub mode

### Shared Edge Cases

- Profile with no AI-generated markers renders identically to current behavior
- Expansion of a node that reveals an already-visible node adds only the edge
- Hub mode disabled (full graph view) behaves exactly as the current production experience

---

## Implementation Sequence

1. **#1618 first** — backend prompt changes + frontend parser + component integration + profile regeneration
2. **#1619 second** — client-side only, no backend dependency, can be developed independently after #1618

Both features are independent at the code level (zero file overlap between the two), so they can be developed in parallel lanes if desired. However, #1618 requires profile regeneration which takes ~15 minutes and has API cost, so it should be validated thoroughly before triggering regeneration.
