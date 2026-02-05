# Victorian Social Circles - Interactive Network Visualization

**Version:** 3.0 (BMX 3.0 Release)
**Created:** 2026-01-26
**Status:** Design Complete - Ready for Implementation

## Overview

An interactive network graph showing the human connections in the book collection - who knew whom, who published whom, who influenced whom. This is the flagship feature of BMX 3.0.

### Why This Matters

The collection reveals the interconnected web of Victorian intellectual life:
- **Elizabeth Barrett Browning → Robert Browning** - Married; the most famous literary couple in Victorian England
- **Lord Byron → John Murray (publisher) → Charles Darwin** - Same publisher, 40 years later!
- **Charlotte Brontë → Elizabeth Gaskell** - Friends, both Smith Elder authors
- **Charles Dickens → Wilkie Collins** - Collaborators, Chapman & Hall connection
- **Leigh Hunt → Keats, Shelley, Byron** - Knew them all!
- **Thomas Carlyle → John Ruskin** - Mentor/influence, both published major works

**Your collection isn't just books - it's a map of Victorian intellectual London. Everyone knew everyone. Same publishers, same binderies, same social circles.**

### Connection Visualization Vision

**Connections:** Lines showing relationships
- **Thick line** = strong connection (frequent publisher, personal friendship)
- **Dotted line** = influence (Carlyle influenced Ruskin)
- **Colored by type:** green = publisher relationship, blue = personal, purple = same binder

**Interactive:** Click a node and it highlights all connections
- Click "John Murray" → lights up Byron, Darwin, Lyell, Goldsmith, Borrow
- Click "Rivière" → lights up all books they bound

**The revelation:** Your collection isn't just books - it's a map of Victorian intellectual London. Everyone knew everyone. Same publishers, same binderies, same social circles.

---

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Graph Library | Cytoscape.js | Purpose-built for networks, good performance, easier than D3 |
| Route | `/socialcircles` | Evocative name, top-level nav |
| Data Source | Inferred from BMX data | No manual entry, auto-sync with collection |
| State Management | URL + Composables | Shareable links, reactive UI |

---

## GitHub Issues - Optimized Implementation Order

### Phase 1: MVP (15 issues)

Organized to minimize touching same component twice within phase.

**1.1 Foundation** (everything depends on this)
| # | Feature | Files |
|---|---------|-------|
| #1334 | Architectural foundation | types/, utils/, constants/ |
| - | Backend API | backend/api/v1/social_circles.py |

**1.2 Core NetworkGraph** (all NetworkGraph work together)
| # | Feature |
|---|---------|
| #1320 | Node shapes/colors by type |
| #1321 | Node size by collection count |
| #1317 | Click node → highlight connections |
| #1337 | Zoom controls |

**1.3 Tooltips**
| # | Feature |
|---|---------|
| #1318 | Hover connection tooltips |

**1.4 Filter System** (all FilterPanel work together)
| # | Feature |
|---|---------|
| #1319 | Filter panel |
| #1338 | Active filter pills |

**1.5 Timeline**
| # | Feature |
|---|---------|
| #1322 | Timeline slider (point + range mode) |

**1.6 Detail Panel**
| # | Feature |
|---|---------|
| #1323 | Biographical pop-ups |

**1.7 States**
| # | Feature |
|---|---------|
| #1339 | Loading skeleton |
| #1340 | Empty state |

**1.8 Integration**
| # | Feature |
|---|---------|
| #1328 | Dashboard preview card |
| #1341 | Export/Share |

**Epic:** #1316

---

### Phase 2: Enhanced Features (9 issues)

**2.1 Search & Discovery**
| # | Feature |
|---|---------|
| #1324 | Search |
| #1343 | Find Similar |

**2.2 Statistics** (both use graph algorithms)
| # | Feature |
|---|---------|
| #1325 | Statistics panel |
| #1326 | Degrees of separation |

**2.3 Graph Enhancements**
| # | Feature |
|---|---------|
| #1342 | Layout mode switcher |

