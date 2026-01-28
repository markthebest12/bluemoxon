# Node Detail Panel Redesign - Phase 1 pt 2

## Overview

Redesign the node/edge detail panels in Social Circles to enable graph exploration without losing context. The current modal covers the entire graph, making navigation and testing impossible.

**Phase:** 1 pt 2 (foundation work before Phase 2)

## Problems with Current Implementation

1. **Panel covers entire graph** - Can't see or interact with network while viewing details
2. **Shows wrong books** - API call returns unrelated books (bug - see #1377)
3. **Raw tier values** - Shows "TIER_2" instead of human-friendly display
4. **No graph navigation** - Can't click to related nodes from panel

## Design Summary

| User Action | Opens | Panel Type | Size |
|-------------|-------|------------|------|
| Click **node** (author/publisher/binder) | Entity summary | Floating card | ~280px wide, max-height 400px |
| Click **edge** (connection line) | Relationship details | Slide-out sidebar | 30-40% viewport width |

---

## Interaction Model

### Mutual Exclusivity
Only one panel open at a time:
- Click edge → edge sidebar opens
- While edge sidebar open, click node → sidebar **closes**, card **opens**
- While card open, click edge → card **closes**, sidebar **opens**

### Close Methods
- Click graph background (outside any node/edge)
- X button in panel corner
- ESC key

### Toggle Behavior
Clicking the **same** node/edge that's already selected:
- Closes the panel/card
- **Keeps the item selected/highlighted** in the graph
- Allows "peek and dismiss" - check details, close UI, keep visual reference

Selection clears when clicking a different item or using close methods.

### Pinned Mode (Optional Enhancement)
Power users may want to keep a card open while exploring connections:

```
┌────────────────────────────────┐
│                    [📌] [X]    │  ← Pin icon
│  Charles Dickens               │
│  ...                           │
└────────────────────────────────┘
```

- Click pin icon → card stays open even when clicking background
- Click pin again → returns to normal "click-away" behavior

```typescript
const isPinned = ref(false);

function handleBackgroundClick() {
  if (!isPinned.value) {
    closePanel();
  }
}
```

### Keyboard Navigation

| Key | Action |
|-----|--------|
| ESC | Close panel |
| Tab | Cycle through clickable items in panel |
| Arrow Down/Up | Navigate between connections in mini-list |
| Enter | Click focused item |

```vue
<div
  ref="panelRef"
  role="dialog"
  aria-modal="false"
  @keydown.esc="close"
  @keydown.tab="handleTab"
  @keydown.arrow-down="focusNextConnection"
>
```

### Animations
- ~200ms transitions with sepia fade-in (Victorian aesthetic)
- **Sidebar:** Slides in from right edge
- **Floating card:** Fades in with slight scale (0.95 → 1.0)
- **Close:** Reverse animations, same timing

**Easing curves:** Victorian = subtle elegance, not linear motion.

```css
/* Subtle spring for period feel */
.card-enter-active {
  transition: transform 200ms cubic-bezier(0.4, 0.0, 0.2, 1),
              opacity 200ms ease-out;
}

.card-leave-active {
  transition: transform 150ms cubic-bezier(0.4, 0.0, 1, 1),
              opacity 150ms ease-in;
}

/* Alternative: subtle bounce */
.card-enter-active {
  transition: transform 200ms cubic-bezier(0.34, 1.56, 0.64, 1),
              opacity 200ms ease-out;
}
```

**Performance requirements:**
- Use `transform` and `opacity` only (GPU-accelerated)
- Avoid `left`, `width`, `height` transitions (trigger layout recalculation)
- Use `will-change` sparingly, remove after animation

```css
.floating-card {
  will-change: transform, opacity;
}

.floating-card.animation-done {
  will-change: auto;
}
```

**Animation Interruptibility:**
- Animations can be interrupted by user actions
- Card animating IN + user clicks background → Reverse animation immediately (don't wait)
- Card animating OUT + user clicks new node → Complete OUT animation, then start IN for new node
- Prevents animation jank and "stuck" UI states

---

## Node Floating Card

### Positioning

Smart placement - card appears on whichever side of the clicked node has the most available space.

**Algorithm:**

```typescript
interface Position { x: number; y: number; }
interface Size { width: number; height: number; }
type Quadrant = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';

function getBestCardPosition(
  nodePos: Position,
  cardSize: Size,
  viewport: Size,
  margin: number = 20
): { position: Position; quadrant: Quadrant } {
  // 1. Calculate available space in each quadrant
  const quadrants = {
    'top-left': {
      width: nodePos.x - margin,
      height: nodePos.y - margin,
    },
    'top-right': {
      width: viewport.width - nodePos.x - margin,
      height: nodePos.y - margin,
    },
    'bottom-left': {
      width: nodePos.x - margin,
      height: viewport.height - nodePos.y - margin,
    },
    'bottom-right': {
      width: viewport.width - nodePos.x - margin,
      height: viewport.height - nodePos.y - margin,
    },
  };

  // 2. Score each quadrant
  // - Can fit card? (required)
  // - Distance from edges (higher = better)
  // - Prefer right over left (reading order)
  // - Prefer bottom over top (natural flow)
  const scores = Object.entries(quadrants).map(([name, space]) => {
    const canFit = space.width >= cardSize.width && space.height >= cardSize.height;
    if (!canFit) return { name, score: -1 };

    let score = 0;
    score += Math.min(space.width - cardSize.width, 100);  // Edge distance
    score += Math.min(space.height - cardSize.height, 100);
    if (name.includes('right')) score += 20;  // Prefer right
    if (name.includes('bottom')) score += 10; // Prefer bottom

    return { name, score };
  });

  // 3. Pick best quadrant
  const best = scores.reduce((a, b) => a.score > b.score ? a : b);
  const quadrant = best.name as Quadrant;

  // 4. Calculate position with margin
  const position = {
    x: quadrant.includes('right') ? nodePos.x + margin : nodePos.x - cardSize.width - margin,
    y: quadrant.includes('bottom') ? nodePos.y + margin : nodePos.y - cardSize.height - margin,
  };

  return { position, quadrant };
}
```

### Card Sizing
- Width: ~280px fixed
- Max height: 400px with `overflow-y: auto`
- Show first 5 connections, then "[View N more in full profile →]"

```
Connections: (showing 5 of 12)
 → John Murray
 → Percy Shelley
 → Leigh Hunt
 → William Wordsworth
 → Samuel Coleridge
 [View 7 more in full profile →]
```

### Type-Specific Layouts

Three distinct card layouts optimized for each entity type:

#### Author Card
```
┌────────────────────────────────┐
│ ┌──────────┐                   │
│ │ Victorian│  Charles Dickens  │
│ │ portrait │  ★★★ (tier icons) │
│ │ litho    │  1812 - 1870      │
│ └──────────┘  Victorian Era    │
├────────────────────────────────┤
│ 12 books · 5 connections       │
├────────────────────────────────┤
│ Connections: (showing 5 of 12) │
│  📚 Chapman & Hall (publisher) │
│  📚 Bradbury & Evans (publisher│
│  🤝 Hablot Browne (author)     │
│  🪡 Rivière & Son (binder)     │
│  [+8 more...]                  │
├────────────────────────────────┤
│ [View Full Profile →]          │
└────────────────────────────────┘
```

#### Publisher Card
```
┌────────────────────────────────┐
│ ┌──────────┐                   │
│ │ Publisher│  Chapman & Hall   │
│ │ office / │  ★★★ (tier icons) │
│ │ logo     │  Est. 1830        │
│ └──────────┘  London           │
├────────────────────────────────┤
│ 8 books · 12 authors           │
├────────────────────────────────┤
│ Connections: (showing 5 of 12) │
│  📚 Charles Dickens (author)   │
│  📚 William Thackeray (author) │
│  [+10 more...]                 │
├────────────────────────────────┤
│ [View Full Profile →]          │
└────────────────────────────────┘
```

#### Binder Card
```
┌────────────────────────────────┐
│ ┌──────────┐                   │
│ │ Bindery  │  Riviere & Son    │
│ │ workshop │  ★★ (tier icons)  │
│ │ image    │  Est. 1840        │
│ └──────────┘  Fine leather     │
├────────────────────────────────┤
│ 6 books · 4 authors            │
├────────────────────────────────┤
│ Connections:                   │
│  🪡 John Ruskin (author)       │
│  🪡 Alfred Tennyson (author)   │
│  [+2 more...]                  │
├────────────────────────────────┤
│ [View Full Profile →]          │
└────────────────────────────────┘
```

### Connection Type Icons

Visual indicators for quick scanning:

| Icon | Connection Type |
|------|-----------------|
| 📚 | Publisher relationship |
| 🤝 | Author-to-author (shared publisher) |
| 🪡 | Binder relationship |

**Alternative:** Use Victorian sticker icons instead of emoji.

### Card Interactions
- **Clicking a connection** in the mini-list → selects that edge (closes card, opens sidebar, highlights connection)
- **View Full Profile** → links to entity page (future feature, can be disabled initially)
- **Hover on book/connection** → underline + pointer cursor (visual affordance)

---

## Edge Sidebar

### Layout
- Slides in from right
- Takes 30-40% viewport width
- Graph remains visible and interactive on the left

### Scroll Behavior

```vue
<div class="edge-sidebar">
  <div class="sidebar-header">
    <!-- Source/target entities - STICKY -->
  </div>
  <div class="sidebar-content" style="overflow-y: auto; max-height: calc(100vh - 120px);">
    <!-- Scrollable book list -->
  </div>
  <div class="sidebar-footer">
    <!-- Action buttons - STICKY -->
  </div>
</div>
```

Header and footer remain sticky; only middle content scrolls.

### Type-Specific Layouts

Three distinct sidebar layouts for each connection type:

#### Publisher Connection (Author → Publisher)
```
┌─────────────────────────────────────────┐
│                                 [📌] [X]│
│  ┌─────────┐          ┌─────────┐      │
│  │ Author  │    →     │Publisher│      │
│  │ portrait│          │ office  │      │
│  └─────────┘          └─────────┘      │
│                                         │
│  Charles Dickens  ──  Chapman & Hall    │
│  (click to view)      (click to view)   │
├─────────────────────────────────────────┤
│  CONNECTION: Published together         │
│  Strength: ●●●●○ (4 works)              │
├─────────────────────────────────────────┤
│  Shared Books                           │
│  ┌─────────────────────────────────┐   │
│  │ 📖 The Pickwick Papers (1837)   │   │
│  │ 📖 Oliver Twist (1838)          │   │
│  │ 📖 Nicholas Nickleby (1839)     │   │
│  │ 📖 The Old Curiosity Shop (1841)│   │
│  └─────────────────────────────────┘   │
├─────────────────────────────────────────┤
│  [View Author Page] [View Publisher]    │
└─────────────────────────────────────────┘
```

#### Shared Publisher Connection (Author ↔ Author)

**Simple case (one shared publisher):**
```
┌─────────────────────────────────────────┐
│                                 [📌] [X]│
│  ┌─────────┐          ┌─────────┐      │
│  │ Author  │    ↔     │ Author  │      │
│  │ portrait│          │ portrait│      │
│  └─────────┘          └─────────┘      │
│                                         │
│  Charles Dickens  ──  William Thackeray │
│  (click to view)      (click to view)   │
├─────────────────────────────────────────┤
│  CONNECTION: Shared Publisher           │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ Both published by:              │   │
│  │ ┌─────────┐                     │   │
│  │ │Publisher│  Chapman & Hall     │   │
│  │ │ logo    │  (click to view)    │   │
│  │ └─────────┘                     │   │
│  └─────────────────────────────────┘   │
├─────────────────────────────────────────┤
│  [View Dickens] [View Thackeray]        │
└─────────────────────────────────────────┘
```

**Multiple shared publishers case:**
```
┌─────────────────────────────────────────┐
│  CONNECTION: Shared Publishers (2)      │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ Chapman & Hall                  │   │
│  │ ● 5 Dickens books               │   │
│  │ ● 5 Thackeray books             │   │
│  │ (click to view publisher)       │   │
│  ├─────────────────────────────────┤   │
│  │ Bradbury & Evans                │   │
│  │ ● 2 Dickens books               │   │
│  │ ● 2 Thackeray books             │   │
│  │ (click to view publisher)       │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

Shows **why** the connection strength is high - multiple shared publishers.

#### Binder Connection (Author → Binder)
```
┌─────────────────────────────────────────┐
│                                 [📌] [X]│
│  ┌─────────┐          ┌─────────┐      │
│  │ Author  │    →     │ Bindery │      │
│  │ portrait│          │workshop │      │
│  └─────────┘          └─────────┘      │
│                                         │
│  John Ruskin    ──    Riviere & Son     │
│  (click to view)      (click to view)   │
├─────────────────────────────────────────┤
│  CONNECTION: Bound works                │
│  Strength: ●●○○○ (2 works)              │
├─────────────────────────────────────────┤
│  Bound Books                            │
│  ┌─────────────────────────────────┐   │
│  │ 📖 Modern Painters Vol I (1843) │   │
│  │ 📖 The Stones of Venice (1851)  │   │
│  └─────────────────────────────────┘   │
├─────────────────────────────────────────┤
│  [View Author Page] [View Bindery]      │
└─────────────────────────────────────────┘
```

### Book List Interactivity

Clicking a book title navigates to the book detail page:

```vue
<a
  :href="`/books/${book.id}`"
  class="book-link"
>
  📖 Oliver Twist (1838)
</a>
```

Visual affordance: underline on hover, pointer cursor.

### Sidebar Interactions
- **Clicking entity names/images** at top → opens their floating card (closes sidebar)
- **Clicking book titles** → navigates to book detail page

---

## Visual Styling

### Curated Placeholder Images

Period-appropriate Victorian imagery (public domain). **This attention to detail separates "functional" from "delightful."**

**Directory structure:**
```
/public/images/entity-placeholders/
├── authors/
│   ├── generic-victorian-portrait-1.jpg
│   ├── generic-victorian-portrait-2.jpg
│   ├── generic-victorian-portrait-3.jpg
│   └── generic-victorian-portrait-4.jpg
├── publishers/
│   ├── london-bookshop-exterior.jpg
│   ├── victorian-printing-press.jpg
│   ├── publisher-office-interior.jpg
│   └── victorian-publisher-logo.jpg
└── binders/
    ├── bookbinding-tools.jpg
    ├── leather-workshop.jpg
    ├── bindery-workbench.jpg
    └── victorian-bindery-scene.jpg
```

**Image assignment:** Randomly assign on entity creation based on entity ID, or allow admin to upload specific images later.

**Sources:**
- Library of Congress Digital Collections
- British Library Flickr Commons
- Wikimedia Commons Victorian collections

### Image Optimization

Victorian images from source libraries can be 5MB+. Optimize for fast load times:

| Context | Dimensions | Format |
|---------|------------|--------|
| Card thumbnail | 200x200px | WebP (JPEG fallback) |
| Sidebar portrait | 400x400px | WebP (JPEG fallback) |

```html
<!-- Lazy loading with LQIP (Low-Quality Image Placeholder) -->
<img
  :src="entity.image || getPlaceholderImage(entity.type, entity.id)"
  loading="lazy"
  decoding="async"
  width="200"
  height="200"
  :alt="`Portrait of ${entity.name}`"
/>
```

**Requirements:**
- Serve from `/images/entity-placeholders/` (static assets, CDN-cached)
- Generate WebP versions at build time
- Include JPEG fallback for older browsers
- Maximum file size: 50KB per image

### Tier Icons with Accessibility

Victorian-style icons from `/stickers` collection instead of text labels.

```html
<!-- Accessible tier display -->
<span class="sr-only">Tier 1 - Premier Publisher</span>
<div class="tier-icons" aria-hidden="true" title="Tier 1 - Premier Publisher">
  ★★★
</div>
```

- Show tooltip on hover with tier description
- Screen reader text for accessibility (stars alone are not accessible)

### Color Palette

Exact hex values for pixel-perfect implementation:

```css
:root {
  /* Backgrounds */
  --color-card-bg: #F5F1E8;          /* Sepia cream */
  --color-sidebar-bg: #FAF8F3;       /* Lighter cream */
  --color-skeleton-bg: #E8E4DB;      /* Skeleton shimmer */

  /* Text */
  --color-text-primary: #2C2416;     /* Victorian ink */
  --color-text-secondary: #5C5446;   /* Faded ink */
  --color-text-muted: #8B8579;       /* Subtle text */

  /* Interactive */
  --color-accent-gold: #B8860B;      /* Dark goldenrod */
  --color-hover: #8B4513;            /* Saddle brown */
  --color-selected: #2C5F77;         /* Victorian blue */
  --color-link: #6B4423;             /* Book spine brown */

  /* Borders */
  --color-border: #D4CFC4;           /* Subtle cream border */
  --color-border-strong: #A69F92;    /* Stronger border */

  /* Entity type accents (match graph nodes) */
  --color-author: #7B4B94;           /* Victorian purple */
  --color-publisher: #2C5F77;        /* Victorian blue */
  --color-binder: #8B4513;           /* Leather brown */
}
```

### Hover States

Visual affordance - users need to know what's clickable:

```css
/* Connection items */
.connection-item:hover {
  background: rgba(184, 134, 11, 0.1); /* Gold tint */
  transform: translateX(4px);
  transition: all 150ms ease-out;
}

/* Book links */
.book-link:hover {
  color: var(--color-accent-gold);
  text-decoration: underline;
  text-decoration-color: rgba(184, 134, 11, 0.4);
}

/* Entity names (clickable) */
.entity-name:hover {
  color: var(--color-hover);
  cursor: pointer;
  text-decoration: underline;
}

/* Buttons */
.action-button:hover {
  background: var(--color-accent-gold);
  color: white;
  transform: translateY(-1px);
}
```

### Typography
- Headers: Serif font (period-appropriate feel)
- Body: Readable sans-serif for data
- Book titles: Italic treatment

---

## Loading States

### Card Loading Skeleton

200ms animation + potential API delay = noticeable. Skeleton prevents "flash of empty content."

```vue
<div v-if="loading" class="card-skeleton">
  <div class="skeleton-image"></div>
  <div class="skeleton-text"></div>
  <div class="skeleton-text short"></div>
</div>
```

```
┌────────────────────────────────┐
│ ┌──────────┐  ░░░░░░░░░░░░░░░ │
│ │ ░░░░░░░░ │  ░░░░░░░░░░░░░░░ │
│ │ ░░░░░░░░ │  ░░░░░░░░        │
│ └──────────┘                   │
├────────────────────────────────┤
│ ░░░░░░░░░░░░░░░░░░░░          │
├────────────────────────────────┤
│ ░░░░░░░░░░░░░░░░░             │
│ ░░░░░░░░░░░░░░░░░             │
│ ░░░░░░░░░░░░░░░░░             │
└────────────────────────────────┘
```

### Sidebar Loading Skeleton

```vue
<div v-if="loading" class="sidebar-skeleton">
  <div class="skeleton-header"></div>
  <div class="skeleton-books">
    <div class="skeleton-book"></div>
    <div class="skeleton-book"></div>
    <div class="skeleton-book"></div>
  </div>
</div>
```

- Animated shimmer effect on all placeholder elements
- Dim action buttons until loaded

---

## Error States

### API Failure

```vue
<div v-if="error" class="card-error">
  <p>Unable to load details</p>
  <button @click="retry">Try Again</button>
</div>
```

Log error for debugging. Fallback to cached data if available.

### Empty States

**No connections:**
```
Connections: None found

This entity isn't connected to books
in your collection yet.
```

**No books:**
```
No books in your collection from this publisher.
```

**No image:**
Show generic Victorian-style placeholder per entity type (from `/public/images/entity-placeholders/`).

### Network Timeout

After 10 seconds:
```
Taking longer than expected.
[Cancel] [Keep Waiting]
```

---

## Responsive Behavior

### Breakpoints

| Breakpoint | Device | Floating Card | Edge Sidebar |
|------------|--------|---------------|--------------|
| <768px | Mobile | Bottom sheet | Full-width overlay |
| 768-1024px | Tablet | Smart positioned | 50% width |
| >1024px | Desktop | Smart positioned | 30-40% width |

### Touch Target Sizes (Accessibility)

```css
/* iOS guideline: 44x44px minimum */
.mobile-button,
.close-button,
.pin-button {
  min-width: 44px;
  min-height: 44px;
  padding: 12px;
}

/* Android material guideline: 48px */
.connection-item,
.book-item {
  min-height: 48px;
  padding: 12px 16px;
}

/* Drag handle for mobile bottom sheet */
.drag-handle {
  width: 40px;
  height: 4px;
  margin: 12px auto;
}
```

### Mobile (<768px)

**Floating Card:**
- Fixed to bottom 20% of viewport (bottom sheet pattern)
- Swipe down to dismiss
- Graph dims 40% behind card (focus on content)
- Touch gestures still work on dimmed graph (pan/zoom)

```
┌─────────────────────────────────┐
│           [Drag handle]          │ ← Swipe down to dismiss
│                                  │
│  Charles Dickens                 │
│  1812 - 1870                     │
│  Victorian Era                   │
│                                  │
│  12 books · 5 connections        │
│  ...                             │
└─────────────────────────────────┘
```

**Edge Sidebar:**
- Full-width overlay
- Header: `[← Back to Graph]` `[X]`
- Swipe right edge to dismiss
- Graph hidden while sidebar open
- Smooth 200ms slide-in/out

### Tablet (768-1024px)

**Floating Card:**
- Smart positioned (same as desktop)
- Slightly larger touch targets

**Edge Sidebar:**
- 50% viewport width
- Graph visible but interaction limited
- Tap graph area to close sidebar

### Touch Gestures
- Swipe card down → dismiss
- Swipe sidebar right → dismiss
- Pinch-zoom still works on graph while card open

---

## Z-Index Layering

| Layer | Element | Z-Index |
|-------|---------|---------|
| 1 | Base graph | 1 |
| 2 | Graph tooltips | 1000 |
| 3 | Floating node card | 2000 |
| 4 | Edge sidebar | 3000 |
| 5 | Modals (if any) | 4000 |

**Tooltip behavior with card/sidebar open:**
- Disable tooltips on other nodes when card/sidebar is open
- Otherwise tooltip over card = cluttered

---

## Focus Management (Accessibility)

When card/sidebar opens:
1. Focus moves to first interactive element (close button)
2. Tab cycles through clickable items
3. Tab from last item wraps to first (focus trap)
4. ESC closes and returns focus to graph

```vue
<script setup>
import { useFocusTrap } from '@vueuse/integrations/useFocusTrap';

const cardRef = ref<HTMLElement>();
const { activate, deactivate } = useFocusTrap(cardRef);

watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    nextTick(() => activate());
  } else {
    deactivate();
  }
});
</script>
```

---

## URL State Management

Selected node/edge persisted in URL for shareability:

```
/social-circles?node=author:123      → Byron card opens on page load
/social-circles?edge=e:author:123:publisher:456  → Sidebar opens on page load
```

**Benefits:**
- Shareable "look at this connection!" links
- Browser back/forward works
- Bookmark specific views

```typescript
// useUrlState.ts
watch(() => selection.selectedNodeId, (nodeId) => {
  if (nodeId) {
    router.replace({
      query: { ...route.query, node: nodeId }
    });
  }
});
```

---

## Data Transformations

### Tier Display Formatting

Backend returns raw `TIER_1`, `TIER_2`, `TIER_3`. Transform to human-friendly display:

```typescript
// utils/formatters.ts
interface TierDisplay {
  label: string;
  stars: number;
  tooltip: string;
}

