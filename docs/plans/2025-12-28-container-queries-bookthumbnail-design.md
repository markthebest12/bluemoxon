# Container-Responsive BookThumbnail Design

**Issue:** #623
**Date:** 2025-12-28
**Status:** Approved

## Overview

Replace BookThumbnail's rigid `size` prop with Tailwind v4 container queries so it automatically adapts to its container width while maintaining proper aspect ratio.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Scope | BookThumbnail only | Validate pattern before applying to other components |
| Size prop | Remove entirely | Container queries make explicit sizing unnecessary |
| Breakpoints | 2-tier (<200px, ≥200px) | Simple, covers main use cases |
| Sizing model | Aspect ratio + fill width | Parent controls width, component maintains 4:5 ratio |

## Implementation

### BookThumbnail.vue Changes

**Props (remove size):**

```typescript
// Before
defineProps<{
  bookId: number;
  imageUrl?: string | null;
  size?: "sm" | "md" | "lg";
}>();

// After
defineProps<{
  bookId: number;
  imageUrl?: string | null;
}>();
```

**Template:**

```vue
<template>
  <!-- Wrapper becomes @container -->
  <div class="@container w-full">
    <!-- Inner element uses container query variants -->
    <div class="aspect-[4/5] w-full @sm:max-w-24 relative rounded-xs overflow-hidden bg-victorian-paper-cream border border-victorian-paper-antique transition-all"
         :class="hasImage ? 'cursor-pointer hover:border-victorian-gold-muted hover:shadow-md' : ''">
      <img :src="imageUrl || placeholderUrl" class="w-full h-full object-cover" ... />
      <!-- Badge adjusts text size based on container -->
      <div v-if="hasImage" class="absolute bottom-1 right-1 ... text-xs @xs:text-[10px]">
        ...
      </div>
    </div>
  </div>
</template>
```

**Breakpoint Behavior:**

| Container Width | Thumbnail Behavior |
|-----------------|-------------------|
| < 200px | Full container width, smaller badge text |
| ≥ 200px | Capped at 96px width (w-24) |

### Parent Component Changes

**BooksView.vue:**

```vue
<!-- Before -->
<BookThumbnail :book-id="book.id" :image-url="book.primary_image_url" size="md" />

<!-- After: Parent controls width -->
<div class="w-24">
  <BookThumbnail :book-id="book.id" :image-url="book.primary_image_url" />
</div>
```

**BookDetailView.vue:**

```vue
<!-- Before -->
<BookThumbnail :book-id="booksStore.currentBook.id" size="lg" />

<!-- After: Parent provides larger container -->
<div class="w-48">
  <BookThumbnail :book-id="booksStore.currentBook.id" />
</div>
```

## Testing

### Unit Tests (BookThumbnail.spec.ts)

Update existing tests to remove size prop references, add:

```typescript
describe('BookThumbnail container queries', () => {
  it('has @container class on wrapper')
  it('maintains 4:5 aspect ratio via aspect-[4/5] class')
  it('renders full width within container')
})
```

### Manual Testing

1. Verify thumbnail in BooksView list (w-24 container)
2. Verify thumbnail in BookDetailView placeholder (w-48 container)
3. Resize browser to confirm no viewport-based breakage

## Related Issues

- #630 - AnalysisViewer container queries (future)
- #631 - StatisticsDashboard container queries (future)
