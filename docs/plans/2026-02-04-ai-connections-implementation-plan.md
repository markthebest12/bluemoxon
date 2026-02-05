# AI-Discovered Connections — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add AI-discovered personal connections (family, friendship, influence, collaboration, scandal) to social circles so the Brownings, Dickens↔Collins, Carlyle→Ruskin, etc. become visible.

**Architecture:** New `ai_connections` JSONB column on `entity_profiles`. AI discovery happens during profile generation, before bio generation. Discovered edges merge into both entity profile view and main social circles graph. Frontend gets type-specific edge styling and click-to-highlight.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic, AWS Bedrock Claude (Haiku), Vue 3 + TypeScript, Cytoscape.js, Playwright E2E.

**Design Doc:** `docs/plans/2026-02-04-ai-discovered-connections-design.md`

**GitHub Issues:** #1803 (epic), #1804-#1810 (children)

---

## Task 1: Foundation — Migration + Model + Schema (#1804)

**Files:**
- Create: `backend/alembic/versions/a1b2c3d4e5f6_add_ai_connections_column.py`
- Modify: `backend/app/models/entity_profile.py:27` (after `model_version`)
- Modify: `backend/app/schemas/social_circles.py:28-29` (after `binder` enum)
- Modify: `backend/app/db/migration_sql.py:1007-1009` (append to MIGRATIONS list)
- Modify: `frontend/src/types/socialCircles.ts:27` (ConnectionType union)
- Modify: `frontend/src/constants/socialCircles.ts:66-70` (EDGE_COLORS)
- Modify: `frontend/src/constants/socialCircles.ts:110-114` (EDGE_STYLES)

**Step 1: Add ConnectionType enum values**

In `backend/app/schemas/social_circles.py`, after line 28:

```python
class ConnectionType(str, Enum):
    """Types of connections between nodes."""

    publisher = "publisher"  # Author published by publisher
    shared_publisher = "shared_publisher"  # Two authors share a publisher
    binder = "binder"  # Author's book bound by binder
    # AI-discovered personal connections
    family = "family"
    friendship = "friendship"
    influence = "influence"
    collaboration = "collaboration"
    scandal = "scandal"
```

**Step 2: Add ai_connections column to model**

In `backend/app/models/entity_profile.py`, after line 27:

```python
    model_version: Mapped[str | None] = mapped_column(String(100))
    ai_connections: Mapped[list | None] = mapped_column(JSON)
```

**Step 3: Create Alembic migration**

Create `backend/alembic/versions/a1b2c3d4e5f6_add_ai_connections_column.py`:

```python
"""Add ai_connections column to entity_profiles.

Revision ID: a1b2c3d4e5f6
Revises: z4567890klmn
Create Date: 2026-02-05

Issue #1804: Store AI-discovered personal connections (family,
friendship, influence, collaboration, scandal) as JSON.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "z4567890klmn"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add ai_connections JSONB column."""
    op.add_column("entity_profiles", sa.Column("ai_connections", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Drop ai_connections column."""
    op.drop_column("entity_profiles", "ai_connections")
```

**Step 4: Add migration SQL to registry**

In `backend/app/db/migration_sql.py`, add the SQL constant (find similar patterns nearby) and append to MIGRATIONS list after `z4567890klmn`:

```python
MIGRATION_A1B2C3D4E5F6_SQL = [
    "ALTER TABLE entity_profiles ADD COLUMN ai_connections JSONB;",
]

# Then in MIGRATIONS list, after the z4567890klmn entry:
    {
        "id": "a1b2c3d4e5f6",
        "name": "add_ai_connections_column",
        "sql_statements": MIGRATION_A1B2C3D4E5F6_SQL,
    },
```

**Step 5: Update frontend TypeScript types**

In `frontend/src/types/socialCircles.ts` line 27:

```typescript
export type ConnectionType = "publisher" | "shared_publisher" | "binder"
  | "family" | "friendship" | "influence" | "collaboration" | "scandal";
```

**Step 6: Update frontend constants**

In `frontend/src/constants/socialCircles.ts`, update EDGE_COLORS (line 66):

```typescript
export const EDGE_COLORS: Record<ConnectionType, string> = {
  publisher: "#4ade80",        // green (was gold)
  shared_publisher: "#4ade80", // green (was hunter)
  binder: "#a78bfa",           // purple (was burgundy)
  family: "#60a5fa",           // blue
  friendship: "#60a5fa",       // blue
  influence: "#60a5fa",        // blue
  collaboration: "#60a5fa",    // blue
  scandal: "#f87171",          // rose
};
```

