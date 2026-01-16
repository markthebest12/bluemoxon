# App Shell Design (#876)

**Date:** 2026-01-06
**Issue:** [#876](https://github.com/bluemoxon/bluemoxon/issues/876) - perf: [Quick Win] Prefetch HomeView + show app shell during auth
**Status:** Approved

## Problem

Frontend waterfall shows ~9 second blank page on cold start:

1. `fetchAuthSession()` - 825ms (Cognito)
2. `/users/me` API call - 7+ seconds (Lambda cold start)
3. HomeView.vue loads (4KB, 179ms)

Users see nothing during this entire sequence.

## Solution

**Option A: Static HTML skeleton** (chosen)

Render a static nav bar and loading skeleton in `index.html` that users see immediately. When Vue mounts, it replaces this content seamlessly.

### Visual Timeline

**Before:**

```text
0s        1s        2s        3s        ...       9s
|---------|---------|---------|---------|---------|
[       BLANK PAGE                      ][Content]
```

**After:**

```text
0s        1s        2s        3s        ...       9s
|---------|---------|---------|---------|---------|
[Nav+Skeleton immediately][  Same skeleton  ][Content]
```

## Implementation

### 1. index.html - Static Skeleton

Add inside `<div id="app">`:

```html
<!-- App Shell - shown immediately, replaced when Vue mounts -->
<nav class="app-shell-nav">
  <div class="nav-container">
    <a href="/" class="nav-logo">BlueMoxon</a>
    <div class="nav-links">
      <a href="/">Collection</a>
      <a href="/about">About</a>
    </div>
  </div>
</nav>
<main class="app-shell-main">
  <div class="skeleton-header"></div>
  <div class="skeleton-grid">
    <div class="skeleton-card"></div>
    <div class="skeleton-card"></div>
    <div class="skeleton-card"></div>
    <div class="skeleton-card"></div>
    <div class="skeleton-card"></div>
    <div class="skeleton-card"></div>
  </div>
</main>
```

Add inline `<style>` with critical CSS (~30 lines):

- Nav bar styling matching NavBar.vue
- Skeleton card dimensions matching BookCard.vue
- Pulse animation for loading effect
- Theme-aware using CSS custom properties

### 2. main.ts - Prefetch HomeView

```typescript
// Start prefetching HomeView immediately (don't await)
const homeViewPrefetch = import("@/views/HomeView.vue");

async function initApp() {
  try {
    await fetchAuthSession();
  } catch (_e) { /* ... */ }

  const app = createApp(App);
  app.use(createPinia());
  app.use(router);
  app.mount("#app");

  // Ensure prefetch completes (likely already done)
  homeViewPrefetch.catch(() => {
    // Ignore - router will handle if needed
  });
}
```

### 3. App.vue - No Changes

Vue naturally replaces `#app` content when it mounts.

## Files to Modify

| File | Change |
|------|--------|
| `frontend/index.html` | Add static nav + skeleton HTML + inline CSS |
| `frontend/src/main.ts` | Add speculative HomeView import |

## Testing Strategy

### Unit Test (main.prefetch.spec.ts)

- Verify `import()` called before `fetchAuthSession()` resolves
- Verify `.catch()` handler doesn't throw

### E2E Test (app-shell.spec.ts)

- Nav bar visible within 500ms
- Skeleton cards visible before auth completes
- Seamless replacement when Vue mounts (no flicker)

## Acceptance Criteria

- [ ] Nav bar visible within 1 second of page load
- [ ] Loading skeleton shown while auth in progress
- [ ] HomeView chunk prefetched during auth wait

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| **A. Static HTML (chosen)** | Fastest paint, works without JS | Slight nav duplication |
| B. Mount Vue immediately | Single source of truth | Complex state management |
| C. Vue Suspense | Most Vue-native | Requires auth restructure |

## Impact

- **User impact:** High - meaningful content 8+ seconds sooner
- **Effort:** Low - ~50 lines of code
- **Risk:** Low - additive change, easy rollback
