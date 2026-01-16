# Error Handling Design - Issue #855

**Date:** 2026-01-05
**Issue:** [#855](https://github.com/bluemoxon/bluemoxon/issues/855) - Fix silent error handling (empty catch blocks)
**Status:** Approved

## Summary

Create a toast notification system for user-facing error feedback, replacing silent catch blocks with proper error handling.

## Decisions

| Decision | Choice |
|----------|--------|
| Approach | Composable + Toast (no external library) |
| Position | Top-right stack, auto-dismiss 5s |
| Toast types | Error + Success |
| Scope | Critical path first (8 catch blocks) |

## Architecture

```text
frontend/src/
├── composables/
│   └── useToast.ts          # Composable for triggering toasts
├── components/
│   └── ToastContainer.vue   # Global container (mounted in App.vue)
└── utils/
    └── errorHandler.ts      # Wraps existing error utils + toast integration
```

### Flow

1. `ToastContainer.vue` renders in `App.vue` (fixed position, top-right)
2. `useToast()` composable provides `showError()` and `showSuccess()`
3. `errorHandler.ts` combines existing `getErrorMessage()` with toast display
4. Components call `handleApiError(error, "Loading books")` - logs, extracts message, shows toast

## Component: ToastContainer

**Visual design:**

```text
┌─────────────────────────────────┐
│ ✕  Failed to load images        │  ← Error toast (red)
└─────────────────────────────────┘
┌─────────────────────────────────┐
│ ✓  Book deleted successfully    │  ← Success toast (green)
└─────────────────────────────────┘
```

**Styling:** Uses existing CSS variables:

- Error: `--color-status-error-bg`, `--color-status-error-border`, `--color-status-error-accent`
- Success: `--color-status-success-bg`, `--color-status-success-border`, `--color-status-success-accent`

**Behavior:**

- Max 3 toasts visible (oldest dismissed if exceeded)
- 5 second auto-dismiss
- Click dismiss button or toast to close early
- Hover pauses auto-dismiss timer
- Slide-in animation from right
- Stack from top, new toasts push down

**Accessibility:**

- `role="alert"` and `aria-live="polite"`
- Dismiss button has `aria-label="Dismiss notification"`

## API: useToast Composable

```typescript
interface Toast {
  id: number
  type: 'error' | 'success'
  message: string
  timestamp: number
}

function showError(message: string): void
function showSuccess(message: string): void
function dismiss(id: number): void
const toasts: Readonly<Ref<Toast[]>>
```

## API: errorHandler Utility

```typescript
// Main function - use in catch blocks
function handleApiError(error: unknown, context: string): string

// For success actions
function handleSuccess(message: string): void
```

**Usage:**

```typescript
try {
  await api.delete(`/books/${id}/images/${imageId}`)
  handleSuccess("Image deleted")
} catch (e) {
  handleApiError(e, "Deleting image")
}
```

## Files to Update (Critical Path)

| File | Line | Change |
|------|------|--------|
| `stores/auth.ts` | 118 | Add `handleApiError(e, "Checking session")` |
| `stores/references.ts` | 35 | Replace with `handleApiError(e, "Loading authors")` |
| `stores/references.ts` | 44 | Replace with `handleApiError(e, "Loading publishers")` |
| `stores/references.ts` | 53 | Replace with `handleApiError(e, "Loading binders")` |
| `views/BookDetailView.vue` | 112 | Add `handleApiError(e, "Loading images")` |
| `views/BookDetailView.vue` | 164 | Add `handleApiError(e, "Refreshing images")` |
| `components/books/ImageCarousel.vue` | 55 | Add `handleApiError(e, "Loading carousel")` |

**Not changing (intentional):**

- `stores/auth.ts:137` - Intentional during logout
- `AdminView.vue` catches - Already delegate to store
- Date parsing catches - Cosmetic fallbacks
- URL validation catches - Boolean returns correct

**Success toasts to add:**

- `BookDetailView.vue` - after image delete
- `BookDetailView.vue` - after image upload

## Testing Strategy

| File | Tests |
|------|-------|
| `composables/useToast.spec.ts` | Composable unit tests |
| `components/ToastContainer.spec.ts` | Component rendering tests |
| `utils/errorHandler.spec.ts` | Integration with toast |

**Key test cases:**

- `showError()` / `showSuccess()` add toast with correct type
- Auto-dismiss after 5 seconds (fake timers)
- Max 3 toasts enforced
- Dismiss removes specific toast
- Accessibility attributes present
- errorHandler extracts message and calls showError
