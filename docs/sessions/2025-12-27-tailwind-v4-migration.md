# Tailwind CSS v4 Migration - Session Log

**Issue:** #166
**Date:** 2025-12-27 to 2025-12-28
**Postmortem:** `docs/postmortems/2025-12-28-tailwind-v4-migration.md`

---

## Current Status (2025-12-28 ~19:00 UTC)

### Issue #5: CSS Cascade Layers Breaking Form Elements - FIX PENDING REVIEW

**Branch:** `fix/tailwind-v4-forms-plugin`
**PR #617:** <https://github.com/markthebest12/bluemoxon/pull/617>
**Status:** CI passing, AWAITING USER REVIEW before merge

### Solution Implemented

Added `@tailwindcss/forms` plugin to provide properly styled form elements:

```css
@import "tailwindcss";

/* Tailwind Forms Plugin - provides properly styled form elements that work with utilities */
@plugin "@tailwindcss/forms";
```

**Changes in PR #617:**

- Installed `@tailwindcss/forms` as devDependency
- Added `@plugin "@tailwindcss/forms";` to main.css (v4 syntax)

### Important Caveat

The `@tailwindcss/forms` plugin styles `input`, `select`, `textarea` elements but does NOT directly style `<button>` elements. If buttons are still broken after this PR:

**Potential additional fixes needed:**

1. Override button preflight in `@layer base`:

   ```css
   @layer base {
     button {
       background-color: revert;
       border-radius: revert;
     }
   }
   ```

2. Ensure all buttons use `.btn-*` component classes instead of utility classes directly

---

## Root Cause Analysis (Issue #5)

### The Problem

Tailwind v4 preflight in `@layer base` resets form elements:

```css
button, input, select, optgroup, textarea {
  background-color: transparent;
  border-radius: 0;
  padding: 0;
}
```

Despite `@layer utilities` being declared AFTER `@layer base`, utility classes were not overriding the form element reset for buttons specifically.

### Evidence from Playwright Testing

| Element | `.bg-blue-600` Works? | Computed Background |
|---------|----------------------|---------------------|
| `<div>` | YES | `oklch(0.546 0.245 262.881)` |
| `<button>` | NO | `rgba(0, 0, 0, 0)` (transparent) |

### Key Technical Differences

| Aspect | Production (v3) | Staging (v4) |
|--------|-----------------|--------------|
| CSS Rules | 561 flat rules | 62 rules in @layer blocks |
| `@layer` usage | NONE | `@layer properties, theme, base, components, utilities` |
| Form element reset | Works with utilities | Utilities DON'T override base for form elements |

---

## Next Steps After User Review

1. **User reviews PR #617** - Do NOT merge without approval
2. **If approved:** Merge PR #617 to staging
3. **Deploy and validate:** Visual comparison staging vs production
4. **If buttons still broken:** Implement button-specific fix (override in @layer base)
5. **Update postmortem** with Issue #5 complete findings
6. **Promote to production** via staging→main PR

---

## PRs in This Migration

| PR | Title | Status | Notes |
|----|-------|--------|-------|
| #609 | feat: Upgrade to Tailwind CSS v4 | Merged | Initial migration |
| #612 | fix: Navbar logo height | Merged | Added !h-14 |
| #613 | fix: Deprecated classes | Merged | **Wrong** - doubled radius |
| #614 | fix: Add --radius-xs to @theme | Merged | Correct radius fix |
| #615 | fix: Replace space-*with gap-* | Merged | Partial fix |
| #616 | fix: Convert @utility to @layer components | Merged to staging | Partial fix |
| #617 | fix: Add @tailwindcss/forms plugin | **PENDING REVIEW** | Issue #5 fix |

---

## Issues Identified in This Migration

