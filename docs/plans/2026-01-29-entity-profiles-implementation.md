# Entity Profiles Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build dedicated profile pages for authors, publishers, and binders at `/entity/:type/:id` with AI-generated biographical gossip and narrative connections.

**Architecture:** Full-page Vue views backed by a FastAPI endpoint that assembles entity data, connections, books, and AI-generated content from a cache table. AI content generated lazily on first view via Claude API (configurable model). Two-tier gossip: personal stories on entities, relationship stories on connections.

**Tech Stack:** Vue 3 + TypeScript + Cytoscape.js (frontend), FastAPI + SQLAlchemy + Alembic (backend), Claude API via Anthropic SDK (AI enrichment), Vitest (frontend tests), pytest (backend tests)

**GitHub Issues:** #1542 (epic), #1543-#1547 (phase issues)

**Design Doc:** `docs/plans/2026-01-29-entity-profiles-design.md`

**Seed Data:** `docs/plans/2026-01-29-entity-profiles-seed-data.md`

---

## Phase 1: Core Profile Page (No AI)

### Task 1: Database Migration — entity_profiles table

**Files:**
- Create: `backend/app/models/entity_profile.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/ep001_add_entity_profiles_table.py`

**Step 1: Create the SQLAlchemy model**

Create `backend/app/models/entity_profile.py`:

```python
"""Entity profile model — caches AI-generated biographical content."""

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EntityProfile(Base):
    """Cached AI-generated profile for an entity (author, publisher, binder)."""

    __tablename__ = "entity_profiles"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "owner_id", name="uq_entity_profile"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    bio_summary: Mapped[str | None] = mapped_column(Text)
    personal_stories: Mapped[dict | None] = mapped_column(JSONB, default=list)
    connection_narratives: Mapped[dict | None] = mapped_column(JSONB)
    generated_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    model_version: Mapped[str | None] = mapped_column(String(100))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
```

**Step 2: Register model in `__init__.py`**

Add to `backend/app/models/__init__.py`:

```python
from app.models.entity_profile import EntityProfile
```

And add `"EntityProfile"` to the `__all__` list.

**Step 3: Create migration**

Run: `cd /Users/mark/projects/bluemoxon/backend && poetry run alembic revision --autogenerate -m "add_entity_profiles_table"`

Review the generated migration. It should create the `entity_profiles` table with all columns, the unique constraint, and an index on `(entity_type, entity_id, owner_id)`.

If the index is not auto-generated, add manually:

```python
op.create_index(
    "idx_entity_profiles_lookup",
    "entity_profiles",
    ["entity_type", "entity_id", "owner_id"],
)
```

**Step 4: Run migration locally**

Run: `cd /Users/mark/projects/bluemoxon/backend && poetry run alembic upgrade head`

Expected: Migration applies cleanly.

**Step 5: Commit**

```
git add backend/app/models/entity_profile.py backend/app/models/__init__.py backend/alembic/versions/ep001_*.py
git commit -m "feat(entity-profiles): Add entity_profiles table and model (#1543)"
```

---

### Task 2: Backend Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/entity_profile.py`

**Step 1: Create schema file**

Create `backend/app/schemas/entity_profile.py`:

```python
"""Pydantic schemas for entity profile endpoints."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    author = "author"
    publisher = "publisher"
    binder = "binder"


class BiographicalFact(BaseModel):
    """A single biographical fact / gossip item."""

    text: str = Field(..., description="The story (1-2 sentences)")
    year: int | None = Field(None, description="Year the event occurred")
    significance: str = Field(..., description="revelation, notable, or context")
    tone: str = Field(..., description="dramatic, scandalous, tragic, intellectual, or triumphant")
    display_in: list[str] = Field(default_factory=list, description="hero-bio, timeline, hover-tooltip")


class RelationshipNarrative(BaseModel):
    """Full relationship story for a high-impact connection."""

    summary: str = Field(..., description="One-line summary for card display")
    details: list[BiographicalFact] = Field(default_factory=list, description="Story facts")
    narrative_style: str = Field("prose-paragraph", description="prose-paragraph, bullet-facts, or timeline-events")


class ProfileEntity(BaseModel):
    """Entity summary in profile response."""

    id: int
    type: EntityType
    name: str
    birth_year: int | None = None
    death_year: int | None = None
    founded_year: int | None = None
    closed_year: int | None = None
    era: str | None = None
    tier: str | None = None


class ProfileData(BaseModel):
    """AI-generated profile content."""

    bio_summary: str | None = None
    personal_stories: list[BiographicalFact] = Field(default_factory=list)
    is_stale: bool = False
    generated_at: datetime | None = None
    model_version: str | None = None


class ProfileConnection(BaseModel):
    """A connection to another entity."""

    entity: ProfileEntity
    connection_type: str
    strength: int
    shared_book_count: int
    shared_books: list[dict] = Field(default_factory=list)
    narrative: str | None = None
    narrative_trigger: str | None = None
    is_key: bool = False
    relationship_story: RelationshipNarrative | None = None


class ProfileBook(BaseModel):
    """A book in the entity's collection."""

    id: int
    title: str
    year: int | None = None
    condition: str | None = None
    edition: str | None = None


class ProfileStats(BaseModel):
    """Collection statistics for this entity."""

    total_books: int = 0
    total_estimated_value: float | None = None
    first_editions: int = 0
    date_range: list[int] = Field(default_factory=list)


class EntityProfileResponse(BaseModel):
    """Full entity profile response."""

    entity: ProfileEntity
    profile: ProfileData
    connections: list[ProfileConnection] = Field(default_factory=list)
    books: list[ProfileBook] = Field(default_factory=list)
    stats: ProfileStats
```

**Step 2: Commit**

```
git add backend/app/schemas/entity_profile.py
git commit -m "feat(entity-profiles): Add Pydantic schemas for profile endpoint (#1544)"
```

---

### Task 3: Backend Service Layer

**Files:**
- Create: `backend/app/services/entity_profile.py`

**Step 1: Create service**

Create `backend/app/services/entity_profile.py`:

```python
"""Entity profile service — assembles profile data from DB."""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.author import Author
from app.models.binder import Binder
from app.models.book import Book
from app.models.entity_profile import EntityProfile
from app.models.publisher import Publisher
from app.schemas.entity_profile import (
    EntityProfileResponse,
    EntityType,
    ProfileBook,
    ProfileConnection,
    ProfileData,
    ProfileEntity,
    ProfileStats,
)
from app.services.social_circles import build_social_circles_graph


# Status values for owned books
OWNED_STATUSES = ("ON_HAND", "IN_TRANSIT")


def _get_entity(db: Session, entity_type: str, entity_id: int):
    """Fetch entity from appropriate table."""
    model_map = {
        "author": Author,
        "publisher": Publisher,
        "binder": Binder,
    }
    model = model_map.get(entity_type)
    if not model:
        return None
    return db.query(model).filter(model.id == entity_id).first()


def _get_entity_books(db: Session, entity_type: str, entity_id: int) -> list[Book]:
    """Fetch owned books for an entity."""
    filters = [Book.status.in_(OWNED_STATUSES)]
    if entity_type == "author":
        filters.append(Book.author_id == entity_id)
    elif entity_type == "publisher":
        filters.append(Book.publisher_id == entity_id)
    elif entity_type == "binder":
        filters.append(Book.binder_id == entity_id)
    return db.query(Book).filter(*filters).order_by(Book.year_start.asc()).all()


def _build_profile_entity(entity, entity_type: str) -> ProfileEntity:
    """Convert DB entity to ProfileEntity schema."""
    return ProfileEntity(
        id=entity.id,
        type=EntityType(entity_type),
        name=entity.name,
        birth_year=getattr(entity, "birth_year", None),
        death_year=getattr(entity, "death_year", None),
        founded_year=getattr(entity, "founded_year", None),
        closed_year=getattr(entity, "closed_year", None),
        era=getattr(entity, "era", None),
        tier=getattr(entity, "tier", None),
    )


def _build_profile_books(books: list[Book]) -> list[ProfileBook]:
    """Convert Book models to ProfileBook schemas."""
    return [
        ProfileBook(
            id=book.id,
            title=book.title,
            year=book.year_start,
            condition=getattr(book, "condition_grade", None),
            edition=book.edition,
        )
        for book in books
    ]


def _build_stats(books: list[Book]) -> ProfileStats:
    """Calculate collection stats from books."""
    if not books:
        return ProfileStats()

    years = [b.year_start for b in books if b.year_start]
    values = [float(b.fmv_mid) for b in books if getattr(b, "fmv_mid", None)]

    return ProfileStats(
        total_books=len(books),
        total_estimated_value=sum(values) if values else None,
        first_editions=sum(
            1 for b in books
            if b.edition and "first" in b.edition.lower()
        ),
        date_range=[min(years), max(years)] if years else [],
    )


def _check_staleness(db: Session, profile: EntityProfile, entity_type: str, entity_id: int) -> bool:
    """Check if profile is stale by comparing against book updates."""
    if not profile or not profile.generated_at:
        return False

    filters = [Book.status.in_(OWNED_STATUSES)]
    if entity_type == "author":
        filters.append(Book.author_id == entity_id)
    elif entity_type == "publisher":
        filters.append(Book.publisher_id == entity_id)
    elif entity_type == "binder":
        filters.append(Book.binder_id == entity_id)

    latest_update = db.query(func.max(Book.updated_at)).filter(*filters).scalar()
    if latest_update and latest_update > profile.generated_at:
        return True
    return False


def _build_connections(
    db: Session,
    entity_type: str,
    entity_id: int,
    profile: EntityProfile | None,
) -> list[ProfileConnection]:
    """Build connection list from social circles graph."""
    node_id = f"{entity_type}:{entity_id}"
    graph = build_social_circles_graph(db)

    # Find edges connected to this entity
    connected_edges = [
        e for e in graph.edges
        if e.source == node_id or e.target == node_id
    ]

    # Build node lookup
    node_map = {n.id: n for n in graph.nodes}

    # Get cached narratives
    narratives = {}
    if profile and profile.connection_narratives:
        narratives = profile.connection_narratives

    connections = []
    for edge in connected_edges:
        other_id = edge.target if edge.source == node_id else edge.source
        other_node = node_map.get(other_id)
        if not other_node:
            continue

        narrative_key = f"{node_id}:{other_id}"
        narrative_key_rev = f"{other_id}:{node_id}"

        connections.append(ProfileConnection(
            entity=ProfileEntity(
                id=other_node.entity_id,
                type=EntityType(other_node.type.value if hasattr(other_node.type, "value") else other_node.type),
                name=other_node.name,
                birth_year=other_node.birth_year,
                death_year=other_node.death_year,
                era=other_node.era.value if hasattr(other_node.era, "value") and other_node.era else None,
                tier=other_node.tier,
            ),
            connection_type=edge.type.value if hasattr(edge.type, "value") else edge.type,
            strength=edge.strength,
            shared_book_count=len(edge.shared_book_ids) if edge.shared_book_ids else 0,
            shared_books=[],
            narrative=narratives.get(narrative_key) or narratives.get(narrative_key_rev),
            is_key=False,
        ))

    # Sort by strength descending
    connections.sort(key=lambda c: c.strength, reverse=True)

    # Mark top 5 as key (with type diversity)
    seen_types = set()
    key_count = 0
    for conn in connections:
        if key_count >= 5:
            break
        if conn.connection_type not in seen_types or key_count < 3:
            conn.is_key = True
            seen_types.add(conn.connection_type)
            key_count += 1

    return connections


def get_entity_profile(
    db: Session,
    entity_type: str,
    entity_id: int,
    owner_id: int,
) -> EntityProfileResponse | None:
    """Assemble full entity profile response."""
    entity = _get_entity(db, entity_type, entity_id)
    if not entity:
        return None

    books = _get_entity_books(db, entity_type, entity_id)

    # Fetch cached profile
    cached = (
        db.query(EntityProfile)
        .filter(
            EntityProfile.entity_type == entity_type,
            EntityProfile.entity_id == entity_id,
            EntityProfile.owner_id == owner_id,
        )
        .first()
    )

    is_stale = _check_staleness(db, cached, entity_type, entity_id)

    profile_data = ProfileData(
        bio_summary=cached.bio_summary if cached else None,
        personal_stories=cached.personal_stories if cached and cached.personal_stories else [],
        is_stale=is_stale,
        generated_at=cached.generated_at if cached else None,
        model_version=cached.model_version if cached else None,
    )

    connections = _build_connections(db, entity_type, entity_id, cached)

    return EntityProfileResponse(
        entity=_build_profile_entity(entity, entity_type),
        profile=profile_data,
        connections=connections,
        books=_build_profile_books(books),
        stats=_build_stats(books),
    )
```

**Step 2: Commit**

```
git add backend/app/services/entity_profile.py
git commit -m "feat(entity-profiles): Add profile service layer (#1544)"
```

---

### Task 4: Backend API Route

**Files:**
- Create: `backend/app/api/v1/entity_profile.py`
- Modify: `backend/app/api/v1/__init__.py`

**Step 1: Create route handler**

Create `backend/app/api/v1/entity_profile.py`:

```python
"""Entity profile API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from app.auth import require_viewer
from app.db import get_db
from app.schemas.entity_profile import EntityProfileResponse, EntityType
from app.services.entity_profile import get_entity_profile

router = APIRouter()


@router.get(
    "/{entity_type}/{entity_id}/profile",
    response_model=EntityProfileResponse,
    summary="Get entity profile",
    description="Returns full profile for an entity including bio, connections, books, and stats.",
)
def get_profile(
    entity_type: EntityType = Path(..., description="Entity type: author, publisher, or binder"),
    entity_id: int = Path(..., ge=1, description="Entity database ID"),
    db: Session = Depends(get_db),
    user_info=Depends(require_viewer),
) -> EntityProfileResponse:
    """Get entity profile with AI-generated content if available."""
    result = get_entity_profile(db, entity_type.value, entity_id, user_info["user_id"])
    if not result:
        raise HTTPException(status_code=404, detail=f"Entity {entity_type.value}:{entity_id} not found")
    return result
```

**Step 2: Register route in `__init__.py`**

Add to `backend/app/api/v1/__init__.py`:

```python
from app.api.v1 import entity_profile
```

Add to the router includes:

```python
router.include_router(entity_profile.router, prefix="/entity", tags=["entity-profiles"])
```

**Step 3: Run backend tests**

Run: `cd /Users/mark/projects/bluemoxon/backend && poetry run pytest tests/ -x -q`

Expected: Existing tests pass. No new test failures.

**Step 4: Commit**

```
git add backend/app/api/v1/entity_profile.py backend/app/api/v1/__init__.py
git commit -m "feat(entity-profiles): Add GET /entity/:type/:id/profile endpoint (#1544)"
```

---

### Task 5: Backend Tests

**Files:**
- Create: `backend/tests/test_entity_profile.py`

**Step 1: Create test file**

Create `backend/tests/test_entity_profile.py`:

```python
"""Tests for entity profile endpoint."""

import pytest
from app.models import Author, Book, Publisher, Binder


class TestEntityProfileEndpoint:
    """Tests for GET /api/v1/entity/:type/:id/profile."""

    def test_author_profile_returns_200(self, client, db):
        """Author profile returns entity data."""
        author = Author(name="Elizabeth Barrett Browning", birth_year=1806, death_year=1861, tier="TIER_1")
        db.add(author)
        db.flush()

        book = Book(
            title="Aurora Leigh",
            author_id=author.id,
            status="ON_HAND",
            year_start=1877,
            edition="American reprint",
        )
        db.add(book)
        db.commit()

        response = client.get(f"/api/v1/entity/author/{author.id}/profile")
        assert response.status_code == 200

        data = response.json()
        assert data["entity"]["name"] == "Elizabeth Barrett Browning"
        assert data["entity"]["type"] == "author"
        assert data["entity"]["birth_year"] == 1806
        assert data["stats"]["total_books"] == 1

    def test_publisher_profile_returns_200(self, client, db):
        """Publisher profile returns entity data."""
        publisher = Publisher(name="Smith, Elder & Co.", tier="TIER_1")
        db.add(publisher)
        db.commit()

        response = client.get(f"/api/v1/entity/publisher/{publisher.id}/profile")
        assert response.status_code == 200

        data = response.json()
        assert data["entity"]["name"] == "Smith, Elder & Co."
        assert data["entity"]["type"] == "publisher"

    def test_binder_profile_returns_200(self, client, db):
        """Binder profile returns entity data."""
        binder = Binder(name="Riviere & Son", tier="TIER_1")
        db.add(binder)
        db.commit()

        response = client.get(f"/api/v1/entity/binder/{binder.id}/profile")
        assert response.status_code == 200

        data = response.json()
        assert data["entity"]["name"] == "Riviere & Son"

    def test_nonexistent_entity_returns_404(self, client, db):
        """Requesting missing entity returns 404."""
        response = client.get("/api/v1/entity/author/99999/profile")
        assert response.status_code == 404

    def test_invalid_entity_type_returns_422(self, client, db):
        """Invalid entity type returns validation error."""
        response = client.get("/api/v1/entity/invalid/1/profile")
        assert response.status_code == 422

    def test_profile_includes_books(self, client, db):
        """Profile includes the entity's books."""
        author = Author(name="Robert Browning", birth_year=1812, death_year=1889)
        db.add(author)
        db.flush()

        book1 = Book(title="Ring and the Book", author_id=author.id, status="ON_HAND", year_start=1868, edition="First Edition")
        book2 = Book(title="Poetical Works", author_id=author.id, status="ON_HAND", year_start=1898)
        db.add_all([book1, book2])
        db.commit()

        response = client.get(f"/api/v1/entity/author/{author.id}/profile")
        data = response.json()

        assert data["stats"]["total_books"] == 2
        assert len(data["books"]) == 2
        titles = [b["title"] for b in data["books"]]
        assert "Ring and the Book" in titles
        assert "Poetical Works" in titles

    def test_profile_excludes_removed_books(self, client, db):
        """Profile only includes ON_HAND and IN_TRANSIT books."""
        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        book_owned = Book(title="Owned Book", author_id=author.id, status="ON_HAND")
        book_sold = Book(title="Sold Book", author_id=author.id, status="SOLD")
        db.add_all([book_owned, book_sold])
        db.commit()

        response = client.get(f"/api/v1/entity/author/{author.id}/profile")
        data = response.json()

        assert data["stats"]["total_books"] == 1
        assert data["books"][0]["title"] == "Owned Book"

    def test_profile_without_ai_content(self, client, db):
        """Profile works without cached AI content."""
        author = Author(name="Obscure Author")
        db.add(author)
        db.commit()

        response = client.get(f"/api/v1/entity/author/{author.id}/profile")
        data = response.json()

        assert data["profile"]["bio_summary"] is None
        assert data["profile"]["personal_stories"] == []
        assert data["profile"]["is_stale"] is False

    def test_stats_calculation(self, client, db):
        """Stats are correctly calculated from books."""
        author = Author(name="Stats Author")
        db.add(author)
        db.flush()

        book1 = Book(title="Book 1", author_id=author.id, status="ON_HAND", year_start=1850, edition="First Edition")
        book2 = Book(title="Book 2", author_id=author.id, status="ON_HAND", year_start=1870)
        db.add_all([book1, book2])
        db.commit()

        response = client.get(f"/api/v1/entity/author/{author.id}/profile")
        data = response.json()

        assert data["stats"]["total_books"] == 2
        assert data["stats"]["first_editions"] == 1
        assert data["stats"]["date_range"] == [1850, 1870]

    def test_requires_authentication(self, unauthenticated_client, db):
        """Endpoint requires authentication."""
        response = unauthenticated_client.get("/api/v1/entity/author/1/profile")
        assert response.status_code == 401
```