Update EDGE_STYLES (line 110):

```typescript
export const EDGE_STYLES: Record<ConnectionType, { lineStyle: string; opacity: number }> = {
  publisher: { lineStyle: "solid", opacity: 0.8 },
  shared_publisher: { lineStyle: "solid", opacity: 0.6 },
  binder: { lineStyle: "dashed", opacity: 0.5 },
  family: { lineStyle: "solid", opacity: 0.8 },
  friendship: { lineStyle: "solid", opacity: 0.7 },
  influence: { lineStyle: "dotted", opacity: 0.7 },
  collaboration: { lineStyle: "solid", opacity: 0.7 },
  scandal: { lineStyle: "dashed", opacity: 0.8 },
};
```

**Step 7: Validate**

Run:
```bash
poetry run ruff check backend/
poetry run ruff format --check backend/
npm run --prefix frontend lint
npm run --prefix frontend type-check
```

**Step 8: Commit**

```bash
git add backend/app/models/entity_profile.py backend/app/schemas/social_circles.py \
  backend/alembic/versions/a1b2c3d4e5f6_add_ai_connections_column.py \
  backend/app/db/migration_sql.py \
  frontend/src/types/socialCircles.ts frontend/src/constants/socialCircles.ts
git commit -m "feat: add ai_connections column and 5 new ConnectionType values (#1804)"
```

---

## Task 2: AI Discovery Function + Validation (#1805)

**Files:**
- Modify: `backend/app/services/ai_profile_generator.py:174` (after `_RELATIONSHIP_SYSTEM_PROMPT`)
- Test: `backend/tests/test_entity_profile.py`

**Step 1: Write failing tests for generate_ai_connections()**

Add to `backend/tests/test_entity_profile.py` — a new test class:

```python
class TestGenerateAIConnections:
    """Tests for AI connection discovery function."""

    def test_valid_response_parsed(self):
        """Valid AI response returns list of connection dicts."""
        mock_response = json.dumps([
            {
                "target_type": "author",
                "target_id": 227,
                "target_name": "Robert Browning",
                "relationship": "family",
                "sub_type": "marriage",
                "summary": "Married in secret in 1846",
                "confidence": "confirmed",
            }
        ])
        collection_ids = {"author:227", "author:31", "publisher:167"}
        source_key = "author:31"

        with patch("app.services.ai_profile_generator._invoke", return_value=mock_response):
            config = MagicMock(spec=GeneratorConfig)
            result = generate_ai_connections(
                name="Elizabeth Barrett Browning",
                entity_type="author",
                entity_id=31,
                birth_year=1806,
                death_year=1861,
                book_titles=["Aurora Leigh"],
                collection_entities=[
                    {"type": "author", "id": 227, "name": "Robert Browning", "dates": "1812-1889"},
                ],
                collection_entity_ids=collection_ids,
                config=config,
            )
        assert len(result) == 1
        assert result[0]["target_id"] == 227
        assert result[0]["relationship"] == "family"

    def test_empty_array_handled(self):
        """Empty JSON array returns empty list."""
        with patch("app.services.ai_profile_generator._invoke", return_value="[]"):
            config = MagicMock(spec=GeneratorConfig)
            result = generate_ai_connections(
                name="Obscure Author", entity_type="author", entity_id=999,
                collection_entities=[], collection_entity_ids=set(), config=config,
            )
        assert result == []

    def test_self_connections_rejected(self):
        """Connections from entity to itself are stripped."""
        mock_response = json.dumps([
            {"target_type": "author", "target_id": 31, "target_name": "Self",
             "relationship": "family", "sub_type": "self", "summary": "x", "confidence": "confirmed"}
        ])
        with patch("app.services.ai_profile_generator._invoke", return_value=mock_response):
            config = MagicMock(spec=GeneratorConfig)
            result = generate_ai_connections(
                name="EBB", entity_type="author", entity_id=31,
                collection_entities=[], collection_entity_ids={"author:31"},
                config=config,
            )
        assert result == []

    def test_invalid_relationship_type_rejected(self):
        """Connections with invalid relationship types are stripped."""
        mock_response = json.dumps([
            {"target_type": "author", "target_id": 227, "target_name": "RB",
             "relationship": "nemesis", "sub_type": "x", "summary": "x", "confidence": "confirmed"}
        ])
        with patch("app.services.ai_profile_generator._invoke", return_value=mock_response):
            config = MagicMock(spec=GeneratorConfig)
            result = generate_ai_connections(
                name="EBB", entity_type="author", entity_id=31,
                collection_entities=[], collection_entity_ids={"author:227"},
                config=config,
            )
        assert result == []

    def test_non_collection_ids_rejected(self):
        """Connections to entities not in collection are stripped."""
        mock_response = json.dumps([
            {"target_type": "author", "target_id": 9999, "target_name": "Ghost",
             "relationship": "family", "sub_type": "x", "summary": "x", "confidence": "confirmed"}
        ])
        with patch("app.services.ai_profile_generator._invoke", return_value=mock_response):
            config = MagicMock(spec=GeneratorConfig)
            result = generate_ai_connections(
                name="EBB", entity_type="author", entity_id=31,
                collection_entities=[], collection_entity_ids={"author:227"},
                config=config,
            )
        assert result == []

    def test_duplicate_connections_deduplicated(self):
        """Duplicate target+relationship combos keep only first."""
        mock_response = json.dumps([
            {"target_type": "author", "target_id": 227, "target_name": "RB",
             "relationship": "family", "sub_type": "marriage", "summary": "First", "confidence": "confirmed"},
            {"target_type": "author", "target_id": 227, "target_name": "RB",
             "relationship": "family", "sub_type": "marriage", "summary": "Dupe", "confidence": "confirmed"},
        ])
        with patch("app.services.ai_profile_generator._invoke", return_value=mock_response):
            config = MagicMock(spec=GeneratorConfig)
            result = generate_ai_connections(
                name="EBB", entity_type="author", entity_id=31,
                collection_entities=[], collection_entity_ids={"author:227"},
                config=config,
            )
        assert len(result) == 1
        assert result[0]["summary"] == "First"

    def test_invalid_json_returns_empty(self):
        """Malformed JSON gracefully returns empty list."""
        with patch("app.services.ai_profile_generator._invoke", return_value="not json"):
            config = MagicMock(spec=GeneratorConfig)
            result = generate_ai_connections(
                name="EBB", entity_type="author", entity_id=31,
                collection_entities=[], collection_entity_ids=set(),
                config=config,
            )
        assert result == []
```

