# Victorian Social Circles - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an interactive network graph visualization showing connections between authors, publishers, and binders in the Victorian book collection.

**Architecture:** Single backend endpoint infers all connections from existing book data. Frontend uses Cytoscape.js for graph rendering with Vue 3 composables managing state. URL-synced filters enable shareable links.

**Tech Stack:** FastAPI + SQLAlchemy (backend), Vue 3 + TypeScript + Cytoscape.js (frontend), Pinia for state, existing Victorian theme tokens.

**Design Document:** `docs/plans/2026-01-26-victorian-social-circles-design.md`

**Epic:** #1316 | **Label:** `bmx 3.0`

---

## Phase 1.1: Foundation (#1334)

### Task 1: Create TypeScript Types

**Files:**
- Create: `frontend/src/types/socialCircles.ts`

**Step 1: Create the types file with branded IDs and core types**

```typescript
// frontend/src/types/socialCircles.ts

/**
 * Social Circles domain types.
 * Uses branded types for type-safe IDs.
 */

// =============================================================================
// Branded ID Types
// =============================================================================

/** Node identifier (e.g., "author:42", "publisher:7") */
export type NodeId = string & { readonly __brand: 'NodeId' };

/** Edge identifier (e.g., "e:author:42:publisher:7") */
export type EdgeId = string & { readonly __brand: 'EdgeId' };

/** Book ID reference */
export type BookId = number & { readonly __brand: 'BookId' };

// =============================================================================
// Enums
// =============================================================================

export type NodeType = 'author' | 'publisher' | 'binder';

export type ConnectionType = 'publisher' | 'shared_publisher' | 'binder';

export type Era =
  | 'pre_romantic'
  | 'romantic'
  | 'victorian'
  | 'edwardian'
  | 'post_1910'
  | 'unknown';

export type Tier = 'Tier 1' | 'Tier 2' | 'Tier 3' | null;

export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

export type LayoutMode = 'force' | 'circle' | 'grid' | 'hierarchical';

export type TimelineMode = 'point' | 'range';

export type PlaybackSpeed = 0.5 | 1 | 2 | 5;

// =============================================================================
// API Response Types
// =============================================================================

export interface ApiNode {
  id: NodeId;
  entity_id: number;
  name: string;
  type: NodeType;
  birth_year?: number;
  death_year?: number;
  era?: Era;
  tier?: Tier;
  founded_year?: number;
  closed_year?: number;
  book_count: number;
  book_ids: BookId[];
}

export interface ApiEdge {
  id: EdgeId;
  source: NodeId;
  target: NodeId;
  type: ConnectionType;
  strength: number;
  evidence?: string;
  shared_book_ids?: BookId[];
  start_year?: number;
  end_year?: number;
}

export interface SocialCirclesMeta {
  total_books: number;
  total_authors: number;
  total_publishers: number;
  total_binders: number;
  date_range: [number, number];
  generated_at: string;
}

export interface SocialCirclesResponse {
  nodes: ApiNode[];
  edges: ApiEdge[];
  meta: SocialCirclesMeta;
}

// =============================================================================
// State Types
// =============================================================================

export interface FilterState {
  showAuthors: boolean;
  showPublishers: boolean;
  showBinders: boolean;
  connectionTypes: ConnectionType[];
  tier1Only: boolean;
  eras: Era[];
  searchQuery: string;
}

export interface TimelineState {
  currentYear: number;
  minYear: number;
  maxYear: number;
  isPlaying: boolean;
  playbackSpeed: PlaybackSpeed;
  mode: TimelineMode;
  rangeStart?: number;
  rangeEnd?: number;
}

export interface SelectionState {
  selectedNodeId: NodeId | null;
  highlightedNodeIds: Set<NodeId>;
  highlightedEdgeIds: Set<EdgeId>;
  hoveredNodeId: NodeId | null;
  hoveredEdgeId: EdgeId | null;
}

// =============================================================================
// Error Types
// =============================================================================

export type ErrorType = 'network' | 'parse' | 'not_found' | 'timeout' | 'unknown';

export interface AppError {
  type: ErrorType;
  message: string;
  retryable: boolean;
}

export type Result<T, E = AppError> =
  | { success: true; data: T }
  | { success: false; error: E };

// =============================================================================
// Type Guards & Validators
// =============================================================================

const NODE_ID_PATTERN = /^(author|publisher|binder):\d+$/;
const EDGE_ID_PATTERN = /^e:(author|publisher|binder):\d+:(author|publisher|binder):\d+$/;

export function isNodeId(id: string): id is NodeId {
  return NODE_ID_PATTERN.test(id);
}

export function isEdgeId(id: string): id is EdgeId {
  return EDGE_ID_PATTERN.test(id);
}

export function createNodeId(type: NodeType, entityId: number): NodeId {
  return `${type}:${entityId}` as NodeId;
}

export function createEdgeId(source: NodeId, target: NodeId): EdgeId {
  return `e:${source}:${target}` as EdgeId;
}

export function parseNodeId(id: NodeId): { type: NodeType; entityId: number } {
  const [type, entityId] = id.split(':');
  return { type: type as NodeType, entityId: parseInt(entityId, 10) };
}

// Node type guards
export function isAuthorNode(node: ApiNode): node is ApiNode & { type: 'author' } {
  return node.type === 'author';
}

export function isPublisherNode(node: ApiNode): node is ApiNode & { type: 'publisher' } {
  return node.type === 'publisher';
}

export function isBinderNode(node: ApiNode): node is ApiNode & { type: 'binder' } {
  return node.type === 'binder';
}

// =============================================================================
// Default Values
// =============================================================================

export const DEFAULT_FILTER_STATE: FilterState = {
  showAuthors: true,
  showPublishers: true,
  showBinders: true,
  connectionTypes: ['publisher', 'shared_publisher', 'binder'],
  tier1Only: false,
  eras: [],
  searchQuery: '',
};

export const DEFAULT_TIMELINE_STATE: TimelineState = {
  currentYear: 1850,
  minYear: 1780,
  maxYear: 1920,
  isPlaying: false,
  playbackSpeed: 1,
  mode: 'point',
  rangeStart: undefined,
  rangeEnd: undefined,
};

export const DEFAULT_SELECTION_STATE: SelectionState = {
  selectedNodeId: null,
  highlightedNodeIds: new Set(),
  highlightedEdgeIds: new Set(),
  hoveredNodeId: null,
  hoveredEdgeId: null,
};
```

