# Session: Frontend Modernization - Tailwind v4 & ESLint 9 Features

**Date:** 2025-12-28
**Status:** In progress - brainstorming animation system design

## CRITICAL: Session Rules

### ALWAYS Use Superpowers Skills
- **MANDATORY:** Use superpowers skills at ALL stages (brainstorming, planning, implementation, review)
- Before ANY task, check if a skill applies and USE IT
- Follow skill instructions EXACTLY as written
- Current skill in use: `superpowers:brainstorming`

### Bash Command Formatting (NEVER violate)

**NEVER use (triggers permission prompts):**
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` or `$((...))` command/arithmetic substitution
- `||` or `&&` chaining (even simple chaining breaks auto-approve)
- `!` in quoted strings (bash history expansion corrupts values)

**ALWAYS use:**
- Simple single-line commands only
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls (no permission prompts)

---

## Background

After completing Tailwind v4 (#166) and ESLint 9 (#567) migrations, we explored modern features to leverage. Created 4 GitHub issues:

| Issue | Title | Priority |
|-------|-------|----------|
| #623 | Container queries for responsive components | - |
| #624 | Micro-interactions and polish animations | **CURRENT** |
| #625 | Stricter TypeScript-ESLint rules | - |
| #626 | Victorian dark mode theme | - |

User chose #624 (animations) as first priority because UI feels static/unpolished.

## Scope Decisions Made

1. **Scope:** Full treatment (1-2 days) - comprehensive animation system
2. **Coverage:** Light pass across entire app (not focused on one area)
3. **Areas:** Acquisitions dashboard, book details, navigation/modals, loading states

## Design Sections - Approval Status

### Section 1: Animation Design Tokens ✅ APPROVED

```css
@theme {
  /* Durations */
  --duration-instant: 75ms;    /* Micro-feedback (button press) */
  --duration-fast: 150ms;      /* Hover states, small transitions */
  --duration-normal: 250ms;    /* Modals, dropdowns, standard UI */
  --duration-slow: 400ms;      /* Page transitions, large reveals */
  --duration-slower: 600ms;    /* Skeleton pulse, ambient motion */

  /* Easings */
  --ease-out-soft: cubic-bezier(0.25, 0.1, 0.25, 1);
  --ease-out-back: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-spring: cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
```

### Section 2: Hover States & Interactive Feedback ✅ APPROVED

```css
@layer components {
  .card-interactive {
    transition: transform var(--duration-fast) var(--ease-out-soft),
                box-shadow var(--duration-fast) var(--ease-out-soft);
  }
  .card-interactive:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 16px -4px rgb(0 0 0 / 0.1),
                0 4px 6px -2px rgb(0 0 0 / 0.05);
  }

  .btn-press {
    transition: transform var(--duration-instant) var(--ease-out-soft);
  }
  .btn-press:active {
    transform: scale(0.97);
  }

  .link-animated { /* ... animated underline on hover */ }
}
```

### Section 3: Modal & Dropdown Transitions ✅ APPROVED

```css
@layer components {
  /* Modal backdrop fade */
  .modal-backdrop-enter-from, .modal-backdrop-leave-to { opacity: 0; }
  .modal-backdrop-enter-active, .modal-backdrop-leave-active {
    transition: opacity var(--duration-normal) var(--ease-out-soft);
  }

  /* Modal content - fade + slide */
  .modal-enter-from { opacity: 0; transform: translateY(16px) scale(0.98); }
  .modal-leave-to { opacity: 0; transform: translateY(-8px) scale(0.98); }
  .modal-enter-active { transition: all var(--duration-normal) var(--ease-spring); }
  .modal-leave-active { transition: all var(--duration-fast) var(--ease-out-soft); }

  /* Dropdown menu */
  .dropdown-enter-from, .dropdown-leave-to { opacity: 0; transform: translateY(-4px); }
  .dropdown-enter-active, .dropdown-leave-active {
    transition: all var(--duration-fast) var(--ease-out-soft);
  }
}
```

### Section 4: Loading States ⏳ NOT YET PRESENTED

Still need to design:
- Skeleton screens with `animate-pulse`
- AI analysis generation progress indicators
- Spinner animations for async operations

### Section 5: Component Application ⏳ NOT YET PRESENTED

Still need to define:
- Which components get which animation classes
- Vue `<Transition>` wrapper patterns
- Testing approach

## Next Steps

1. **Continue brainstorming skill** - present Section 4 (Loading States)
2. Present Section 5 (Component Application)
3. Ask if design looks complete
4. Write design doc to `docs/plans/2025-12-28-animation-system-design.md`
5. Use `superpowers:using-git-worktrees` to create isolated workspace
6. Use `superpowers:writing-plans` to create implementation plan
7. Implement with TDD approach

## Related Issues

- #624 - Main tracking issue for this work
- #166 - Tailwind v4 migration (completed)
- #567 - ESLint 9 migration (completed)
- #623 - Container queries (future)
- #625 - Stricter ESLint rules (future)
- #626 - Dark mode (future)
