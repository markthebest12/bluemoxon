# AI-Discovered Personal Connections

**Created:** 2026-02-04
**Status:** Design Complete — Ready for Implementation
**Depends on:** Victorian Social Circles (2026-01-26)

## Overview

The social circles system currently discovers connections only through shared book data (publisher, shared_publisher, binder). This misses the most compelling relationships — marriages, friendships, mentorships, collaborations, and scandals that made Victorian literary life a soap opera.

**The Browning Problem:** Elizabeth Barrett Browning (author:31) and Robert Browning (author:227) have 6 books in the collection but share zero publishers (she: James Miller, OUP, Dean & Son; he: Smith Elder x3). The most famous literary couple in Victorian England is invisible.

### Solution

Add AI-discovered personal connections to the entity profile generation pipeline. During profile generation, ask Claude which entities in the collection had personal relationships. Store as structured JSON, merge into both entity profiles and the main social circles graph.

### Design Principles

- **Zero new infrastructure** — uses existing SQS pipeline and entity_profiles table
- **Discovery at generation time** — connections found when profiles are generated
- **Batch flow for initial creation** — existing `POST /entity/profiles/generate-all`
- **Collection-scoped edges** — graph edges only between entities in the collection
- **AI narrative can name-drop** — bios can reference external figures not in collection

---

## 1. Data Model

**Table:** `entity_profiles` (existing)
**New column:** `ai_connections` (JSON, nullable)

### Migration

```sql
ALTER TABLE entity_profiles ADD COLUMN ai_connections JSONB;
```

Nullable — existing profiles continue to work. Populated on next generation.

### Schema

```json
{
  "ai_connections": [
    {
      "target_type": "author",
      "target_id": 227,
      "target_name": "Robert Browning",
      "relationship": "family",
      "sub_type": "marriage",
      "summary": "Married in secret in 1846, eloping to Italy against her father's wishes",
      "confidence": "confirmed"
    }
  ]
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `target_type` | string | Entity type: author, publisher, binder |
| `target_id` | int | Entity ID in collection |
| `target_name` | string | Display name (denormalized for convenience) |
| `relationship` | string | One of 5 types (see below) |
| `sub_type` | string | Specific relationship: marriage, mentor, rival, etc. |
| `summary` | string | 1-2 sentence description of the connection |
| `confidence` | string | `confirmed`, `likely`, or `rumored` |

### Connection Types

| Type | Examples | Edge Color |
|------|----------|------------|
| `family` | Marriage, siblings, parent-child | Blue #60a5fa |
| `friendship` | Personal friends, social circle | Blue #60a5fa |
| `influence` | Mentor/mentee, intellectual influence | Blue #60a5fa (dotted) |
| `collaboration` | Co-authors, literary partnerships | Blue #60a5fa |
| `scandal` | Affairs, public feuds, controversies | Rose #f87171 (dashed) |

### Storage

Each entity stores connections **from its own perspective**. No bidirectional flag — deduplication happens at the graph level using canonical key ordering (lower ID first in edge ID).

---

## 2. AI Discovery Prompt

### System Prompt

```
You are a literary historian specializing in Victorian-era personal relationships,
scandals, and social networks. You have deep knowledge of who knew whom, who married
whom, who influenced whom, and the personal dramas that connected the literary world.

Return ONLY valid JSON. Be factual. Draw from commonly known historical record.
For uncertain connections, mark confidence as "rumored".
```

### User Prompt

```
Given this entity from a rare book collection:
  Name: {name}
  Type: {entity_type}
  Dates: {birth_year} - {death_year}
  Books in collection: {book_titles}

The following entities are also in this collection:
{entity_list}

Identify personal connections between {name} and ANY of the listed entities.
Include: family ties, friendships, mentorships, collaborations, rivalries, scandals.
Do NOT include publisher/binder relationships (those are handled separately).
Only return connections to entities in the provided list — never invent entity IDs.