**Step 2: Run TypeScript check to verify types compile**

Run: `npm run --prefix frontend type-check`
Expected: PASS (no errors)

**Step 3: Commit**

```bash
git add frontend/src/types/socialCircles.ts
git commit -m "feat(socialcircles): Add TypeScript types with branded IDs and type guards

- Add branded types for NodeId, EdgeId, BookId
- Add API response types matching backend schema
- Add state types for filters, timeline, selection
- Add type guards and validators
- Add default state values

Part of #1334"
```

---

### Task 2: Create Cytoscape Type Declarations

**Files:**
- Create: `frontend/src/types/cytoscape.d.ts`

**Step 1: Create Cytoscape type extensions**

```typescript
// frontend/src/types/cytoscape.d.ts

/**
 * Cytoscape.js type extensions for Social Circles.
 * Extends core Cytoscape types with our custom data shapes.
 */

import type { NodeId, EdgeId, NodeType, ConnectionType, Era, Tier, BookId } from './socialCircles';

declare module 'cytoscape' {
  interface NodeDataDefinition {
    id: NodeId;
    entity_id: number;
    name: string;
    type: NodeType;
    birth_year?: number;
    death_year?: number;
    era?: Era;
    tier?: Tier;
    founded_year?: number;
    closed_year?: number;
    book_count: number;
    book_ids: BookId[];
  }

  interface EdgeDataDefinition {
    id: EdgeId;
    source: NodeId;
    target: NodeId;
    type: ConnectionType;
    strength: number;
    evidence?: string;
    shared_book_ids?: BookId[];
    start_year?: number;
    end_year?: number;
  }
}

export {};
```

**Step 2: Run TypeScript check**

Run: `npm run --prefix frontend type-check`
Expected: PASS

**Step 3: Commit**

```bash
git add frontend/src/types/cytoscape.d.ts
git commit -m "feat(socialcircles): Add Cytoscape.js type declarations

Extends Cytoscape node/edge data definitions with our custom shapes.

Part of #1334"
```

---

### Task 3: Create Constants

**Files:**
- Create: `frontend/src/constants/socialCircles.ts`

**Step 1: Create constants file**