**2.4 Quality & Polish**
| # | Feature |
|---|---------|
| #1335 | Test coverage |
| #1336 | Analytics tracking |
| #1344 | Keyboard shortcuts help |
| #1327 | Mobile optimization |

---

### Phase 3: Visual Enhancements (3 issues)

| # | Feature | Component |
|---|---------|-----------|
| #1345 | Filter count badges | FilterPanel |
| #1346 | Mini-map | NetworkGraph |
| #1347 | Timeline markers | TimelineSlider |

---

### Component Touch Matrix

| Component | Phase 1 | Phase 2 | Phase 3 |
|-----------|---------|---------|---------|
| NetworkGraph.vue | #1317, #1320, #1321, #1337 | #1342 | #1346 |
| FilterPanel.vue | #1319, #1338 | #1324 | #1345 |
| TimelineSlider.vue | #1322 | - | #1347 |
| NodeDetailPanel.vue | #1323 | - | - |
| ConnectionTooltip.vue | #1318 | - | - |

Phase 2/3 touches are additive enhancements to stable Phase 1 components.

---

## Frontend Architecture

### File Structure

```
frontend/src/
├── views/
│   └── SocialCirclesView.vue              # Main page
│
├── components/socialcircles/
│   ├── NetworkGraph.vue                   # Cytoscape wrapper
│   ├── FilterPanel.vue                    # Sidebar filters
│   ├── TimelineSlider.vue                 # Timeline with play/pause
│   ├── NodeDetailPanel.vue                # Slide-out bio panel
│   ├── ConnectionTooltip.vue              # Hover tooltip
│   ├── NetworkLegend.vue                  # Visual encoding guide
│   ├── ZoomControls.vue                   # Zoom in/out/fit
│   ├── ActiveFilterPills.vue              # Removable filter tags
│   ├── LoadingState.vue                   # Skeleton loader
│   ├── ErrorState.vue                     # Error with retry
│   ├── EmptyState.vue                     # No results message
│   └── ExportMenu.vue                     # Export PNG/JSON/Share
│
├── composables/socialcircles/
│   ├── useSocialCircles.ts                # Main orchestrator
│   ├── useNetworkData.ts                  # Fetching + caching
│   ├── useNetworkFilters.ts               # Filter state + logic
│   ├── useNetworkTimeline.ts              # Timeline animation
│   ├── useNetworkSelection.ts             # Selection + highlighting
│   ├── useNetworkExport.ts                # Export PNG/JSON
│   ├── useNetworkKeyboard.ts              # Keyboard navigation
│   └── useUrlState.ts                     # URL sync
│
├── utils/socialcircles/
│   ├── graphAlgorithms.ts                 # Shortest path, centrality
│   ├── colorPalettes.ts                   # Victorian colors
│   ├── layoutConfigs.ts                   # Cytoscape layouts
│   └── dataTransformers.ts                # API → Cytoscape format
│
├── constants/socialcircles/
│   └── index.ts                           # All constants
│
├── types/
│   ├── socialcircles.ts                   # Domain types
│   └── cytoscape.d.ts                     # Cytoscape extensions
│
└── styles/socialcircles/
    ├── _variables.scss                    # Shared variables
    └── _mixins.scss                       # Shared mixins
```

---

## TypeScript Types

### Core Types

```typescript
// Branded ID types for type safety
export type NodeId = string & { readonly __brand: 'NodeId' };
export type EdgeId = string & { readonly __brand: 'EdgeId' };
export type BookId = number & { readonly __brand: 'BookId' };

// Enums
export type NodeType = 'author' | 'publisher' | 'binder';
export type ConnectionType = 'publisher' | 'shared_publisher' | 'binder';
export type Era = 'pre_romantic' | 'romantic' | 'victorian' | 'edwardian' | 'post_1910' | 'unknown';
export type Tier = 'Tier 1' | 'Tier 2' | 'Tier 3' | null;

// Loading state
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

export interface AppError {
  type: 'network' | 'parse' | 'not_found' | 'timeout' | 'unknown';
  message: string;
  retryable: boolean;
}
```