**Step 2: Run tests to verify they fail**

```bash
poetry run pytest backend/tests/test_entity_profile.py::TestGenerateAIConnections -v
```

Expected: FAIL — `generate_ai_connections` not defined.

**Step 3: Implement generate_ai_connections()**

In `backend/app/services/ai_profile_generator.py`, after line 174 (after `_RELATIONSHIP_SYSTEM_PROMPT`):

```python
_DISCOVERY_SYSTEM_PROMPT = (
    "You are a literary historian specializing in Victorian-era personal relationships, "
    "scandals, and social networks. You have deep knowledge of who knew whom, who married "
    "whom, who influenced whom, and the personal dramas that connected the literary world. "
    "Return ONLY valid JSON. Be factual. Draw from commonly known historical record. "
    "For uncertain connections, mark confidence as \"rumored\"."
)

VALID_RELATIONSHIP_TYPES = frozenset({"family", "friendship", "influence", "collaboration", "scandal"})


def _validate_ai_connections(
    connections: list[dict],
    source_type: str,
    source_id: int,
    collection_entity_ids: set[str],
) -> list[dict]:
    """Validate and deduplicate AI-discovered connections.

    Strips:
    - Self-connections
    - Non-collection entity IDs
    - Invalid relationship types
    - Duplicates (same target + relationship)
    """
    seen: set[str] = set()
    valid: list[dict] = []
    source_key = f"{source_type}:{source_id}"

    for conn in connections:
        target_key = f"{conn.get('target_type')}:{conn.get('target_id')}"

        # Self-connection
        if target_key == source_key:
            logger.warning("AI discovery: stripping self-connection for %s", source_key)
            continue

        # Not in collection
        if target_key not in collection_entity_ids:
            logger.warning("AI discovery: stripping non-collection ID %s", target_key)
            continue

        # Invalid relationship type
        relationship = conn.get("relationship", "")
        if relationship not in VALID_RELATIONSHIP_TYPES:
            logger.warning("AI discovery: stripping invalid relationship '%s'", relationship)
            continue

        # Dedup by target + relationship
        dedup_key = f"{target_key}:{relationship}"
        if dedup_key in seen:
            logger.debug("AI discovery: stripping duplicate %s", dedup_key)
            continue
        seen.add(dedup_key)

        valid.append(conn)

    return valid


def generate_ai_connections(
    name: str,
    entity_type: str,
    entity_id: int,
    birth_year: int | None = None,
    death_year: int | None = None,
    book_titles: list[str] | None = None,
    collection_entities: list[dict] | None = None,
    collection_entity_ids: set[str] | None = None,
    *,
    config: GeneratorConfig,
) -> list[dict]:
    """Discover personal connections between entity and collection via AI.

    Returns validated list of connection dicts:
    [{target_type, target_id, target_name, relationship, sub_type, summary, confidence}]
    """
    if not collection_entities:
        return []

    dates_line = ""
    if birth_year and death_year:
        dates_line = f"Dates: {birth_year} - {death_year}"

    book_list = ", ".join(book_titles) if book_titles else "None in collection"

    entity_lines = "\n".join(
        f"- {e['type']}:{e['id']} \"{e['name']}\" ({e.get('dates', 'dates unknown')})"
        for e in collection_entities
    )

    user_prompt = f"""Given this entity from a rare book collection:
  Name: {name}
  Type: {entity_type}
  {dates_line}
  Books in collection: {book_list}

The following entities are also in this collection:
{entity_lines}

Identify personal connections between {name} and ANY of the listed entities.
Include: family ties, friendships, mentorships, collaborations, rivalries, scandals.
Do NOT include publisher/binder relationships (those are handled separately).
Only return connections to entities in the provided list — never invent entity IDs.

Return JSON array:
[
  {{
    "target_type": "author",
    "target_id": 227,
    "target_name": "Robert Browning",
    "relationship": "family",
    "sub_type": "marriage",
    "summary": "Married in secret in 1846...",
    "confidence": "confirmed"
  }}
]

If no personal connections exist, return an empty array: []"""

    try:
        raw = _invoke(_DISCOVERY_SYSTEM_PROMPT, user_prompt, max_tokens=1024, config=config)
        text = _strip_markdown_fences(raw)
        result = json.loads(text)
        if not isinstance(result, list):
            logger.warning("AI discovery returned non-list for %s:%d", entity_type, entity_id)
            return []
        return _validate_ai_connections(
            result, entity_type, entity_id, collection_entity_ids or set()
        )
    except Exception:
        logger.exception("Failed AI connection discovery for %s:%d", entity_type, entity_id)
        return []
```

