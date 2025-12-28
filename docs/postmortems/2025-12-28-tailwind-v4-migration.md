# Postmortem: Tailwind CSS v4 Migration

**Issue:** #166
**Date:** 2025-12-27 to 2025-12-28
**Status:** Complete
**Severity:** Critical - Production visual regressions
**Duration:** 2 days

---

## Executive Summary

The Tailwind CSS v4 migration encountered multiple silent failures that required 6 separate PRs to address. The root causes were Tailwind v4's architectural changes that produce no build warnings when utilities fail to generate CSS.

**Key Takeaways:**
1. Tailwind v4 uses `:where()` wrappers giving some utilities zero CSS specificity
2. Custom theme values require explicit `@theme` definitions (no defaults)
3. Silent CSS generation failures make automated testing unreliable
4. `@utility` with `@apply` silently fails for component classes - use `@layer components` instead

---

## Issue 1: Border Radius Silent Failure

### Timeline

| PR | What Was Done | Result |
|----|---------------|--------|
| #609 | Initial migration - kept `rounded-xs` | Class existed but **generated no CSS** |
| #613 | Changed `rounded-xs` → `rounded-sm` | **WRONG** - doubled radius (2px → 4px) |
| #614 | Added `--radius-xs` to @theme, reverted to `rounded-xs` | **CORRECT** |

### Root Cause

In Tailwind v4, utility classes only generate CSS if their underlying CSS variables are defined:

```css
@theme {
  --radius-xs: 0.125rem;  /* Without this, rounded-xs generates NOTHING */
}
```

**The failure was silent** - no build errors, no warnings. The class was in HTML but no CSS rule was generated.

### Why PR #613 Was Wrong

1. **Observed:** `rounded-xs` class in HTML, no 2px radius visible
2. **Incorrect diagnosis:** "Tailwind v4 renamed `rounded-xs` to `rounded-sm`"
3. **Incorrect fix:** Replace all `rounded-xs` with `rounded-sm`
4. **Actual result:** Changed 2px radius to 4px (doubled it)

**Correct diagnosis:** Tailwind v4 requires explicit `--radius-xs` definition in @theme.

### Lesson Learned

> When a utility doesn't work in Tailwind v4, check if it needs a @theme definition FIRST. Don't assume renames.

---

## Issue 2: space-* Zero Specificity

### Timeline

| PR | What Was Done | Result |
|----|---------------|--------|
| #609 | Initial migration - kept `space-*` utilities | Spacing broken on many components |
| #615 | Replace all `space-*` with `gap-*` across 19 files | **CORRECT** |

### Root Cause

Tailwind v4 wraps `space-*` utilities in `:where()` pseudo-class:

```css
/* Tailwind v3 (Production) */
.space-x-6>:not([hidden])~:not([hidden]) {
  margin-right: 1.5rem;
}

/* Tailwind v4 (Staging) */
:where(.space-x-6>:not(:last-child)) {
  margin-inline-end: calc(...);
}
```

**The `:where()` wrapper gives ZERO specificity**, meaning ANY other CSS rule can override it.

### Symptom

Navbar links displayed as "DashboardCollectionReportsAcquisitions" (smashed together, no spacing).

### Solution

Replace all `space-*` utilities with `gap-*`:

```html
<!-- Before (broken in v4) -->
<div class="flex space-x-6">

<!-- After (works in v4) -->
<div class="flex gap-6">
```

For non-flex containers:

```html
<!-- Before -->
<div class="space-y-4">

<!-- After -->
<div class="flex flex-col gap-4">
```

### Why gap-* Works

`gap-*` utilities have normal specificity (no `:where()` wrapper):

```css
.gap-6 { gap: calc(var(--spacing)*6); }
```

### Scope of Fix

**PR #615 modified 19 files:**
- AcquireModal, AddToWatchlistModal, AddTrackingModal
- EditWatchlistModal, ImportListingModal, PasteOrderModal
- ScoreCard, BookForm, EvalRunbookModal
- ImageReorderModal, ImageUploadModal
- AcquisitionsView, AdminConfigView, AdminView
- BookDetailView, BooksView, LoginView
- ProfileView, SearchView

---

## Issue 3: Image Height Override

### Timeline

| PR | What Was Done | Result |
|----|---------------|--------|
| #609 | Initial migration | Giant watermark logo over dashboard |
| #612 | Added `!h-14` important modifier | **CORRECT** |

### Root Cause

CSS cascade layers in Tailwind v4:
1. Base layer includes: `img, video { height: auto; }`
2. Utility layer has: `.h-14 { height: calc(var(--spacing)*14); }`
3. Despite utilities having higher cascade priority, base rule was winning on images

### Solution

Use Tailwind v4's `!` important modifier:

```html
<img class="!h-14 w-auto" />
```

Generates: `.!h-14{height:calc(var(--spacing)*14)!important}`

---