```typescript
// frontend/src/constants/socialCircles.ts

/**
 * Social Circles constants.
 * Visual encoding, animation timings, and configuration.
 */

import type { NodeType, ConnectionType, Era, LayoutMode } from '@/types/socialCircles';

// =============================================================================
// Victorian Color Palette
// =============================================================================

/** Node colors by type and variant */
export const NODE_COLORS: Record<string, string> = {
  // Authors by era
  'author:romantic': 'var(--color-victorian-burgundy-light)',     // #8b3a42
  'author:victorian': 'var(--color-victorian-hunter-700)',        // #254a3d
  'author:edwardian': 'var(--color-victorian-hunter-500)',        // #3a6b5c
  'author:default': 'var(--color-victorian-hunter-600)',          // #2f5a4b

  // Publishers by tier
  'publisher:tier1': 'var(--color-victorian-gold-light)',         // #d4af37
  'publisher:tier2': 'var(--color-victorian-gold-muted)',         // #b8956e
  'publisher:default': 'var(--color-victorian-gold)',             // #c9a227

  // Binders
  'binder:tier1': 'var(--color-victorian-burgundy-dark)',         // #5c262e
  'binder:default': 'var(--color-victorian-burgundy)',            // #722f37
};

/** Edge colors by connection type */
export const EDGE_COLORS: Record<ConnectionType, string> = {
  publisher: 'var(--color-victorian-gold)',            // #c9a227
  shared_publisher: 'var(--color-victorian-hunter-500)', // #3a6b5c
  binder: 'var(--color-victorian-burgundy)',           // #722f37
};

// =============================================================================
// Node Visual Encoding
// =============================================================================

/** Node shapes by type */
export const NODE_SHAPES: Record<NodeType, string> = {
  author: 'ellipse',
  publisher: 'rectangle',
  binder: 'diamond',
};

/** Node size calculation */
export const NODE_SIZE = {
  author: { base: 20, perBook: 5, max: 60 },
  publisher: { base: 25, perBook: 4, max: 65 },
  binder: { base: 20, perBook: 5, max: 55 },
} as const;

/** Calculate node size based on book count */
export function calculateNodeSize(type: NodeType, bookCount: number): number {
  const config = NODE_SIZE[type];
  return Math.min(config.base + bookCount * config.perBook, config.max);
}

// =============================================================================
// Edge Visual Encoding
// =============================================================================

/** Edge width by strength (1-10 scale) */
export const EDGE_WIDTH = {
  min: 1,
  max: 6,
} as const;

/** Edge styles by connection type */
export const EDGE_STYLES: Record<ConnectionType, { lineStyle: string; opacity: number }> = {
  publisher: { lineStyle: 'solid', opacity: 0.8 },
  shared_publisher: { lineStyle: 'solid', opacity: 0.6 },
  binder: { lineStyle: 'dashed', opacity: 0.5 },
};

/** Calculate edge width from strength */
export function calculateEdgeWidth(strength: number): number {
  const normalized = Math.min(Math.max(strength, 1), 10) / 10;
  return EDGE_WIDTH.min + normalized * (EDGE_WIDTH.max - EDGE_WIDTH.min);
}

// =============================================================================
// Animation Timings
// =============================================================================

export const ANIMATION = {
  nodeHover: 150,
  nodeSelect: 250,
  highlightSpread: 400,
  timelineFade: 400,
  panelSlide: 300,
  layoutReflow: 800,
  debounceFilter: 100,
  debounceUrl: 300,
} as const;

// =============================================================================
// Layout Configurations
// =============================================================================

export const LAYOUT_CONFIGS: Record<LayoutMode, object> = {
  force: {
    name: 'cose',
    idealEdgeLength: 100,
    nodeOverlap: 20,
    refresh: 20,
    fit: true,
    padding: 30,
    randomize: false,
    componentSpacing: 100,
    nodeRepulsion: 400000,
    edgeElasticity: 100,
    nestingFactor: 5,
    gravity: 80,
    numIter: 1000,
    initialTemp: 200,
    coolingFactor: 0.95,
    minTemp: 1.0,
  },
  circle: {
    name: 'circle',
    fit: true,
    padding: 30,
    avoidOverlap: true,
    spacingFactor: 1.5,
  },
  grid: {
    name: 'grid',
    fit: true,
    padding: 30,
    avoidOverlap: true,
    condense: true,
    rows: undefined,
    cols: undefined,
  },
  hierarchical: {
    name: 'dagre',
    rankDir: 'TB',
    nodeSep: 50,
    rankSep: 100,
    fit: true,
    padding: 30,
  },
};

// =============================================================================
// Era Date Ranges
// =============================================================================

export const ERA_RANGES: Record<Era, [number, number]> = {
  pre_romantic: [1700, 1789],
  romantic: [1789, 1837],
  victorian: [1837, 1901],
  edwardian: [1901, 1910],
  post_1910: [1910, 1950],
  unknown: [1700, 1950],
};

/** Determine era from year */
export function getEraFromYear(year: number): Era {
  if (year < 1789) return 'pre_romantic';
  if (year < 1837) return 'romantic';
  if (year < 1901) return 'victorian';
  if (year < 1910) return 'edwardian';
  return 'post_1910';
}

// =============================================================================
// API Configuration
// =============================================================================

export const API = {
  endpoint: '/api/v1/social-circles',
  cacheKey: 'social-circles-data',
  cacheTtlMs: 5 * 60 * 1000, // 5 minutes
} as const;

// =============================================================================
// Keyboard Shortcuts
// =============================================================================

export const KEYBOARD_SHORTCUTS = {
  zoomIn: ['+', '='],
  zoomOut: ['-', '_'],
  fitToView: ['0'],
  togglePlay: [' '],
  escape: ['Escape'],
  search: ['/'],
  export: ['e'],
  share: ['s'],
  help: ['?'],
  nextNode: ['ArrowRight'],
  prevNode: ['ArrowLeft'],
  openDetails: ['Enter'],
} as const;
```

**Step 2: Run TypeScript check**

Run: `npm run --prefix frontend type-check`
Expected: PASS

**Step 3: Commit**

```bash
git add frontend/src/constants/socialCircles.ts
git commit -m "feat(socialcircles): Add constants for visual encoding and configuration

- Victorian color palette for nodes and edges
- Node shapes and size calculations
- Edge width and style configurations
- Animation timings
- Layout configurations for Cytoscape
- Era date ranges
- Keyboard shortcuts

Part of #1334"
```

---

### Task 4: Create Backend Schemas

**Files:**
- Create: `backend/app/schemas/social_circles.py`

**Step 1: Create Pydantic schemas**