| Issue | Root Cause | Status |
|-------|-----------|--------|
| #1 | `rounded-xs` needs `--radius-xs` in @theme | FIXED (PR #614) |
| #2 | `space-*` has zero specificity due to `:where()` wrapper | FIXED (PR #615) |
| #3 | Image height override needed `!h-14` | FIXED (PR #612) |
| #4 | `@utility` with `@apply` silently fails | FIXED (PR #616) |
| #5 | CSS Cascade Layers - form element reset overrides utilities | **PR #617 PENDING** |

---

## CRITICAL: Session Continuation Instructions

### 1. MANDATORY: Use Superpowers Skills

**ALWAYS check and use Superpowers skills at ALL stages. NO EXCEPTIONS.**

| Task Type | Required Skill Chain |
|-----------|---------------------|
| Debugging failures | `systematic-debugging` -> `root-cause-tracing` -> `defense-in-depth` |
| Code review | `requesting-code-review` -> `receiving-code-review` |
| Completing work | `verification-before-completion` -> `finishing-a-development-branch` |
| Any task | Check skill list FIRST, use if ANY skill applies |

**Rationalizations that mean FAILURE:**

- "This is simple, don't need skills" - WRONG
- "I can skip verification" - WRONG
- "I'll just fix this directly" - WRONG
- "I know the fix already" - WRONG

**If you think there is even a 1% chance a skill might apply, YOU MUST USE IT.**

### 2. NEVER Use These Bash Patterns (Trigger Permission Prompts)

```bash
# NEVER USE - ALL OF THESE TRIGGER PERMISSION PROMPTS:

# comment lines before commands
command1 \
  --with-continuation           # backslash line continuations
command $(subcommand)           # $(...) command substitution
command1 && command2            # && chaining
command1 || command2            # || chaining
echo "password!"                # ! in quoted strings
```

**ENFORCEMENT:** If you catch yourself about to use `&&`, STOP. Make separate sequential Bash tool calls instead.

### 3. ALWAYS Use These Bash Patterns

```bash
# ALWAYS USE - These work without permission prompts:

# Simple single-line commands only
curl -s https://api.example.com/health

# Separate sequential Bash tool calls instead of &&
# (make multiple Bash tool calls, not one chained command)

# bmx-api for all BlueMoxon API calls (no permission prompts)
bmx-api GET /books
bmx-api --prod GET /books/123
bmx-api POST /books '{"title":"..."}'
bmx-api --text-file analysis.md PUT /books/123/analysis
```

---

## Technical Reference

### Why @utility with @apply Breaks in v4

Tailwind v4 changed how custom utilities work. The `@utility` directive with `@apply` inside does not properly expand the applied utilities into CSS properties. Some properties (like `background-color`) may work while others (`border`, `padding`) silently fail.

**Solution:** Use `@layer components` with explicit CSS properties and CSS custom variables from `@theme`.

### Why space-* Breaks in v4

Tailwind v4 wraps `space-*` in `:where()` giving zero CSS specificity:

```css
/* v4 - gets overridden by anything */
:where(.space-x-6>:not(:last-child)) { ... }

/* gap-* has normal specificity */
.gap-6 { gap: ...; }
```

### Why Form Elements Break in v4

The preflight form element reset in `@layer base` was overriding `@layer utilities` for form elements. The `@tailwindcss/forms` plugin provides properly layered form element styles that work with the utility system.

---

## Relevant Resources

- [Tailwind CSS Preflight docs](https://tailwindcss.com/docs/preflight)
- [Tailwind CSS Forms Plugin](https://github.com/tailwindlabs/tailwindcss-forms)
- [v4 Upgrade Guide](https://tailwindcss.com/docs/upgrade-guide)
- [Disabling Preflight in v4](https://github.com/tailwindlabs/tailwindcss/discussions/17481)
- [CSS Cascade Layers Discussion](https://github.com/tailwindlabs/tailwindcss/discussions/16578)

---

## Worktree Location

```
/Users/mark/projects/bluemoxon/.worktrees/tailwind-v4/
```

**Current Branch:** `fix/tailwind-v4-forms-plugin` (PR #617)