export function formatTier(tier: string | null): TierDisplay {
  const tierMap: Record<string, TierDisplay> = {
    TIER_1: {
      label: 'Premier',
      stars: 3,
      tooltip: 'Tier 1 - Premier Figure'
    },
    TIER_2: {
      label: 'Established',
      stars: 2,
      tooltip: 'Tier 2 - Established Figure'
    },
    TIER_3: {
      label: 'Known',
      stars: 1,
      tooltip: 'Tier 3 - Known Figure'
    },
  };

  return tierMap[tier ?? ''] || {
    label: 'Unranked',
    stars: 0,
    tooltip: 'Unranked'
  };
}
```

### Connection Strength Formula

Strength displayed as filled circles (●●●○○). Formula:

```typescript
// Connection strength = number of shared books, capped at 5
function calculateStrength(sharedBooks: number): number {
  return Math.min(sharedBooks, 5);
}

// Display as filled/unfilled circles
function renderStrength(strength: number, max: number = 5): string {
  const filled = '●'.repeat(strength);
  const unfilled = '○'.repeat(max - strength);
  return filled + unfilled;
}

// Example: 4 shared books → "●●●●○ (4 works)"
```

**Rationale:** Simple count-based formula. Cap at 5 for visual simplicity - more than 5 shared books doesn't need finer granularity.

---

## Technical Notes

### Bug Fix Required
Current `NodeDetailPanel.vue` fetches wrong books - the API call at line ~80 uses `/books?ids=${ids}` but returns unrelated books instead of the entity's actual books. See GitHub issue #1377.

### Graph Interaction
While sidebar or card is open, users can still:
- Pan and zoom the graph
- Click different nodes/edges (triggers mutual exclusivity swap)
- Tooltips disabled to reduce clutter (see Z-Index section)

### Entity Page Links
"View Full Profile" buttons link to entity pages (future feature). Can be disabled or hidden initially if those pages don't exist yet.

---

## Related Issues

- Book fetching bug: #1377 (phase:1.6-detail-panel)
- Original Social Circles design: `docs/plans/2026-01-26-victorian-social-circles-design.md`

---

## Approval

- [x] Design approved by Mark (2026-01-27)
- [x] Implementation plan created: `docs/plans/2026-01-27-node-detail-panel-implementation.md`