```python
# backend/app/schemas/social_circles.py

"""Social Circles API schemas.

Defines request/response schemas for the social circles endpoint.
All data is inferred from existing book/author/publisher/binder relationships.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of nodes in the social network."""
    author = "author"
    publisher = "publisher"
    binder = "binder"


class ConnectionType(str, Enum):
    """Types of connections between nodes."""
    publisher = "publisher"  # Author published by publisher
    shared_publisher = "shared_publisher"  # Two authors share a publisher
    binder = "binder"  # Author's book bound by binder


class Era(str, Enum):
    """Historical eras for categorization."""
    pre_romantic = "pre_romantic"
    romantic = "romantic"
    victorian = "victorian"
    edwardian = "edwardian"
    post_1910 = "post_1910"
    unknown = "unknown"


class SocialCircleNode(BaseModel):
    """A node in the social network graph."""

    id: str = Field(..., description="Node ID (e.g., 'author:42')")
    entity_id: int = Field(..., description="Database entity ID")
    name: str = Field(..., description="Display name")
    type: NodeType = Field(..., description="Node type")

    # Author-specific fields
    birth_year: int | None = Field(None, description="Birth year (authors)")
    death_year: int | None = Field(None, description="Death year (authors)")
    era: Era | None = Field(None, description="Historical era")
    tier: str | None = Field(None, description="Tier classification")

    # Publisher/binder-specific fields
    founded_year: int | None = Field(None, description="Year founded (publishers/binders)")
    closed_year: int | None = Field(None, description="Year closed (publishers/binders)")

    # Collection stats
    book_count: int = Field(..., description="Number of books in collection")
    book_ids: list[int] = Field(default_factory=list, description="Book IDs in collection")


class SocialCircleEdge(BaseModel):
    """An edge (connection) in the social network graph."""

    id: str = Field(..., description="Edge ID (e.g., 'e:author:42:publisher:7')")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: ConnectionType = Field(..., description="Connection type")
    strength: int = Field(..., ge=1, le=10, description="Connection strength (1-10)")
    evidence: str | None = Field(None, description="Evidence for connection")
    shared_book_ids: list[int] | None = Field(None, description="Books connecting these nodes")
    start_year: int | None = Field(None, description="Start of relationship")
    end_year: int | None = Field(None, description="End of relationship")


class SocialCirclesMeta(BaseModel):
    """Metadata about the social circles response."""

    total_books: int = Field(..., description="Total books analyzed")
    total_authors: int = Field(..., description="Total authors in graph")
    total_publishers: int = Field(..., description="Total publishers in graph")
    total_binders: int = Field(..., description="Total binders in graph")
    date_range: tuple[int, int] = Field(..., description="Min/max year range")
    generated_at: datetime = Field(..., description="When data was generated")


class SocialCirclesResponse(BaseModel):
    """Response schema for the social circles endpoint."""

    nodes: list[SocialCircleNode] = Field(..., description="Graph nodes")
    edges: list[SocialCircleEdge] = Field(..., description="Graph edges")
    meta: SocialCirclesMeta = Field(..., description="Response metadata")


class SocialCirclesParams(BaseModel):
    """Query parameters for the social circles endpoint."""

    include_binders: bool = Field(True, description="Include binder nodes and edges")
    min_book_count: int = Field(1, ge=1, description="Minimum books to include entity")
    era: list[Era] | None = Field(None, description="Filter by era(s)")
```

**Step 2: Run backend linting**

Run: `poetry run ruff check backend/app/schemas/social_circles.py`
Expected: PASS (no errors)

**Step 3: Commit**

```bash
git add backend/app/schemas/social_circles.py
git commit -m "feat(socialcircles): Add Pydantic schemas for API

- SocialCircleNode for graph nodes (authors, publishers, binders)
- SocialCircleEdge for connections with strength and evidence
- SocialCirclesMeta for response metadata
- SocialCirclesResponse combining all
- SocialCirclesParams for query parameters

Part of #1334"
```

---

### Task 5: Create Backend Service

**Files:**
- Create: `backend/app/services/social_circles.py`

**Step 1: Create service with connection inference logic**

