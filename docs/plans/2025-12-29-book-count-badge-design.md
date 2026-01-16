# Design: Book Count Badge with Gold Flourish

**Issue:** #660 - Improve visual of book counts in book view
**Date:** 2025-12-29
**Status:** Approved

## Problem

The current book count in the filter/sort bar is displayed as a plain number in muted gray text at the far right, making it hard to notice and visually unengaging.

**Current implementation** (BooksView.vue:326-328):

```vue
<div class="ml-auto text-xs sm:text-sm text-[var(--color-text-muted)]">
  {{ booksStore.total }}
</div>
```

## Solution

Replace with a styled "Gold Flourish" badge that matches the Victorian aesthetic of the application.

### Visual Design

```text
Desktop:  ✦ 42 books ✦
Mobile:   42 (pill only)
```

### Styling Specifications

| Property | Value |
|----------|-------|
| Background | `rgba(201, 162, 39, 0.1)` (light gold tint) |
| Border | `1px solid rgba(201, 162, 39, 0.3)` |
| Text color | `var(--color-text-primary)` |
| Flourish color | Gold at 60% opacity |
| Padding | `px-3 py-1` (comfortable pill shape) |
| Border radius | `rounded-full` |
| Font size | `text-sm` |

### Responsive Behavior

- **Desktop (sm+)**: Full format with flourishes: `✦ 42 books ✦`
- **Mobile**: Compact pill with just the number: `42`

### Component Structure

Create a reusable `BookCountBadge.vue` component:

```vue
<template>
  <div class="book-count-badge">
    <span class="flourish hidden sm:inline">✦</span>
    <span class="count">{{ count }}</span>
    <span class="label hidden sm:inline">books</span>
    <span class="flourish hidden sm:inline">✦</span>
  </div>
</template>
```

### Integration

Replace the current plain text in BooksView.vue filter bar with:

```vue
<BookCountBadge :count="booksStore.total" />
```

## Files to Modify

1. **Create**: `frontend/src/components/books/BookCountBadge.vue`
2. **Modify**: `frontend/src/views/BooksView.vue` (import and use component)

## Testing Strategy

- Unit test: Component renders correct count
- Unit test: Responsive classes applied correctly
- Unit test: Pluralization (1 book vs 2 books) if implemented
- Visual verification in browser

## Future Considerations

- Could extend to show "Showing X of Y" when filters active
- Animation on count change (optional enhancement)
