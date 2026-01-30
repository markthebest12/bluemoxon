# Entity Profiles - Design Document

**Version:** 1.1
**Created:** 2026-01-29
**Updated:** 2026-01-29
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
| AI Model | Configurable (start Haiku, may upgrade Sonnet) | Model via env var, ~$0.20 Haiku / ~$3 Sonnet for full collection |
| Cache Strategy | DB table + lazy generation | Persistent, survives deploys, no Redis dependency |
| Ego Network | Reuse Cytoscape.js | Consistent visual language, existing infrastructure |
| Graph Layout | Concentric | Entity at center, connections in ring. Clear for small graphs |
| Gossip Storage | Two-tier (personal + relationship) | Personal stories on entity, relationship stories on connections |
| Gossip Authoring | AI-generated (Claude Haiku) | Same model generates bios, stories, and narratives |
| Narrative Triggers | Rule-based classification | Cross-era bridges, social circles, hubs, influence chains |

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
| Personal stories | AI-generated | Biographical "gossip" facts (Tier 1), displayed below bio |

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

## Two-Tier Gossip Model

Biographical "gossip" (personal history, anecdotes, relationships) is stored in two tiers, scoped to where the story belongs.

### Tier 1: Personal Stories (Entity-Scoped)

Stories about the individual that don't require another entity. Stored on `entity_profiles`.

```typescript
interface BiographicalFact {
  text: string                                              // The story
  year?: number                                             // When it happened
  significance: 'revelation' | 'notable' | 'context'       // Impact level
  tone: 'dramatic' | 'scandalous' | 'tragic' | 'intellectual' | 'triumphant'
  displayIn: Array<'hero-bio' | 'timeline' | 'hover-tooltip'>
}
```

**Examples:**
- EBB: "Her domineering father forbade all of his children from marrying" (context, dramatic, hero-bio)
- Byron: "Scandalous affairs and rumored incest forced him to flee England in 1816" (revelation, scandalous, hero-bio + timeline)

### Tier 2: Relationship Stories (Connection-Scoped)

Stories that require both entities in a connection. Stored on `social_circle_edges`.

```typescript
interface RelationshipNarrative {
  summary: string                                           // One-liner for card display
  details: BiographicalFact[]                               // Full story facts
  narrativeStyle: 'prose-paragraph' | 'bullet-facts' | 'timeline-events'
}
```

**Examples:**
- EBB + Robert Browning: "Secret courtship and dramatic elopement to Italy" with 4 detail facts covering the 574 letters, secret wedding, and flight to Italy
- Dickens + Collins: "Collaborator and friend who pioneered the sensation novel"

### Correct Duplication