Return JSON array:
[
  {
    "target_type": "author",
    "target_id": 227,
    "target_name": "Robert Browning",
    "relationship": "family",
    "sub_type": "marriage",
    "summary": "Married in secret in 1846...",
    "confidence": "confirmed"
  }
]

If no personal connections exist, return an empty array: []
```

### Entity List

**CRITICAL:** Pass ALL collection entities from `graph.nodes` (~264), not just graph-connected ones. The Brownings aren't graph-connected — that's the whole problem we're solving.

Format: `- author:31 "Elizabeth Barrett Browning" (1806-1861)`

### Post-Processing

1. Parse JSON (strip markdown fences if present)
2. Validate each connection:
   - `target_type:target_id` must exist in collection entity set
   - `relationship` must be one of 5 valid types
   - No self-connections (target != source)
   - No duplicates (same target + relationship)
3. Strip invalid entries (graceful degradation, log warnings)

### Cost

- Model: Haiku (via `model.entity_profiles` config)
- ~$0.0015 per entity
- ~$0.40 for full 264-entity batch sweep

---

## 3. Graph Integration

### ConnectionType Enum

**File:** `backend/app/schemas/social_circles.py`

Add 5 new values to `ConnectionType`:

```python
class ConnectionType(str, Enum):
    publisher = "publisher"
    shared_publisher = "shared_publisher"
    binder = "binder"
    # AI-discovered personal connections
    family = "family"
    friendship = "friendship"
    influence = "influence"
    collaboration = "collaboration"
    scandal = "scandal"
```

### Entity Profile View (`_build_connections()`)

**File:** `backend/app/services/entity_profile.py`

After building connections from graph data, merge AI-discovered connections from `entity_profile.ai_connections`:

```python
# After existing graph-based connections...
if cached_profile and cached_profile.ai_connections:
    for conn in cached_profile.ai_connections:
        connections.append({
            "entity_type": conn["target_type"],
            "entity_id": conn["target_id"],
            "name": conn["target_name"],
            "connection_type": conn["relationship"],
            "sub_type": conn["sub_type"],
            "strength": _ai_connection_strength(conn),
            "evidence": conn["summary"],
            "is_ai_discovered": True,
        })
```

**Key connection priority:** Personal connections always get key connection slots first (they're more interesting than shared publishers).

### Main Social Circles Graph (`build_social_circles_graph()`)

**File:** `backend/app/services/social_circles.py`

**MUST CHANGE.** After building book-data edges, query `entity_profiles` for all AI connections and merge as additional edges:

```python
# After existing publisher/binder edge building...
ai_edges = _load_ai_connections(db)  # Query entity_profiles.ai_connections
for edge in ai_edges:
    edge_id = _canonical_edge_id(edge)  # e.g., "e:author:31:author:227:family"
    if edge_id not in seen_edges:
        graph.edges.append(edge)
        seen_edges.add(edge_id)
```

Edge ID includes relationship type for dedup: `e:author:31:author:227:family`

This ensures the main `/socialcircles` page shows personal connections, not just the entity profile ego network.

---

## 4. Edge Styling

### Color & Style Table

| Connection Type | Color | Line Style | Width |
|----------------|-------|------------|-------|
| publisher | Green #4ade80 | Solid | 2-6px (scaled by strength) |
| shared_publisher | Green #4ade80 | Solid | 1-3px (scaled by strength) |
| binder | Purple #a78bfa | Dashed | 1-3px (scaled by strength) |
| family | Blue #60a5fa | Solid | 3px |
| friendship | Blue #60a5fa | Solid | 2px |
| influence | Blue #60a5fa | Dotted | 2px |
| collaboration | Blue #60a5fa | Solid | 2px |
| scandal | Rose #f87171 | Dashed | 2px |

Three color categories matching the user's vision:
- **Green** = publisher relationships
- **Blue** = personal connections
- **Purple** = binder relationships
- **Rose** = scandal (the soap opera layer)

### Interaction Model

| Component | Behavior | Rationale |
|-----------|----------|-----------|
| **SocialCirclesView** (main graph) | Click-to-highlight: dim non-connected nodes/edges to 0.15 opacity | Full network — highlighting reveals structure |
| **EgoNetwork** (profile page) | Click-to-navigate: click node → navigate to that entity's profile | Star graph — everything connects to center, highlighting adds nothing |

### Confidence Styling

| Confidence | Text Style | Indicator |
|------------|-----------|-----------|
| `confirmed` | Normal | None |
| `likely` | Normal | None |
| `rumored` | Italic | "Rumored" badge — the soap opera effect |

---

## 5. Pipeline Integration

### Generation Flow

```
resolve config
  → get entity details
    → build social circles graph
      → extract ALL nodes from graph.nodes (~264 entities)
        → AI connection discovery (NEW)
          → validate connections
            → merge into cross-link markers
              → bio + stories generation (can now reference discovered connections)
                → narrative generation
                  → upsert to entity_profiles
