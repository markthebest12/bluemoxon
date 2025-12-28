# Animation System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add micro-interactions and polish animations across the BlueMoxon frontend.

**Architecture:** CSS-first approach using Tailwind v4's `@theme` for design tokens and `@layer components` for reusable animation classes. Vue `<Transition>` components wrap animated elements.

**Tech Stack:** Tailwind CSS v4, Vue 3 Transitions, CSS custom properties

**Issue:** #624

---

## Task 1: Add Animation Design Tokens

**Files:**
- Modify: `frontend/src/assets/main.css:10-60` (inside `@theme` block)

**Step 1: Add duration and easing tokens to @theme**

Open `frontend/src/assets/main.css` and add these tokens inside the existing `@theme { }` block, after the color definitions (around line 59):

```css
  /* Animation Durations */
  --duration-instant: 75ms;
  --duration-fast: 150ms;
  --duration-normal: 250ms;
  --duration-slow: 400ms;
  --duration-slower: 600ms;

  /* Animation Easings */
  --ease-out-soft: cubic-bezier(0.25, 0.1, 0.25, 1);
  --ease-out-back: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-spring: cubic-bezier(0.175, 0.885, 0.32, 1.275);
```

**Step 2: Verify CSS is valid**

Run: `npm run --prefix frontend build`

Expected: Build succeeds with no errors

**Step 3: Commit**

```bash
git add frontend/src/assets/main.css
git commit -m "feat(animations): Add animation design tokens to theme"
```

---

## Task 2: Add Interactive Card Class

**Files:**
- Modify: `frontend/src/assets/main.css` (add to `@layer components`)

**Step 1: Add card-interactive class**

Add this after the existing `.card-highlight` class (around line 310):

```css
  /* ============================================
     INTERACTIVE ANIMATIONS
     ============================================ */
  .card-interactive {
    transition: transform var(--duration-fast) var(--ease-out-soft),
                box-shadow var(--duration-fast) var(--ease-out-soft);
  }
  .card-interactive:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 16px -4px rgb(0 0 0 / 0.1),
                0 4px 6px -2px rgb(0 0 0 / 0.05);
  }
```

**Step 2: Verify CSS is valid**

Run: `npm run --prefix frontend build`

Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/assets/main.css
git commit -m "feat(animations): Add card-interactive hover class"
```

---

## Task 3: Add Button Press Feedback Class

**Files:**
- Modify: `frontend/src/assets/main.css`

**Step 1: Add btn-press class**

Add after the `.card-interactive` class:

```css
  .btn-press {
    transition: transform var(--duration-instant) var(--ease-out-soft);
  }
  .btn-press:active {
    transform: scale(0.97);
  }
```

**Step 2: Verify CSS is valid**

Run: `npm run --prefix frontend build`

Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/assets/main.css
git commit -m "feat(animations): Add btn-press active state class"
```

---

## Task 4: Add Link Animated Class

**Files:**
- Modify: `frontend/src/assets/main.css`

**Step 1: Add link-animated class**

Add after the `.btn-press` class:

```css
  .link-animated {
    position: relative;
  }
  .link-animated::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 1px;
    background: currentColor;
    transform: scaleX(0);
    transform-origin: right;
    transition: transform var(--duration-fast) var(--ease-out-soft);
  }
  .link-animated:hover::after {
    transform: scaleX(1);
    transform-origin: left;
  }
```

**Step 2: Verify CSS is valid**

Run: `npm run --prefix frontend build`

Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/assets/main.css
git commit -m "feat(animations): Add link-animated underline class"
```

---

## Task 5: Add Modal Transition Classes

**Files:**
- Modify: `frontend/src/assets/main.css`

**Step 1: Add modal transition classes**

Add after the link-animated class:

```css
  /* ============================================
     MODAL & DROPDOWN TRANSITIONS
     ============================================ */
  .modal-backdrop-enter-from,
  .modal-backdrop-leave-to {
    opacity: 0;
  }
  .modal-backdrop-enter-active,
  .modal-backdrop-leave-active {
    transition: opacity var(--duration-normal) var(--ease-out-soft);
  }

  .modal-enter-from {
    opacity: 0;
    transform: translateY(16px) scale(0.98);
  }
  .modal-leave-to {
    opacity: 0;
    transform: translateY(-8px) scale(0.98);
  }
  .modal-enter-active {
    transition: all var(--duration-normal) var(--ease-spring);
  }
  .modal-leave-active {
    transition: all var(--duration-fast) var(--ease-out-soft);
  }

  .dropdown-enter-from,
  .dropdown-leave-to {
    opacity: 0;
    transform: translateY(-4px);
  }
  .dropdown-enter-active,
  .dropdown-leave-active {
    transition: all var(--duration-fast) var(--ease-out-soft);
  }
```

**Step 2: Verify CSS is valid**

Run: `npm run --prefix frontend build`

Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/assets/main.css
git commit -m "feat(animations): Add modal and dropdown transition classes"
```

---

## Task 6: Update Skeleton Loading Classes

**Files:**
- Modify: `frontend/src/assets/main.css`

