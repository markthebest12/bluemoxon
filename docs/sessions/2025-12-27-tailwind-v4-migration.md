# Tailwind CSS v4 Migration - Session Log

**Issue:** #166
**Date:** 2025-12-27 to 2025-12-28
**Postmortem:** `docs/postmortems/2025-12-28-tailwind-v4-migration.md`

---

## Current Status (2025-12-28 ~23:30 UTC)

### PR #616 - AWAITING REVIEW

**Branch:** `fix/tailwind-v4-component-classes`
**PR:** https://github.com/markthebest12/bluemoxon/pull/616
**Status:** Created, awaiting user review before merge to staging

### Root Cause IDENTIFIED

The TRUE root cause of visual regressions was NOT `space-*` vs `gap-*` (that was a partial fix).

**Actual Root Cause:** `@utility` with `@apply` does NOT properly generate CSS in Tailwind v4.

Component classes defined with `@utility { @apply ... }` were silently failing:
- `.card` rendered with `border: 0px`, `padding: 0px` instead of intended styles
- `.input` rendered with `border: 0px`, `padding: 0px` instead of intended styles
- `.btn-primary`, `.btn-secondary`, etc. had missing or broken styles

### Evidence Gathered

Used Playwright `browser_evaluate` to compare computed styles:

| Element | Staging (broken) | Production (correct) |
|---------|------------------|---------------------|
| `.card` | `padding: 0px`, `border: 0px` | `padding: 24px`, `border: 1px solid rgb(232,225,213)` |
| `.input` | `padding: 0px`, `border: 0px` | `padding: 8px 12px`, `border: 1px solid rgb(232,225,213)` |

### Fix Applied in PR #616

Converted ALL `@utility` blocks to `@layer components` with explicit CSS properties:

**Before (broken in v4):**
```css
@utility card {
  @apply bg-victorian-paper-cream rounded-xs border border-victorian-paper-antique p-6;
}
```

**After (works in v4):**
```css
@layer components {
  .card {
    background-color: var(--color-victorian-paper-cream);
    border-radius: var(--radius-xs);
    border: 1px solid var(--color-victorian-paper-antique);
    padding: 1.5rem;
    /* ... explicit CSS properties */
  }
}
```

### Components Fixed

- `btn-primary`, `btn-secondary`, `btn-danger`, `btn-accent`
- `card`, `card-static`
- `input`, `select`
- `badge-binder`, `badge-zaehnsdorf`, `badge-riviere`, `badge-sangorski`, `badge-bayntun`, `badge-default`
- `divider-flourish`, `divider-flourish-symbol`, `section-header`

### Verified in Local Build

```
npm run build  # SUCCESS

# Compiled CSS contains proper styles:
.btn-primary { background-color:var(--color-victorian-hunter-800); border:1px solid...; padding:.5rem 1rem }
.card { background-color:var(--color-victorian-paper-cream); border:1px solid...; padding:1.5rem }
.input { background-color:var(--color-victorian-paper-white); border:1px solid...; padding:.5rem .75rem }
```

---

## Next Steps

1. **User reviews PR #616** - DO NOT MERGE until approved
2. **After approval:** Merge to staging, deploy, validate visually
3. **Visual comparison:** Compare staging screenshots to production baseline
4. **If validated:** Promote staging to main
5. **Update postmortem** with root cause findings

---

## PRs in This Migration

| PR | Title | Status | Notes |
|----|-------|--------|-------|
| #609 | feat: Upgrade to Tailwind CSS v4 | Merged | Initial migration |
| #612 | fix: Navbar logo height | Merged | Added !h-14 |
| #613 | fix: Deprecated classes | Merged | **Wrong** - doubled radius |
| #614 | fix: Add --radius-xs to @theme | Merged | Correct radius fix |
| #615 | fix: Replace space-* with gap-* | Merged to staging | Partial fix only |
| #616 | fix: Convert @utility to @layer components | **AWAITING REVIEW** | TRUE root cause fix |

---

## CRITICAL: Session Continuation Instructions

### 1. MANDATORY: Use Superpowers Skills

**ALWAYS check and use Superpowers skills at ALL stages:**

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

### 2. NEVER Use These Bash Patterns (Trigger Permission Prompts)

```bash
# NEVER USE:
# comment lines before commands
command1 \
  --with-continuation           # backslash line continuations
command $(subcommand)           # $(...) command substitution
command1 && command2            # && chaining
command1 || command2            # || chaining
echo "password!"                # ! in quoted strings
```

### 3. ALWAYS Use These Bash Patterns

```bash
# ALWAYS USE:
# Simple single-line commands only
curl -s https://api.example.com/health

# Separate sequential Bash tool calls instead of &&
# (make multiple Bash tool calls, not one chained command)

# bmx-api for all BlueMoxon API calls (no permission prompts)
bmx-api GET /books
bmx-api --prod GET /books/123
```

---

## Technical Reference

### Why @utility with @apply Breaks in v4

Tailwind v4 changed how custom utilities work. The `@utility` directive with `@apply` inside does not properly expand the applied utilities into CSS properties. Some properties (like `background-color`) may work while others (`border`, `padding`) silently fail.

**Solution:** Use `@layer components` with explicit CSS properties and CSS custom variables from `@theme`.

### Why space-* Breaks in v4 (Previous Finding)

Tailwind v4 wraps `space-*` in `:where()` giving zero CSS specificity:

```css
/* v4 - gets overridden by anything */
:where(.space-x-6>:not(:last-child)) { ... }

/* gap-* has normal specificity */
.gap-6 { gap: ...; }
```

---

## Worktree Location

```
/Users/mark/projects/bluemoxon/.worktrees/tailwind-v4/
```

Branch: `fix/tailwind-v4-component-classes` (PR #616)