**Step 2: Run tests**

Run: `cd /Users/mark/projects/bluemoxon/backend && poetry run pytest tests/test_entity_profile.py -v`

Expected: All tests pass.

**Step 3: Commit**

```
git add backend/tests/test_entity_profile.py
git commit -m "test(entity-profiles): Add backend endpoint tests (#1544)"
```

---

### Task 6: Frontend Types

**Files:**
- Create: `frontend/src/types/entityProfile.ts`

**Step 1: Create types file**

Create `frontend/src/types/entityProfile.ts`:

```typescript
/**
 * Entity Profile types.
 * Maps to backend EntityProfileResponse schema.
 */

import type { NodeType, Era, Tier } from "@/types/socialCircles";

// === Gossip Types ===

export type Significance = "revelation" | "notable" | "context";
export type Tone = "dramatic" | "scandalous" | "tragic" | "intellectual" | "triumphant";
export type DisplayLocation = "hero-bio" | "timeline" | "hover-tooltip" | "connection-detail";
export type NarrativeStyle = "prose-paragraph" | "bullet-facts" | "timeline-events";
export type NarrativeTrigger = "cross_era_bridge" | "social_circle" | "hub_figure" | "influence_chain" | null;

export interface BiographicalFact {
  text: string;
  year?: number;
  significance: Significance;
  tone: Tone;
  display_in: DisplayLocation[];
}

export interface RelationshipNarrative {
  summary: string;
  details: BiographicalFact[];
  narrative_style: NarrativeStyle;
}

// === Profile Response Types ===

export interface ProfileEntity {
  id: number;
  type: NodeType;
  name: string;
  birth_year?: number;
  death_year?: number;
  founded_year?: number;
  closed_year?: number;
  era?: string;
  tier?: Tier;
}

export interface ProfileData {
  bio_summary: string | null;
  personal_stories: BiographicalFact[];
  is_stale: boolean;
  generated_at: string | null;
  model_version: string | null;
}

export interface ProfileConnection {
  entity: ProfileEntity;
  connection_type: string;
  strength: number;
  shared_book_count: number;
  shared_books: Array<{ id: number; title: string; year?: number }>;
  narrative: string | null;
  narrative_trigger: NarrativeTrigger;
  is_key: boolean;
  relationship_story: RelationshipNarrative | null;
}

export interface ProfileBook {
  id: number;
  title: string;
  year?: number;
  condition?: string;
  edition?: string;
}

export interface ProfileStats {
  total_books: number;
  total_estimated_value: number | null;
  first_editions: number;
  date_range: number[];
}

export interface EntityProfileResponse {
  entity: ProfileEntity;
  profile: ProfileData;
  connections: ProfileConnection[];
  books: ProfileBook[];
  stats: ProfileStats;
}
```

**Step 2: Commit**

```
git add frontend/src/types/entityProfile.ts
git commit -m "feat(entity-profiles): Add frontend TypeScript types (#1545)"
```

---

### Task 7: Frontend Composable — useEntityProfile

**Files:**
- Create: `frontend/src/composables/entityprofile/useEntityProfile.ts`
- Create: `frontend/src/composables/entityprofile/index.ts`

**Step 1: Create the composable**

Create `frontend/src/composables/entityprofile/useEntityProfile.ts`:

```typescript
/**
 * Main data fetcher and orchestrator for entity profiles.
 */

import { computed, ref, shallowRef } from "vue";
import { useAuthStore } from "@/stores/auth";
import type { EntityProfileResponse } from "@/types/entityProfile";

export type LoadingState = "idle" | "loading" | "loaded" | "error";

export function useEntityProfile() {
  const profileData = shallowRef<EntityProfileResponse | null>(null);
  const loadingState = ref<LoadingState>("idle");
  const error = ref<string | null>(null);

  const authStore = useAuthStore();

  const isLoading = computed(() => loadingState.value === "loading");
  const hasError = computed(() => loadingState.value === "error");
  const entity = computed(() => profileData.value?.entity ?? null);
  const profile = computed(() => profileData.value?.profile ?? null);
  const connections = computed(() => profileData.value?.connections ?? []);
  const keyConnections = computed(() => connections.value.filter((c) => c.is_key));
  const otherConnections = computed(() => connections.value.filter((c) => !c.is_key));
  const books = computed(() => profileData.value?.books ?? []);
  const stats = computed(() => profileData.value?.stats ?? null);

  async function fetchProfile(entityType: string, entityId: number | string): Promise<void> {
    loadingState.value = "loading";
    error.value = null;

    try {
      const token = authStore.idToken;
      const baseUrl = import.meta.env.VITE_API_BASE_URL || "";
      const response = await fetch(`${baseUrl}/api/v1/entity/${entityType}/${entityId}/profile`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch profile: ${response.status} ${response.statusText}`);
      }

      profileData.value = await response.json();
      loadingState.value = "loaded";
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Unknown error";
      loadingState.value = "error";
    }
  }

  return {
    profileData,
    loadingState,
    error,
    isLoading,
    hasError,
    entity,
    profile,
    connections,
    keyConnections,
    otherConnections,
    books,
    stats,
    fetchProfile,
  };
}
```

Create `frontend/src/composables/entityprofile/index.ts`:

```typescript
export { useEntityProfile } from "./useEntityProfile";
```

**Step 2: Commit**

```
git add frontend/src/composables/entityprofile/
git commit -m "feat(entity-profiles): Add useEntityProfile composable (#1545)"
```

---

### Task 8: Frontend Route Registration

**Files:**
- Modify: `frontend/src/router/index.ts`

**Step 1: Add entity profile route**

Add before the closing `]` of routes array in `frontend/src/router/index.ts`, after the social-circles route:

```typescript
    {
      path: "/entity/:type/:id",
      name: "entity-profile",
      component: () => import("@/views/EntityProfileView.vue"),
      meta: { requiresAuth: true },
      props: true,
    },