**Step 1: Add skeleton loading classes**

The existing `.spinner` class is around line 315. Add skeleton classes nearby:

```css
  /* ============================================
     SKELETON LOADING
     ============================================ */
  .skeleton {
    background: linear-gradient(
      90deg,
      rgb(0 0 0 / 0.06) 25%,
      rgb(0 0 0 / 0.12) 50%,
      rgb(0 0 0 / 0.06) 75%
    );
    background-size: 200% 100%;
    animation: skeleton-pulse var(--duration-slower) var(--ease-in-out) infinite;
    border-radius: 4px;
  }

  @keyframes skeleton-pulse {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  .skeleton-text {
    height: 1em;
    margin-bottom: 0.5em;
  }
  .skeleton-title {
    height: 1.5em;
    width: 60%;
  }
  .skeleton-image {
    aspect-ratio: 4/3;
  }
```

**Step 2: Verify CSS is valid**

Run: `npm run --prefix frontend build`

Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/assets/main.css
git commit -m "feat(animations): Add skeleton loading classes"
```

---

## Task 7: Update Progress Bar with Animation

**Files:**
- Modify: `frontend/src/assets/main.css`

**Step 1: Update progress bar classes**

Find existing `.progress-bar` class (around line 343) and replace/extend it:

```css
  /* ============================================
     PROGRESS BARS - Victorian colors with animation
     ============================================ */
  .progress-bar {
    height: 4px;
    background: rgb(0 0 0 / 0.1);
    border-radius: 2px;
    overflow: hidden;
  }

  .progress-bar-fill {
    height: 100%;
    background: var(--color-victorian-hunter-500);
    transition: width var(--duration-normal) var(--ease-out-soft);
    border-radius: 2px;
  }

  .progress-bar-gold .progress-bar-fill {
    background: var(--color-victorian-gold);
  }

  .progress-bar-indeterminate .progress-bar-fill {
    width: 30%;
    animation: progress-slide 1.5s var(--ease-in-out) infinite;
  }

  @keyframes progress-slide {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(400%); }
  }
```

**Step 2: Verify CSS is valid**

Run: `npm run --prefix frontend build`

Expected: Build succeeds

**Step 3: Commit**

```bash
git add frontend/src/assets/main.css
git commit -m "feat(animations): Update progress bar with animation support"
```

---

## Task 8: Apply card-interactive to BooksView

**Files:**
- Modify: `frontend/src/views/BooksView.vue:532`

**Step 1: Update book card class**

Find line 532 which has:
```vue
class="card cursor-pointer hover:shadow-lg transition-shadow"
```

Change to:
```vue
class="card card-interactive cursor-pointer"
```

**Step 2: Run tests**

Run: `npm run --prefix frontend test:run`

Expected: All tests pass

**Step 3: Commit**

```bash
git add frontend/src/views/BooksView.vue
git commit -m "feat(animations): Apply card-interactive to book cards"
```

---

## Task 9: Add btn-press to Primary Buttons

**Files:**
- Modify: `frontend/src/assets/main.css`

**Step 1: Add btn-press to btn-primary**

Find the `.btn-primary` class and add `btn-press` behavior by updating the transition:

In the `.btn-primary` definition, change:
```css
transition: background-color 0.15s ease-in-out;
```

To:
```css
transition: background-color var(--duration-fast) var(--ease-out-soft),
            transform var(--duration-instant) var(--ease-out-soft);
```

And add after the `:disabled` rule:
```css
  .btn-primary:active:not(:disabled) {
    transform: scale(0.97);
  }
```

**Step 2: Do the same for btn-secondary, btn-danger, btn-accent**

Apply same pattern to each button class.

**Step 3: Verify CSS is valid**

Run: `npm run --prefix frontend build`

Expected: Build succeeds

**Step 4: Commit**

```bash
git add frontend/src/assets/main.css
git commit -m "feat(animations): Add press feedback to all button classes"
```

---

## Task 10: Add Modal Transitions to AcquireModal

**Files:**
- Modify: `frontend/src/components/AcquireModal.vue`

**Step 1: Wrap backdrop with Transition**

Find the template section (line 155-156). Change from:

```vue
<Teleport to="body">
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
```

To:

```vue
<Teleport to="body">
  <Transition
    enter-from-class="modal-backdrop-enter-from"
    enter-active-class="modal-backdrop-enter-active"
    leave-to-class="modal-backdrop-leave-to"
    leave-active-class="modal-backdrop-leave-active"
  >
    <div
      v-if="true"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
```

Note: The modal is already conditionally shown by the parent, so we just need the transition wrapper.

**Step 2: Wrap modal content with Transition**

Find the modal content div (line 161). Wrap it:

```vue
<Transition
  enter-from-class="modal-enter-from"
  enter-active-class="modal-enter-active"
  leave-to-class="modal-leave-to"
  leave-active-class="modal-leave-active"
>
  <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 max-h-[90vh] flex flex-col">
