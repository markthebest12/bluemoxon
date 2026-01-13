# Collection Spotlight Design

**Date:** 2026-01-12
**Status:** Approved

## Overview

Replace the redundant "Browse Collection" and "Premium Bindings" action cards on the dashboard with a single full-width **Collection Spotlight** component that showcases 2-3 randomly selected books from the top 20% by value on each page load.

## Goals

- Reclaim wasted space from redundant navigation (both cards link to destinations already accessible via stat cards)
- Add visual interest with rotating high-value items
- Create a "rediscover your collection" experience

## Design Decisions

| Aspect | Decision |
|--------|----------|
| Replaces | Browse Collection + Premium Bindings cards |
| Layout | Full-width, 2-3 books horizontal (stacked on mobile) |
| Content per book | Thumbnail, title, author, value, binder badge (if premium) |
| Selection pool | Top 20% by `value_mid` (currently 34 of 170 books) |
| Rotation | Random shuffle on each page load (client-side) |
| Data fetching | Separate fetch, progressive loading |
| Backend changes | None |

## Visual Design

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  COLLECTION SPOTLIGHT                                           │
├─────────────────────┬─────────────────────┬─────────────────────┤
│  ┌───────────────┐  │  ┌───────────────┐  │  ┌───────────────┐  │
│  │   Thumbnail   │  │  │   Thumbnail   │  │  │   Thumbnail   │  │
│  │               │  │  │               │  │  │               │  │
│  └───────────────┘  │  └───────────────┘  │  └───────────────┘  │
│  Title              │  Title              │  Title              │
│  Author Name        │  Author Name        │  Author Name        │
│  $1,200             │  $850               │  $650               │
│  [Zaehnsdorf]       │                     │  [Rivière]          │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

### Each Book Item Shows

- Thumbnail image (or placeholder if no image)
- Title (truncated if long)
- Author name
- Value (formatted as currency)
- Binder badge (only if premium binding exists)

### Interactions

- Clicking a book navigates to its detail page
- Cmd/Ctrl+click opens in new tab (consistent with stat cards)

### Responsive Behavior

- Desktop: 3 books in a row
- Tablet: 2-3 books in a row
- Mobile: Stack vertically, 1 book per row

## Data & Selection Logic

### Pool Definition

Top 20% of primary collection by `value_mid`. Currently 34 books with values ranging from $500 to $4,750.

### Selection Algorithm

```typescript
// On component mount
const pool = books
  .filter(b => b.inventory_type === 'PRIMARY')
  .sort((a, b) => b.value_mid - a.value_mid)
  .slice(0, Math.ceil(totalCount * 0.2));

const shuffled = [...pool].sort(() => Math.random() - 0.5);
const spotlight = shuffled.slice(0, 3);
```

### Threshold Recalculation

Happens automatically as collection size changes - always the top 20%.

## Implementation

### Files to Modify

1. **`frontend/src/views/HomeView.vue`**
   - Remove "Quick Links" section (lines 243-263)
   - Import and place `CollectionSpotlight` component

2. **`frontend/src/components/dashboard/CollectionSpotlight.vue`** (new file)
   - Fetches books from API (multiple pages if needed)
   - Sorts by value, takes top 20%
   - Shuffles and picks 2-3 on mount
   - Shows skeleton while loading
   - Renders spotlight cards

### Data Fetching Strategy

Separate fetch in the spotlight component rather than adding to dashboard endpoint. This is preferred because:

- Dashboard has heavy Lambda cold starts
- Progressive loading feels faster (dashboard stats appear first, spotlight loads after)
- No backend changes required
- Spotlight is self-contained and easy to modify

### API Calls

```
GET /books?inventory_type=PRIMARY&page=1
GET /books?inventory_type=PRIMARY&page=2
... (up to 9 pages for 170 books)
```

Note: Consider adding a dedicated lightweight endpoint in the future if this becomes a performance concern.

## Current Top 20% Books (Reference)

| Rank | Title | Value | Binder |
|------|-------|-------|--------|
| 1 | Works of Charles Dickens (Library Ed.) | $4,750 | — |
| 2 | Kriss Kringle's Book | $1,800 | — |
| 3 | Kidnapped | $1,600 | Bayntun |
| 4 | Works (Kingsley) | $1,400 | Sotheran |
| 5 | Memoirs Life of Sir Walter Scott | $1,200 | — |
| 6 | Rubaiyat of Omar Khayyam | $1,200 | S&S |
| ... | ... | ... | ... |
| 34 | A Christmas Carol | $500 | — |

## Future Considerations

- Add a dedicated `/books/top` endpoint if fetching all pages becomes slow
- Consider caching the top 20% calculation if recalculating on every load is expensive
- Option to manually "pin" certain books to always appear in rotation
