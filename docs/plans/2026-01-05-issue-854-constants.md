# Issue #854: Extract Shared Constants Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract duplicated constants (statusOptions, magic numbers) into a centralized constants file.

**Architecture:** Create `frontend/src/constants/` directory with typed constants. Update consumers to import from centralized location.

**Tech Stack:** TypeScript, Vue 3

---

## Task 1: Create Constants File

**Files:**
- Create: `frontend/src/constants/index.ts`
- Test: `frontend/src/constants/__tests__/index.spec.ts`

**Step 1: Write the failing test**

```typescript
// frontend/src/constants/__tests__/index.spec.ts
import { describe, it, expect } from "vitest";
import {
  BOOK_STATUS_OPTIONS,
  BOOK_STATUSES,
  PAGINATION,
  UI_TIMING,
} from "../index";

describe("constants", () => {
  describe("BOOK_STATUS_OPTIONS", () => {
    it("has all required status options", () => {
      expect(BOOK_STATUS_OPTIONS).toHaveLength(4);
      expect(BOOK_STATUS_OPTIONS.map((s) => s.value)).toEqual([
        "EVALUATING",
        "ON_HAND",
        "IN_TRANSIT",
        "REMOVED",
      ]);
    });

    it("has display labels", () => {
      const evaluating = BOOK_STATUS_OPTIONS.find((s) => s.value === "EVALUATING");
      expect(evaluating?.label).toBe("EVAL");
    });
  });

  describe("BOOK_STATUSES", () => {
    it("exports status string constants", () => {
      expect(BOOK_STATUSES.EVALUATING).toBe("EVALUATING");
      expect(BOOK_STATUSES.ON_HAND).toBe("ON_HAND");
      expect(BOOK_STATUSES.IN_TRANSIT).toBe("IN_TRANSIT");
      expect(BOOK_STATUSES.REMOVED).toBe("REMOVED");
    });
  });

  describe("PAGINATION", () => {
    it("exports pagination limits", () => {
      expect(PAGINATION.DEFAULT_PER_PAGE).toBe(100);
      expect(PAGINATION.RECEIVED_PER_PAGE).toBe(50);
      expect(PAGINATION.RECEIVED_DAYS_LOOKBACK).toBe(30);
    });
  });

  describe("UI_TIMING", () => {
    it("exports timing constants", () => {
      expect(UI_TIMING.COMBOBOX_BLUR_DELAY_MS).toBe(200);
    });
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm run --prefix frontend test -- --run src/constants/__tests__/index.spec.ts`
Expected: FAIL with "Cannot find module '../index'"

**Step 3: Write minimal implementation**

```typescript
// frontend/src/constants/index.ts
/**
 * Centralized constants for the BlueMoxon frontend.
 * Extracted to eliminate duplication and magic numbers.
 */

/**
 * Book status string constants for type-safe comparisons.
 */
export const BOOK_STATUSES = {
  EVALUATING: "EVALUATING",
  ON_HAND: "ON_HAND",
  IN_TRANSIT: "IN_TRANSIT",
  REMOVED: "REMOVED",
} as const;

export type BookStatus = (typeof BOOK_STATUSES)[keyof typeof BOOK_STATUSES];

/**
 * Status dropdown options with display labels.
 * Used in BookDetailView.vue and BookForm.vue.
 */
export const BOOK_STATUS_OPTIONS = [
  { value: "EVALUATING", label: "EVAL" },
  { value: "ON_HAND", label: "ON HAND" },
  { value: "IN_TRANSIT", label: "IN TRANSIT" },
  { value: "REMOVED", label: "REMOVED" },
] as const;

export type BookStatusOption = (typeof BOOK_STATUS_OPTIONS)[number];

/**
 * Pagination configuration constants.
 */
export const PAGINATION = {
  /** Default items per page for API calls */
  DEFAULT_PER_PAGE: 100,
  /** Items per page for received books list */
  RECEIVED_PER_PAGE: 50,
  /** Days to look back for received items filter */
  RECEIVED_DAYS_LOOKBACK: 30,
} as const;

/**
 * UI timing constants in milliseconds.
 */
export const UI_TIMING = {
  /** Delay before closing combobox dropdown on blur */
  COMBOBOX_BLUR_DELAY_MS: 200,
} as const;
```

**Step 4: Run test to verify it passes**

Run: `npm run --prefix frontend test -- --run src/constants/__tests__/index.spec.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/constants/
git commit -m "feat(frontend): add centralized constants file (#854)"
```

---

## Task 2: Update BookDetailView.vue

**Files:**
- Modify: `frontend/src/views/BookDetailView.vue:78-83`

**Step 1: Verify existing behavior**

Run: `npm run --prefix frontend type-check`
Expected: PASS (baseline)

**Step 2: Update import and remove local constant**