**Step 4: Add import in test file**

Add `generate_ai_connections` to the test imports from `app.services.ai_profile_generator`.

**Step 5: Run tests to verify they pass**

```bash
poetry run pytest backend/tests/test_entity_profile.py::TestGenerateAIConnections -v
```

**Step 6: Lint and commit**

```bash
poetry run ruff check backend/
poetry run ruff format --check backend/
git add backend/app/services/ai_profile_generator.py backend/tests/test_entity_profile.py
git commit -m "feat: add generate_ai_connections() with validation (#1805)"
```

---

## Task 3: Pipeline Integration (#1806)

**Files:**
- Modify: `backend/app/services/entity_profile.py:500-656` (generate_and_cache_profile)
- Modify: `backend/app/services/entity_profile.py:288-435` (_build_connections)
- Test: `backend/tests/test_entity_profile.py`

**Step 1: Write failing test for AI connections in pipeline**

```python
class TestPipelineAIConnections:
    """Tests for AI connection integration in generate_and_cache_profile."""

    @patch("app.services.entity_profile.generate_ai_connections")
    @patch("app.services.entity_profile.generate_bio_and_stories")
    @patch("app.services.entity_profile.get_or_build_graph")
    def test_ai_connections_stored_on_profile(
        self, mock_graph, mock_bio, mock_ai_conn, db
    ):
        """AI connections from discovery are persisted on entity_profiles."""
        # Setup
        author = Author(name="Elizabeth Barrett Browning", birth_year=1806, death_year=1861)
        db.add(author)
        db.flush()

        mock_graph.return_value = _empty_graph()
        mock_bio.return_value = {"biography": "A poet", "personal_stories": []}
        mock_ai_conn.return_value = [
            {
                "target_type": "author", "target_id": 227,
                "target_name": "Robert Browning", "relationship": "family",
                "sub_type": "marriage", "summary": "Married in 1846",
                "confidence": "confirmed",
            }
        ]

        profile = generate_and_cache_profile(db, "author", author.id)
        assert profile.ai_connections is not None
        assert len(profile.ai_connections) == 1
        assert profile.ai_connections[0]["relationship"] == "family"
```

**Step 2: Write failing test for AI connections in _build_connections**