```python
# backend/app/services/social_circles.py

"""Social Circles business logic.

Infers connections between authors, publishers, and binders from the books table.
No manual data entry required - all relationships are derived from existing data.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.schemas.social_circles import (
    ConnectionType,
    Era,
    NodeType,
    SocialCircleEdge,
    SocialCircleNode,
    SocialCirclesMeta,
    SocialCirclesResponse,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def get_era_from_year(year: int | None) -> Era:
    """Determine historical era from a year."""
    if year is None:
        return Era.unknown
    if year < 1789:
        return Era.pre_romantic
    if year < 1837:
        return Era.romantic
    if year < 1901:
        return Era.victorian
    if year < 1910:
        return Era.edwardian
    return Era.post_1910


def build_social_circles_graph(
    db: Session,
    include_binders: bool = True,
    min_book_count: int = 1,
    era_filter: list[Era] | None = None,
) -> SocialCirclesResponse:
    """Build the social circles graph from book data.

    Args:
        db: Database session
        include_binders: Whether to include binder nodes/edges
        min_book_count: Minimum books for an entity to be included
        era_filter: Optional list of eras to filter by

    Returns:
        SocialCirclesResponse with nodes, edges, and metadata.
    """
    from app.models import Author, Binder, Book, Publisher

    # Fetch all books with relationships
    books_query = db.query(Book).filter(Book.is_garbage.is_(False))
    books = books_query.all()

    # Build node maps
    nodes: dict[str, SocialCircleNode] = {}
    edges: dict[str, SocialCircleEdge] = {}

    # Track relationships for edge building
    author_publishers: dict[int, set[int]] = defaultdict(set)  # author_id -> publisher_ids
    publisher_authors: dict[int, set[int]] = defaultdict(set)  # publisher_id -> author_ids
    author_binders: dict[int, set[int]] = defaultdict(set)     # author_id -> binder_ids
    author_books: dict[int, list[int]] = defaultdict(list)     # author_id -> book_ids
    publisher_books: dict[int, list[int]] = defaultdict(list)  # publisher_id -> book_ids
    binder_books: dict[int, list[int]] = defaultdict(list)     # binder_id -> book_ids

    # First pass: collect relationships
    for book in books:
        if book.author_id:
            author_books[book.author_id].append(book.id)
            if book.publisher_id:
                author_publishers[book.author_id].add(book.publisher_id)
                publisher_authors[book.publisher_id].add(book.author_id)
                publisher_books[book.publisher_id].append(book.id)
            if book.binder_id and include_binders:
                author_binders[book.author_id].add(book.binder_id)
                binder_books[book.binder_id].append(book.id)

    # Build author nodes
    authors = db.query(Author).filter(
        Author.id.in_(list(author_books.keys()))
    ).all()

    for author in authors:
        book_ids = author_books[author.id]
        if len(book_ids) < min_book_count:
            continue

        era = get_era_from_year(author.birth_year)
        if era_filter and era not in era_filter:
            continue

        node_id = f"author:{author.id}"
        nodes[node_id] = SocialCircleNode(
            id=node_id,
            entity_id=author.id,
            name=author.name,
            type=NodeType.author,
            birth_year=author.birth_year,
            death_year=author.death_year,
            era=era,
            tier=author.tier,
            book_count=len(book_ids),
            book_ids=book_ids,
        )

    # Build publisher nodes
    publishers = db.query(Publisher).filter(
        Publisher.id.in_(list(publisher_books.keys()))
    ).all()

    for publisher in publishers:
        book_ids = publisher_books[publisher.id]
        if len(book_ids) < min_book_count:
            continue

        node_id = f"publisher:{publisher.id}"
        nodes[node_id] = SocialCircleNode(
            id=node_id,
            entity_id=publisher.id,
            name=publisher.name,
            type=NodeType.publisher,
            tier=publisher.tier,
            book_count=len(book_ids),
            book_ids=book_ids,
        )

    # Build binder nodes
    if include_binders:
        binders = db.query(Binder).filter(
            Binder.id.in_(list(binder_books.keys()))
        ).all()

        for binder in binders:
            book_ids = binder_books[binder.id]
            if len(book_ids) < min_book_count:
                continue

            node_id = f"binder:{binder.id}"
            nodes[node_id] = SocialCircleNode(
                id=node_id,
                entity_id=binder.id,
                name=binder.name,
                type=NodeType.binder,
                tier=binder.tier,
                book_count=len(book_ids),
                book_ids=book_ids,
            )

    # Build edges: Author -> Publisher
    for author_id, publisher_ids in author_publishers.items():
        author_node_id = f"author:{author_id}"
        if author_node_id not in nodes:
            continue

        for publisher_id in publisher_ids:
            publisher_node_id = f"publisher:{publisher_id}"
            if publisher_node_id not in nodes:
                continue

            # Find shared books
            shared_books = [
                bid for bid in author_books[author_id]
                if bid in publisher_books[publisher_id]
            ]

            edge_id = f"e:{author_node_id}:{publisher_node_id}"
            strength = min(len(shared_books) * 2, 10)  # Scale strength

            edges[edge_id] = SocialCircleEdge(
                id=edge_id,
                source=author_node_id,
                target=publisher_node_id,
                type=ConnectionType.publisher,
                strength=strength,
                evidence=f"Published {len(shared_books)} work(s)",
                shared_book_ids=shared_books,
            )

    # Build edges: Author <-> Author (shared publisher)
    for publisher_id, author_ids in publisher_authors.items():
        publisher_node_id = f"publisher:{publisher_id}"
        if publisher_node_id not in nodes:
            continue

        author_list = list(author_ids)
        for i, author1_id in enumerate(author_list):
            author1_node_id = f"author:{author1_id}"
            if author1_node_id not in nodes:
                continue

            for author2_id in author_list[i + 1:]:
                author2_node_id = f"author:{author2_id}"
                if author2_node_id not in nodes:
                    continue

                # Ensure consistent edge ID ordering
                if author1_node_id > author2_node_id:
                    author1_node_id, author2_node_id = author2_node_id, author1_node_id

                edge_id = f"e:{author1_node_id}:{author2_node_id}"
                if edge_id in edges:
                    continue  # Already added from another publisher

                edges[edge_id] = SocialCircleEdge(
                    id=edge_id,
                    source=author1_node_id,
                    target=author2_node_id,
                    type=ConnectionType.shared_publisher,
                    strength=3,  # Lower strength for indirect connection
                    evidence=f"Both published by {nodes[publisher_node_id].name}",
                )

    # Build edges: Author -> Binder
    if include_binders:
        for author_id, binder_ids in author_binders.items():
            author_node_id = f"author:{author_id}"
            if author_node_id not in nodes:
                continue

            for binder_id in binder_ids:
                binder_node_id = f"binder:{binder_id}"
                if binder_node_id not in nodes:
                    continue

                shared_books = [
                    bid for bid in author_books[author_id]
                    if bid in binder_books[binder_id]
                ]

                edge_id = f"e:{author_node_id}:{binder_node_id}"
                strength = min(len(shared_books) * 2, 10)

                edges[edge_id] = SocialCircleEdge(
                    id=edge_id,
                    source=author_node_id,
                    target=binder_node_id,
                    type=ConnectionType.binder,
                    strength=strength,
                    evidence=f"Bound {len(shared_books)} work(s)",
                    shared_book_ids=shared_books,
                )

    # Calculate date range
    years = []
    for node in nodes.values():
        if node.birth_year:
            years.append(node.birth_year)
        if node.death_year:
            years.append(node.death_year)

    date_range = (min(years) if years else 1800, max(years) if years else 1900)

    # Build metadata
    meta = SocialCirclesMeta(
        total_books=len(books),
        total_authors=sum(1 for n in nodes.values() if n.type == NodeType.author),
        total_publishers=sum(1 for n in nodes.values() if n.type == NodeType.publisher),
        total_binders=sum(1 for n in nodes.values() if n.type == NodeType.binder),
        date_range=date_range,
        generated_at=datetime.now(timezone.utc),
    )

    return SocialCirclesResponse(
        nodes=list(nodes.values()),
        edges=list(edges.values()),
        meta=meta,
    )
```

**Step 2: Run backend linting**

Run: `poetry run ruff check backend/app/services/social_circles.py`
Expected: PASS

**Step 3: Commit**