### API Response Types

```typescript
export interface SocialCirclesResponse {
  nodes: ApiNode[];
  edges: ApiEdge[];
  meta: {
    total_books: number;
    total_authors: number;
    total_publishers: number;
    total_binders: number;
    date_range: [number, number];
    generated_at: string;
  };
}

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
```

### Filter & Timeline State

```typescript
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
  playbackSpeed: 0.5 | 1 | 2 | 5;
  mode: 'point' | 'range';
  rangeStart?: number;
  rangeEnd?: number;
}
```

---

## Visual Design

### Color Palette (Victorian Theme Integration)

```scss
// Node colors - aligned with main.css tokens
$node-colors: (
  author-romantic: var(--color-victorian-burgundy),      // #8b3a42
  author-victorian: var(--color-moxon-700),              // #254a3d
  publisher-tier1: var(--color-gold-light),              // #d4af37
  publisher-tier2: var(--color-gold-muted),              // #b8956e
  binder-tier1: var(--color-victorian-burgundy-dark),    // #5c262e
);

// Edge colors by connection type
$edge-colors: (
  publisher: var(--color-gold-medium),     // #c9a227
  shared_publisher: var(--color-moxon-500), // #3a6b5c
  binder: var(--color-victorian-burgundy), // #722f37
);
```

### Node Shapes

| Type | Shape | Size Formula |
|------|-------|--------------|
| Author | Ellipse (circle) | 20px + (bookCount * 5), max 60px |
| Publisher | Rectangle (square) | 25px + (bookCount * 4), max 65px |
| Binder | Diamond | 20px + (bookCount * 5), max 55px |

### Edge Styles

| Connection Type | Color | Style | Width |
|-----------------|-------|-------|-------|
| Publisher | Gold | Solid | 2-6px by strength |
| Shared Publisher | Green | Solid | 1-3px |
| Binder | Burgundy | Dashed | 1-3px |

### Animation Timings

| Animation | Duration | Easing |
|-----------|----------|--------|
| Node hover | 150ms | ease-out-soft |
| Node select | 250ms | ease-out-soft |
| Highlight spread | 400ms | ease-spring |
| Timeline fade | 400ms | ease-out-soft |
| Panel slide | 300ms | ease-spring |
| Layout reflow | 800ms | ease-in-out |

---

## Page Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│ NavBar              [Export↓] [Share] [?] [Theme] [User]                │
├──────────┬───────────────────────────────────────────────────────────────┤
│ FILTERS  │                                               [+] 100% [-]   │
│          │                                               [⊡] Fit        │
│ [Search] │                                                              │
│          │                                                              │
│ Active:  │                 GRAPH VIEWPORT                               │
│ [×Tier1] │                                                              │
│          │              ●━━━━━●                                         │
│ NODE     │            ╱       ╲                                         │
│ TYPES    │          ●           ■━━━━◆                                  │
│ ☑ Authors│            ╲       ╱                                         │
│ ☑ Publish│              ●━━━━●                                          │
│ ☑ Binders│                                                              │
│          │                                           Layout: [F][○][○]  │
│ CONNECT  │                                           Legend: ● ■ ◆     │
│ ☑ Publish│                                                              │
│ ☐ Binder │                                                              │
│          │                                                              │
│ ☐ Tier 1 │                                                              │
│          │                                                              │
│ [Reset]  │                                                              │
├──────────┴───────────────────────────────────────────────────────────────┤
│ Mode: [●Point][○Range]   1800 ═════════⚫══════════════ 1900            │
│ [◀◀] [◀] [▶ Play] [▶] [▶▶]                              [1× ▼]         │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Backend API

### Endpoint

```
GET /api/v1/social-circles
```

**Authentication:** `require_viewer`

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `include_binders` | bool | true | Include binder nodes/edges |
| `min_book_count` | int | 1 | Minimum books to include entity |
| `era` | Era[] | all | Filter by era |