```python
class TestBuildConnectionsAI:
    """Tests for AI connection merge in _build_connections."""

    def test_ai_connections_merged(self, db):
        """AI-discovered connections appear in connection list."""
        author = Author(name="EBB", birth_year=1806, death_year=1861)
        other = Author(name="Robert Browning", birth_year=1812, death_year=1889)
        db.add_all([author, other])
        db.flush()

        profile = EntityProfile(
            entity_type="author",
            entity_id=author.id,
            bio_summary="A poet",
            ai_connections=[
                {
                    "target_type": "author", "target_id": other.id,
                    "target_name": "Robert Browning", "relationship": "family",
                    "sub_type": "marriage", "summary": "Married in 1846",
                    "confidence": "confirmed",
                }
            ],
        )
        db.add(profile)
        db.commit()

        graph = _empty_graph_with_nodes(author, other)
        connections = _build_connections(db, "author", author.id, profile, graph)

        ai_conns = [c for c in connections if c.connection_type == "family"]
        assert len(ai_conns) == 1
        assert ai_conns[0].entity.name == "Robert Browning"

    def test_ai_connections_get_key_priority(self, db):
        """Personal connections prioritized for key connection slots."""
        # Create author with many publisher connections AND one AI connection
        # Assert the AI connection gets is_key=True first
        pass  # Implement with setup similar to above
```

**Step 3: Run tests to verify they fail**

```bash
poetry run pytest backend/tests/test_entity_profile.py::TestPipelineAIConnections -v
poetry run pytest backend/tests/test_entity_profile.py::TestBuildConnectionsAI -v
```

**Step 4: Implement pipeline changes in generate_and_cache_profile()**

In `backend/app/services/entity_profile.py`, after line 517 (after `valid_entity_ids` is built), add:

```python
    # Discover AI connections — pass ALL collection entities, not just graph-connected
    all_collection_entities = [
        {
            "type": n.type.value if hasattr(n.type, "value") else str(n.type),
            "id": n.entity_id,
            "name": n.name,
            "dates": _format_entity_dates(n),
        }
        for n in graph.nodes
        if n.id != node_id  # exclude self
    ]
    all_collection_ids = {n.id for n in graph.nodes}

    ai_connections = generate_ai_connections(
        name=entity.name,
        entity_type=entity_type,
        entity_id=entity_id,
        birth_year=getattr(entity, "birth_year", None),
        death_year=getattr(entity, "death_year", None),
        book_titles=book_titles,
        collection_entities=all_collection_entities,
        collection_entity_ids=all_collection_ids,
        config=config,
    )

    # Add discovered connections to the valid_entity_ids set and prompt connections
    for conn in ai_connections:
        target_key = f"{conn['target_type']}:{conn['target_id']}"
        valid_entity_ids.add(target_key)
```

In the upsert section (around line 631+), add `ai_connections`:

```python
    if existing:
        # ... existing fields ...
        existing.ai_connections = ai_connections or None
    else:
        profile = EntityProfile(
            # ... existing fields ...
            ai_connections=ai_connections or None,
        )
```

Add import at top: `from app.services.ai_profile_generator import generate_ai_connections`

**Step 5: Implement _build_connections merge**

In `backend/app/services/entity_profile.py`, after line 411 (after main connections loop, before sort), add:

```python
    # Merge AI-discovered connections
    if profile and profile.ai_connections:
        node_map = {n.id: n for n in graph.nodes} if graph else {}
        for ai_conn in profile.ai_connections:
            target_key = f"{ai_conn['target_type']}:{ai_conn['target_id']}"
            # Skip if already in connections (graph-based edge exists)
            if any(
                f"{c.entity.type.value}:{c.entity.id}" == target_key
                for c in connections
            ):
                continue

            target_node = node_map.get(target_key)
            entity_data = ProfileEntity(
                id=ai_conn["target_id"],
                type=EntityType(ai_conn["target_type"]),
                name=ai_conn["target_name"],
                birth_year=target_node.birth_year if target_node else None,
                death_year=target_node.death_year if target_node else None,
                founded_year=target_node.founded_year if target_node else None,
                closed_year=target_node.closed_year if target_node else None,
                era=_era_str(target_node) if target_node else None,
                tier=target_node.tier if target_node else None,
            )
            connections.append(
                ProfileConnection(
                    entity=entity_data,
                    connection_type=ai_conn["relationship"],
                    strength=6,  # Default strength for AI-discovered
                    shared_book_count=0,
                    shared_books=[],
                    narrative=ai_conn.get("summary"),
                    narrative_trigger="social_circle",
                    is_key=False,
                    relationship_story=None,
                )
            )
```