The same underlying event can appear in both tiers with different framing:
- **Tier 1 (EBB's personal story):** "Her tyrannical father forbade marriage" — personal context
- **Tier 2 (EBB-Browning connection):** "Secret wedding to escape her father" — relationship drama

This is intentional. Personal context stands alone; relationship drama needs both people.

### Display Mapping

| Content Type | Stored On | Display Location | Example |
|-------------|-----------|------------------|---------|
| Bio summary | entity_profiles | Hero section | "Leading Victorian poet..." |
| Personal stories | entity_profiles.personal_stories | Hero bio, tooltips, timeline | "Tyrannical father forbade marriage" |
| Relationship stories | social_circle_edges.relationship_story | Connection detail panel | "574 letters, secret wedding, elopement" |
| Connection narrative | entity_profiles.connection_narratives | Key connections section | "Published 7 works with Chapman & Hall" |

---

## Revelation Triggers (Narrative Classification)

Not all connections deserve narrative prose. A rules engine classifies each connection to determine display treatment.

### Trigger Hierarchy (Highest Impact First)

**1. Cross-Era Bridges** — Connections spanning 40+ years across eras

> "John Murray published Lord Byron's Romantic poetry (1812-1824) and Charles Darwin's scientific works (1839-1882) — 70 years bridging poetry and science!"

Trigger: `timeSpan >= 40 && differentEras` → Full prose narrative

**2. Social Circles / Personal Relationships** — Known personal connections

> "Charlotte Bronte and Elizabeth Gaskell were personal friends. After Bronte's death in 1855, Gaskell wrote her definitive biography."

Trigger: Connection has `relationship_story` with details → Prose paragraph with "View full story"

**3. Hub Figures** — Entities connecting 5+ others across diverse types

> "Smith, Elder published 8 authors in your collection — the Bronte sisters, Thackeray, Browning, Ruskin, Trollope, and Gaskell."

Trigger: `connectionCount >= 5 && diverseGenres` → Publisher dominance narrative

**4. Collaborators / Influence Chains** — Mentorship and intellectual influence

> "Thomas Carlyle's social criticism profoundly influenced John Ruskin's later works on art and society."

Trigger: Connection type is `collaborator` or `mentor` → Influence narrative

### Structured Cards (No Narrative)

Connections that don't hit any trigger get a structured card instead of prose:

- Simple publisher relationships (< 3 works, no social relationship)
- Single-work connections
- Binderies (unless high count or notable)

### Template Types

Each trigger maps to a typed narrative template:

| Trigger | Template | Key Fields |
|---------|----------|------------|
| Cross-Era Bridge | `CrossEraBridge` | intermediary, person1 (era, years), person2 (era, years), timeSpan |
| Social Hub | `SocialHub` | person, connections[], era, note |
| Publisher Dominance | `PublisherDominance` | publisher, authorCount, authors[], significance |
| Influence Chain | `InfluenceChain` | mentor, mentee, relationship, details |

The AI generates content using the appropriate template based on classification. Templates guide the prompt, not the output format.

---

## AI Enrichment Architecture

### Database Schema

```sql
CREATE TABLE entity_profiles (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL,       -- 'author', 'publisher', 'binder'
    entity_id INTEGER NOT NULL,
    bio_summary TEXT,                        -- 2-3 sentence biography
    personal_stories JSONB DEFAULT '[]',     -- BiographicalFact[] (Tier 1 gossip)
    connection_narratives JSONB,             -- {"author:42:publisher:7": "Published 7 works..."}
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model_version VARCHAR(100),              -- e.g., 'claude-3-5-haiku-20241022'
    owner_id INTEGER NOT NULL REFERENCES users(id),
    UNIQUE(entity_type, entity_id, owner_id)
);

CREATE INDEX idx_entity_profiles_lookup ON entity_profiles(entity_type, entity_id, owner_id);

-- Tier 2 gossip: relationship stories on edges
ALTER TABLE social_circle_edges
    ADD COLUMN relationship_story JSONB;     -- RelationshipNarrative (Tier 2 gossip)
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

**Model:** Configurable — start with `claude-3-5-haiku-20241022`, upgrade to Sonnet if quality insufficient. Model name stored in backend config (env var `ENTITY_PROFILE_MODEL`), not hardcoded.

**Prompts:**

Bio summary + personal stories (single call):
```
You are a reference librarian and literary historian specializing in Victorian-era
literature and publishing. You have deep knowledge of personal histories, scandals,
relationships, and anecdotes of the period.

Given this entity from a rare book collection:
  Name: {name}
  Type: {type}
  {dates_line}
  Books in collection: {book_list}

Provide:

1. BIOGRAPHY: A 2-3 sentence biographical summary focusing on their significance
   in Victorian literary/publishing history.

2. PERSONAL_STORIES: An array of biographical facts — the "gossip" that makes this
   figure come alive. Include personal drama, scandals, tragedies, triumphs, and
   notable anecdotes. Each fact should have:
   - text: The story (1-2 sentences)
   - year: When it happened (if known)
   - significance: "revelation" (surprising/impactful), "notable" (interesting), or "context" (background)
   - tone: "dramatic", "scandalous", "tragic", "intellectual", or "triumphant"

Return JSON: {"biography": "...", "personal_stories": [...]}
Be factual. Draw from commonly known historical record.
If the entity is obscure, provide what is known and note the obscurity.
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

Relationship story (for high-impact connections):
```
You are a literary historian with deep knowledge of Victorian-era personal relationships.

Given this connection between two entities in a rare book collection:
  Entity 1: {entity1_name} ({entity1_type}, {entity1_dates})
  Entity 2: {entity2_name} ({entity2_type}, {entity2_dates})
  Connection type: {connection_type}
  Shared works: {book_titles}
  Narrative trigger: {trigger_type}

Provide the relationship story:

1. SUMMARY: One-line summary of the relationship (for card display)

2. DETAILS: Array of biographical facts about this specific relationship.
   Each fact: {text, year?, significance, tone}
   Focus on personal anecdotes, dramatic events, and the human story.

3. NARRATIVE_STYLE: "prose-paragraph" for dramatic stories, "bullet-facts" for
   factual relationships, "timeline-events" for long-spanning connections.

Return JSON: {"summary": "...", "details": [...], "narrative_style": "..."}
Be factual. Draw from commonly known historical record.
```

**Cost estimate (Haiku):**
- Bio + personal stories: ~300 tokens input, ~300 tokens output per entity
- Connection narrative: ~150 tokens input, ~50 tokens output
- Relationship story: ~250 tokens input, ~400 tokens output (high-impact only)
- ~100 entities × 1 bio + ~5 narratives + ~1 relationship story = ~700 API calls
- Haiku: ~$0.20 total for full collection
- Sonnet: ~$3.00 total (if upgrade needed)

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
    "personal_stories": [
      {
        "text": "His childhood experience working in a blacking factory...",
        "year": 1824,
        "significance": "revelation",
        "tone": "tragic",
        "display_in": ["hero-bio", "timeline"]
      }
    ],
    "is_stale": false,
    "generated_at": "2026-01-29T10:30:00Z",
    "model_version": "claude-3-5-haiku-20241022"
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
      "narrative_trigger": "hub_figure",
      "is_key": true,
      "relationship_story": null
    },
    {
      "entity": {
        "id": 99,
        "type": "author",
        "name": "Wilkie Collins"
      },
      "connection_type": "shared_publisher",
      "strength": 5,
      "shared_book_count": 3,
      "shared_books": [
        {"id": 205, "title": "The Moonstone", "year": 1868}
      ],
      "narrative": "Collaborator and friend who pioneered the sensation novel.",
      "narrative_trigger": "social_circle",
      "is_key": true,
      "relationship_story": {
        "summary": "Literary collaborators and close friends for two decades",
        "details": [
          {
            "text": "Collins and Dickens first met in 1851...",
            "year": 1851,
            "significance": "notable",
            "tone": "intellectual"
          }
        ],
        "narrative_style": "prose-paragraph"
      }
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
8. Claude API integration in backend service (configurable model via `ENTITY_PROFILE_MODEL` env var)
9. Bio summary + personal stories generation (single call, Tier 1 gossip)
10. Connection narrative generation + caching
11. Revelation trigger classification engine (cross-era, social circle, hub, influence)
12. Relationship story generation for high-impact connections (Tier 2 gossip)
13. KeyConnections component with narratives + "View full story" for relationship stories
14. Staleness detection + "Regenerate" button
15. Batch generation endpoint + admin UI

### Phase 3: Polish
16. Publication timeline visualization
17. Mobile optimization
18. Loading skeletons
19. Connection detail panel for relationship stories (full gossip display)
20. E2E tests
21. Analytics tracking

---

## Related Issues

- Existing: "View Full Profile" button in `NodeFloatingCard.vue` (currently disabled)
- New epic needed for Entity Profiles
- #1108 (FMV automation) - entity profiles could eventually link to FMV data

---

## Approval

- [ ] Design approved by Mark
- [ ] Implementation plan created