### Connection Inference Rules

1. **PUBLISHER**: Author → Publisher (author published by publisher)
2. **SHARED_PUBLISHER**: Author ↔ Author (both published by same publisher)
3. **BINDER**: Author → Binder (author's book bound by binder)

### Response Example

```json
{
  "nodes": [
    {
      "id": "author:42",
      "entity_id": 42,
      "name": "Lord Byron",
      "type": "author",
      "birth_year": 1788,
      "death_year": 1824,
      "era": "romantic",
      "tier": "Tier 1",
      "book_count": 3,
      "book_ids": [101, 102, 103]
    }
  ],
  "edges": [
    {
      "id": "e:author:42:publisher:7",
      "source": "author:42",
      "target": "publisher:7",
      "type": "publisher",
      "strength": 6,
      "evidence": "Published 3 works",
      "shared_book_ids": [101, 102, 103]
    }
  ],
  "meta": {
    "total_books": 150,
    "total_authors": 23,
    "total_publishers": 6,
    "total_binders": 4,
    "date_range": [1800, 1900],
    "generated_at": "2026-01-26T10:30:00Z"
  }
}
```

### Backend Files

```
backend/app/
├── api/v1/
│   └── social_circles.py        # Route handler
├── schemas/
│   └── social_circles.py        # Pydantic schemas
└── services/
    └── social_circles.py        # Connection inference logic
```

---

## Component Interaction Flow

### Page Load Sequence

1. SocialCirclesView mounts, shows LoadingState
2. useUrlState reads query params, initializes state
3. useNetworkData fetches API (checks cache first)
4. Cytoscape initializes with Victorian stylesheet
5. Apply URL state (selection, year, filters)
6. Hide loading, show interactive graph

### Node Selection Flow

1. User clicks node → Cytoscape 'tap' event
2. NetworkGraph emits 'node-selected'
3. selectNode() updates selection state
4. highlightConnections() finds neighbors
5. Computed properties add CSS classes
6. Cytoscape re-renders, URL updates, panel opens

### Filter Change Flow

1. User toggles filter → FilterPanel @change
2. applyFilter() updates filter state
3. filteredNodes computed reacts
4. Graph re-renders (debounced)
5. URL updates, filter pills update
6. If 0 results → EmptyState

### State Synchronization

- **URL is source of truth** for shareable state
- State → URL: Debounced 300ms on change
- URL → State: On page load
- State → Cytoscape: Reactive via watch()
- Cytoscape → State: Events via emit()

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| → | Select next connected node |
| ← | Select previous node |
| Enter | Open node details |
| Escape | Deselect / close panel |
| + / - | Zoom in / out |
| 0 | Fit to view |
| / | Focus search |
| Space | Play/pause timeline |
| E | Export menu |
| S | Share |
| ? | Show shortcuts help |

---

## Performance Considerations

| Concern | Solution |
|---------|----------|
| Large response | Redis cache (5-min TTL) |
| N+1 queries | Batch fetch all entities upfront |
| Graph re-renders | Debounce updates (100ms) |
| Cytoscape bundle | Lazy-load (~300KB) |
| Mobile performance | Simplified view, larger touch targets |

---

## Accessibility

- Zoom controls for touch devices
- Keyboard navigation for all actions
- ARIA labels on interactive elements
- Focus trap in detail panel
- Color contrast WCAG AA compliant
- Reduced motion support

---

## Success Metrics

- Average time on page: Target 3-5 minutes
- Share rate: Track via analytics
- Node clicks: Most popular connections
- Filter usage: Most common patterns
- Export usage: PNG vs JSON vs Share

---

## Next Steps

1. Create feature branch from staging
2. Set up architectural foundation (#1334)
3. Implement backend API
4. Build core components (NetworkGraph first)
5. Add interactivity (filters, timeline, selection)
6. Polish (animations, loading states, empty states)
7. Review and test
8. PR to staging
