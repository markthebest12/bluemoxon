# Victorian Dark Mode Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a warm, Victorian "Evening Reading" dark mode with system preference detection and manual toggle.

**Architecture:** Semantic CSS tokens in `@theme` with `.dark` class overrides. Vue composable manages state (localStorage + system preference). Toggle component in navbar.

**Tech Stack:** Tailwind v4 CSS variables, Vue 3 composables, TypeScript

---

## Task 1: Add Semantic Color Tokens to CSS

**Files:**
- Modify: `frontend/src/assets/main.css:10-72` (inside @theme block)

**Step 1: Add semantic tokens after existing color definitions**

Add these lines inside the `@theme { }` block, after line 71 (after `--ease-spring`):

```css
  /* ============================================
     SEMANTIC TOKENS - Theme-aware colors
     ============================================ */
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
```

**Step 2: Verify CSS is valid**

Run: `npm run build --prefix frontend`
Expected: Build succeeds without CSS errors

**Step 3: Commit**

```
git add frontend/src/assets/main.css
git commit -m "feat(theme): add semantic color tokens to @theme"
```

---

## Task 2: Add Dark Mode CSS Overrides

**Files:**
- Modify: `frontend/src/assets/main.css` (add after @theme block, before @layer base)

**Step 1: Add dark mode override block**

Add after the closing `}` of `@theme` block (around line 88), before the border compatibility comment:

```css
/* ============================================
   DARK MODE - Victorian "Evening Reading" theme
   ============================================ */
.dark {
  color-scheme: dark;

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

**Step 2: Verify CSS is valid**

Run: `npm run build --prefix frontend`
Expected: Build succeeds

**Step 3: Commit**

```
git add frontend/src/assets/main.css
git commit -m "feat(theme): add dark mode CSS variable overrides"
```

---

## Task 3: Update Body Background to Use Semantic Token

**Files:**
- Modify: `frontend/src/assets/main.css:554-555` (@layer base html,body)

**Step 1: Change body background from hardcoded to semantic**

Find in `@layer base`:
```css
  html,
  body {
    @apply overflow-x-hidden;
    @apply bg-victorian-paper-aged;
  }
```

Change to:
```css
  html,
  body {
    @apply overflow-x-hidden;
    background-color: var(--color-surface-base);
  }
