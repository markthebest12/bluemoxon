# Design: Split BookDetailView.vue (#856)

**Date:** 2026-01-06
**Issue:** #856 - refactor: Split BookDetailView.vue god component
**Status:** Approved

## Problem

`BookDetailView.vue` is 1132 lines with 15+ ref declarations handling:

- Image management (4 modals, upload, reorder, delete)
- Analysis job polling and generation
- Provenance editing
- Status management
- Delete confirmation
- Multiple modal states

This is a "god component" anti-pattern that makes the code hard to understand, test, and maintain.

## Solution

Split into focused child components using **props-down, events-up** pattern.

### Component Structure

```text
frontend/src/components/book-detail/
├── ImageGallerySection.vue    (~180 lines)
├── AnalysisSection.vue        (~200 lines)
├── ProvenanceSection.vue      (~100 lines)
├── BookMetadataSection.vue    (~180 lines)
├── BookSidebarSection.vue     (~150 lines)
└── BookActionsBar.vue         (~80 lines)
```

Parent `BookDetailView.vue` becomes ~250 line orchestrator.

### Component Interfaces

#### ImageGallerySection.vue

```typescript
// Props
bookId: number
images: BookImage[]
isEditor: boolean

// Emits
'open-carousel': (index: number) => void
'images-changed': (images: BookImage[]) => void

// Internal state
- uploadModalVisible, reorderModalVisible
- deleteImageModalVisible, imageToDelete, deletingImage, deleteImageError
```

#### AnalysisSection.vue

```typescript
// Props
book: Book  // needs: id, has_analysis, analysis_job_status, has_eval_runbook, analysis_issues
isEditor: boolean

// Internal (no emits - uses booksStore.generateAnalysisAsync directly)
- analysisVisible, evalRunbookVisible
- startingAnalysis, selectedModel
- analysisPoller composable
```

#### ProvenanceSection.vue

```typescript
// Props
bookId: number
provenance: string | null
isEditor: boolean

// Emits
'provenance-saved': (newProvenance: string | null) => void

// Internal state
- provenanceEditing, provenanceText, savingProvenance
```

#### BookMetadataSection.vue

```typescript
// Props
book: Book  // all publication/binding fields
isEditor: boolean

// Emits
'status-changed': (newStatus: string) => void

// Internal state
- updatingStatus
```

#### BookSidebarSection.vue

```typescript
// Props
book: Book  // valuation, acquisition, source fields
imageCount: number

// No emits - purely presentational
```

#### BookActionsBar.vue

```typescript
// Props
book: Book  // needs: id, title
isEditor: boolean

// Emits
'delete': () => void
'print': () => void
// Edit uses RouterLink directly
```

### Parent Orchestration

**BookDetailView.vue** owns:

- Route handling, back link computation
- `images` array (fetched on mount)
- `carouselVisible`, `carouselInitialIndex` (shared modal)
- Delete book modal state (navigates on success)
- Loading state display

**Template structure:**

```vue
<template>
  <div v-if="loading">Loading...</div>
  <div v-else-if="book" class="max-w-5xl mx-auto">
    <BookActionsBar :book="book" :is-editor="isEditor"
      @delete="handleDelete" @print="handlePrint" />

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <div class="lg:col-span-2 flex flex-col gap-6">
        <ImageGallerySection :book-id="book.id" :images="images" :is-editor="isEditor"
          @open-carousel="handleOpenCarousel" @images-changed="handleImagesChanged" />
        <BookMetadataSection :book="book" :is-editor="isEditor"
          @status-changed="handleStatusChanged" />
        <ProvenanceSection :book-id="book.id" :provenance="book.provenance" :is-editor="isEditor"
          @provenance-saved="handleProvenanceSaved" />
        <AnalysisSection :book="book" :is-editor="isEditor" />
      </div>
      <BookSidebarSection :book="book" :image-count="images.length" />
    </div>

    <ImageCarousel :visible="carouselVisible" ... />
    <DeleteBookModal :visible="deleteModalVisible" ... />
  </div>
</template>
```

### Key Decisions

1. **ImageCarousel stays in parent** - shared across gallery thumbnail clicks
2. **Delete book modal stays in parent** - navigates away on success
3. **Each section manages its own modals** - upload, reorder, delete image, analysis viewer, eval runbook
4. **AnalysisSection uses store directly** - avoids complex event chains for async operations

## Testing Strategy

**Test file structure:**

```text
frontend/src/components/book-detail/__tests__/
├── ImageGallerySection.spec.ts
├── AnalysisSection.spec.ts
├── ProvenanceSection.spec.ts
├── BookMetadataSection.spec.ts
├── BookSidebarSection.spec.ts
└── BookActionsBar.spec.ts
```

**Test categories:**

| Component | Key test cases |
|-----------|----------------|
| ImageGallerySection | Renders grid, opens carousel, editor-only buttons, delete flow |
| AnalysisSection | View button when has_analysis, polling state, generate calls store |
| ProvenanceSection | View/edit modes, save emits, cancel resets |
| BookMetadataSection | All fields display, status dropdown for editors, emits on change |
| BookSidebarSection | Currency formatting, conditional sections, stats display |
| BookActionsBar | Edit link, delete/print emits, editor-only visibility |

## Implementation Order

### Phase 1: Setup & Simplest Component

1. Create `frontend/src/components/book-detail/` directory
2. `BookSidebarSection.vue` - read-only, no events, simplest

### Phase 2: Actions & Metadata

3. `BookActionsBar.vue` - simple events, no internal state
2. `BookMetadataSection.vue` - one event, one internal state

### Phase 3: Interactive Sections

5. `ProvenanceSection.vue` - edit mode, save flow
2. `ImageGallerySection.vue` - multiple modals, complex

### Phase 4: Analysis

7. `AnalysisSection.vue` - polling, store integration, multiple states

### Phase 5: Integration

8. Refactor `BookDetailView.vue` to use all components
2. Manual verification of all functionality
3. Full test suite pass

## Success Criteria

- [ ] All existing functionality preserved
- [ ] `BookDetailView.vue` reduced from ~1130 to ~250 lines
- [ ] Each child component under 200 lines
- [ ] All new components have test coverage
- [ ] CI passes (lint, type-check, tests)

## Files to Create

- `frontend/src/components/book-detail/ImageGallerySection.vue`
- `frontend/src/components/book-detail/AnalysisSection.vue`
- `frontend/src/components/book-detail/ProvenanceSection.vue`
- `frontend/src/components/book-detail/BookMetadataSection.vue`
- `frontend/src/components/book-detail/BookSidebarSection.vue`
- `frontend/src/components/book-detail/BookActionsBar.vue`
- `frontend/src/components/book-detail/__tests__/` (6 test files)

## Files to Modify

- `frontend/src/views/BookDetailView.vue` (major refactor)