Replace lines 78-83:
```typescript
// REMOVE:
const statusOptions = [
  { value: "EVALUATING", label: "EVAL" },
  { value: "ON_HAND", label: "ON HAND" },
  { value: "IN_TRANSIT", label: "IN TRANSIT" },
  { value: "REMOVED", label: "REMOVED" },
];
```

Add import at top (after line 10):
```typescript
import { BOOK_STATUS_OPTIONS } from "@/constants";
```

Update template reference from `statusOptions` to `BOOK_STATUS_OPTIONS` (line 583).

**Step 3: Run type-check**

Run: `npm run --prefix frontend type-check`
Expected: PASS

**Step 4: Commit**

```bash
git add frontend/src/views/BookDetailView.vue
git commit -m "refactor(frontend): use BOOK_STATUS_OPTIONS in BookDetailView (#854)"
```

---

## Task 3: Update BookForm.vue

**Files:**
- Modify: `frontend/src/components/books/BookForm.vue:85-91`

**Step 1: Update import and remove local constant**

Replace lines 85-91:
```typescript
// REMOVE:
const statuses = [
  { value: "EVALUATING", label: "EVAL" },
  { value: "ON_HAND", label: "ON HAND" },
  { value: "IN_TRANSIT", label: "IN TRANSIT" },
  { value: "REMOVED", label: "REMOVED" },
];
```

Add import at top (after line 7):
```typescript
import { BOOK_STATUS_OPTIONS } from "@/constants";
```

Update template reference from `statuses` to `BOOK_STATUS_OPTIONS` (line 325).

**Step 2: Run type-check**

Run: `npm run --prefix frontend type-check`
Expected: PASS

**Step 3: Commit**

```bash
git add frontend/src/components/books/BookForm.vue
git commit -m "refactor(frontend): use BOOK_STATUS_OPTIONS in BookForm (#854)"
```

---

## Task 4: Update acquisitions.ts

**Files:**
- Modify: `frontend/src/stores/acquisitions.ts:107,116,125,137`

**Step 1: Update imports and replace magic numbers**

Add import at top:
```typescript
import { PAGINATION } from "@/constants";
```

Replace magic numbers:
- Line 107: `per_page: 100` → `per_page: PAGINATION.DEFAULT_PER_PAGE`
- Line 116: `per_page: 100` → `per_page: PAGINATION.DEFAULT_PER_PAGE`
- Line 125: `per_page: 50` → `per_page: PAGINATION.RECEIVED_PER_PAGE`
- Line 137: `30` → `PAGINATION.RECEIVED_DAYS_LOOKBACK`

**Step 2: Run existing tests**

Run: `npm run --prefix frontend test -- --run src/stores/__tests__/acquisitions.spec.ts`
Expected: PASS

**Step 3: Commit**

```bash
git add frontend/src/stores/acquisitions.ts
git commit -m "refactor(frontend): use PAGINATION constants in acquisitions store (#854)"
```

---

## Task 5: Update ComboboxWithAdd.vue

**Files:**
- Modify: `frontend/src/components/ComboboxWithAdd.vue:85`

**Step 1: Update import and replace magic number**

Add import at top:
```typescript
import { UI_TIMING } from "@/constants";
```

Replace line 85:
```typescript
// FROM:
  }, 200);

// TO:
  }, UI_TIMING.COMBOBOX_BLUR_DELAY_MS);
```

**Step 2: Run existing tests**

Run: `npm run --prefix frontend test -- --run src/components/__tests__/ComboboxWithAdd.spec.ts`
Expected: PASS

**Step 3: Commit**

```bash
git add frontend/src/components/ComboboxWithAdd.vue
git commit -m "refactor(frontend): use UI_TIMING constant in ComboboxWithAdd (#854)"
```

---

## Task 6: Final Validation

**Step 1: Run all frontend checks**

Run: `npm run --prefix frontend lint`
Expected: PASS

Run: `npm run --prefix frontend type-check`
Expected: PASS

Run: `npm run --prefix frontend test`
Expected: All tests PASS

**Step 2: Squash commits if needed**

If making a single PR, consider squashing:
```bash
git rebase -i HEAD~5
# Squash all into first commit with message:
# "refactor(frontend): extract shared constants (fix #854)"
```

---

## Summary

| Task | File | Change |
|------|------|--------|
| 1 | `constants/index.ts` | Create constants file with tests |
| 2 | `BookDetailView.vue` | Replace `statusOptions` with import |
| 3 | `BookForm.vue` | Replace `statuses` with import |
| 4 | `acquisitions.ts` | Replace pagination magic numbers |
| 5 | `ComboboxWithAdd.vue` | Replace 200ms with constant |
| 6 | - | Final validation |

**Total files changed:** 5 files
**Tests added:** 1 new test file
