# Container-Responsive BookThumbnail Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace BookThumbnail's rigid `size` prop with Tailwind v4 container queries for automatic container-responsive sizing.

**Architecture:** Component uses `@container` wrapper with `aspect-[4/5]` ratio. Parent components control width, thumbnail fills and maintains aspect ratio. Two-tier breakpoints: small (<200px) and medium (>=200px).

**Tech Stack:** Vue 3, TypeScript, Tailwind CSS v4 (container queries via `@container`, `@sm:` variants)

---

## Task 1: Create BookThumbnail Test File

**Files:**

- Create: `frontend/src/components/books/__tests__/BookThumbnail.spec.ts`

**Step 1: Write the test file with failing tests**

```typescript
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import BookThumbnail from "../BookThumbnail.vue";

describe("BookThumbnail", () => {
  const defaultProps = {
    bookId: 123,
  };

  describe("container query structure", () => {
    it("has @container class on wrapper element", () => {
      const wrapper = mount(BookThumbnail, { props: defaultProps });
      const container = wrapper.find("[class*='@container']");
      expect(container.exists()).toBe(true);
    });

    it("has aspect-[4/5] class for proper aspect ratio", () => {
      const wrapper = mount(BookThumbnail, { props: defaultProps });
      const inner = wrapper.find("[class*='aspect-']");
      expect(inner.exists()).toBe(true);
      expect(inner.classes()).toContain("aspect-[4/5]");
    });

    it("fills container width with w-full class", () => {
      const wrapper = mount(BookThumbnail, { props: defaultProps });
      const container = wrapper.find("[class*='@container']");
      expect(container.classes()).toContain("w-full");
    });
  });

  describe("image rendering", () => {
    it("renders placeholder when no imageUrl provided", () => {
      const wrapper = mount(BookThumbnail, { props: defaultProps });
      const img = wrapper.find("img");
      expect(img.exists()).toBe(true);
      expect(img.attributes("src")).toContain("/images/placeholder");
    });

    it("renders provided imageUrl", () => {
      const wrapper = mount(BookThumbnail, {
        props: { ...defaultProps, imageUrl: "https://example.com/book.jpg" },
      });
      const img = wrapper.find("img");
      expect(img.attributes("src")).toBe("https://example.com/book.jpg");
    });

    it("shows image indicator badge when has image", () => {
      const wrapper = mount(BookThumbnail, {
        props: { ...defaultProps, imageUrl: "https://example.com/book.jpg" },
      });
      const badge = wrapper.find("svg");
      expect(badge.exists()).toBe(true);
    });

    it("does not show image indicator badge when no image", () => {
      const wrapper = mount(BookThumbnail, { props: defaultProps });
      const badge = wrapper.find("svg");
      expect(badge.exists()).toBe(false);
    });
  });

  describe("click behavior", () => {
    it("emits click when has image and clicked", async () => {
      const wrapper = mount(BookThumbnail, {
        props: { ...defaultProps, imageUrl: "https://example.com/book.jpg" },
      });
      await wrapper.trigger("click");
      expect(wrapper.emitted("click")).toHaveLength(1);
    });

    it("does not emit click when no image and clicked", async () => {
      const wrapper = mount(BookThumbnail, { props: defaultProps });
      await wrapper.trigger("click");
      expect(wrapper.emitted("click")).toBeUndefined();
    });

    it("has cursor-pointer class when has image", () => {
      const wrapper = mount(BookThumbnail, {
        props: { ...defaultProps, imageUrl: "https://example.com/book.jpg" },
      });
      const clickable = wrapper.find("[class*='cursor-pointer']");
      expect(clickable.exists()).toBe(true);
    });
  });

  describe("no size prop", () => {
    it("does not accept size prop (removed)", () => {
      // This test documents that size prop was intentionally removed
      // Component should work without any size prop
      const wrapper = mount(BookThumbnail, { props: defaultProps });
      expect(wrapper.exists()).toBe(true);
    });
  });
});
```

**Step 2: Run tests to verify they fail**

Run: `npm --prefix frontend run test -- --run src/components/books/__tests__/BookThumbnail.spec.ts`

Expected: FAIL - tests looking for `@container` and `aspect-[4/5]` classes won't find them in current implementation.

**Step 3: Commit test file**

```bash
git add frontend/src/components/books/__tests__/BookThumbnail.spec.ts
git commit -m "test: add BookThumbnail tests for container query migration"
```

---

## Task 2: Update BookThumbnail Component

**Files:**

- Modify: `frontend/src/components/books/BookThumbnail.vue`

**Step 1: Update the component to use container queries**

Replace entire file content:

```vue
<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  bookId: number;
  imageUrl?: string | null;
}>();

const emit = defineEmits<{
  click: [];
}>();

const hasImage = computed(() => !!props.imageUrl);

// Use API placeholder for books without images
const API_URL = import.meta.env.VITE_API_URL || "/api/v1";
const placeholderUrl = `${API_URL}/images/placeholder`;

function handleClick() {
  if (hasImage.value) {
    emit("click");
  }
}
</script>

<template>
  <div class="@container w-full" @click="handleClick">
    <div
      :class="[
        'aspect-[4/5] w-full @sm:max-w-24 relative rounded-xs overflow-hidden bg-victorian-paper-cream border border-victorian-paper-antique transition-all',
        hasImage ? 'cursor-pointer hover:border-victorian-gold-muted hover:shadow-md' : '',
      ]"
    >
      <!-- Image or Placeholder -->
      <img
        :src="imageUrl || placeholderUrl"
        alt="Book image"
        loading="lazy"
        decoding="async"
        class="w-full h-full object-cover"
      />

      <!-- Image indicator badge (only for actual images) -->
      <div
        v-if="hasImage"
        class="absolute bottom-1 right-1 bg-victorian-hunter-900/70 text-victorian-paper-cream text-xs px-1.5 py-0.5 rounded-xs"
      >
        <svg class="w-3 h-3 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
      </div>
    </div>
  </div>
</template>
```

**Step 2: Run tests to verify they pass**

Run: `npm --prefix frontend run test -- --run src/components/books/__tests__/BookThumbnail.spec.ts`

Expected: PASS - all tests should pass now.

**Step 3: Run type check**

Run: `npm --prefix frontend run type-check`

Expected: No errors.

**Step 4: Commit component changes**

```bash
git add frontend/src/components/books/BookThumbnail.vue
git commit -m "feat(BookThumbnail): replace size prop with container queries (#623)"
```

---

## Task 3: Update BooksView.vue

**Files:**

- Modify: `frontend/src/views/BooksView.vue:536-541`

**Step 1: Find and update the BookThumbnail usage**

Find this code (around line 536):

```vue
          <BookThumbnail
            :book-id="book.id"
            :image-url="book.primary_image_url"
            size="md"
            @click="openCarousel(book.id)"
          />
```

Replace with:

```vue
          <div class="w-24 shrink-0">
            <BookThumbnail
              :book-id="book.id"
              :image-url="book.primary_image_url"
              @click="openCarousel(book.id)"
            />
          </div>
```

**Step 2: Run lint check**

Run: `npm --prefix frontend run lint`

Expected: No errors.

**Step 3: Run all frontend tests**

Run: `npm --prefix frontend run test -- --run`

Expected: All tests pass.

**Step 4: Commit**

```bash
git add frontend/src/views/BooksView.vue
git commit -m "refactor(BooksView): wrap BookThumbnail in sized container (#623)"
```

---

## Task 4: Update BookDetailView.vue

**Files:**

- Modify: `frontend/src/views/BookDetailView.vue:469`

**Step 1: Find and update the BookThumbnail usage**

Find this code (around line 469):

```vue
              <BookThumbnail :book-id="booksStore.currentBook.id" size="lg" />
```

Replace with:

```vue
              <div class="w-48">
                <BookThumbnail :book-id="booksStore.currentBook.id" />
              </div>
```

**Step 2: Run lint check**

Run: `npm --prefix frontend run lint`

Expected: No errors.

**Step 3: Run type check**

Run: `npm --prefix frontend run type-check`

Expected: No errors.

**Step 4: Commit**

```bash
git add frontend/src/views/BookDetailView.vue
git commit -m "refactor(BookDetailView): wrap BookThumbnail in sized container (#623)"
```

---

## Task 5: Final Validation

**Step 1: Run full test suite**

Run: `npm --prefix frontend run test -- --run`

Expected: All 84+ tests pass.

**Step 2: Run lint**

Run: `npm --prefix frontend run lint`

Expected: No errors.

**Step 3: Run type check**

Run: `npm --prefix frontend run type-check`

Expected: No errors.

**Step 4: Build check**

Run: `npm --prefix frontend run build`

Expected: Build succeeds.

**Step 5: Commit any final fixes if needed**

---

## Task 6: Create PR to Staging

**Step 1: Push branch**

Run: `git push -u origin feat/623-container-queries`

**Step 2: Create PR targeting staging**

```bash
gh pr create --base staging --title "feat: Add container queries to BookThumbnail (#623)" --body "## Summary
- Replace BookThumbnail size prop with Tailwind v4 container queries
- Component now auto-sizes based on parent container width
- Maintains 4:5 aspect ratio
- Two-tier breakpoints: small (<200px) and medium (>=200px)

## Changes
- Remove \`size\` prop from BookThumbnail
- Add \`@container\` wrapper with \`aspect-[4/5]\` ratio
- Update BooksView to wrap thumbnail in \`w-24\` container
- Update BookDetailView to wrap thumbnail in \`w-48\` container
- Add comprehensive unit tests

## Test Plan
- [ ] CI passes
- [ ] Manual: Verify thumbnails in book list view
- [ ] Manual: Verify placeholder thumbnail on book detail page
- [ ] Manual: Resize browser to confirm no breakage

Closes #623"
```

**Step 3: Watch CI**

Run: `gh pr checks --watch`

Expected: All checks pass.

---

## Manual Testing Checklist

After PR is created, verify in staging:

1. **BooksView (list page)**
   - Thumbnails display at consistent 96px width
   - Images maintain 4:5 aspect ratio
   - Click opens image carousel
   - Placeholder shows for books without images

2. **BookDetailView (detail page)**
   - Placeholder thumbnail displays at 192px width when no images
   - Aspect ratio maintained

3. **Responsive behavior**
   - Resize browser - no layout breakage
   - Container queries respond to container, not viewport