```bash
git add backend/app/services/social_circles.py
git commit -m "feat(socialcircles): Add service for connection inference

- build_social_circles_graph() infers all connections from book data
- Creates author, publisher, binder nodes
- Creates publisher, shared_publisher, binder edges
- Calculates connection strength from shared books
- Supports filtering by min_book_count and era

Part of #1334"
```

---

### Task 6: Create Backend API Endpoint

**Files:**
- Create: `backend/app/api/v1/social_circles.py`
- Modify: `backend/app/api/v1/__init__.py`

**Step 1: Create the API endpoint**

```python
# backend/app/api/v1/social_circles.py

"""Social Circles API endpoint.

Provides network graph data showing connections between authors,
publishers, and binders in the book collection.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import require_viewer
from app.db import get_db
from app.schemas.social_circles import (
    Era,
    SocialCirclesResponse,
)
from app.services.social_circles import build_social_circles_graph

router = APIRouter()


@router.get(
    "/social-circles",
    response_model=SocialCirclesResponse,
    summary="Get social circles network graph",
    description="""
    Returns a network graph of connections between authors, publishers,
    and binders based on the book collection.

    Connections are inferred from:
    - **publisher**: Author was published by a publisher
    - **shared_publisher**: Two authors share the same publisher
    - **binder**: Author's book was bound by a binder
    """,
)
async def get_social_circles(
    include_binders: bool = Query(
        True,
        description="Include binder nodes and edges in the graph",
    ),
    min_book_count: int = Query(
        1,
        ge=1,
        description="Minimum books for an entity to be included",
    ),
    era: list[Era] | None = Query(
        None,
        description="Filter nodes by historical era(s)",
    ),
    db: Session = Depends(get_db),
    _user_info=Depends(require_viewer),
) -> SocialCirclesResponse:
    """Get the social circles network graph."""
    return build_social_circles_graph(
        db=db,
        include_binders=include_binders,
        min_book_count=min_book_count,
        era_filter=era,
    )
```

**Step 2: Register the router in `__init__.py`**

Read `backend/app/api/v1/__init__.py` first to find the router registration pattern, then add:

```python
from app.api.v1.social_circles import router as social_circles_router

# Add to the router includes (find the pattern)
api_router.include_router(social_circles_router, tags=["social-circles"])
```

**Step 3: Run backend linting**

Run: `poetry run ruff check backend/app/api/v1/social_circles.py`
Expected: PASS

**Step 4: Run backend tests to ensure nothing broke**

Run: `poetry run pytest backend/tests/ -x -q`
Expected: All existing tests pass

**Step 5: Commit**

```bash
git add backend/app/api/v1/social_circles.py backend/app/api/v1/__init__.py
git commit -m "feat(socialcircles): Add API endpoint GET /api/v1/social-circles

- Returns network graph with nodes and edges
- Supports include_binders, min_book_count, era filters
- Requires viewer authentication

Part of #1334"
```

---

### Task 7: Create Backend Tests

**Files:**
- Create: `backend/tests/test_social_circles.py`

**Step 1: Write tests for the endpoint**

```python
# backend/tests/test_social_circles.py

"""Tests for social circles API endpoint."""

import pytest


class TestSocialCirclesEndpoint:
    """Tests for GET /api/v1/social-circles."""

    def test_get_social_circles_returns_graph_structure(self, client):
        """Endpoint should return nodes, edges, and meta."""
        response = client.get("/api/v1/social-circles")

        assert response.status_code == 200
        data = response.json()

        assert "nodes" in data
        assert "edges" in data
        assert "meta" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    def test_get_social_circles_meta_structure(self, client):
        """Meta should contain expected fields."""
        response = client.get("/api/v1/social-circles")

        assert response.status_code == 200
        meta = response.json()["meta"]

        assert "total_books" in meta
        assert "total_authors" in meta
        assert "total_publishers" in meta
        assert "total_binders" in meta
        assert "date_range" in meta
        assert "generated_at" in meta

    def test_get_social_circles_node_structure(self, client, sample_book):
        """Nodes should have expected fields."""
        response = client.get("/api/v1/social-circles")

        assert response.status_code == 200
        nodes = response.json()["nodes"]

        if nodes:  # If we have any nodes
            node = nodes[0]
            assert "id" in node
            assert "entity_id" in node
            assert "name" in node
            assert "type" in node
            assert "book_count" in node
            assert node["type"] in ["author", "publisher", "binder"]

    def test_get_social_circles_edge_structure(self, client, sample_book):
        """Edges should have expected fields."""
        response = client.get("/api/v1/social-circles")

        assert response.status_code == 200
        edges = response.json()["edges"]

        if edges:  # If we have any edges
            edge = edges[0]
            assert "id" in edge
            assert "source" in edge
            assert "target" in edge
            assert "type" in edge
            assert "strength" in edge
            assert edge["type"] in ["publisher", "shared_publisher", "binder"]

    def test_get_social_circles_exclude_binders(self, client):
        """Should exclude binders when include_binders=false."""
        response = client.get("/api/v1/social-circles?include_binders=false")

        assert response.status_code == 200
        data = response.json()

        # No binder nodes
        binder_nodes = [n for n in data["nodes"] if n["type"] == "binder"]
        assert len(binder_nodes) == 0

        # No binder edges
        binder_edges = [e for e in data["edges"] if e["type"] == "binder"]
        assert len(binder_edges) == 0

    def test_get_social_circles_min_book_count_filter(self, client):
        """Should filter nodes by minimum book count."""
        response = client.get("/api/v1/social-circles?min_book_count=5")

        assert response.status_code == 200
        nodes = response.json()["nodes"]

        for node in nodes:
            assert node["book_count"] >= 5

    def test_get_social_circles_era_filter(self, client):
        """Should filter nodes by era."""
        response = client.get("/api/v1/social-circles?era=victorian")

        assert response.status_code == 200
        nodes = response.json()["nodes"]

        # Only author nodes have era field
        author_nodes = [n for n in nodes if n["type"] == "author"]
        for node in author_nodes:
            if node.get("era"):
                assert node["era"] == "victorian"
```

