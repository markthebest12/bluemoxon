# Phase 5E Design: Entity Profile Enhancements

## Overview

Three features added to entity profiles, built in sequence: #1633 → #1634 → #1632.

- **#1633** — Extended collection stats (condition breakdown + acquisition timeline)
- **#1634** — Book thumbnails + condition badges
- **#1632** — Portrait images on entity profile hero

## Sequencing Rationale

#1633 is self-contained backend aggregation + frontend charts with no image pipeline. #1634 introduces image display patterns using existing book images (every book already has a primary image in S3). #1632 is the most complex — a Wikidata matching pipeline, S3 storage, and new hero layout — and benefits from image display patterns established by #1634.

---

## #1633 — Extended Collection Stats

### Backend

**Schema changes.** Add two fields to `ProfileStats`:

```python
condition_distribution: dict[str, int]  # {"Fine": 12, "Very Good": 8, "Good": 3}
acquisition_by_year: dict[int, int]     # {2019: 3, 2020: 7, 2021: 5}
```

**Aggregation logic:**

1. **Condition distribution** — group books by `condition` field, count per grade. Normalize raw condition strings to display labels (matching frontend `formatConditionGrade()` logic). Books without condition bucketed as "Ungraded".
2. **Acquisition by year** — group books by year component of acquisition date, count per year. Only books with acquisition dates. Sorted by year.

No new endpoints — data rides on existing `GET /entity/{type}/{id}/profile` response.

### Frontend

**Type update.** Extend `ProfileStats` in `types/entityProfile.ts`:

```typescript
interface ProfileStats {
  total_books: number;
  total_estimated_value: number | null;
  first_editions: number;
  date_range: number[];
  condition_distribution: Record<string, number>;  // new
  acquisition_by_year: Record<number, number>;      // new
}
```

**Condition stacked bar.** New section in `CollectionStats.vue` below the existing stats grid. Single horizontal bar with colored segments proportional to each grade's count. Legend below showing color + label + count.

Fixed color mapping per grade:

| Grade | Color |
|-------|-------|
| Fine | Deep green |
| Near Fine | Green |
| Very Good | Teal |
| Good | Amber |
| Fair | Orange |
| Poor | Red-brown |
| Ungraded | Grey |

Implementation: flex container with child divs, `flex-grow` equals count. Minimum ~3% width per segment so tiny slices remain visible. Hover/tap shows exact count. Skip bar entirely if all books are same condition (show as text instead).

**Acquisition bar chart.** New component `AcquisitionTimeline.vue` below the condition bar. Horizontal axis: years. Vertical bars: book count per year. Hand-rolled CSS — flex row of columns, height proportional to count relative to max year. Year labels below (rotated if dense). Bar color: muted sienna. Hover shows "N books acquired in YYYY". Skip entirely if fewer than 2 distinct acquisition years.

**Layout.** Both visualizations stack vertically below existing 4-stat grid. Each gets a section label ("Condition Breakdown", "Acquisition History"). No new dependencies — hand-rolled CSS consistent with existing `PublicationTimeline`.

---

## #1634 — Book Thumbnails + Condition Badges

### Backend

Add `primary_image_url` to `ProfileBook` schema:

```python
class ProfileBook(BaseModel):
    id: int
    title: str
    year: int | None = None
    condition: str | None = None
    edition: str | None = None
    primary_image_url: str | None = None  # new
```

Populate using same logic as `BookResponse` — find primary image (flagged or first by display_order), generate CloudFront URL. Every book has an image, so always populated.

### Frontend

**Type update.** Add `primary_image_url: string` to `ProfileBook` in `types/entityProfile.ts`.

**ConditionBadge.vue** — new shared component. Takes `condition: string` prop, renders formatted label with background color from the #1633 palette. Used in three places.

**EntityBooks.** Add ~48x64px thumbnail (3:4 book ratio) to left of each book entry. Replace condition text with `ConditionBadge` pill.

**KeyConnections shared books.** Add ~32x40px inline thumbnail before each title. Add `ConditionBadge` after title. Keep list compact.

**PublicationTimeline.** Add thumbnail and `ConditionBadge` to hover tooltip popup. No images on the timeline track itself.

---

## #1632 — Entity Portraits

### Backend — Schema

Add `image_url` column to author, publisher, and binder models:

```python
image_url = Column(String(500), nullable=True)
```

Database migration for all three tables. Include `image_url` in `ProfileEntity` response schema.

### Backend — Wikidata Matching Pipeline

Batch script (not Lambda — runs once) that processes all entities:

