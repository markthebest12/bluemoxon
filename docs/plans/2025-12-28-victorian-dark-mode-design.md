# Victorian Dark Mode Design

**Issue:** #626
**Date:** 2025-12-28
**Status:** Approved

## Overview

Add a Victorian "Evening Reading" dark mode theme with warm, sepia-toned colors that evoke a candlelit study rather than stark black/white.

## Design Decisions

1. **Toggle UX:** System-first with override
   - Defaults to OS `prefers-color-scheme`
   - Sun/moon toggle in navbar to override
   - Persists override to localStorage

2. **CSS Architecture:** Semantic tokens with automatic switching
   - Components use semantic names (`bg-surface-primary`)
   - Dark overrides via `.dark` class on `<html>`
   - Centralized color definitions

3. **Color Palette:** Victorian "candlelit study"
   - Background: `#1a2318` (deep forest)
   - Surface: `#2d3028` (warm charcoal)
   - Elevated: `#343a30` (lighter charcoal)
   - Text: `#e8e1d5` (aged cream)
   - Text muted: `#9a958c`
   - Accent: `#c9a227` (gold - inverted from light mode)
   - Border: `#3d4a3d` (muted olive)

4. **Toggle Placement:**
   - Desktop: Next to user menu (icon button)
   - Mobile: Next to hamburger icon (always visible)

## Architecture

### Semantic Token System

Add to `@theme` in `main.css`:

```css
@theme {
  /* Semantic tokens for theming */
  --color-surface-base: var(--color-victorian-paper-aged);
  --color-surface-primary: var(--color-victorian-paper-white);
  --color-surface-secondary: var(--color-victorian-paper-cream);
  --color-surface-elevated: var(--color-victorian-paper-cream);

  --color-text-primary: var(--color-victorian-ink-black);
  --color-text-secondary: var(--color-victorian-ink-dark);
  --color-text-muted: var(--color-victorian-ink-muted);

  --color-border-default: var(--color-victorian-paper-antique);
  --color-border-subtle: var(--color-gray-200);

  --color-accent-primary: var(--color-victorian-hunter-600);
  --color-accent-highlight: var(--color-victorian-gold);
}
```

### Dark Mode Override

```css
.dark {
  --color-surface-base: #1a2318;
  --color-surface-primary: #1a2318;
  --color-surface-secondary: #2d3028;
  --color-surface-elevated: #343a30;

  --color-text-primary: #e8e1d5;
  --color-text-secondary: #c9c3b8;
  --color-text-muted: #9a958c;

  --color-border-default: #3d4a3d;
  --color-border-subtle: #2d3028;

  --color-accent-primary: var(--color-victorian-gold);
  --color-accent-highlight: var(--color-victorian-gold-light);
}
```

## Components

### useTheme Composable

```typescript
// src/composables/useTheme.ts

type Theme = 'light' | 'dark' | 'system';

export function useTheme() {
  const preference = ref<Theme>(getStoredPreference());

  const resolvedTheme = computed(() => {
    if (preference.value === 'system') {
      return getSystemPreference();
    }
    return preference.value;
  });

  const isDark = computed(() => resolvedTheme.value === 'dark');

  function toggle() {
    preference.value = isDark.value ? 'light' : 'dark';
  }

  function setTheme(theme: Theme) {
    preference.value = theme;
  }

  // Apply .dark class to <html> and persist
  watch(resolvedTheme, (theme) => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    localStorage.setItem('theme', preference.value);
  }, { immediate: true });

  return { preference, resolvedTheme, isDark, toggle, setTheme };
}
```

### ThemeToggle Component

```vue
<script setup lang="ts">
import { useTheme } from '@/composables/useTheme';
const { isDark, toggle } = useTheme();
</script>

<template>
  <button
    @click="toggle"
    class="p-2 rounded-xs text-victorian-paper-cream/80
           hover:text-victorian-gold-light transition-colors"
    :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
  >
    <!-- Sun icon (shown in dark mode) -->
    <svg v-if="isDark" class="w-5 h-5" ...>...</svg>
    <!-- Moon icon (shown in light mode) -->
    <svg v-else class="w-5 h-5" ...>...</svg>
  </button>
</template>
```

### Flash Prevention

Add to `index.html` `<head>`:

```html
<script>
  (function() {
    const p = localStorage.getItem('theme');
    const dark = p === 'dark' || (p !== 'light' && matchMedia('(prefers-color-scheme:dark)').matches);
    if (dark) document.documentElement.classList.add('dark');
  })();
</script>
```

## Component Updates

| Component | Current | Updated |
|-----------|---------|---------|
| `.card` bg | `bg-victorian-paper-cream` | `bg-surface-secondary` |
| `.card` border | `border-victorian-paper-antique` | `border-border-default` |
| `.input` bg | `bg-victorian-paper-white` | `bg-surface-primary` |
| `.input` text | `color-victorian-ink-black` | `color-text-primary` |
| `.btn-secondary` | `bg-victorian-paper-cream` | `bg-surface-secondary` |
| Body background | `bg-victorian-paper-aged` | `bg-surface-base` |
| Navbar dropdown | `bg-white` | `bg-surface-elevated` |

**Navbar background:** Keep `bg-victorian-hunter-900` - works in both modes.

## Accessibility

### Color Contrast (WCAG AA)

| Element | Light Mode | Dark Mode |
|---------|------------|-----------|
| Body text | `#1a1a18` on `#f8f5f0` = 14:1 ✓ | `#e8e1d5` on `#2d3028` = 9.5:1 ✓ |
| Muted text | `#5c5c58` on `#f8f5f0` = 5.2:1 ✓ | `#9a958c` on `#2d3028` = 4.6:1 ✓ |
| Gold accent | `#c9a227` on `#1a3a2f` = 5.8:1 ✓ | `#c9a227` on `#2d3028` = 5.3:1 ✓ |

### Other Requirements

- Focus indicators: Gold focus ring visible in both modes
- Motion: Respects `prefers-reduced-motion`
- Screen readers: `aria-label` on toggle describes action
- Keyboard: Toggle is focusable `<button>`

## Testing

### Unit Tests (Vitest)

- `useTheme.spec.ts` - preference storage, system detection, toggle

### E2E Tests (Playwright)

- Toggle switches theme visually
- Preference persists across reload
- System preference respected
- Keyboard accessible

## Implementation Scope

**In scope (this PR):**

- `main.css` - Semantic tokens + dark overrides + component updates
- `useTheme.ts` - New composable
- `ThemeToggle.vue` - New component
- `NavBar.vue` - Add toggle, fix dropdown
- `index.html` - Flash prevention script
- Tests

**Out of scope:**

- Individual view components (inherit from updated classes)
- Third-party components (Amplify auth UI)