```

**Step 2: Verify build**

Run: `npm run build --prefix frontend`
Expected: Build succeeds

**Step 3: Manual test - add .dark class temporarily**

Open browser devtools, add `dark` class to `<html>`, verify background changes to dark green.

**Step 4: Commit**

```
git add frontend/src/assets/main.css
git commit -m "feat(theme): use semantic token for body background"
```

---

## Task 4: Update Component Classes to Use Semantic Tokens

**Files:**
- Modify: `frontend/src/assets/main.css` (multiple component classes in @layer components)

**Step 1: Update .card class**

Find:
```css
  .card {
    /* Cards - Warm paper feel */
    background-color: var(--color-victorian-paper-cream);
    border-radius: var(--radius-xs);
    border: 1px solid var(--color-victorian-paper-antique);
```

Change to:
```css
  .card {
    /* Cards - Warm paper feel */
    background-color: var(--color-surface-secondary);
    border-radius: var(--radius-xs);
    border: 1px solid var(--color-border-default);
```

**Step 2: Update .card-static class**

Find:
```css
  .card-static {
    /* Card without hover effect */
    background-color: var(--color-victorian-paper-cream);
    border-radius: var(--radius-xs);
    border: 1px solid var(--color-victorian-paper-antique);
```

Change to:
```css
  .card-static {
    /* Card without hover effect */
    background-color: var(--color-surface-secondary);
    border-radius: var(--radius-xs);
    border: 1px solid var(--color-border-default);
```

**Step 3: Update .input class**

Find:
```css
  .input {
    /* Form inputs */
    width: 100%;
    padding: 0.5rem 0.75rem;
    background-color: var(--color-victorian-paper-white);
    border: 1px solid var(--color-victorian-paper-antique);
    border-radius: var(--radius-xs);
    color: var(--color-victorian-ink-black);
  }
```

Change to:
```css
  .input {
    /* Form inputs */
    width: 100%;
    padding: 0.5rem 0.75rem;
    background-color: var(--color-surface-primary);
    border: 1px solid var(--color-border-default);
    border-radius: var(--radius-xs);
    color: var(--color-text-primary);
  }
```

**Step 4: Update .select class**

Find:
```css
  .select {
    /* Select dropdowns */
    width: 100%;
    padding: 0.5rem 0.75rem;
    background-color: var(--color-victorian-paper-white);
    border: 1px solid var(--color-victorian-paper-antique);
    border-radius: var(--radius-xs);
    color: var(--color-victorian-ink-black);
  }
```

Change to:
```css
  .select {
    /* Select dropdowns */
    width: 100%;
    padding: 0.5rem 0.75rem;
    background-color: var(--color-surface-primary);
    border: 1px solid var(--color-border-default);
    border-radius: var(--radius-xs);
    color: var(--color-text-primary);
  }
```

**Step 5: Update .btn-secondary class**

Find:
```css
  .btn-secondary {
    /* Secondary button - Subtle */
    background-color: var(--color-victorian-paper-cream);
    color: var(--color-victorian-ink-dark);
```

Change to:
```css
  .btn-secondary {
    /* Secondary button - Subtle */
    background-color: var(--color-surface-secondary);
    color: var(--color-text-secondary);
```

**Step 6: Verify build and lint**

Run: `npm run build --prefix frontend`
Run: `npm run lint --prefix frontend`
Expected: Both pass

**Step 7: Commit**

```
git add frontend/src/assets/main.css
git commit -m "feat(theme): update component classes to use semantic tokens"
```

---

## Task 5: Create useTheme Composable

**Files:**
- Create: `frontend/src/composables/useTheme.ts`

**Step 1: Create the composable file**

```typescript
import { ref, computed, watch, onMounted } from 'vue';

export type ThemePreference = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

const STORAGE_KEY = 'theme';

function getStoredPreference(): ThemePreference {
  if (typeof window === 'undefined') return 'system';
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'light' || stored === 'dark' || stored === 'system') {
    return stored;
  }
  return 'system';
}

function getSystemPreference(): ResolvedTheme {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

// Shared state across all instances
const preference = ref<ThemePreference>(getStoredPreference());
const systemPreference = ref<ResolvedTheme>(getSystemPreference());

export function useTheme() {
  const resolvedTheme = computed<ResolvedTheme>(() => {
    if (preference.value === 'system') {
      return systemPreference.value;
    }
    return preference.value;
  });

  const isDark = computed(() => resolvedTheme.value === 'dark');

  function toggle(): void {
    preference.value = isDark.value ? 'light' : 'dark';
  }

  function setTheme(theme: ThemePreference): void {
    preference.value = theme;
  }

  // Apply theme to DOM and persist
  watch(
    resolvedTheme,
    (theme) => {
      document.documentElement.classList.toggle('dark', theme === 'dark');
      localStorage.setItem(STORAGE_KEY, preference.value);
    },
    { immediate: true }
  );

  // Listen for system preference changes
  onMounted(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e: MediaQueryListEvent) => {
      systemPreference.value = e.matches ? 'dark' : 'light';
    };
    mediaQuery.addEventListener('change', handler);
  });

  return {
    preference,
    resolvedTheme,
    isDark,
    toggle,
    setTheme,
  };
}
```

**Step 2: Verify TypeScript compiles**

Run: `npm run type-check --prefix frontend`
Expected: No errors

**Step 3: Commit**

```
git add frontend/src/composables/useTheme.ts
git commit -m "feat(theme): add useTheme composable for dark mode state"
```

---

## Task 6: Create ThemeToggle Component

**Files:**
- Create: `frontend/src/components/ui/ThemeToggle.vue`

**Step 1: Create the component**

```vue
<script setup lang="ts">
import { useTheme } from '@/composables/useTheme';

const { isDark, toggle } = useTheme();
</script>

<template>
  <button
    type="button"
    @click="toggle"
    class="p-2 rounded-xs text-victorian-paper-cream/80 hover:text-victorian-gold-light transition-colors focus:outline-none focus:ring-2 focus:ring-victorian-gold-muted"
    :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
    :title="isDark ? 'Light mode' : 'Dark mode'"
  >
    <!-- Sun icon (shown in dark mode - click for light) -->
    <svg
      v-if="isDark"
      class="w-5 h-5"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
      />
    </svg>
    <!-- Moon icon (shown in light mode - click for dark) -->
    <svg
      v-else
      class="w-5 h-5"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
      />
    </svg>
  </button>
</template>
```

**Step 2: Verify TypeScript and lint**

Run: `npm run type-check --prefix frontend`
Run: `npm run lint --prefix frontend`
Expected: Both pass

**Step 3: Commit**

```
git add frontend/src/components/ui/ThemeToggle.vue
git commit -m "feat(theme): add ThemeToggle component with sun/moon icons"
```

---

## Task 7: Add ThemeToggle to NavBar

**Files:**
- Modify: `frontend/src/components/layout/NavBar.vue`

**Step 1: Add import**

After line 4 (`import { useAuthStore } from "@/stores/auth";`), add:

```typescript
import ThemeToggle from "@/components/ui/ThemeToggle.vue";
```

**Step 2: Add toggle to desktop nav (before user menu)**

Find (around line 85):
```vue
        <!-- Right side: User Menu (desktop) + Hamburger (mobile) -->
        <div class="flex items-center gap-4">
          <!-- User Menu - Desktop -->
```

Change to:
```vue
        <!-- Right side: User Menu (desktop) + Hamburger (mobile) -->
        <div class="flex items-center gap-4">
          <!-- Theme Toggle - Desktop -->
          <div class="hidden md:block">
            <ThemeToggle />
          </div>
          <!-- User Menu - Desktop -->
```

**Step 3: Add toggle to mobile nav (before hamburger)**

Find (around line 159):
```vue
          <!-- Hamburger Menu Button - Mobile -->
          <button
            @click="toggleMobileMenu"
```

Add before the hamburger button:
```vue
          <!-- Theme Toggle - Mobile -->
          <div class="md:hidden">
            <ThemeToggle />
          </div>
          <!-- Hamburger Menu Button - Mobile -->
          <button
            @click="toggleMobileMenu"
```

**Step 4: Verify build and lint**

Run: `npm run type-check --prefix frontend`
Run: `npm run lint --prefix frontend`
Expected: Both pass

**Step 5: Commit**

```
git add frontend/src/components/layout/NavBar.vue
git commit -m "feat(theme): add ThemeToggle to NavBar (desktop and mobile)"
```

---

## Task 8: Add Flash Prevention Script to index.html

**Files:**
- Modify: `frontend/index.html`

**Step 1: Add inline script in head**

Find the `<head>` section. After the existing content (before `</head>`), add:

```html
    <!-- Prevent flash of wrong theme on load -->
    <script>
      (function() {
        var p = localStorage.getItem('theme');
        var dark = p === 'dark' || (p !== 'light' && window.matchMedia('(prefers-color-scheme: dark)').matches);
        if (dark) document.documentElement.classList.add('dark');
      })();
    </script>
```

**Step 2: Verify HTML is valid**

Run: `npm run build --prefix frontend`
Expected: Build succeeds

**Step 3: Commit**

```
git add frontend/index.html
git commit -m "feat(theme): add flash prevention script to index.html"
```

---

## Task 9: Fix NavBar Dropdown for Dark Mode

**Files:**
- Modify: `frontend/src/components/layout/NavBar.vue`

**Step 1: Update dropdown menu background**

Find (around line 112-114):
```vue
                  <div
                    v-if="showDropdown"
                    class="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-50"
```

Change to:
```vue
                  <div
                    v-if="showDropdown"
                    class="absolute right-0 mt-2 w-48 rounded-md shadow-lg py-1 z-50"
                    style="background-color: var(--color-surface-elevated)"
```

**Step 2: Update dropdown menu item colors**

Find all instances of `text-gray-700 hover:bg-gray-100` in the dropdown items (around lines 117-141) and change to:

```vue
class="block px-4 py-2 text-sm hover:bg-black/10 dark:hover:bg-white/10"
style="color: var(--color-text-primary)"
```

Apply this to:
- Profile link
- Config link
- Admin Settings link
- Sign Out button

**Step 3: Verify build and lint**

Run: `npm run type-check --prefix frontend`
Run: `npm run lint --prefix frontend`
Expected: Both pass

**Step 4: Commit**

```
git add frontend/src/components/layout/NavBar.vue
git commit -m "feat(theme): fix NavBar dropdown colors for dark mode"
```

---

## Task 10: Add Unit Tests for useTheme

**Files:**
- Create: `frontend/src/composables/__tests__/useTheme.spec.ts`

**Step 1: Create test file**

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useTheme } from '../useTheme';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    clear: () => {
      store = {};
    },
  };
})();

// Mock matchMedia
const createMatchMediaMock = (matches: boolean) => {
  return vi.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
};

describe('useTheme', () => {
  beforeEach(() => {
    localStorageMock.clear();
    Object.defineProperty(window, 'localStorage', { value: localStorageMock });
    document.documentElement.classList.remove('dark');
  });

  it('defaults to system preference when no stored value', () => {
    window.matchMedia = createMatchMediaMock(false);
    const { resolvedTheme, isDark } = useTheme();
    expect(resolvedTheme.value).toBe('light');
    expect(isDark.value).toBe(false);
  });

  it('respects stored light preference', () => {
    localStorageMock.setItem('theme', 'light');
    window.matchMedia = createMatchMediaMock(true); // System is dark
    const { resolvedTheme } = useTheme();
    expect(resolvedTheme.value).toBe('light');
  });

  it('respects stored dark preference', () => {
    localStorageMock.setItem('theme', 'dark');
    window.matchMedia = createMatchMediaMock(false); // System is light
    const { resolvedTheme } = useTheme();
    expect(resolvedTheme.value).toBe('dark');
  });

  it('toggle switches from light to dark', () => {
    localStorageMock.setItem('theme', 'light');
    window.matchMedia = createMatchMediaMock(false);
    const { isDark, toggle } = useTheme();
    expect(isDark.value).toBe(false);
    toggle();
    expect(isDark.value).toBe(true);
  });

  it('toggle switches from dark to light', () => {
    localStorageMock.setItem('theme', 'dark');
    window.matchMedia = createMatchMediaMock(false);
    const { isDark, toggle } = useTheme();
    expect(isDark.value).toBe(true);
    toggle();
    expect(isDark.value).toBe(false);
  });

  it('setTheme updates preference', () => {
    window.matchMedia = createMatchMediaMock(false);
    const { preference, setTheme } = useTheme();
    setTheme('dark');
    expect(preference.value).toBe('dark');
  });
});
```

**Step 2: Run tests**

Run: `npm run test --prefix frontend -- --run`
Expected: All tests pass

**Step 3: Commit**

```
git add frontend/src/composables/__tests__/useTheme.spec.ts
git commit -m "test(theme): add unit tests for useTheme composable"
```

---

## Task 11: Final Verification and PR

**Step 1: Run all checks**

Run: `npm run type-check --prefix frontend`
Run: `npm run lint --prefix frontend`
Run: `npm run build --prefix frontend`
Expected: All pass

**Step 2: Manual testing checklist**

- [ ] Light mode displays correctly (default)
- [ ] Click toggle → switches to dark mode
- [ ] Dark mode colors match design (deep forest green bg)
- [ ] Cards, inputs, buttons all themed correctly
- [ ] Reload page → dark mode persists
- [ ] Toggle back to light → persists
- [ ] Set OS to dark mode, clear localStorage, reload → follows system
- [ ] Mobile: toggle visible next to hamburger
- [ ] Dropdown menu readable in both modes

**Step 3: Push branch**

```
git push -u origin feat/626-victorian-dark-mode
```

**Step 4: Create PR to staging**

```
gh pr create --base staging --title "feat: Add Victorian dark mode theme (#626)" --body "## Summary
- Add semantic color tokens for theme-aware styling
- Add dark mode CSS overrides (Victorian 'Evening Reading' palette)
- Add useTheme composable for state management
- Add ThemeToggle component to navbar
- System preference detection with manual override
- Preference persists to localStorage

## Test Plan
- [ ] Toggle switches between light/dark
- [ ] Preference persists across reload
- [ ] System preference respected
- [ ] All components themed correctly
- [ ] Accessibility: keyboard navigable, proper aria-labels

Closes #626"
```

---

## Summary

| Task | Description | Est. Time |
|------|-------------|-----------|
| 1 | Add semantic tokens to @theme | 2 min |
| 2 | Add dark mode CSS overrides | 2 min |
| 3 | Update body background | 2 min |
| 4 | Update component classes | 5 min |
| 5 | Create useTheme composable | 5 min |
| 6 | Create ThemeToggle component | 3 min |
| 7 | Add toggle to NavBar | 3 min |
| 8 | Add flash prevention script | 2 min |
| 9 | Fix NavBar dropdown | 3 min |
| 10 | Add unit tests | 5 min |
| 11 | Final verification + PR | 5 min |

**Total: ~37 minutes**
