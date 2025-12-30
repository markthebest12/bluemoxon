# Design: Semantic Status Color Tokens

**Date:** 2025-12-29
**Issue:** #650
**Status:** Approved

## Overview

Create semantic status color tokens to replace Tailwind class hijacking in dark mode. This provides a scalable, maintainable approach to status colors (success, warning, error, info) that work across light and dark themes.

## Token Structure

```
--color-status-{type}-{variant}

Types: success, warning, error, info
Variants: bg, text, border, solid, solid-text, accent
```

### Variant Usage

| Variant | Purpose | Example |
|---------|---------|---------|
| `bg` | Light background for alerts/badges | Alert boxes, status badges |
| `text` | Text color on light bg | Message text in alerts |
| `border` | Border for light variant | Alert borders |
| `solid` | Solid fill for emphasis | Score bars, buttons |
| `solid-text` | Text on solid bg | Button text |
| `accent` | Inline icons/text | Status icons, links |

## Light Mode Values

```css
@theme {
  /* SUCCESS - Green */
  --color-status-success-bg: #dcfce7;
  --color-status-success-text: #166534;
  --color-status-success-border: #86efac;
  --color-status-success-solid: #22c55e;
  --color-status-success-solid-text: #ffffff;
  --color-status-success-accent: #16a34a;

  /* WARNING - Yellow/Amber */
  --color-status-warning-bg: #fef3c7;
  --color-status-warning-text: #92400e;
  --color-status-warning-border: #fcd34d;
  --color-status-warning-solid: #eab308;
  --color-status-warning-solid-text: #ffffff;
  --color-status-warning-accent: #ca8a04;

  /* ERROR - Red */
  --color-status-error-bg: #fee2e2;
  --color-status-error-text: #991b1b;
  --color-status-error-border: #fca5a5;
  --color-status-error-solid: #ef4444;
  --color-status-error-solid-text: #ffffff;
  --color-status-error-accent: #dc2626;

  /* INFO - Victorian moxon/hunter (brand-aligned) */
  --color-status-info-bg: #f0f5f3;
  --color-status-info-text: #254a3d;
  --color-status-info-border: #8dbaa8;
  --color-status-info-solid: #3a6b5c;
  --color-status-info-solid-text: #ffffff;
  --color-status-info-accent: #2f5a4b;
}
```

## Dark Mode Values

```css
.dark {
  /* SUCCESS */
  --color-status-success-bg: #1a2e1a;
  --color-status-success-text: #86efac;
  --color-status-success-border: #22c55e;
  --color-status-success-solid: #22c55e;
  --color-status-success-solid-text: #ffffff;
  --color-status-success-accent: #4ade80;

  /* WARNING */
  --color-status-warning-bg: #3d3828;
  --color-status-warning-text: #fcd34d;
  --color-status-warning-border: #eab308;
  --color-status-warning-solid: #eab308;
  --color-status-warning-solid-text: #1a1a18;
  --color-status-warning-accent: #facc15;

  /* ERROR */
  --color-status-error-bg: #2e1a1a;
  --color-status-error-text: #fca5a5;
  --color-status-error-border: #ef4444;
  --color-status-error-solid: #ef4444;
  --color-status-error-solid-text: #ffffff;
  --color-status-error-accent: #f87171;

  /* INFO */
  --color-status-info-bg: #2d3028;
  --color-status-info-text: #c9c3b8;
  --color-status-info-border: #3d4a3d;
  --color-status-info-solid: var(--color-victorian-gold);
  --color-status-info-solid-text: #1a1a18;
  --color-status-info-accent: var(--color-victorian-gold-light);
}
```

## Implementation Steps

1. **Add tokens to `main.css`** - 24 light mode + 24 dark mode
2. **Remove Tailwind hijacking** - Delete `.bg-green-*`, `.text-green-*`, `.border-green-*` overrides from `.dark {}`
3. **Update components** - Replace hardcoded Tailwind classes with semantic tokens
4. **Test** - Visual verification in both modes

## Components to Update

Priority order:
1. `ArchiveStatusBadge.vue`
2. `ProfileView.vue`
3. `AdminView.vue`
4. `BookForm.vue`
5. `EvalRunbookModal.vue`
6. Remaining components

## Migration Pattern

```vue
<!-- Before -->
<div class="bg-green-50 text-green-700 border-green-300">

<!-- After -->
<div class="bg-[var(--color-status-success-bg)] text-[var(--color-status-success-text)] border-[var(--color-status-success-border)]">
```

## Related

- Parent: #626 (Victorian dark mode)
- Follow-up: #640 (Apply to remaining views)