## Contributing Factors

1. **No lint/build errors** - Tailwind v4 silently ignores undefined utilities
2. **Automated screenshot comparison inadequate** - Didn't catch subtle changes
3. **Insufficient manual testing** - Merged to staging without thorough review
4. **Confirmation bias** - Assumed working class names were "renamed"

---

## Process Improvements

### Before Any Tailwind v4 Utility Change

1. **Check Tailwind v4 docs** for that specific utility
2. **Verify actual CSS values** generated, not just class names
3. **Test with browser DevTools** - inspect computed styles

### Tailwind v4 Migration Checklist

- [ ] Add all custom theme values to `@theme` block
- [ ] Replace all `space-x-*` with `gap-*` (on flex containers)
- [ ] Replace all `space-y-*` with `flex flex-col gap-*`
- [ ] Add `!` modifier to utilities that need to override base layer
- [ ] Manual visual testing on ALL pages before merge
- [ ] User review before staging merge

### Detection Strategy

For future silent failures, add to CI:
- CSS output size comparison (catch missing utilities)
- Visual regression testing with pixel-level comparison
- Computed style assertions for critical UI elements

---

## Issue 4: @utility with @apply Silent Failure

### Timeline

| PR | What Was Done | Result |
|----|---------------|--------|
| #609 | Initial migration - used @utility with @apply | Component classes silently broken |
| #616 | Convert @utility to @layer components | **CORRECT** - TRUE root cause fix |

### Root Cause

Tailwind v4 `@utility` directive does NOT work correctly with `@apply` for component-style classes. Some properties (like `background-color`) may work while others (`border`, `padding`) silently fail to generate CSS.

### Symptom

Component classes rendered with missing styles:

| Element | Staging (broken) | Production (correct) |
|---------|------------------|---------------------|
| `.card` | `padding: 0px`, `border: 0px` | `padding: 24px`, `border: 1px solid` |
| `.input` | `padding: 0px`, `border: 0px` | `padding: 8px 12px`, `border: 1px solid` |

### Solution

Convert ALL `@utility` blocks to `@layer components` with explicit CSS properties:

```css
/* BROKEN in v4 */
@utility card {
  @apply bg-victorian-paper-cream rounded-xs border border-victorian-paper-antique p-6;
}

/* WORKS in v4 */
@layer components {
  .card {
    background-color: var(--color-victorian-paper-cream);
    border-radius: var(--radius-xs);
    border: 1px solid var(--color-victorian-paper-antique);
    padding: 1.5rem;
  }
}
```

### Components Affected

- `.btn-primary`, `.btn-secondary`, `.btn-danger`, `.btn-accent`
- `.card`, `.card-static`
- `.input`, `.select`
- All `.badge-*` variants
- `.divider-flourish`, `.section-header`

### Lesson Learned

> In Tailwind v4, custom component classes MUST use `@layer components` with explicit CSS properties. Do NOT use `@utility` with `@apply` for component-style classes.

---

## Summary of PRs

| PR | Title | Status | Verdict |
|----|-------|--------|---------|
| #609 | feat: Upgrade to Tailwind CSS v4 | Merged | Had hidden bugs |
| #611 | chore: Promote staging to production | Blocked | Superseded |
| #612 | fix: Navbar logo height | Merged | Correct |
| #613 | fix: Tailwind v4 deprecated classes | Merged | **WRONG** (rounded-xs→rounded-sm) |
| #614 | fix: Add --radius-xs to @theme | Merged | Correct (reverted #613) |
| #615 | fix: Replace space-* with gap-* | Merged | Partial fix |
| #616 | fix: Convert @utility to @layer components | Merged | TRUE root cause fix |

---

## Appendix: Tailwind v4 Breaking Changes

### Utilities Requiring @theme Definitions

| Utility | Required @theme Variable |
|---------|-------------------------|
| `rounded-xs` | `--radius-xs: 0.125rem` |
| Custom colors | `--color-[name]: [value]` |
| Custom spacing | `--spacing-[name]: [value]` |

### Utilities With Zero Specificity (Use Alternatives)

| Avoid | Use Instead |
|-------|-------------|
| `space-x-*` | `gap-*` (in flex/grid) |
| `space-y-*` | `flex flex-col gap-*` |
| `divide-x-*` | Consider alternatives |
| `divide-y-*` | Consider alternatives |

### Utilities Needing Important Modifier

| Context | Solution |
|---------|----------|
| `h-*` on images | `!h-*` |
| `w-*` on images | `!w-*` |
| Any base layer override | `!utility` |

### Custom Component Classes

| Avoid | Use Instead |
|-------|-------------|
| `@utility name { @apply ... }` | `@layer components { .name { explicit CSS } }` |

**Why:** `@utility` with `@apply` silently fails to generate some CSS properties (border, padding) while others (background-color) may work. This creates partial, broken styles with no build warnings.
