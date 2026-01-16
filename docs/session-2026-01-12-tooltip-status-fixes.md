# Session: Tooltip and Status Filter Fixes

**Date:** 2026-01-12
**Branch:** `fix/tooltip-status-filter`
**PR:** #1098

## Background

After merging PR #1097 (dashboard tooltips and click-to-filter), user testing revealed three issues:

1. **Tooltips clipped** - BaseTooltip content was being cut off by parent card containers with `overflow: hidden`
2. **status=ON_HAND filter not working** - URL parameter wasn't being synced in BooksView
3. **Premium card missing status filter** - Clicked to `binding_authenticated=true` but should also include `status=ON_HAND`

## Fixes Applied

### 1. BaseTooltip Rewrite (Teleport)

**File:** `frontend/src/components/BaseTooltip.vue`

Rewrote component to use Vue's `<Teleport to="body">` with fixed positioning:

- Tooltip renders outside parent overflow containers
- Position calculated from trigger element's `getBoundingClientRect()`
- Updates on scroll/resize while visible
- Style only computed when visible to avoid conflicts with v-show

### 2. Status Filter Sync

**File:** `frontend/src/views/BooksView.vue`

Added missing line to `syncFiltersFromUrl()`:

```typescript
booksStore.filters.status = (route.query.status as string) || undefined;
```

### 3. Premium FilterParam

**File:** `frontend/src/constants/index.ts`

Updated PREMIUM constant:

```typescript
filterParam: "binding_authenticated=true&status=ON_HAND",
```

## Current Blocker: Test Failure

**File:** `frontend/src/components/__tests__/AnalysisIssuesWarning.spec.ts`

The "shows tooltip on hover" test is failing because:

- Test triggers `mouseenter` on the BaseTooltip wrapper
- `isVisible` ref should become `true`, removing `display: none`
- But tooltip remains hidden after event

**Attempts made:**

1. Stubbing Teleport - didn't help
2. Using `attachTo` for real DOM - didn't help
3. Native `dispatchEvent` - didn't help
4. `flushPromises()` and `nextTick()` - didn't help

**Root cause hypothesis:** JSDOM doesn't properly handle mouseenter events with Vue's event binding. The event is fired but the Vue component's `show()` handler isn't being invoked.

**Next steps to try:**

1. Mock the `isVisible` ref directly via component instance
2. Use `wrapper.vm` to access component internals
3. Test BaseTooltip in isolation first
4. Consider using `@vue/test-utils` `setValue` on a wrapper method

## Files Modified (Uncommitted Test Changes)

- `frontend/src/components/BaseTooltip.vue` - Teleport rewrite
- `frontend/src/components/__tests__/AnalysisIssuesWarning.spec.ts` - Updated test (failing)
- `frontend/src/views/BooksView.vue` - Status filter sync
- `frontend/src/constants/index.ts` - Premium filterParam

## Git Status

- On branch: `fix/tooltip-status-filter`
- Committed: Initial fixes (69ff7d0)
- Uncommitted: Test file changes attempting to fix the failing test

---

## CRITICAL REMINDERS FOR NEXT SESSION

### 1. ALWAYS Use Superpowers Skills

Invoke relevant skills BEFORE any response or action:

- `superpowers:brainstorming` - Before any creative/feature work
- `superpowers:systematic-debugging` - For ANY bug/test failure
- `superpowers:test-driven-development` - Before writing implementation code
- `superpowers:verification-before-completion` - Before claiming work is done

**If a skill might apply (even 1% chance), invoke it.**

### 2. NEVER Use These Bash Patterns (Permission Prompts)

```bash
# BAD - triggers permission prompts:
# Comment lines before commands
command1 \
  --with-continuation
$(command substitution)
command1 && command2
command1 || command2
password='Test1234!'  # ! gets expanded
```

### 3. ALWAYS Use These Patterns

```bash
# GOOD - no permission prompts:
simple-single-line-command --flag value
```

For sequential operations, use **separate Bash tool calls** instead of `&&`.

For API calls, use `bmx-api`:

```bash
bmx-api GET /books
bmx-api --prod GET /books/123
```

### 4. Test Fix Strategy

For the failing BaseTooltip test, try:

```typescript
// Access component instance directly
const vm = wrapper.findComponent(BaseTooltip).vm;
vm.isVisible = true;
await nextTick();
// Then check tooltip visibility
```

Or test BaseTooltip in isolation with simpler assertions.