```

**Step 3: Run tests**

Run: `npm run --prefix frontend test:run`

Expected: All tests pass

**Step 4: Commit**

```bash
git add frontend/src/components/AcquireModal.vue
git commit -m "feat(animations): Add modal transitions to AcquireModal"
```

---

## Task 11: Add Modal Transitions to Other Modals

**Files:**
- Modify: `frontend/src/components/AddToWatchlistModal.vue`
- Modify: `frontend/src/components/EditWatchlistModal.vue`
- Modify: `frontend/src/components/AddTrackingModal.vue`
- Modify: `frontend/src/components/ImportListingModal.vue`
- Modify: `frontend/src/components/PasteOrderModal.vue`
- Modify: `frontend/src/components/books/EvalRunbookModal.vue`
- Modify: `frontend/src/components/books/ImageUploadModal.vue`
- Modify: `frontend/src/components/books/ImageReorderModal.vue`

**Step 1: Apply same transition pattern to each modal**

For each modal file, wrap the backdrop and content with Transition components using the same classes as Task 10.

**Step 2: Run tests after each file**

Run: `npm run --prefix frontend test:run`

Expected: All tests pass

**Step 3: Commit after all modals**

```bash
git add frontend/src/components/*.vue frontend/src/components/books/*.vue
git commit -m "feat(animations): Add modal transitions to all modals"
```

---

## Task 12: Add Skeleton Loading to BooksView

**Files:**
- Modify: `frontend/src/views/BooksView.vue`

**Step 1: Replace loading text with skeleton cards**

Find the loading state (around line 522-525):

```vue
<!-- Loading state -->
<div v-if="booksStore.loading" class="text-center py-12">
  <p class="text-gray-500">Loading books...</p>
</div>
```

Replace with:

```vue
<!-- Loading state - skeleton cards -->
<div v-if="booksStore.loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  <div v-for="n in 6" :key="n" class="card">
    <div class="flex gap-4">
      <div class="skeleton skeleton-image w-24 h-32"></div>
      <div class="flex-1">
        <div class="skeleton skeleton-title mb-2"></div>
        <div class="skeleton skeleton-text w-3/4"></div>
        <div class="skeleton skeleton-text w-1/2"></div>
      </div>
    </div>
  </div>
</div>
```

**Step 2: Run tests**

Run: `npm run --prefix frontend test:run`

Expected: All tests pass

**Step 3: Commit**

```bash
git add frontend/src/views/BooksView.vue
git commit -m "feat(animations): Add skeleton loading to BooksView"
```

---

## Task 13: Add Skeleton Loading to AcquisitionsView

**Files:**
- Modify: `frontend/src/views/AcquisitionsView.vue`

**Step 1: Find and update loading state**

Search for the loading indicator in AcquisitionsView and replace with skeleton rows appropriate to that view's layout.

**Step 2: Run tests**

Run: `npm run --prefix frontend test:run`

Expected: All tests pass

**Step 3: Commit**

```bash
git add frontend/src/views/AcquisitionsView.vue
git commit -m "feat(animations): Add skeleton loading to AcquisitionsView"
```

---

## Task 14: Run Full Test Suite and Lint

**Step 1: Run all frontend tests**

Run: `npm run --prefix frontend test:run`

Expected: All 84+ tests pass

**Step 2: Run linting**

Run: `npm run --prefix frontend lint`

Expected: No errors

**Step 3: Run type checking**

Run: `npm run --prefix frontend type-check`

Expected: No errors

**Step 4: Run build**

Run: `npm run --prefix frontend build`

Expected: Build succeeds

---

## Task 15: Create PR to Staging

**Step 1: Push branch**

```bash
git push -u origin feat/624-animation-system
```

**Step 2: Create PR**

```bash
gh pr create --base staging --title "feat: Add animation system for micro-interactions (#624)" --body "## Summary
- Add animation design tokens (durations, easings) to Tailwind theme
- Add interactive card hover effects
- Add button press feedback
- Add modal enter/leave transitions
- Add skeleton loading states
- Apply animations across BooksView and AcquisitionsView

## Test Plan
- [ ] CI passes
- [ ] Manual testing of hover states on book cards
- [ ] Manual testing of modal open/close animations
- [ ] Manual testing of skeleton loading states
- [ ] Verify animations are subtle and not distracting

Closes #624"
```

**Step 3: Watch CI**

Run: `gh pr checks --watch`

Expected: All checks pass

---

## Summary of Changes

| File | Changes |
|------|---------|
| `frontend/src/assets/main.css` | Animation tokens, interactive classes, transitions, skeletons |
| `frontend/src/views/BooksView.vue` | card-interactive, skeleton loading |
| `frontend/src/views/AcquisitionsView.vue` | Skeleton loading |
| `frontend/src/components/AcquireModal.vue` | Modal transitions |
| `frontend/src/components/*.vue` | Modal transitions (8 files) |

## Verification Checklist

- [ ] All duration tokens use `--duration-*` variables
- [ ] All easing tokens use `--ease-*` variables
- [ ] Book cards lift on hover
- [ ] Buttons compress on press
- [ ] Modals fade and slide in/out
- [ ] Skeleton loading shows during data fetch
- [ ] No animation on `prefers-reduced-motion: reduce` (future enhancement)