```

**Step 2: Commit**

```
git add frontend/src/router/index.ts
git commit -m "feat(entity-profiles): Register /entity/:type/:id route (#1545)"
```

---

### Task 9: Frontend EntityProfileView + Section Components

**Files:**
- Create: `frontend/src/views/EntityProfileView.vue`
- Create: `frontend/src/components/entityprofile/ProfileHero.vue`
- Create: `frontend/src/components/entityprofile/EntityBooks.vue`
- Create: `frontend/src/components/entityprofile/AllConnections.vue`
- Create: `frontend/src/components/entityprofile/KeyConnections.vue`
- Create: `frontend/src/components/entityprofile/CollectionStats.vue`
- Create: `frontend/src/components/entityprofile/ProfileSkeleton.vue`
- Create: `frontend/src/components/entityprofile/StaleProfileBanner.vue`

**This task is large. Create each file in sequence and commit after all are done.**

**Step 1: Create EntityProfileView.vue**

Create `frontend/src/views/EntityProfileView.vue`:

```vue
<script setup lang="ts">
import { onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import { useEntityProfile } from "@/composables/entityprofile";
import ProfileHero from "@/components/entityprofile/ProfileHero.vue";
import KeyConnections from "@/components/entityprofile/KeyConnections.vue";
import AllConnections from "@/components/entityprofile/AllConnections.vue";
import EntityBooks from "@/components/entityprofile/EntityBooks.vue";
import CollectionStats from "@/components/entityprofile/CollectionStats.vue";
import ProfileSkeleton from "@/components/entityprofile/ProfileSkeleton.vue";
import StaleProfileBanner from "@/components/entityprofile/StaleProfileBanner.vue";

const props = defineProps<{
  type: string;
  id: string;
}>();

const route = useRoute();
const { entity, profile, keyConnections, otherConnections, books, stats, isLoading, hasError, error, fetchProfile } =
  useEntityProfile();

onMounted(() => {
  fetchProfile(props.type, props.id);
});

// Refetch when route params change (navigating between profiles)
watch(
  () => route.params,
  (newParams) => {
    if (newParams.type && newParams.id) {
      fetchProfile(newParams.type as string, newParams.id as string);
    }
  },
);
</script>

<template>
  <div class="entity-profile-view">
    <nav class="entity-profile-view__nav">
      <router-link to="/social-circles" class="entity-profile-view__back"> &larr; Back to Social Circles </router-link>
    </nav>

    <ProfileSkeleton v-if="isLoading" />

    <div v-else-if="hasError" class="entity-profile-view__error">
      <p>Failed to load profile: {{ error }}</p>
      <button @click="fetchProfile(props.type, props.id)">Retry</button>
    </div>

    <template v-else-if="entity">
      <StaleProfileBanner v-if="profile?.is_stale" :entity-type="entity.type" :entity-id="entity.id" />

      <ProfileHero :entity="entity" :profile="profile" />

      <!-- TODO Task 10: EgoNetwork component goes here -->

      <div class="entity-profile-view__content">
        <div class="entity-profile-view__left">
          <KeyConnections v-if="keyConnections.length > 0" :connections="keyConnections" />
          <AllConnections v-if="otherConnections.length > 0" :connections="otherConnections" />
        </div>

        <div class="entity-profile-view__right">
          <EntityBooks :books="books" />
          <CollectionStats v-if="stats" :stats="stats" />
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.entity-profile-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.entity-profile-view__nav {
  margin-bottom: 24px;
}

.entity-profile-view__back {
  color: var(--color-accent-gold, #b8860b);
  text-decoration: none;
  font-size: 14px;
}

.entity-profile-view__back:hover {
  text-decoration: underline;
}

.entity-profile-view__error {
  text-align: center;
  padding: 48px;
  color: var(--color-danger, #dc3545);
}

.entity-profile-view__content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-top: 24px;
}

.entity-profile-view__left,
.entity-profile-view__right {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

@media (max-width: 1024px) {
  .entity-profile-view__content {
    grid-template-columns: 1fr;
  }
}
</style>
```

**Step 2: Create ProfileHero.vue**

Create `frontend/src/components/entityprofile/ProfileHero.vue`:

```vue
<script setup lang="ts">
import { computed } from "vue";
import type { ProfileEntity, ProfileData } from "@/types/entityProfile";
import { formatTier } from "@/utils/socialCircles/formatters";

const props = defineProps<{
  entity: ProfileEntity;
  profile: ProfileData | null;
}>();

const dateDisplay = computed(() => {
  if (props.entity.birth_year && props.entity.death_year) {
    return `${props.entity.birth_year} \u2013 ${props.entity.death_year}`;
  }
  if (props.entity.founded_year) {
    return `Est. ${props.entity.founded_year}`;
  }
  return null;
});

const heroStories = computed(() => {
  if (!props.profile?.personal_stories) return [];
  return props.profile.personal_stories.filter((s) => s.display_in.includes("hero-bio"));
});
</script>

<template>
  <section class="profile-hero" :class="`profile-hero--${entity.type}`">
    <div class="profile-hero__info">
      <h1 class="profile-hero__name">{{ entity.name }}</h1>
      <div class="profile-hero__meta">
        <span v-if="entity.tier" class="profile-hero__tier">{{ formatTier(entity.tier) }}</span>
        <span v-if="entity.era" class="profile-hero__era">{{ entity.era }}</span>
        <span v-if="dateDisplay" class="profile-hero__dates">{{ dateDisplay }}</span>
      </div>

      <p v-if="profile?.bio_summary" class="profile-hero__bio">
        {{ profile.bio_summary }}
      </p>
      <p v-else class="profile-hero__bio profile-hero__bio--placeholder">
        Biographical summary not yet generated.
      </p>

      <div v-if="heroStories.length > 0" class="profile-hero__stories">
        <div v-for="(story, i) in heroStories" :key="i" class="profile-hero__story" :class="`--${story.tone}`">
          <span class="profile-hero__story-year" v-if="story.year">{{ story.year }}</span>
          {{ story.text }}
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.profile-hero {
  padding: 32px;
  background: var(--color-surface, #faf8f5);
  border-radius: 8px;
  border: 1px solid var(--color-border, #e8e4de);
}

.profile-hero__name {
  font-size: 28px;
  margin: 0 0 8px;
  color: var(--color-text, #2c2420);
}

.profile-hero__meta {
  display: flex;
  gap: 12px;
  font-size: 14px;
  color: var(--color-text-muted, #8b8579);
  margin-bottom: 16px;
}

.profile-hero__bio {
  font-size: 16px;
  line-height: 1.6;
  color: var(--color-text, #2c2420);
}

.profile-hero__bio--placeholder {
  font-style: italic;
  color: var(--color-text-muted, #8b8579);
}

.profile-hero__stories {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.profile-hero__story {
  padding: 12px 16px;
  background: var(--color-background, #fff);
  border-left: 3px solid var(--color-accent-gold, #b8860b);
  border-radius: 0 4px 4px 0;
  font-size: 14px;
  line-height: 1.5;
}

.profile-hero__story-year {
  font-weight: 600;
  margin-right: 8px;
}
</style>
```

**Step 3: Create KeyConnections.vue**

Create `frontend/src/components/entityprofile/KeyConnections.vue`:

```vue
<script setup lang="ts">
import type { ProfileConnection } from "@/types/entityProfile";

defineProps<{
  connections: ProfileConnection[];
}>();
</script>

<template>
  <section class="key-connections">
    <h2 class="key-connections__title">Key Connections</h2>
    <div class="key-connections__list">
      <div v-for="conn in connections" :key="`${conn.entity.type}:${conn.entity.id}`" class="key-connections__card">
        <div class="key-connections__header">
          <router-link
            :to="{ name: 'entity-profile', params: { type: conn.entity.type, id: conn.entity.id } }"
            class="key-connections__name"
          >
            {{ conn.entity.name }}
          </router-link>
          <span class="key-connections__type">{{ conn.connection_type.replace("_", " ") }}</span>
        </div>
        <p v-if="conn.narrative" class="key-connections__narrative">{{ conn.narrative }}</p>
        <div class="key-connections__meta">
          <span>{{ conn.shared_book_count }} shared {{ conn.shared_book_count === 1 ? "book" : "books" }}</span>
          <span class="key-connections__strength">
            <span v-for="i in 5" :key="i" :class="i <= Math.ceil(conn.strength / 2) ? '--filled' : '--empty'">
              &bull;
            </span>
          </span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.key-connections__title {
  font-size: 20px;
  margin: 0 0 16px;
}

.key-connections__list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.key-connections__card {
  padding: 16px;
  background: var(--color-surface, #faf8f5);
  border-radius: 8px;
  border: 1px solid var(--color-border, #e8e4de);
}

.key-connections__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.key-connections__name {
  font-weight: 600;
  color: var(--color-accent-gold, #b8860b);
  text-decoration: none;
}

.key-connections__name:hover {
  text-decoration: underline;
}

.key-connections__type {
  font-size: 12px;
  text-transform: uppercase;
  color: var(--color-text-muted, #8b8579);
}

.key-connections__narrative {
  font-size: 14px;
  line-height: 1.5;
  font-style: italic;
  margin: 8px 0;
}

.key-connections__meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--color-text-muted, #8b8579);
}

.key-connections__strength .--filled {
  color: var(--color-accent-gold, #b8860b);
}

.key-connections__strength .--empty {
  opacity: 0.3;
}
</style>
```

**Step 4: Create AllConnections.vue**

Create `frontend/src/components/entityprofile/AllConnections.vue`:

```vue
<script setup lang="ts">
import type { ProfileConnection } from "@/types/entityProfile";

defineProps<{
  connections: ProfileConnection[];
}>();
</script>

<template>
  <section class="all-connections">
    <h2 class="all-connections__title">All Connections</h2>
    <div class="all-connections__list">
      <router-link
        v-for="conn in connections"
        :key="`${conn.entity.type}:${conn.entity.id}`"
        :to="{ name: 'entity-profile', params: { type: conn.entity.type, id: conn.entity.id } }"
        class="all-connections__card"
      >
        <span class="all-connections__name">{{ conn.entity.name }}</span>
        <span class="all-connections__detail">
          {{ conn.connection_type.replace("_", " ") }} &middot; {{ conn.shared_book_count }}
          {{ conn.shared_book_count === 1 ? "book" : "books" }}
        </span>
      </router-link>
    </div>
  </section>
</template>

<style scoped>
.all-connections__title {
  font-size: 20px;
  margin: 0 0 16px;
}

.all-connections__list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.all-connections__card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--color-surface, #faf8f5);
  border-radius: 6px;
  border: 1px solid var(--color-border, #e8e4de);
  text-decoration: none;
  color: inherit;
  transition: border-color 150ms;
}

.all-connections__card:hover {
  border-color: var(--color-accent-gold, #b8860b);
}

.all-connections__name {
  font-weight: 500;
}

.all-connections__detail {
  font-size: 12px;
  color: var(--color-text-muted, #8b8579);
}
</style>
```

**Step 5: Create EntityBooks.vue**

Create `frontend/src/components/entityprofile/EntityBooks.vue`:

```vue
<script setup lang="ts">
import { computed, ref } from "vue";
import type { ProfileBook } from "@/types/entityProfile";

const props = defineProps<{
  books: ProfileBook[];
}>();

const showAll = ref(false);
const INITIAL_COUNT = 6;

const visibleBooks = computed(() => {
  if (showAll.value || props.books.length <= INITIAL_COUNT) {
    return props.books;
  }
  return props.books.slice(0, INITIAL_COUNT);
});
</script>

<template>
  <section class="entity-books">
    <h2 class="entity-books__title">Books in Collection ({{ books.length }})</h2>
    <div class="entity-books__list">
      <router-link
        v-for="book in visibleBooks"
        :key="book.id"
        :to="{ name: 'book-detail', params: { id: book.id } }"
        class="entity-books__card"
      >
        <span class="entity-books__book-title">{{ book.title }}</span>
        <div class="entity-books__book-meta">
          <span v-if="book.year">{{ book.year }}</span>
          <span v-if="book.condition" class="entity-books__condition">{{ book.condition }}</span>
          <span v-if="book.edition" class="entity-books__edition">{{ book.edition }}</span>
        </div>
      </router-link>
    </div>
    <button
      v-if="books.length > INITIAL_COUNT && !showAll"
      class="entity-books__show-all"
      @click="showAll = true"
    >
      Show all {{ books.length }} books
    </button>
  </section>
</template>

<style scoped>
.entity-books__title {
  font-size: 20px;
  margin: 0 0 16px;
}

.entity-books__list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.entity-books__card {
  display: flex;
  flex-direction: column;
  padding: 12px 16px;
  background: var(--color-surface, #faf8f5);
  border-radius: 6px;
  border: 1px solid var(--color-border, #e8e4de);
  text-decoration: none;
  color: inherit;
  transition: border-color 150ms;
}

.entity-books__card:hover {
  border-color: var(--color-accent-gold, #b8860b);
}

.entity-books__book-title {
  font-weight: 500;
}

.entity-books__book-meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: var(--color-text-muted, #8b8579);
  margin-top: 4px;
}

.entity-books__condition {
  padding: 1px 6px;
  background: var(--color-border, #e8e4de);
  border-radius: 3px;
}

.entity-books__show-all {
  margin-top: 12px;
  padding: 8px 16px;
  background: none;
  border: 1px solid var(--color-border, #e8e4de);
  border-radius: 6px;
  cursor: pointer;
  color: var(--color-accent-gold, #b8860b);
  width: 100%;
}

.entity-books__show-all:hover {
  background: var(--color-surface, #faf8f5);
}
</style>
```

**Step 6: Create CollectionStats.vue**

Create `frontend/src/components/entityprofile/CollectionStats.vue`:

```vue
<script setup lang="ts">
import type { ProfileStats } from "@/types/entityProfile";

defineProps<{
  stats: ProfileStats;
}>();
</script>

<template>
  <section class="collection-stats">
    <h2 class="collection-stats__title">Collection Stats</h2>
    <dl class="collection-stats__grid">
      <div class="collection-stats__item">
        <dt>Total Books</dt>
        <dd>{{ stats.total_books }}</dd>
      </div>
      <div v-if="stats.total_estimated_value" class="collection-stats__item">
        <dt>Estimated Value</dt>
        <dd>${{ stats.total_estimated_value.toLocaleString() }}</dd>
      </div>
      <div v-if="stats.first_editions > 0" class="collection-stats__item">
        <dt>First Editions</dt>
        <dd>{{ stats.first_editions }}</dd>
      </div>
      <div v-if="stats.date_range.length === 2" class="collection-stats__item">
        <dt>Date Range</dt>
        <dd>{{ stats.date_range[0] }} &ndash; {{ stats.date_range[1] }}</dd>
      </div>
    </dl>
  </section>
</template>

<style scoped>
.collection-stats__title {
  font-size: 20px;
  margin: 0 0 16px;
}

.collection-stats__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin: 0;
}

.collection-stats__item {
  padding: 12px;
  background: var(--color-surface, #faf8f5);
  border-radius: 6px;
  border: 1px solid var(--color-border, #e8e4de);
}

.collection-stats__item dt {
  font-size: 12px;
  color: var(--color-text-muted, #8b8579);
  text-transform: uppercase;
  margin-bottom: 4px;
}

.collection-stats__item dd {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}
</style>
```

**Step 7: Create ProfileSkeleton.vue**

Create `frontend/src/components/entityprofile/ProfileSkeleton.vue`:

```vue
<template>
  <div class="profile-skeleton" aria-busy="true" aria-label="Loading profile">
    <div class="profile-skeleton__hero">
      <div class="profile-skeleton__line profile-skeleton__line--title" />
      <div class="profile-skeleton__line profile-skeleton__line--meta" />
      <div class="profile-skeleton__line profile-skeleton__line--bio" />
      <div class="profile-skeleton__line profile-skeleton__line--bio" />
    </div>
    <div class="profile-skeleton__content">
      <div class="profile-skeleton__block" />
      <div class="profile-skeleton__block" />
    </div>
  </div>
</template>

<style scoped>
.profile-skeleton__hero {
  padding: 32px;
  background: var(--color-surface, #faf8f5);
  border-radius: 8px;
  margin-bottom: 24px;
}

.profile-skeleton__line {
  background: var(--color-border, #e8e4de);
  border-radius: 4px;
  animation: pulse 1.5s ease-in-out infinite;
}

.profile-skeleton__line--title {
  width: 40%;
  height: 28px;
  margin-bottom: 12px;
}

.profile-skeleton__line--meta {
  width: 30%;
  height: 14px;
  margin-bottom: 16px;
}

.profile-skeleton__line--bio {
  width: 90%;
  height: 14px;
  margin-bottom: 8px;
}

.profile-skeleton__content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.profile-skeleton__block {
  height: 200px;
  background: var(--color-surface, #faf8f5);
  border-radius: 8px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@media (max-width: 1024px) {
  .profile-skeleton__content {
    grid-template-columns: 1fr;
  }
}
</style>
```

**Step 8: Create StaleProfileBanner.vue**

Create `frontend/src/components/entityprofile/StaleProfileBanner.vue`:

```vue
<script setup lang="ts">
defineProps<{
  entityType: string;
  entityId: number;
}>();
</script>

<template>
  <div class="stale-banner" role="status">
    <span class="stale-banner__text">Profile may be outdated. Your collection has changed since this was generated.</span>
    <!-- Regenerate button will be wired in Phase 2 (AI enrichment) -->
  </div>
</template>

<style scoped>
.stale-banner {
  padding: 12px 16px;
  background: var(--color-warning-bg, #fff8e1);
  border: 1px solid var(--color-warning, #f9a825);
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 14px;
}
</style>
```

**Step 9: Run frontend lint and type-check**

Run: `npm run --prefix frontend lint`
Run: `npm run --prefix frontend type-check`

Fix any errors.

**Step 10: Commit**

```
git add frontend/src/views/EntityProfileView.vue frontend/src/components/entityprofile/
git commit -m "feat(entity-profiles): Add EntityProfileView and section components (#1545)"
```

---

### Task 10: Wire NodeFloatingCard "View Full Profile" Button

**Files:**
- Modify: `frontend/src/components/socialcircles/NodeFloatingCard.vue`

**Step 1: Replace disabled button with router-link**

In `frontend/src/components/socialcircles/NodeFloatingCard.vue`, find the disabled button (around line 265-272):

```html
          <button
            class="node-floating-card__profile-button node-floating-card__profile-button--disabled"
            disabled
            title="Entity profiles coming in a future update"
          >
            View Full Profile
            <span class="node-floating-card__coming-soon">(Coming Soon)</span>
          </button>
```

Replace with:

```html
          <router-link
            :to="{ name: 'entity-profile', params: { type: node.type, id: node.entity_id } }"
            class="node-floating-card__profile-button"
          >
            View Full Profile
          </router-link>
```

**Step 2: Update CSS**

Remove the `--disabled` CSS rules since the button is no longer disabled. Find and remove:

```css
.node-floating-card__profile-button--disabled { ... }
.node-floating-card__profile-button--disabled:hover { ... }
.node-floating-card__coming-soon { ... }
```

Add display block for router-link (since `<a>` is inline by default):

```css
.node-floating-card__profile-button {
  display: block;
  text-align: center;
  /* ... existing styles ... */
}
```

**Step 3: Run frontend lint**

Run: `npm run --prefix frontend lint`

**Step 4: Commit**

```
git add frontend/src/components/socialcircles/NodeFloatingCard.vue
git commit -m "feat(entity-profiles): Wire View Full Profile button in NodeFloatingCard (#1545)"
```

---

### Task 11: Frontend Component Tests

**Files:**
- Create: `frontend/src/components/entityprofile/__tests__/ProfileHero.test.ts`
- Create: `frontend/src/components/entityprofile/__tests__/EntityBooks.test.ts`
- Create: `frontend/src/components/entityprofile/__tests__/CollectionStats.test.ts`

**Step 1: Create ProfileHero test**

Create `frontend/src/components/entityprofile/__tests__/ProfileHero.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import ProfileHero from "../ProfileHero.vue";
import type { ProfileEntity, ProfileData } from "@/types/entityProfile";

const mockAuthor: ProfileEntity = {
  id: 31,
  type: "author",
  name: "Elizabeth Barrett Browning",
  birth_year: 1806,
  death_year: 1861,
  era: "romantic",
  tier: "TIER_1",
};

const mockProfile: ProfileData = {
  bio_summary: "One of the most prominent Victorian poets.",
  personal_stories: [
    {
      text: "Her domineering father forbade all of his children from marrying.",
      year: 1835,
      significance: "context",
      tone: "dramatic",
      display_in: ["hero-bio"],
    },
  ],
  is_stale: false,
  generated_at: "2026-01-29T10:00:00Z",
  model_version: "claude-3-5-haiku-20241022",
};

describe("ProfileHero", () => {
  it("renders entity name", () => {
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: mockProfile },
    });
    expect(wrapper.text()).toContain("Elizabeth Barrett Browning");
  });

  it("renders date range for authors", () => {
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: mockProfile },
    });
    expect(wrapper.text()).toContain("1806");
    expect(wrapper.text()).toContain("1861");
  });

  it("renders bio summary", () => {
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: mockProfile },
    });
    expect(wrapper.text()).toContain("One of the most prominent Victorian poets.");
  });

  it("renders personal stories filtered to hero-bio", () => {
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: mockProfile },
    });
    expect(wrapper.text()).toContain("domineering father");
  });

  it("shows placeholder when no bio", () => {
    const wrapper = mount(ProfileHero, {
      props: { entity: mockAuthor, profile: null },
    });
    expect(wrapper.text()).toContain("not yet generated");
  });

  it("renders founded year for publishers", () => {
    const publisher: ProfileEntity = {
      id: 7,
      type: "publisher",
      name: "Smith, Elder & Co.",
      founded_year: 1816,
      tier: "TIER_1",
    };
    const wrapper = mount(ProfileHero, {
      props: { entity: publisher, profile: null },
    });
    expect(wrapper.text()).toContain("Est. 1816");
  });
});
```

**Step 2: Create EntityBooks test**

Create `frontend/src/components/entityprofile/__tests__/EntityBooks.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import EntityBooks from "../EntityBooks.vue";
import type { ProfileBook } from "@/types/entityProfile";

const mockBooks: ProfileBook[] = [
  { id: 59, title: "Aurora Leigh", year: 1877, condition: "Near Fine", edition: "American reprint" },
  { id: 608, title: "Sonnets from the Portuguese", year: 1920, condition: "VG+" },
];

describe("EntityBooks", () => {
  it("renders book count in title", () => {
    const wrapper = mount(EntityBooks, {
      props: { books: mockBooks },
      global: { stubs: { "router-link": { template: "<a><slot /></a>" } } },
    });
    expect(wrapper.text()).toContain("Books in Collection (2)");
  });

  it("renders all book titles", () => {
    const wrapper = mount(EntityBooks, {
      props: { books: mockBooks },
      global: { stubs: { "router-link": { template: "<a><slot /></a>" } } },
    });
    expect(wrapper.text()).toContain("Aurora Leigh");
    expect(wrapper.text()).toContain("Sonnets from the Portuguese");
  });

  it("shows 'Show all' button when more than 6 books", () => {
    const manyBooks: ProfileBook[] = Array.from({ length: 10 }, (_, i) => ({
      id: i,
      title: `Book ${i}`,
    }));
    const wrapper = mount(EntityBooks, {
      props: { books: manyBooks },
      global: { stubs: { "router-link": { template: "<a><slot /></a>" } } },
    });
    expect(wrapper.text()).toContain("Show all 10 books");
  });
});
```

**Step 3: Create CollectionStats test**

Create `frontend/src/components/entityprofile/__tests__/CollectionStats.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import CollectionStats from "../CollectionStats.vue";
import type { ProfileStats } from "@/types/entityProfile";

const mockStats: ProfileStats = {
  total_books: 2,
  total_estimated_value: 800,
  first_editions: 0,
  date_range: [1877, 1920],
};

describe("CollectionStats", () => {
  it("renders total books", () => {
    const wrapper = mount(CollectionStats, { props: { stats: mockStats } });
    expect(wrapper.text()).toContain("2");
  });

  it("renders estimated value", () => {
    const wrapper = mount(CollectionStats, { props: { stats: mockStats } });
    expect(wrapper.text()).toContain("$800");
  });

  it("renders date range", () => {
    const wrapper = mount(CollectionStats, { props: { stats: mockStats } });
    expect(wrapper.text()).toContain("1877");
    expect(wrapper.text()).toContain("1920");
  });

  it("hides first editions when zero", () => {
    const wrapper = mount(CollectionStats, { props: { stats: mockStats } });
    expect(wrapper.text()).not.toContain("First Editions");
  });

  it("shows first editions when present", () => {
    const statsWithFE = { ...mockStats, first_editions: 1 };
    const wrapper = mount(CollectionStats, { props: { stats: statsWithFE } });
    expect(wrapper.text()).toContain("First Editions");
  });
});
```

**Step 4: Run tests**

Run: `npm run --prefix frontend test`

Expected: All tests pass.

**Step 5: Commit**

```
git add frontend/src/components/entityprofile/__tests__/
git commit -m "test(entity-profiles): Add component tests for ProfileHero, EntityBooks, CollectionStats (#1545)"
```

---

## Phase 2: AI Enrichment

### Task 12: Claude API Integration — Backend Service

**Files:**
- Create: `backend/app/services/ai_profile_generator.py`

**Step 1: Create AI generation service**

Create `backend/app/services/ai_profile_generator.py`:

```python
"""AI profile generation via Claude API."""

import json
import logging
import os

from anthropic import Anthropic

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-3-5-haiku-20241022"


def _get_model() -> str:
    """Get model from env var, falling back to default."""
    return os.environ.get("ENTITY_PROFILE_MODEL", DEFAULT_MODEL)


def _get_client() -> Anthropic:
    """Create Anthropic client. API key from ANTHROPIC_API_KEY env var."""
    return Anthropic()


def generate_bio_and_stories(
    name: str,
    entity_type: str,
    birth_year: int | None = None,
    death_year: int | None = None,
    founded_year: int | None = None,
    book_titles: list[str] | None = None,
) -> dict:
    """Generate bio summary and personal stories for an entity.

    Returns: {"biography": str, "personal_stories": list[dict]}
    """
    dates_line = ""
    if birth_year and death_year:
        dates_line = f"Dates: {birth_year} - {death_year}"
    elif founded_year:
        dates_line = f"Founded: {founded_year}"

    book_list = ", ".join(book_titles) if book_titles else "None in collection"

    prompt = f"""You are a reference librarian and literary historian specializing in Victorian-era literature and publishing. You have deep knowledge of personal histories, scandals, relationships, and anecdotes of the period.

Given this entity from a rare book collection:
  Name: {name}
  Type: {entity_type}
  {dates_line}
  Books in collection: {book_list}

Provide:

1. BIOGRAPHY: A 2-3 sentence biographical summary focusing on their significance in Victorian literary/publishing history.

2. PERSONAL_STORIES: An array of biographical facts — the "gossip" that makes this figure come alive. Include personal drama, scandals, tragedies, triumphs, and notable anecdotes. Each fact should have:
   - text: The story (1-2 sentences)
   - year: When it happened (if known, otherwise null)
   - significance: "revelation" (surprising/impactful), "notable" (interesting), or "context" (background)
   - tone: "dramatic", "scandalous", "tragic", "intellectual", or "triumphant"

Return ONLY valid JSON: {{"biography": "...", "personal_stories": [...]}}
Be factual. Draw from commonly known historical record.
If the entity is obscure, provide what is known and note the obscurity."""

    try:
        client = _get_client()
        response = client.messages.create(
            model=_get_model(),
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        return json.loads(text)
    except Exception:
        logger.exception("Failed to generate bio for %s %s", entity_type, name)
        return {"biography": None, "personal_stories": []}


def generate_connection_narrative(
    entity1_name: str,
    entity1_type: str,
    entity2_name: str,
    entity2_type: str,
    connection_type: str,
    shared_book_titles: list[str],
) -> str | None:
    """Generate one-sentence narrative for a connection.

    Returns: narrative string or None on failure.
    """
    books_str = ", ".join(shared_book_titles) if shared_book_titles else "various works"

    prompt = f"""You are a reference librarian specializing in Victorian-era publishing networks.

Describe this connection in one sentence for a rare book collector:
  {entity1_name} ({entity1_type}) connected to {entity2_name} ({entity2_type})
  Connection: {connection_type}
  Shared works: {books_str}

Focus on why this connection matters in Victorian publishing history.
Be factual and concise. Return ONLY the single sentence, no quotes."""

    try:
        client = _get_client()
        response = client.messages.create(
            model=_get_model(),
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception:
        logger.exception("Failed to generate narrative for %s-%s", entity1_name, entity2_name)
        return None


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
) -> dict | None:
    """Generate full relationship story for high-impact connections.

    Returns: {"summary": str, "details": list[dict], "narrative_style": str} or None.
    """
    books_str = ", ".join(shared_book_titles) if shared_book_titles else "various works"

    prompt = f"""You are a literary historian with deep knowledge of Victorian-era personal relationships.

Given this connection between two entities in a rare book collection:
  Entity 1: {entity1_name} ({entity1_type}, {entity1_dates})
  Entity 2: {entity2_name} ({entity2_type}, {entity2_dates})
  Connection type: {connection_type}
  Shared works: {books_str}
  Narrative trigger: {trigger_type}

Provide the relationship story:

1. SUMMARY: One-line summary of the relationship (for card display)

2. DETAILS: Array of biographical facts about this specific relationship.
   Each fact: {{"text": "...", "year": null_or_int, "significance": "revelation|notable|context", "tone": "dramatic|scandalous|tragic|intellectual|triumphant"}}
   Focus on personal anecdotes, dramatic events, and the human story.

3. NARRATIVE_STYLE: "prose-paragraph" for dramatic stories, "bullet-facts" for factual relationships, "timeline-events" for long-spanning connections.

Return ONLY valid JSON: {{"summary": "...", "details": [...], "narrative_style": "..."}}
Be factual. Draw from commonly known historical record."""

    try:
        client = _get_client()
        response = client.messages.create(
            model=_get_model(),
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        return json.loads(text)
    except Exception:
        logger.exception("Failed to generate relationship story for %s-%s", entity1_name, entity2_name)
        return None
```

**Step 2: Commit**

```
git add backend/app/services/ai_profile_generator.py
git commit -m "feat(entity-profiles): Add Claude API integration for profile generation (#1546)"
```

---

### Task 13: Profile Generation + Caching Endpoint

**Files:**
- Modify: `backend/app/services/entity_profile.py`
- Modify: `backend/app/api/v1/entity_profile.py`

**Step 1: Add generation logic to service**

Add to `backend/app/services/entity_profile.py`:

```python
from app.services.ai_profile_generator import (
    generate_bio_and_stories,
    generate_connection_narrative,
)


def generate_and_cache_profile(
    db: Session,
    entity_type: str,
    entity_id: int,
    owner_id: int,
) -> EntityProfile:
    """Generate AI profile and cache in DB."""
    entity = _get_entity(db, entity_type, entity_id)
    if not entity:
        raise ValueError(f"Entity {entity_type}:{entity_id} not found")

    books = _get_entity_books(db, entity_type, entity_id)
    book_titles = [b.title for b in books]

    # Generate bio + personal stories
    bio_data = generate_bio_and_stories(
        name=entity.name,
        entity_type=entity_type,
        birth_year=getattr(entity, "birth_year", None),
        death_year=getattr(entity, "death_year", None),
        founded_year=getattr(entity, "founded_year", None),
        book_titles=book_titles,
    )

    # Generate connection narratives
    node_id = f"{entity_type}:{entity_id}"
    graph = build_social_circles_graph(db)
    connected_edges = [
        e for e in graph.edges
        if e.source == node_id or e.target == node_id
    ]
    node_map = {n.id: n for n in graph.nodes}

    narratives = {}
    for edge in connected_edges:
        other_id = edge.target if edge.source == node_id else edge.source
        other_node = node_map.get(other_id)
        if not other_node:
            continue

        narrative = generate_connection_narrative(
            entity1_name=entity.name,
            entity1_type=entity_type,
            entity2_name=other_node.name,
            entity2_type=other_node.type.value if hasattr(other_node.type, "value") else other_node.type,
            connection_type=edge.type.value if hasattr(edge.type, "value") else edge.type,
            shared_book_titles=[b.title for b in books if b.id in (edge.shared_book_ids or [])],
        )
        if narrative:
            narratives[f"{node_id}:{other_id}"] = narrative

    import os
    model_version = os.environ.get("ENTITY_PROFILE_MODEL", "claude-3-5-haiku-20241022")

    # Upsert profile
    existing = (
        db.query(EntityProfile)
        .filter(
            EntityProfile.entity_type == entity_type,
            EntityProfile.entity_id == entity_id,
            EntityProfile.owner_id == owner_id,
        )
        .first()
    )

    if existing:
        existing.bio_summary = bio_data.get("biography")
        existing.personal_stories = bio_data.get("personal_stories", [])
        existing.connection_narratives = narratives
        existing.generated_at = datetime.utcnow()
        existing.model_version = model_version
        profile = existing
    else:
        profile = EntityProfile(
            entity_type=entity_type,
            entity_id=entity_id,
            bio_summary=bio_data.get("biography"),
            personal_stories=bio_data.get("personal_stories", []),
            connection_narratives=narratives,
            model_version=model_version,
            owner_id=owner_id,
        )
        db.add(profile)

    db.commit()
    return profile
```

**Step 2: Add regenerate endpoint**

Add to `backend/app/api/v1/entity_profile.py`:

```python
from app.services.entity_profile import generate_and_cache_profile


@router.post(
    "/{entity_type}/{entity_id}/profile/regenerate",
    summary="Regenerate entity profile",
    description="Triggers regeneration of AI-generated profile content.",
)
def regenerate_profile(
    entity_type: EntityType = Path(...),
    entity_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user_info=Depends(require_viewer),
):
    """Regenerate AI profile content."""
    generate_and_cache_profile(db, entity_type.value, entity_id, user_info["user_id"])
    return {"status": "regenerated"}
```

**Step 3: Run backend tests**

Run: `cd /Users/mark/projects/bluemoxon/backend && poetry run pytest tests/test_entity_profile.py -v`

Expected: All existing tests pass. (AI generation tests would need mocking — add in next step.)

**Step 4: Commit**

```
git add backend/app/services/entity_profile.py backend/app/api/v1/entity_profile.py
git commit -m "feat(entity-profiles): Add profile generation, caching, and regenerate endpoint (#1546)"
```

---

### Task 14: Revelation Trigger Classification

**Files:**
- Create: `backend/app/services/narrative_classifier.py`

**Step 1: Create classifier**

Create `backend/app/services/narrative_classifier.py`:

```python
"""Narrative trigger classification for entity connections."""


ERA_ORDER = ["pre_romantic", "romantic", "victorian", "edwardian", "post_1910"]

# Minimum time span in years to qualify as cross-era bridge
CROSS_ERA_THRESHOLD = 40

# Minimum connections for hub figure classification
HUB_THRESHOLD = 5


def classify_connection(
    source_era: str | None,
    target_era: str | None,
    source_years: tuple[int | None, int | None],
    target_years: tuple[int | None, int | None],
    connection_type: str,
    source_connection_count: int,
    has_relationship_story: bool,
) -> str | None:
    """Classify a connection's narrative trigger type.

    Returns: "cross_era_bridge", "social_circle", "hub_figure", "influence_chain", or None.
    Triggers are checked in priority order (highest first).
    """
    # 1. Cross-Era Bridge
    if _is_cross_era(source_era, target_era, source_years, target_years):
        return "cross_era_bridge"

    # 2. Social Circle / Personal Relationship
    if has_relationship_story:
        return "social_circle"

    # 3. Hub Figure
    if source_connection_count >= HUB_THRESHOLD:
        return "hub_figure"

    # 4. Influence Chain (future: detect from connection metadata)
    # For now, no connections are classified as influence chains.
    # This will be enriched when relationship_story data is populated.

    return None


def _is_cross_era(
    source_era: str | None,
    target_era: str | None,
    source_years: tuple[int | None, int | None],
    target_years: tuple[int | None, int | None],
) -> bool:
    """Check if connection spans eras with sufficient time gap."""
    if not source_era or not target_era:
        return False
    if source_era == target_era:
        return False

    # Check time span using available years
    all_years = [y for y in [*source_years, *target_years] if y is not None]
    if len(all_years) < 2:
        return False

    time_span = max(all_years) - min(all_years)
    return time_span >= CROSS_ERA_THRESHOLD
```

**Step 2: Create tests**

Create `backend/tests/test_narrative_classifier.py`:

```python
"""Tests for narrative trigger classification."""

from app.services.narrative_classifier import classify_connection


class TestClassifyConnection:
    def test_cross_era_bridge(self):
        result = classify_connection(
            source_era="romantic",
            target_era="victorian",
            source_years=(1788, 1824),
            target_years=(1809, 1882),
            connection_type="publisher",
            source_connection_count=2,
            has_relationship_story=False,
        )
        assert result == "cross_era_bridge"

    def test_social_circle_with_relationship_story(self):
        result = classify_connection(
            source_era="romantic",
            target_era="romantic",
            source_years=(1806, 1861),
            target_years=(1812, 1889),
            connection_type="shared_publisher",
            source_connection_count=3,
            has_relationship_story=True,
        )
        assert result == "social_circle"

    def test_hub_figure(self):
        result = classify_connection(
            source_era="victorian",
            target_era="victorian",
            source_years=(1812, 1870),
            target_years=(None, None),
            connection_type="publisher",
            source_connection_count=8,
            has_relationship_story=False,
        )
        assert result == "hub_figure"

    def test_no_trigger(self):
        result = classify_connection(
            source_era="victorian",
            target_era="victorian",
            source_years=(1850, 1900),
            target_years=(1860, 1910),
            connection_type="publisher",
            source_connection_count=2,
            has_relationship_story=False,
        )
        assert result is None

    def test_cross_era_priority_over_social(self):
        """Cross-era bridge takes priority over social circle."""
        result = classify_connection(
            source_era="romantic",
            target_era="edwardian",
            source_years=(1788, 1824),
            target_years=(1850, 1920),
            connection_type="publisher",
            source_connection_count=2,
            has_relationship_story=True,
        )
        assert result == "cross_era_bridge"

    def test_same_era_not_cross_era(self):
        result = classify_connection(
            source_era="victorian",
            target_era="victorian",
            source_years=(1812, 1870),
            target_years=(1815, 1882),
            connection_type="publisher",
            source_connection_count=2,
            has_relationship_story=False,
        )
        assert result is None

    def test_missing_eras_not_cross_era(self):
        result = classify_connection(
            source_era=None,
            target_era="victorian",
            source_years=(None, None),
            target_years=(1812, 1870),
            connection_type="publisher",
            source_connection_count=2,
            has_relationship_story=False,
        )
        assert result is None
```

**Step 3: Run tests**

Run: `cd /Users/mark/projects/bluemoxon/backend && poetry run pytest tests/test_narrative_classifier.py -v`

Expected: All tests pass.

**Step 4: Commit**

```
git add backend/app/services/narrative_classifier.py backend/tests/test_narrative_classifier.py
git commit -m "feat(entity-profiles): Add revelation trigger classification engine (#1546)"
```

---

### Task 15: Frontend StaleProfileBanner — Wire Regenerate Button

**Files:**
- Modify: `frontend/src/components/entityprofile/StaleProfileBanner.vue`
- Modify: `frontend/src/composables/entityprofile/useEntityProfile.ts`

**Step 1: Add regenerate function to composable**

Add to `useEntityProfile.ts`, inside the `useEntityProfile()` function:

```typescript
  async function regenerateProfile(entityType: string, entityId: number | string): Promise<void> {
    try {
      const token = authStore.idToken;
      const baseUrl = import.meta.env.VITE_API_BASE_URL || "";
      await fetch(`${baseUrl}/api/v1/entity/${entityType}/${entityId}/profile/regenerate`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      // Refetch after regeneration
      await fetchProfile(entityType, entityId);
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Regeneration failed";
    }
  }
```

Add `regenerateProfile` to the return object.

**Step 2: Update StaleProfileBanner**

Update `StaleProfileBanner.vue` to include regenerate button:

```vue
<script setup lang="ts">
import { ref } from "vue";

const props = defineProps<{
  entityType: string;
  entityId: number;
}>();

const emit = defineEmits<{
  regenerate: [];
}>();

const regenerating = ref(false);

async function handleRegenerate() {
  regenerating.value = true;
  emit("regenerate");
}
</script>

<template>
  <div class="stale-banner" role="status">
    <span class="stale-banner__text">Profile may be outdated. Your collection has changed since this was generated.</span>
    <button
      class="stale-banner__button"
      :disabled="regenerating"
      @click="handleRegenerate"
    >
      {{ regenerating ? "Regenerating..." : "Regenerate" }}
    </button>
  </div>
</template>
```

**Step 3: Wire in EntityProfileView**

Update the StaleProfileBanner usage in `EntityProfileView.vue`:

```vue
      <StaleProfileBanner
        v-if="profile?.is_stale"
        :entity-type="entity.type"
        :entity-id="entity.id"
        @regenerate="regenerateProfile(entity.type, entity.id)"
      />
```

Add `regenerateProfile` to the destructured composable imports.

**Step 4: Commit**

```
git add frontend/src/components/entityprofile/StaleProfileBanner.vue frontend/src/composables/entityprofile/useEntityProfile.ts frontend/src/views/EntityProfileView.vue
git commit -m "feat(entity-profiles): Wire regenerate button in stale profile banner (#1546)"
```

---

## Phase 3: Polish

### Task 16: EgoNetwork Component

**Files:**
- Create: `frontend/src/components/entityprofile/EgoNetwork.vue`
- Create: `frontend/src/composables/entityprofile/useEgoNetwork.ts`
- Modify: `frontend/src/views/EntityProfileView.vue`

**This task reuses Cytoscape.js patterns from NetworkGraph.vue. The ego network is a filtered view of the social circles data showing only 1-hop connections around the center entity. Implementation details depend on the existing Cytoscape setup — consult `frontend/src/components/socialcircles/NetworkGraph.vue` and `frontend/src/utils/socialCircles/dataTransformers.ts` for patterns.**

**Commit message:** `feat(entity-profiles): Add ego network component with concentric layout (#1545)`

---

### Task 17: Publication Timeline

**Files:**
- Create: `frontend/src/components/entityprofile/PublicationTimeline.vue`
- Modify: `frontend/src/views/EntityProfileView.vue`

**Simple HTML/CSS horizontal bar chart. Each book is a dot on the timeline. Range from earliest to latest year. Hover shows tooltip with title.**

**Commit message:** `feat(entity-profiles): Add publication timeline component (#1547)`

---

### Task 18: Batch Generation Endpoint

**Files:**
- Modify: `backend/app/api/v1/entity_profile.py`

**Add `POST /api/v1/entity/profiles/generate-all` (admin-only). Iterates all entities and calls `generate_and_cache_profile` for each. Rate-limited with batches of 10.**

**Commit message:** `feat(entity-profiles): Add admin batch generation endpoint (#1546)`

---

## Validation Checklist

After all tasks complete:

```bash
# Backend
cd /Users/mark/projects/bluemoxon/backend
poetry run ruff check backend/
poetry run ruff format --check backend/
poetry run pytest tests/ -x -q

# Frontend
cd /Users/mark/projects/bluemoxon/frontend
npm run lint
npm run format
npm run type-check
npm run test
```

---

## Execution Notes

- **Phase 1 (Tasks 1-11)** is entirely testable without Claude API access. All profile content is null/empty until Phase 2.
- **Phase 2 (Tasks 12-15)** requires `ANTHROPIC_API_KEY` env var. Backend tests should mock the Anthropic client.
- **Phase 3 (Tasks 16-18)** can be done in any order.
- **Seed profiles** (EBB + Robert Browning) from `docs/plans/2026-01-29-entity-profiles-seed-data.md` should be used to verify the UI renders correctly with both sparse and rich data.