```

**Key:** Discovery happens BEFORE bio generation so bios can reference discovered connections via cross-link markers like `{{entity:author:227|Robert Browning}}`.

### Batch Flow

Existing `POST /entity/profiles/generate-all` → SQS → profile worker pipeline.

Zero new infrastructure. Each entity's profile generation now includes the AI discovery step.

Use cases:
- **Initial creation:** Run batch to discover connections across all ~264 entities
- **Model upgrades:** Re-run batch when a new AI model is available for richer discovery
- **Collection changes:** New books/entities trigger individual profile regeneration

### Cost

| Scenario | Entities | Cost |
|----------|----------|------|
| Single entity | 1 | ~$0.0015 |
| Full batch | ~264 | ~$0.40 |
| Model upgrade re-run | ~264 | ~$0.40 |

---

## 6. Frontend Changes

### Badge Display

Show `sub_type` (specific) not `relationship` (broad):

| Instead of | Show |
|------------|------|
| FAMILY | MARRIAGE |
| INFLUENCE | MENTOR |
| SCANDAL | AFFAIR |
| FRIENDSHIP | FRIEND |
| COLLABORATION | CO-AUTHOR |

More compelling and specific for the user.

### Components to Modify

| Component | Change |
|-----------|--------|
| `EgoNetwork.vue` | Add type-specific edge selectors (color, style, width per connection type) |
| `KeyConnections.vue` | Show AI-discovered connections with sub_type badges |
| `ConnectionGossipPanel.vue` | Display AI connection summary with confidence styling |
| `SocialCirclesView.vue` | Add click-to-highlight behavior, type-specific edge styling |

### Cytoscape Edge Selectors (EgoNetwork / SocialCirclesView)

```javascript
// Personal connections — blue
'edge[connection_type = "family"]': { 'line-color': '#60a5fa', 'line-style': 'solid', 'width': 3 },
'edge[connection_type = "friendship"]': { 'line-color': '#60a5fa', 'line-style': 'solid', 'width': 2 },
'edge[connection_type = "influence"]': { 'line-color': '#60a5fa', 'line-style': 'dotted', 'width': 2 },
'edge[connection_type = "collaboration"]': { 'line-color': '#60a5fa', 'line-style': 'solid', 'width': 2 },
// Scandal — rose
'edge[connection_type = "scandal"]': { 'line-color': '#f87171', 'line-style': 'dashed', 'width': 2 },
// Publisher — green (existing, update color)
'edge[connection_type = "publisher"]': { 'line-color': '#4ade80', 'line-style': 'solid', 'width': 'mapData(strength, 2, 10, 2, 6)' },
// Binder — purple (existing, update color)
'edge[connection_type = "binder"]': { 'line-color': '#a78bfa', 'line-style': 'dashed', 'width': 'mapData(strength, 2, 10, 1, 3)' },
```

---

## 7. Testing Strategy

### Unit Tests

| Category | Tests |
|----------|-------|
| **AI Generation** | Prompt includes all collection entities; response parsed correctly; empty array handled |
| **Validation** | Self-connections rejected; duplicate connections rejected; invalid relationship types rejected; non-collection entity IDs rejected; invalid JSON handled gracefully |
| **Connection Merge** | AI connections merged into entity profile connections; personal connections get key slots first; dedup with existing graph connections |
| **Graph Builder** | AI edges appear in social circles graph; edge IDs include relationship type; canonical key ordering for dedup |

### Integration Tests

| Test | Validates |
|------|-----------|
| Profile generation with AI connections | Full pipeline: discovery → validate → merge → bio references connections |
| Batch generation | All entities get AI connections; batch doesn't fail on individual errors |

### E2E Tests

| Test | Validates |
|------|-----------|
| Entity profile page | AI-discovered connections visible with correct badges and styling |
| Social circles page | Personal connection edges visible with correct colors; click-to-highlight works |

### Hallucination Edge Cases

Critical — AI may hallucinate connections. Explicit test coverage for:
- Self-connections (entity connected to itself)
- Duplicate connections (same target + same relationship)
- Invalid relationship types (not in the 5-type enum)
- Non-collection entity IDs (IDs that don't exist in graph.nodes)
- Empty `shared_books` handling (personal connections have no shared books)

---

## 8. Files to Modify

### Backend (4-5 files)

| File | Change |
|------|--------|
| `backend/app/services/ai_profile_generator.py` | New `generate_ai_connections()` function with discovery prompt |
| `backend/app/services/entity_profile.py` | Insert AI discovery before bio generation; merge AI connections in `_build_connections()` |
| `backend/app/services/social_circles.py` | Merge AI edges in `build_social_circles_graph()` |
| `backend/app/schemas/social_circles.py` | Add 5 new `ConnectionType` enum values |
| `backend/app/models/entity_profile.py` | Add `ai_connections` JSON column |

### Migration (1 file)

| File | Change |
|------|--------|
| `backend/alembic/versions/xxxx_add_ai_connections.py` | Add nullable `ai_connections` JSONB column |

### Frontend (3-4 files)

| File | Change |
|------|--------|
| `frontend/src/components/entityprofile/EgoNetwork.vue` | Type-specific edge selectors (color, style, width) |
| `frontend/src/components/entityprofile/KeyConnections.vue` | AI-discovered connections with sub_type badges |
| `frontend/src/components/entityprofile/ConnectionGossipPanel.vue` | AI connection summary with confidence styling |
| `frontend/src/views/SocialCirclesView.vue` | Click-to-highlight behavior, type-specific edge styling |

### Tests

| File | Change |
|------|--------|
| `backend/tests/test_entity_profile.py` | AI connection generation, validation, merge tests |
| `backend/tests/test_social_circles.py` | Graph builder AI edge merge tests |
| `frontend/e2e/social-circles.spec.ts` | AI connection visibility and edge styling |

---

## Decisions Log

All decisions made and approved during brainstorming (2026-02-04):

| # | Decision | Choice |
|---|----------|--------|
| 1 | Discovery method | AI-discovered at profile generation time + batch flow |
| 2 | Connection types | 5 types: family, friendship, influence, collaboration, scandal |
| 3 | Scope | Collection + notable mentions (edges only between collection entities) |
| 4 | Data model | New `ai_connections` JSON column on `entity_profiles` — no new table |
| 5 | Pipeline position | Discovery BEFORE bio generation (so bios can reference connections) |
| 6 | Entity list for AI | ALL collection entities from `graph.nodes` (~264) |
| 7 | Bidirectional | Dropped — each entity stores own perspective, graph dedup at display |
| 8 | Edge styling | Green=publisher, Blue=personal, Purple=binder, Rose=scandal |
| 9 | Interaction | SocialCirclesView=click-to-highlight, EgoNetwork=click-to-navigate |
| 10 | Badge display | Shows sub_type ("MARRIAGE") not relationship ("FAMILY") |
| 11 | Confidence styling | "Rumored" connections get italic + indicator |
| 12 | Graph builder | MUST merge AI edges — otherwise main /socialcircles never shows them |
