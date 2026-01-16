# Book Detail View Analysis Buttons Enhancement

**Issue:** #459
**Date:** 2025-12-19
**Status:** Design Complete

## Problem

The book detail view (`/books/:id`) lacks generate/regenerate analysis functionality. The existing "View Analysis" button only appears when an analysis exists. Users (editors/admins) cannot trigger analysis generation from this view.

The AnalysisViewer component has a broken synchronous `generateAnalysis()` that times out or returns before completion.

## Solution

Add generate/regenerate analysis buttons to the BookDetailView's "Detailed Analysis" card, using the working async job pattern from AcquisitionsView.

## UI States

### State A: No analysis exists (editor/admin)

```
┌─────────────────────────────────────────────┐
│ 📊 Detailed Analysis                        │
│ Generate a Napoleon-style acquisition       │
│ analysis for this book.                     │
│                                             │
│ Model: [Sonnet 4.5 ▼]  [⚡ Generate Analysis]│
└─────────────────────────────────────────────┘
```

### State B: Analysis job running

```
┌─────────────────────────────────────────────┐
│ 📊 Detailed Analysis                        │
│ ⏳ Queued... (or "Analyzing...")            │
└─────────────────────────────────────────────┘
```

### State C: Analysis exists (editor/admin)

```
┌─────────────────────────────────────────────┐
│ 📊 Detailed Analysis                        │
│ View the full Napoleon-style acquisition    │
│ analysis for this book.                     │
│                                             │
│ [View Analysis] Model: [▼] [🔄 Regenerate]  │
└─────────────────────────────────────────────┘
```

### State D: Analysis exists (viewer)

```
┌─────────────────────────────────────────────┐
│ 📊 Detailed Analysis                        │
│ [View Analysis]                             │
└─────────────────────────────────────────────┘
```

## Technical Approach

### Use Async Job Pattern (not sync)

The AcquisitionsView uses `booksStore.generateAnalysisAsync()` which:

1. POSTs to `/books/{id}/analysis/generate-async`
2. Returns immediately with job info
3. Starts polling via `startJobPoller(bookId)`
4. Updates `activeAnalysisJobs` Map reactively
5. On completion, sets `currentBook.has_analysis = true`

This pattern works. The AnalysisViewer's sync approach does not.

### Implementation in BookDetailView

**Imports:**

```typescript
import { storeToRefs } from "pinia";
const { activeAnalysisJobs } = storeToRefs(booksStore);
```

**State:**

```typescript
const startingAnalysis = ref(false);
const selectedModel = ref<"sonnet" | "opus">("sonnet");

const modelOptions = [
  { value: "sonnet", label: "Sonnet 4.5" },
  { value: "opus", label: "Opus 4.5" },
];
```

**Functions:**

```typescript
function isAnalysisRunning(): boolean {
  if (!booksStore.currentBook) return false;
  return booksStore.hasActiveJob(booksStore.currentBook.id);
}

function getJobStatus() {
  if (!booksStore.currentBook) return null;
  return booksStore.getActiveJob(booksStore.currentBook.id);
}

async function handleGenerateAnalysis() {
  const book = booksStore.currentBook;
  if (!book || isAnalysisRunning() || startingAnalysis.value) return;

  startingAnalysis.value = true;
  try {
    await booksStore.generateAnalysisAsync(book.id, selectedModel.value);
  } catch (e: any) {
    alert(e.response?.data?.detail || "Failed to start analysis");
  } finally {
    startingAnalysis.value = false;
  }
}
```

### Visibility

- Generate/Regenerate buttons: `authStore.isEditor` (includes admin + editor)
- View Analysis button: all authenticated users

### Files Modified

- `frontend/src/views/BookDetailView.vue` - Add analysis generation UI and logic

### Files NOT Modified

- `frontend/src/components/books/AnalysisViewer.vue` - Keep as view/edit only modal
- `frontend/src/stores/books.ts` - Already has all required functions

## Out of Scope

- Removing the broken sync generation from AnalysisViewer (can be done separately)
- Extracting shared composable (YAGNI - only 2 locations use this)