Update key connection priority (around line 416): prioritize AI personal connections for first slots:

```python
    # Mark top 5 as key connections (prefer personal > diverse type > strength)
    PERSONAL_TYPES = {"family", "friendship", "influence", "collaboration", "scandal"}
    seen_types: set[str] = set()
    key_count = 0

    # First pass: personal connections get priority slots
    for conn in connections:
        if key_count >= 2:
            break
        if conn.connection_type in PERSONAL_TYPES:
            conn.is_key = True
            seen_types.add(conn.connection_type)
            key_count += 1

    # Second pass: diverse types for next slots
    for conn in connections:
        if key_count >= 4:
            break
        if not conn.is_key and conn.connection_type not in seen_types:
            conn.is_key = True
            seen_types.add(conn.connection_type)
            key_count += 1

    # Third pass: fill remaining by strength
    for conn in connections:
        if key_count >= 5:
            break
        if not conn.is_key:
            conn.is_key = True
            key_count += 1
```

**Step 6: Run tests**

```bash
poetry run pytest backend/tests/test_entity_profile.py -v -k "AIConnect or Pipeline"
```

**Step 7: Lint and commit**

```bash
poetry run ruff check backend/
poetry run ruff format --check backend/
git add backend/app/services/entity_profile.py backend/tests/test_entity_profile.py
git commit -m "feat: integrate AI discovery into profile pipeline + merge (#1806)"
```

---

## Task 4: Graph Builder — Merge AI Edges (#1807)

**Files:**
- Modify: `backend/app/services/social_circles.py:310-337` (after binder edges, before metadata)
- Test: `backend/tests/test_social_circles.py` (create if needed)

**Step 1: Write failing test**

Create or add to `backend/tests/test_social_circles.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from app.schemas.social_circles import ConnectionType


class TestAIEdgeMerge:
    """Tests for AI-discovered edge merge in build_social_circles_graph."""

    def test_ai_edges_appear_in_graph(self, db):
        """AI connections from entity_profiles appear as graph edges."""
        # Setup: create two authors with no shared publishers
        # Add AI connections to one author's profile
        # Call build_social_circles_graph
        # Assert AI edges present with correct type
        pass  # Implement with DB fixtures

    def test_ai_edge_dedup(self, db):
        """Bidirectional AI connections deduplicated via canonical ID."""
        pass  # Both EBB→RB and RB→EBB should produce one edge

    def test_empty_ai_connections_handled(self, db):
        """Profiles with null/empty ai_connections cause no errors."""
        pass

    def test_ai_edge_id_includes_relationship(self):
        """Edge IDs include relationship type for disambiguation."""
        # e:author:31:author:227:family != e:author:31:author:227:collaboration
        pass
```

**Step 2: Run tests to verify they fail**

```bash
poetry run pytest backend/tests/test_social_circles.py::TestAIEdgeMerge -v
```

**Step 3: Implement AI edge merge**

In `backend/app/services/social_circles.py`, after line 310 (after binder edge loop), before line 312 (date range):

```python
    # Merge AI-discovered connections from entity_profiles
    from app.models.entity_profile import EntityProfile

    ai_profiles = (
        db.query(EntityProfile)
        .filter(EntityProfile.ai_connections.isnot(None))
        .all()
    )
    for profile in ai_profiles:
        source_key = f"{profile.entity_type}:{profile.entity_id}"
        if source_key not in nodes:
            continue
        for conn in (profile.ai_connections or []):
            target_key = f"{conn['target_type']}:{conn['target_id']}"
            if target_key not in nodes:
                continue
            # Canonical edge ID: lower key first + relationship type
            keys = sorted([source_key, target_key])
            rel = conn.get("relationship", "unknown")
            edge_id = f"e:{keys[0]}:{keys[1]}:{rel}"
            if edge_id in edges:
                continue
            edges[edge_id] = SocialCircleEdge(
                id=edge_id,
                source=keys[0],
                target=keys[1],
                type=ConnectionType(rel),
                strength=6,
                evidence=conn.get("summary"),
                shared_book_ids=None,
            )
```

**Step 4: Run tests**

```bash
poetry run pytest backend/tests/test_social_circles.py -v
```

**Step 5: Lint and commit**

```bash
poetry run ruff check backend/
git add backend/app/services/social_circles.py backend/tests/test_social_circles.py
git commit -m "feat: merge AI edges into social circles graph (#1807)"
```

