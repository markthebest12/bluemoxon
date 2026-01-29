# Entity Profiles - Design Document

**Version:** 1.0
**Created:** 2026-01-29
**Status:** Design Complete - Ready for Implementation

## Overview

Dedicated profile pages for authors, publishers, and binders that tell the story of each entity's place in Victorian intellectual London. AI-generated biographical summaries and connection narratives enrich the data already inferred from the book collection.

### Why This Matters

The Social Circles graph shows connections. Entity Profiles explain them. When a collector sees that Dickens and Thackeray share a publisher, the profile page tells the story: "Both published by Chapman & Hall in the 1840s, they were contemporaries and rivals who defined the Victorian novel."

The floating card teases with 5 connections and a "View Full Profile (Coming Soon)" button. This feature delivers on that promise.

---

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Navigation | Full page (`/entity/:type/:id`) | Deep-linkable, rich layout, scrollable, SEO-friendly |
| AI Model | Claude Haiku | Fast, cheap (~$0.10 for entire collection), good enough for bios |
| Cache Strategy | DB table + lazy generation | Persistent, survives deploys, no Redis dependency |
| Ego Network | Reuse Cytoscape.js | Consistent visual language, existing infrastructure |
| Graph Layout | Concentric | Entity at center, connections in ring. Clear for small graphs |

---

## Page Layout

### Desktop (> 1024px)

```
┌─────────────────────────────────────────────────────────────┐
│ ← Back to Social Circles          Victorian Social Circles  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  HERO SECTION                                               │
│  ┌──────────┐                                               │
│  │ Portrait │  Charles Dickens                              │
│  │ (period  │  ★★★ Premier · Victorian Era · 1812-1870     │
│  │  image)  │                                               │
│  └──────────┘  AI-generated biographical summary (2-3 lines)│
│               "The most celebrated novelist of the Victorian│
│                era, whose works defined the social novel..." │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  EGO NETWORK (mini graph, full width, ~400px tall)          │
│         ●───■ Chapman & Hall                                │
│        ╱│                                                   │
│  Collins ●   ●───■ Bradbury & Evans                        │
│        ╲│  ╱                                                │
│         ●───◆ Riviere & Son                                 │
│  Thackeray                                                  │
│                                                             │
│  Click any node for preview card → "View Profile"           │
│                                                             │
├─────────────────────────────────┬───────────────────────────┤
│                                 │                           │
│  KEY CONNECTIONS (narrative)    │  YOUR BOOKS (12)          │
│                                 │                           │
│  ■ Chapman & Hall               │  📖 Pickwick Papers 1837 │
│  "Published 7 works, his       │  📖 Oliver Twist 1838     │
│   primary publisher 1836-1844.  │  📖 Nicholas Nickleby 1839│
│   Also published Thackeray."   │  📖 Old Curiosity Shop    │
│                                 │  📖 Barnaby Rudge 1841   │
│  ● Wilkie Collins               │  ...                      │
│  "Collaborator and friend.      │  [Show all 12]            │
│   Both published by Chapman &   │                           │
│   Hall."                        ├───────────────────────────┤
│                                 │                           │
│  ALL CONNECTIONS (cards)        │  PUBLICATION TIMELINE     │
│  ■ Bradbury & Evans (3 books)   │  1836 ▪▪▪▪▪▪▪▪ 1870    │
│  ◆ Riviere & Son (2 bound)     │                           │
│  ● Thomas Carlyle (shared pub) │  COLLECTION STATS         │
│  ...                            │  12 books · $4,200 total  │
│                                 │  3 first editions         │
│                                 │  Condition: mostly VG+    │
└─────────────────────────────────┴───────────────────────────┘
```

### Tablet (768-1024px)

Same layout but connections and books stack vertically instead of side-by-side.

### Mobile (< 768px)

Single column, all sections stacked:
1. Hero (compact)
2. Ego network (300px tall, simplified labels)
3. Key connections (expandable accordion)
4. Books list
5. Timeline
6. Stats

---

## Route & Navigation

**Route:** `/entity/:type/:id`

Examples:
- `/entity/author/42` - Charles Dickens
- `/entity/publisher/7` - Chapman & Hall
- `/entity/binder/3` - Riviere & Son

