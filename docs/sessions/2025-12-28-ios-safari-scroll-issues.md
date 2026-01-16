# iOS Safari Mobile Scroll Issues - Session Log

**Date:** 2025-12-28
**Branch:** staging (tailwind-v4 worktree)
**Related Issues:** Follow-up from Tailwind v4 migration

## Background

After deploying Tailwind v4 migration and animation system features to staging, user reported two iOS Safari mobile scroll issues:

1. **BookDetailView** - Nav bar not visible on first load, requires scrolling up
2. **AnalysisViewer modal** - Header (triple dots menu + X button) not visible, requires scrolling up

User stated: "We had to address this on other tabs so I assume the fix that was applied to this needs to be applied to 1) and 2)"

## Investigation (Systematic Debugging)

### Phase 1: Root Cause Investigation

Found existing fix pattern in commit `e02aa32`:

- NavBar uses `sticky z-50` with `style="top: env(safe-area-inset-top, 0px)"`
- main.css has iOS safe area support for body left/right padding
- index.html has `viewport-fit=cover` in meta viewport

### Phase 2: Pattern Analysis

**Working pattern (NavBar):**

```html
<nav
  class="bg-victorian-hunter-900 text-white shadow-lg sticky z-50"
  style="top: env(safe-area-inset-top, 0px)"
>
```

**Broken components:**

- BookDetailView - async content loading causes router scroll reset to fire before content renders
- AnalysisViewer - modal opens but header appears scrolled out of view

### Phase 3: Hypothesis Testing

**Initial hypothesis (WRONG for Issue 2):** Safe-area insets causing header to be hidden behind notch.

- Added `padding-top: env(safe-area-inset-top, 0px)` to AnalysisViewer panel
- Result: No effect - "same behavior"

**Revised hypothesis:** The issue is scroll position, NOT safe-area insets.

- Screenshot evidence shows content loading in scrolled-down state
- NavBar is ABOVE the visible viewport, not behind notch
- iOS Safari may have scroll state affecting fixed modal positioning

## Fixes Applied

### Fix 1: BookDetailView (WORKED)

Added scroll reset after async content loads:

```javascript
onMounted(async () => {
  // ... fetch book and images ...

  // Scroll to top after content loads (iOS Safari workaround)
  window.scrollTo({ top: 0, left: 0, behavior: "instant" });
});
```

### Fix 2: AnalysisViewer (DID NOT WORK)

Initial attempt - padding approach was wrong:

```html
<div style="padding-top: env(safe-area-inset-top, 0px)">
```

**Next step:** Add scroll reset when modal opens (similar to Fix 1)

## Next Steps

1. **Remove** the ineffective padding-top from AnalysisViewer panel
2. **Add** scroll reset in the visible watcher when modal opens:

   ```javascript
   watch(
     () => props.visible,
     (visible) => {
       if (visible) {
         document.body.style.overflow = "hidden";
         window.scrollTo({ top: 0, left: 0, behavior: "instant" });
       }
       // ...
     }
   );
   ```

3. **Test** on iOS Safari mobile
4. **If still not working**, investigate iOS Safari-specific fixed positioning issues

## Files Modified

- `frontend/src/views/BookDetailView.vue` - Added scroll reset (committed)
- `frontend/src/components/books/AnalysisViewer.vue` - Added padding (committed, but needs revision)

## Commits

- `0b6a61f fix: iOS Safari mobile scroll issues for book view and analysis modal`

---

## CRITICAL REMINDERS FOR CONTINUATION

### 1. ALWAYS Use Superpowers Skills

**Before ANY task, check if a skill applies:**

- `systematic-debugging` - For ANY bug or unexpected behavior
- `verification-before-completion` - Before claiming work is done
- `test-driven-development` - When implementing features
- `brainstorming` - Before coding new features

**If a skill might apply, USE IT. This is not optional.**

### 2. Bash Command Rules (CRITICAL)

**NEVER use these - they trigger permission prompts:**

- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings

**ALWAYS use:**

- Simple single-line commands
- Separate sequential Bash tool calls instead of &&
- `bmx-api` for all BlueMoxon API calls (no permission prompts)

### 3. Workflow Reminder

- Working in `/Users/mark/projects/bluemoxon/.worktrees/tailwind-v4`
- Direct commits to `staging` branch (no PR needed for this worktree)
- After fix: test on iOS Safari mobile, then promote staging to production