---

## Task 5: Frontend Edge Styling + Click-to-Highlight (#1808)

**Files:**
- Modify: `frontend/src/views/SocialCirclesView.vue`
- Modify: `frontend/src/components/entityprofile/EgoNetwork.vue:110-118`
- Modify: `frontend/src/components/socialcircles/ConnectionTooltip.vue:19-32`
- Modify: `frontend/src/components/socialcircles/EdgeSidebar.vue:68-76`

**Step 1: Update ConnectionTooltip labels**

In `frontend/src/components/socialcircles/ConnectionTooltip.vue`, expand CONNECTION_LABELS (line 19):

```typescript
const CONNECTION_LABELS: Record<ConnectionType, { label: string; description: string }> = {
  publisher: { label: "Publisher Relationship", description: "Author was published by this publisher" },
  shared_publisher: { label: "Shared Publisher", description: "Both authors published by the same publisher" },
  binder: { label: "Same Bindery", description: "Books bound at the same bindery" },
  family: { label: "Family", description: "Family relationship (marriage, siblings, etc.)" },
  friendship: { label: "Friendship", description: "Personal friends and social connections" },
  influence: { label: "Influence", description: "Mentorship or intellectual influence" },
  collaboration: { label: "Collaboration", description: "Literary partnership or co-authorship" },
  scandal: { label: "Scandal", description: "Affairs, feuds, or public controversies" },
};
```

**Step 2: Update EdgeSidebar connection labels**

In `frontend/src/components/socialcircles/EdgeSidebar.vue`, expand labels (around line 70):

```typescript
const labels: Record<ConnectionType, string> = {
  publisher: "Published together",
  shared_publisher: "Shared Publisher",
  binder: "Bound works",
  family: "Family",
  friendship: "Friends",
  influence: "Influence",
  collaboration: "Collaborators",
  scandal: "Scandal",
};
```

**Step 3: Add click-to-highlight to SocialCirclesView**

This requires adding a tap handler on nodes that dims non-connected elements. Find the Cytoscape `cy.on('tap', 'node', ...)` handler and add highlight logic:

```typescript
// In the Cytoscape setup section of SocialCirclesView or NetworkGraph
function handleNodeHighlight(nodeId: string) {
  if (!cy) return;
  const node = cy.getElementById(nodeId);
  const connected = node.connectedEdges().connectedNodes();
  const connectedEdges = node.connectedEdges();

  // Dim everything
  cy.elements().style({ opacity: 0.15 });
  // Highlight connected
  node.style({ opacity: 1 });
  connected.style({ opacity: 1 });
  connectedEdges.style({ opacity: 1 });
}

function resetHighlight() {
  if (!cy) return;
  cy.elements().style({ opacity: '' }); // Remove override, revert to stylesheet
}
```

Wire into tap events:
- `cy.on('tap', 'node', (e) => handleNodeHighlight(e.target.id()))`
- `cy.on('tap', (e) => { if (e.target === cy) resetHighlight() })`

**Step 4: Validate**

```bash
npm run --prefix frontend lint
npm run --prefix frontend type-check
```

**Step 5: Commit**

```bash
git add frontend/src/views/SocialCirclesView.vue \
  frontend/src/components/entityprofile/EgoNetwork.vue \
  frontend/src/components/socialcircles/ConnectionTooltip.vue \
  frontend/src/components/socialcircles/EdgeSidebar.vue
git commit -m "feat: edge styling by connection type + click-to-highlight (#1808)"
```

---

## Task 6: Connection Badges + Confidence Styling (#1809)

**Files:**
- Modify: `frontend/src/components/entityprofile/KeyConnections.vue`
- Modify: `frontend/src/components/entityprofile/ConnectionGossipPanel.vue`

**Step 1: Add sub_type badge to KeyConnections**

In `KeyConnections.vue`, replace or enhance the connection type display (around line 45) to show `sub_type` when available (AI connections) or fall back to `connection_type`:

```vue
<span class="connection-badge" :class="badgeClass(conn)">
  {{ displayType(conn) }}
</span>
```

```typescript
function displayType(conn: ProfileConnection): string {
  // AI connections have sub_type from ai_connections data
  if (conn.sub_type) return conn.sub_type.toUpperCase();
  // Fall back to connection_type for graph-based connections
  const labels: Record<string, string> = {
    publisher: "PUBLISHER",
    shared_publisher: "SHARED PUBLISHER",
    binder: "BINDER",
    family: "FAMILY",
    friendship: "FRIEND",
    influence: "INFLUENCE",
    collaboration: "COLLABORATOR",
    scandal: "SCANDAL",
  };
  return labels[conn.connection_type] || conn.connection_type.toUpperCase();
}
```