**Navigation flows:**
- Main graph → Click node → Floating card → "View Full Profile" → Entity page
- Entity page ego network → Click node → Floating card preview → "View Profile" → Navigate
- Entity page → "Back to Social Circles" → Returns to main graph (preserves graph state via URL)
- Entity page → Click book title → Book detail page (`/books/:id`)

**Browser history:** Standard push navigation. Back button returns to previous page.

---

## Sections Detail

### 1. Hero Section

| Field | Source | Notes |
|-------|--------|-------|
| Name | Entity table | |
| Portrait | `getPlaceholderImage()` | Reuse existing placeholder system |
| Tier | Entity table | Stars display (reuse `formatTier`) |
| Era | Computed from birth_year | Reuse `getEraFromYear` |
| Dates | Entity table | `birth_year - death_year` (authors) or `founded_year - closed_year` (publishers/binders) |
| Bio summary | AI-generated | 2-3 sentences, cached in `entity_profiles` table |

**Type-specific hero content:**

| Entity Type | Dates Display | Extra Field |
|-------------|---------------|-------------|
| Author | 1812 - 1870 | Era badge |
| Publisher | Est. 1830 | Location (if available) |
| Binder | Est. 1840 | Specialty (if available) |

### 2. Ego Network

A focused Cytoscape.js graph showing the 1-hop neighborhood of the entity.

**Data source:** Client-side filter of the main `/social-circles` response. No additional API call.

**Layout:** Concentric -- entity at center (larger), connections in a ring.

**Sizing:** Full width, 400px tall (desktop), 300px (mobile).

**Interactions:**
- Click connected node → Show `NodeFloatingCard` preview (reuse existing component)
- Floating card "View Profile" → Navigate to that entity's page
- Click edge → Show inline connection detail below the graph
- Zoom/pan enabled, fits to view by default
- Same visual encoding as main graph (shapes, colors, sizes)

**Performance:** Small graph (typically 5-30 nodes), no performance concerns.

### 3. Key Connections (Narrative)

Top 3-5 connections by strength, each with an AI-generated narrative sentence.

**Layout:** Card per connection with:
- Entity type icon + name (clickable link to their profile)
- Connection type badge (publisher / shared publisher / binder)
- Strength indicator (filled circles)
- AI narrative sentence
- Shared book count

**Narrative generation prompt:**
```
Given these two Victorian-era entities and their connection:
  Entity 1: Charles Dickens (Author, 1812-1870)
  Entity 2: Chapman & Hall (Publisher)
  Connection type: Publisher
  Shared books: The Pickwick Papers (1837), Oliver Twist (1838), ...
  Connection strength: 7/10

Write one sentence describing this connection for a rare book collector.
Focus on the publishing relationship and its significance.
Keep it factual based on the data provided.
```