**Step 2: Run the tests**

Run: `poetry run pytest backend/tests/test_social_circles.py -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add backend/tests/test_social_circles.py
git commit -m "test(socialcircles): Add tests for social circles endpoint

- Tests graph structure (nodes, edges, meta)
- Tests filtering by include_binders, min_book_count, era
- Tests node and edge field structure

Part of #1334"
```

---

### Task 8: Create Data Transformer Utility

**Files:**
- Create: `frontend/src/utils/socialCircles/dataTransformers.ts`

**Step 1: Create the utility**

```typescript
// frontend/src/utils/socialCircles/dataTransformers.ts

/**
 * Transform API data to Cytoscape format.
 */

import type { Core, ElementDefinition } from 'cytoscape';
import type {
  ApiNode,
  ApiEdge,
  SocialCirclesResponse,
  NodeType,
  ConnectionType,
} from '@/types/socialCircles';
import {
  NODE_COLORS,
  NODE_SHAPES,
  EDGE_COLORS,
  EDGE_STYLES,
  calculateNodeSize,
  calculateEdgeWidth,
} from '@/constants/socialCircles';

/**
 * Get the color key for a node based on type and attributes.
 */
function getNodeColorKey(node: ApiNode): string {
  const { type, era, tier } = node;

  if (type === 'author' && era) {
    return `author:${era}`;
  }
  if (type === 'publisher' && tier) {
    const tierKey = tier === 'Tier 1' ? 'tier1' : 'tier2';
    return `publisher:${tierKey}`;
  }
  if (type === 'binder' && tier === 'Tier 1') {
    return 'binder:tier1';
  }

  return `${type}:default`;
}

/**
 * Transform an API node to Cytoscape element definition.
 */
export function transformNode(node: ApiNode): ElementDefinition {
  const colorKey = getNodeColorKey(node);
  const color = NODE_COLORS[colorKey] || NODE_COLORS[`${node.type}:default`];
  const shape = NODE_SHAPES[node.type];
  const size = calculateNodeSize(node.type, node.book_count);

  return {
    group: 'nodes',
    data: {
      ...node,
    },
    style: {
      'background-color': color,
      shape,
      width: size,
      height: size,
      label: node.name,
    },
  };
}

/**
 * Transform an API edge to Cytoscape element definition.
 */
export function transformEdge(edge: ApiEdge): ElementDefinition {
  const color = EDGE_COLORS[edge.type];
  const { lineStyle, opacity } = EDGE_STYLES[edge.type];
  const width = calculateEdgeWidth(edge.strength);

  return {
    group: 'edges',
    data: {
      ...edge,
    },
    style: {
      'line-color': color,
      'line-style': lineStyle,
      'line-opacity': opacity,
      width,
      'target-arrow-color': color,
      'curve-style': 'bezier',
    },
  };
}

/**
 * Transform full API response to Cytoscape elements.
 */
export function transformToCytoscapeElements(
  response: SocialCirclesResponse
): ElementDefinition[] {
  const nodeElements = response.nodes.map(transformNode);
  const edgeElements = response.edges.map(transformEdge);

  return [...nodeElements, ...edgeElements];
}

/**
 * Filter elements based on filter state.
 * Returns element IDs that should be visible.
 */
export function getVisibleElementIds(
  cy: Core,
  showAuthors: boolean,
  showPublishers: boolean,
  showBinders: boolean,
  connectionTypes: ConnectionType[],
): { nodeIds: Set<string>; edgeIds: Set<string> } {
  const nodeIds = new Set<string>();
  const edgeIds = new Set<string>();

  // Filter nodes by type
  cy.nodes().forEach((node) => {
    const nodeType = node.data('type') as NodeType;

    if (nodeType === 'author' && showAuthors) {
      nodeIds.add(node.id());
    } else if (nodeType === 'publisher' && showPublishers) {
      nodeIds.add(node.id());
    } else if (nodeType === 'binder' && showBinders) {
      nodeIds.add(node.id());
    }
  });

  // Filter edges by type and connected nodes
  cy.edges().forEach((edge) => {
    const edgeType = edge.data('type') as ConnectionType;
    const sourceId = edge.source().id();
    const targetId = edge.target().id();

    if (
      connectionTypes.includes(edgeType) &&
      nodeIds.has(sourceId) &&
      nodeIds.has(targetId)
    ) {
      edgeIds.add(edge.id());
    }
  });

  return { nodeIds, edgeIds };
}
```

**Step 2: Create the utils directory index**

```typescript
// frontend/src/utils/socialCircles/index.ts

export * from './dataTransformers';
```

**Step 3: Run TypeScript check**

Run: `npm run --prefix frontend type-check`
Expected: PASS

**Step 4: Commit**

```bash
git add frontend/src/utils/socialCircles/
git commit -m "feat(socialcircles): Add data transformer utilities

- transformNode() converts API node to Cytoscape element
- transformEdge() converts API edge to Cytoscape element
- transformToCytoscapeElements() converts full response
- getVisibleElementIds() filters elements by type

Part of #1334"
```

