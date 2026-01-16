# Mobile Acquisitions Header Design

**Issue:** [#697](https://github.com/bluemoxon/bluemoxon/issues/697)
**Date:** 2025-12-30
**Status:** Approved

## Problem

The Acquisitions page header looks cluttered on mobile devices:

- Title and subtitle compete for space with two action buttons
- "Import from eBay" and "+ Add Manually" buttons take significant horizontal space
- No responsive breakpoints - same layout on all screen sizes

## Design Decisions

1. **Icon-only buttons on mobile** - Collapse button text, show only icons on mobile (< 640px)
2. **Hide subtitle on mobile** - Show only "Acquisitions" title on mobile
3. **Subtle Victorian ornament** - Add ❧ flourish after title on desktop only

## Layout Specifications

### Mobile (< 640px)

```
┌─────────────────────────────────┐
│ Acquisitions                    │
│ [🔗] [+]                        │
└─────────────────────────────────┘
```

- Header stacks vertically (flex-col)
- Title only, no subtitle
- Icon-only buttons below title

### Desktop (≥ 640px)

```
┌──────────────────────────────────────────────────────┐
│ Acquisitions ❧                   [🔗 Import] [+ Add] │
│ Track books from watchlist through delivery          │
└──────────────────────────────────────────────────────┘
```

- Side-by-side layout (flex-row, justify-between)
- Full subtitle visible
- Full button text with icons
- Decorative ❧ ornament after title

## Implementation

### File: `frontend/src/views/AcquisitionsView.vue`

**Header container (line ~345):**

```html
<div class="mb-6 flex flex-col sm:flex-row sm:items-start sm:justify-between">
```

**Title with ornament:**

```html
<div class="flex items-center gap-2">
  <h1 class="text-2xl font-bold text-gray-900">Acquisitions</h1>
  <span class="hidden sm:inline text-victorian-gold-500 opacity-60">❧</span>
</div>
```

**Subtitle:**

```html
<p class="hidden sm:block text-gray-600">Track books from watchlist through delivery</p>
```

**Buttons container:**

```html
<div class="flex gap-2 mt-3 sm:mt-0">
```

**Import button:**

```html
<button data-testid="import-from-ebay" @click="openImportModal"
        class="btn-primary text-sm flex items-center gap-2">
  <span>🔗</span>
  <span class="hidden sm:inline">Import from eBay</span>
</button>
```

**Add button:**

```html
<button data-testid="add-to-watchlist" @click="openWatchlistModal"
        class="btn-secondary text-sm flex items-center gap-2">
  <span>+</span>
  <span class="hidden sm:inline">Add Manually</span>
</button>
```

## Testing

- Existing tests use `data-testid` attributes which remain unchanged
- Manual verification needed for mobile viewport rendering
- Consider adding Playwright visual test for mobile breakpoint

## Files Modified

- `frontend/src/views/AcquisitionsView.vue` - header section only (~20 lines changed)