**Selection criteria for "key" connections:**
1. Highest strength connections first
2. Diversity of connection types (don't show 5 publishers if there are binders too)
3. Maximum 5 key connections

### 4. All Connections (Cards)

Structured card list of all remaining connections (beyond the key 3-5).

**Card content:**
- Entity type icon (shape matches graph: circle/square/diamond)
- Entity name (link to their profile)
- Connection type label
- Shared book count
- Connection strength dots

**Sorting:** By strength descending, then alphabetically.

**Interaction:** Click card → Navigate to that entity's profile.

### 5. Books in Collection

Full list of the user's books by this entity.

**Card content per book:**
- Title (link to `/books/:id`)
- Publication year
- Condition badge
- Thumbnail (if available)

**Sorting:** By publication year ascending (chronological).

**Pagination:** Show first 6, "Show all N" expander for larger collections.

### 6. Publication Timeline

Horizontal timeline showing book publication years.

**Implementation:** Simple HTML/CSS bar chart. Each book is a dot on the timeline.

**Range:** From earliest to latest publication year of the entity's books.

**Interaction:** Hover dot → tooltip with book title. Click → navigate to book detail.

### 7. Collection Stats

Summary statistics for the user's books by this entity.

| Stat | Source |
|------|--------|
| Total books | Count from API |
| Total estimated value | Sum from book records |
| First editions | Count where `edition = 'first'` |
| Condition breakdown | Count by condition rating |
| Acquisition timeline | Dates books were added to collection |

**Note:** Some stats (value, condition) depend on fields that may not be populated for all books. Show "N/A" or omit sections with no data.

---

## AI Enrichment Architecture

### Database Table

```sql
CREATE TABLE entity_profiles (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL,  -- 'author', 'publisher', 'binder'
    entity_id INTEGER NOT NULL,
    bio_summary TEXT,                   -- 2-3 sentence biography
    connection_narratives JSONB,        -- {"author:42:publisher:7": "Published 7 works..."}
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model_version VARCHAR(100),         -- e.g., 'claude-3-5-haiku-20241022'
    owner_id INTEGER NOT NULL REFERENCES users(id),
    UNIQUE(entity_type, entity_id, owner_id)
);

CREATE INDEX idx_entity_profiles_lookup ON entity_profiles(entity_type, entity_id, owner_id);
```

**Owner-scoped:** Each user gets their own profiles because connection narratives reference their specific collection.

### Generation Flow

```
GET /entity/:type/:id/profile
  │
  ├─ Fetch entity data from authors/publishers/binders table
  ├─ Fetch user's books for this entity
  ├─ Fetch connections from social circles graph
  │
  ├─ Check entity_profiles table for cached profile
  │   ├─ Cache hit + fresh → Return cached content
  │   ├─ Cache hit + stale → Return cached + flag for regeneration
  │   └─ Cache miss → Generate via Claude API → Cache → Return
  │
  └─ Return EntityProfileResponse
```

### Staleness Detection

A profile is stale when the user's collection has changed in a way that affects this entity:
- New book added by this author/publisher/binder
- Book removed
- Book metadata changed (edition, dates)

**Implementation:** Compare `entity_profiles.generated_at` against `MAX(books.updated_at)` for books connected to this entity.

**UI behavior for stale profiles:**
- Show existing cached content immediately (no loading delay)
- Show subtle "Profile may be outdated" badge
- "Regenerate" button triggers async regeneration

### Batch Generation

`POST /entity/profiles/generate-all` (admin-only):
- Queues all entities for profile generation
- Uses existing Lambda worker infrastructure
- Processes in batches of 10 with rate limiting
- Returns job ID for progress tracking

### Claude API Integration

**Model:** `claude-3-5-haiku-20241022` (fast, cheap)

**Prompts:**

Bio summary:
```
You are a reference librarian specializing in Victorian-era literature and publishing.

Given this entity from a rare book collection:
  Name: {name}
  Type: {type}
  {dates_line}
  Books in collection: {book_list}

Write a 2-3 sentence biographical summary. Focus on their significance
in Victorian literary/publishing history. Be factual and concise.
Do not speculate beyond what is commonly known about this figure.
If the entity is obscure, say so briefly.
```

Connection narrative:
```
You are a reference librarian specializing in Victorian-era publishing networks.

Describe this connection in one sentence for a rare book collector:
  {entity1_name} ({entity1_type}) connected to {entity2_name} ({entity2_type})
  Connection: {connection_type}
  Shared works: {book_titles}

Focus on why this connection matters in Victorian publishing history.
Be factual and concise.
```

**Cost estimate:**
- ~200 tokens input, ~100 tokens output per bio
- ~150 tokens input, ~50 tokens output per connection narrative
- ~100 entities × 1 bio + ~5 narratives each = ~600 API calls
- Haiku: ~$0.15 total for full collection

### Error Handling

- Claude API timeout → Return entity data without AI content, show "Bio unavailable" placeholder
- Claude API error → Log, return data without AI content
- Rate limit → Queue for retry, return data without AI content
- Invalid response → Log, return data without AI content

The page is always usable without AI content. It just lacks the narrative enrichment.

---

## API Design

### New Endpoints

**GET `/api/v1/entity/:type/:id/profile`**

Response:
```json
{
  "entity": {
    "id": 42,
    "type": "author",
    "name": "Charles Dickens",
    "birth_year": 1812,
    "death_year": 1870,
    "era": "victorian",
    "tier": "Tier 1"
  },
  "profile": {
    "bio_summary": "The most celebrated novelist of the Victorian era...",
    "is_stale": false,
    "generated_at": "2026-01-29T10:30:00Z"
  },
  "connections": [
    {
      "entity": {
        "id": 7,
        "type": "publisher",
        "name": "Chapman & Hall"
      },
      "connection_type": "publisher",
      "strength": 7,
      "shared_book_count": 7,
      "shared_books": [
        {"id": 101, "title": "The Pickwick Papers", "year": 1837}
      ],
      "narrative": "Published 7 works with Chapman & Hall, his primary publisher from 1836-1844.",
      "is_key": true
    }
  ],
  "books": [
    {
      "id": 101,
      "title": "The Pickwick Papers",
      "year": 1837,
      "condition": "VG+",
      "edition": "First Edition"
    }
  ],
  "stats": {
    "total_books": 12,
    "total_estimated_value": 4200,
    "first_editions": 3,
    "date_range": [1836, 1870]
  }
}
```

Auth: `require_viewer`

**POST `/api/v1/entity/:type/:id/profile/regenerate`**

Triggers async regeneration of the AI profile. Returns immediately.

Auth: `require_viewer` (regenerate own), `require_admin` for batch

**POST `/api/v1/entity/profiles/generate-all`**

Admin-only batch generation of all entity profiles.

Auth: `require_admin`

---

## Frontend Architecture

### New Files

```
frontend/src/
├── views/
│   └── EntityProfileView.vue          # Main profile page
│
├── components/entityprofile/
│   ├── ProfileHero.vue                # Hero section with bio
│   ├── EgoNetwork.vue                 # Mini Cytoscape graph
│   ├── KeyConnections.vue             # Narrative connection cards
│   ├── AllConnections.vue             # Structured connection list
│   ├── EntityBooks.vue                # Book list with links
│   ├── PublicationTimeline.vue        # Horizontal timeline
│   ├── CollectionStats.vue            # Stats summary
│   ├── ProfileSkeleton.vue            # Loading skeleton
│   └── StaleProfileBanner.vue         # "Profile may be outdated" UI
│
├── composables/entityprofile/
│   ├── useEntityProfile.ts            # Main data fetcher + orchestrator
│   └── useEgoNetwork.ts               # Ego network graph logic
│
└── types/
    └── entityProfile.ts               # Profile-specific types
```

### Route Registration

```typescript
{
  path: '/entity/:type/:id',
  name: 'entity-profile',
  component: () => import('@/views/EntityProfileView.vue'),
  meta: {
    requiresAuth: true,
    title: 'Entity Profile',
  },
  props: true,
}
```

### Wiring NodeFloatingCard "View Full Profile"

In `NodeFloatingCard.vue`, change the disabled button to a router link:

```vue
<router-link
  :to="{ name: 'entity-profile', params: { type: node.type, id: node.entity_id } }"
  class="node-floating-card__profile-button"
>
  View Full Profile
</router-link>
```

---

## Backend Architecture

### New Files

```
backend/app/
├── api/v1/
│   └── entity_profile.py             # Route handlers
├── schemas/
│   └── entity_profile.py             # Pydantic schemas
├── services/
│   └── entity_profile.py             # Profile generation + caching
└── models/
    └── entity_profile.py             # SQLAlchemy model (or add to existing models)
```

### Migration

```
alembic revision --autogenerate -m "Add entity_profiles table"
```

---

## Implementation Phases

### Phase 1: Core Profile Page (no AI)
1. Database migration for `entity_profiles` table
2. Backend endpoint `GET /entity/:type/:id/profile` (returns entity + connections + books, no AI yet)
3. Frontend `EntityProfileView.vue` with all sections except AI content
4. Wire "View Full Profile" button in `NodeFloatingCard.vue`
5. Route registration
6. ProfileHero, EntityBooks, AllConnections, CollectionStats components
7. EgoNetwork with concentric layout

### Phase 2: AI Enrichment
8. Claude API integration in backend service
9. Bio summary generation + caching
10. Connection narrative generation + caching
11. KeyConnections component with narratives
12. Staleness detection + "Regenerate" button
13. Batch generation endpoint + admin UI

### Phase 3: Polish
14. Publication timeline visualization
15. Mobile optimization
16. Loading skeletons
17. E2E tests
18. Analytics tracking

---

## Related Issues

- Existing: "View Full Profile" button in `NodeFloatingCard.vue` (currently disabled)
- New epic needed for Entity Profiles
- #1108 (FMV automation) - entity profiles could eventually link to FMV data

---

## Approval

- [ ] Design approved by Mark
- [ ] Implementation plan created