---

### Task 9: Install Cytoscape.js Dependency

**Step 1: Install cytoscape and types**

Run: `npm install --prefix frontend cytoscape`
Run: `npm install --prefix frontend -D @types/cytoscape`

**Step 2: Verify installation**

Run: `npm run --prefix frontend type-check`
Expected: PASS

**Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(socialcircles): Install Cytoscape.js dependency

Part of #1334"
```

---

### Task 10: Create Main View Stub

**Files:**
- Create: `frontend/src/views/SocialCirclesView.vue`

**Step 1: Create the view stub**

```vue
<!-- frontend/src/views/SocialCirclesView.vue -->
<script setup lang="ts">
/**
 * Social Circles - Interactive Network Visualization
 *
 * Main view for the Victorian Social Circles feature.
 * Shows connections between authors, publishers, and binders.
 */

import { ref } from 'vue';

// Placeholder - will be replaced with actual composables
const isLoading = ref(true);
const error = ref<string | null>(null);

// Simulate loading for now
setTimeout(() => {
  isLoading.value = false;
}, 1000);
</script>

<template>
  <div class="social-circles-view">
    <!-- Header -->
    <header class="social-circles-header">
      <h1 class="text-2xl font-serif text-victorian-hunter-700">
        Victorian Social Circles
      </h1>
      <p class="text-sm text-victorian-ink-muted">
        Explore the connections between authors, publishers, and binders
      </p>
    </header>

    <!-- Loading State -->
    <div v-if="isLoading" class="social-circles-loading">
      <div class="animate-pulse flex flex-col items-center gap-4">
        <div class="w-16 h-16 bg-victorian-hunter-200 rounded-full" />
        <p class="text-victorian-ink-muted">Loading network...</p>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="social-circles-error">
      <p class="text-victorian-burgundy">{{ error }}</p>
      <button
        class="mt-4 px-4 py-2 bg-victorian-hunter-600 text-white rounded hover:bg-victorian-hunter-700"
      >
        Retry
      </button>
    </div>

    <!-- Main Content (placeholder) -->
    <div v-else class="social-circles-content">
      <p class="text-center text-victorian-ink-muted py-20">
        Network graph will render here
      </p>
    </div>
  </div>
</template>

<style scoped>
.social-circles-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--color-victorian-paper-cream);
}

.social-circles-header {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--color-victorian-paper-aged);
  background-color: var(--color-victorian-paper-white);
}

.social-circles-loading,
.social-circles-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 2rem;
}

.social-circles-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}
</style>
```

**Step 2: Run TypeScript check**

Run: `npm run --prefix frontend type-check`
Expected: PASS

**Step 3: Commit**

```bash
git add frontend/src/views/SocialCirclesView.vue
git commit -m "feat(socialcircles): Add SocialCirclesView stub

Basic view structure with loading, error, and content areas.
Uses Victorian theme styling.

Part of #1334"
```

---

### Task 11: Add Route

**Files:**
- Modify: `frontend/src/router/index.ts`

**Step 1: Read current router file to find pattern**

**Step 2: Add the route (lazy-loaded)**

```typescript
// Add to routes array
{
  path: '/socialcircles',
  name: 'social-circles',
  component: () => import('@/views/SocialCirclesView.vue'),
  meta: {
    requiresAuth: true,
    title: 'Social Circles',
  },
},
```

**Step 3: Run TypeScript check**

Run: `npm run --prefix frontend type-check`
Expected: PASS

**Step 4: Run frontend lint**

Run: `npm run --prefix frontend lint`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/router/index.ts
git commit -m "feat(socialcircles): Add /socialcircles route

Lazy-loads SocialCirclesView, requires authentication.

Part of #1334"
```

---

### Task 12: Verify End-to-End

**Step 1: Run all backend tests**

Run: `poetry run pytest backend/tests/ -x -q`
Expected: All tests pass

**Step 2: Run all frontend checks**

Run: `npm run --prefix frontend type-check`
Run: `npm run --prefix frontend lint`
Expected: Both pass

**Step 3: Test API endpoint manually**

Run: `bmx-api GET /social-circles`
Expected: Returns JSON with nodes, edges, meta

**Step 4: Final commit for phase 1.1**

```bash
git add -A
git commit -m "chore(socialcircles): Complete Phase 1.1 Foundation

Architectural foundation complete:
- TypeScript types with branded IDs
- Cytoscape type declarations
- Constants for visual encoding
- Backend schemas and service
- API endpoint with tests
- Data transformer utilities
- View stub with route

Closes #1334"
```

---

## Phase 1.2: Core NetworkGraph (#1317, #1320, #1321, #1337)

*[Continue with detailed tasks for NetworkGraph component, zoom controls, node shapes/colors, node sizing, click highlighting...]*

---

## Phase 1.3: Tooltips (#1318)

*[Continue with ConnectionTooltip component...]*

---

## Phase 1.4: Filter System (#1319, #1338)

*[Continue with FilterPanel and ActiveFilterPills...]*

---

*[Additional phases to be detailed as implementation progresses]*

---

## Checkpoint Summary

After each phase, verify:

1. **Backend:** `poetry run pytest backend/tests/ -x`
2. **Frontend types:** `npm run --prefix frontend type-check`
3. **Frontend lint:** `npm run --prefix frontend lint`
4. **Manual test:** `bmx-api GET /social-circles`
5. **Visual test:** Run dev server, navigate to `/socialcircles`

---

**Plan complete for Phase 1.1.** Phases 1.2-1.8 will follow the same detailed structure.