Note: `sub_type` will need to be added to the `ProfileConnection` response schema. In `backend/app/schemas/entity_profile.py`, add `sub_type: str | None = None` to ProfileConnection. In `_build_connections`, populate it from `ai_conn.get("sub_type")` for AI connections.

**Step 2: Add confidence styling to ConnectionGossipPanel**

In `ConnectionGossipPanel.vue`, add styling for "rumored" confidence:

```vue
<p :class="{ 'rumored-text': conn.confidence === 'rumored' }">
  {{ conn.summary }}
  <span v-if="conn.confidence === 'rumored'" class="rumored-badge">Rumored</span>
</p>
```

```css
.rumored-text {
  font-style: italic;
}
.rumored-badge {
  display: inline-block;
  font-size: 0.625rem;
  padding: 0.0625rem 0.25rem;
  border-radius: 3px;
  background-color: var(--color-victorian-paper-cream, #f5f2e9);
  color: var(--color-victorian-ink-muted, #5c5c58);
  margin-left: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
```

Note: `confidence` will also need to be added to ProfileConnection response schema.

**Step 3: Backend schema additions**

In `backend/app/schemas/entity_profile.py`, add to ProfileConnection:

```python
class ProfileConnection(BaseModel):
    # ... existing fields ...
    sub_type: str | None = None
    confidence: str | None = None
    is_ai_discovered: bool = False
```

In `_build_connections` AI merge section, populate these fields.

**Step 4: Validate**

```bash
npm run --prefix frontend lint
npm run --prefix frontend type-check
poetry run ruff check backend/
```

**Step 5: Commit**

```bash
git add frontend/src/components/entityprofile/KeyConnections.vue \
  frontend/src/components/entityprofile/ConnectionGossipPanel.vue \
  backend/app/schemas/entity_profile.py backend/app/services/entity_profile.py
git commit -m "feat: sub_type badges + confidence styling for AI connections (#1809)"
```

---

## Task 7: E2E Tests (#1810)

**Files:**
- Modify: `frontend/e2e/entity-profile.spec.ts` (add AI connection tests)
- Modify: `frontend/e2e/social-circles.spec.ts` (add edge styling tests)

**Step 1: Add entity profile E2E tests**

```typescript
test("AI-discovered connections visible with badges", async ({ page }) => {
  // Navigate to an entity with AI connections (requires seeded data)
  // Assert: connection card shows sub_type badge (e.g., "MARRIAGE")
  // Assert: rumored connections show italic + badge
});
```

**Step 2: Add social circles E2E tests**

```typescript
test("personal connection edges have blue color", async ({ page }) => {
  await page.goto("/socialcircles");
  // Wait for graph to render
  // Check that edges with AI connection types render with correct colors
});

test("click-to-highlight dims non-connected nodes", async ({ page }) => {
  await page.goto("/socialcircles");
  // Click a node
  // Assert non-connected elements have reduced opacity
  // Click background to reset
});
```

**Step 3: Run E2E tests**

```bash
AWS_PROFILE=bmx-staging npx --prefix frontend playwright test
```

**Step 4: Commit**

```bash
git add frontend/e2e/
git commit -m "test: E2E tests for AI-discovered connections (#1810)"
```

---

## Dependency Graph

```
Task 1 (Foundation) ─────────────────────────────────────────────┐
  ├── Task 2 (AI Discovery) ──┐                                  │
  │                            ├── Task 3 (Pipeline) ──┐         │
  ├── Task 4 (Graph Builder) ──┘                       │         │
  │                                                     ├── Task 7 (E2E)
  ├── Task 5 (Edge Styling) ──────────────────────────┘         │
  │                                                              │
  └── Task 6 (Badges/Confidence) ───────────────────────────────┘
```

**Parallelism:** After Task 1, Tasks 2+4+5+6 can run in parallel worktrees. Task 3 waits for Task 2. Task 7 waits for all.

---

## Verification

After all tasks merged:

```bash
# Backend
poetry run ruff check backend/
poetry run ruff format --check backend/
poetry run pytest backend/tests/ -v

# Frontend
npm run --prefix frontend lint
npm run --prefix frontend format
npm run --prefix frontend type-check

# E2E
AWS_PROFILE=bmx-staging npx --prefix frontend playwright test
```