**For authors:**

1. Query **Wikidata SPARQL endpoint** by:
   - Label match (name, fuzzy/alias support)
   - Instance of: human (Q5)
   - Date filter: birth/death years within ±5 years
2. Score candidates using multiple signals:
   - **Name similarity** (normalized Levenshtein or token overlap)
   - **Year overlap** (exact birth+death = high, partial = lower)
   - **Known works** (Wikidata P800 vs book titles in collection)
   - **Occupation** (P106 — writer, poet, novelist)
3. Above confidence threshold → fetch portrait via **P18 property**
4. Download from Commons, resize ~400x400px JPEG
5. Upload to S3 at `entities/author/{id}/portrait.jpg`
6. Update entity `image_url` with CloudFront URL
7. Below threshold → skip, `image_url` stays null

**For publishers/binders (two-tier):**

1. **Tier 1: Wikidata** — same as authors but instance of publisher/organization. Covers famous publishers (John Murray, Macmillan).
2. **Tier 2: NLS historical OS maps** — if no Wikidata match, extract location from `description` field (publishers) or `bio_summary` (AI-generated). Use a lightweight Claude Haiku call: "Extract the city/address from this text, or return null." If location found, geocode and fetch historical OS map tile from NLS tile server. Store as portrait.
3. No location extractable → `image_url` stays null, placeholder SVG used.

**Logging.** Script outputs a report per entity: matched QID, confidence score, image source (Wikidata/NLS/skip), reason for skip.

### Backend — Admin Override

`PUT /entity/{type}/{id}/portrait` — accepts image upload, stores in S3 (same path, overwrites), updates `image_url`. Admin role only.

### Frontend

**ProfileEntity type update.** Add `image_url: string | null` in `types/entityProfile.ts`.

**ProfileHero layout change.**

Desktop (>768px): two-column layout. Left: ~120px circular image with muted gold/sepia border. Right: existing name/bio content. `object-fit: cover` for consistent framing.

Mobile (≤768px): ~80px portrait centered above name, followed by existing content below.

**Image source logic:**
1. `entity.image_url` → CloudFront portrait (Wikidata or NLS)
2. null → `getPlaceholderImage(entity.type, entity.id)` (existing deterministic SVG)

**EgoNetwork.** Nice-to-have: render center node with portrait image as circular background if `image_url` exists. Defer if it complicates Cytoscape rendering.

### S3 Storage

Same images bucket, new prefix: `entities/{type}/{id}/portrait.jpg`. Served via existing CloudFront distribution.

---

## Testing

### Unit Tests

**#1633:**
- `CollectionStats` — stacked bar renders correct segments, single-condition edge case shows text not bar, empty acquisition data handled
- `AcquisitionTimeline` — bars render for year→count data, skips for <2 years, hover shows correct count
- Backend: aggregation returns correct condition counts and year grouping

**#1634:**
- `ConditionBadge` — correct label from `formatConditionGrade()`, correct color class per grade
- `EntityBooks` — thumbnail renders with correct `src`, badge renders
- `KeyConnections` — inline thumbnails in shared book list
- Backend: `ProfileBook` serialization includes `primary_image_url`

**#1632:**
- `ProfileHero` — portrait renders when `image_url` present, placeholder when null, correct alt text
- Backend: Wikidata scoring function with known inputs, S3 path construction
- Pipeline: confidence scoring with mock responses (high/partial/no match)

### E2E Tests (Playwright)

**`e2e/entity-profile-stats.spec.ts` (#1633):**
- Navigate to entity profile, verify condition stacked bar visible with segments
- Verify acquisition chart renders with bar elements
- Verify legend labels match condition grades

**`e2e/entity-profile-books.spec.ts` (#1634):**
- Navigate to entity profile, verify book thumbnails render with valid `src` (not broken)
- Verify condition badges visible next to book entries
- Verify KeyConnections shared books show thumbnails

**`e2e/entity-profile-portrait.spec.ts` (#1632):**
- Navigate to Tier 1 entity (likely Wikidata match), verify portrait image loads
- Navigate to lesser-known entity, verify placeholder SVG renders
- Verify portrait is circular, correct size on desktop

---

## Open Decisions

- **EgoNetwork node images** — deferred as nice-to-have for #1632. Can be added later without design changes.
- **NLS map tile zoom level/style** — to be determined during #1632 implementation based on available NLS API options.
- **Confidence threshold value** — to be tuned during #1632 pipeline development. Start conservative (high threshold), lower if too many entities miss.
