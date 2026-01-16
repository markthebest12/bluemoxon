# Session Log: Victorian Dark Mode Implementation

**Date:** 2025-12-28
**Issue:** #626
**Branch:** `feat/626-victorian-dark-mode`
**PR:** #638 (targeting staging)
**Status:** Code review fixes applied, awaiting CI/merge

---

## Background

Implemented a warm, Victorian "Evening Reading" dark mode with:

- System preference detection (`prefers-color-scheme: dark`)
- Manual toggle in navbar
- localStorage persistence
- Flash prevention (FOUC)

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│ CSS Layer                                                   │
│ ┌─────────────────┐  ┌─────────────────────────────────────┐│
│ │ @theme          │  │ .dark { }                           ││
│ │ --color-surface-*│  │ Overrides semantic tokens          ││
│ │ --color-text-*  │  │ Victorian evening palette           ││
│ │ --color-border-*│  │ #1a2318 base, gold accents          ││
│ └─────────────────┘  └─────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│ useTheme.ts (Singleton Pattern)                             │
│ - Module-level refs: preference, systemPreference           │
│ - Module-level watch: applies .dark class, persists to LS   │
│ - Module-level listener: system preference changes          │
│ - useTheme() just returns shared state + toggle/setTheme    │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│ ThemeToggle.vue                                             │
│ - Sun/moon icons                                            │
│ - In NavBar (desktop + mobile)                              │
└─────────────────────────────────────────────────────────────┘
```

## Commits (11 total)

1. `cd8b393` - feat(theme): add semantic color tokens to @theme
2. `84c17f0` - feat(theme): add dark mode CSS variable overrides
3. `1af7892` - feat(theme): use semantic token for body background
4. `305ddef` - feat(theme): update component classes to semantic tokens
5. `ab5b8ed` - feat(theme): add useTheme composable for dark mode state
6. `398bc28` - feat(theme): add ThemeToggle component with sun/moon icons
7. `4b7e380` - feat(theme): add ThemeToggle to NavBar (desktop and mobile)
8. `a1eb2d2` - feat(theme): add flash prevention script to index.html
9. `bd77892` - feat(theme): fix NavBar dropdown colors for dark mode
10. `7d04c9f` - test(theme): add unit tests for useTheme composable
11. `e350663` - fix(theme): address code review feedback

## Code Review Fixes Applied

| Issue | Status | Fix |
|-------|--------|-----|
| Memory leak (listener never removed) | **Fixed** | Moved to module level singleton |
| Multiple watchers per component | **Fixed** | Moved to module level singleton |
| Placeholder not themed | **Fixed** | Use `--color-text-muted` |
| FOUC script sync comment | **Fixed** | Added SYNC comment |
| Inline styles in NavBar | **Fixed** | Tailwind `bg-[var(...)]` syntax |
| Singleton behavior test | **Fixed** | Added test |
| ThemeToggle hardcoded colors | **No change** | Intentional for always-dark navbar |
| Orphan hex values | **Deferred** | Follow-up issue for named tokens |

## Files Modified

```text
frontend/
├── index.html                          # FOUC prevention script
├── src/
│   ├── assets/main.css                 # Semantic tokens + .dark overrides
│   ├── components/
│   │   ├── layout/NavBar.vue           # ThemeToggle integration
│   │   └── ui/ThemeToggle.vue          # NEW - toggle component
│   └── composables/
│       ├── useTheme.ts                 # NEW - singleton composable
│       └── __tests__/useTheme.spec.ts  # NEW - 6 tests
```

## Next Steps

1. **Wait for CI** on PR #638
2. **Merge to staging** after CI passes
3. **Test in staging:**
   - [ ] Toggle switches between light/dark
   - [ ] Preference persists across reload
   - [ ] System preference respected when set to 'system'
   - [ ] Cards, inputs, buttons themed correctly
   - [ ] Dropdown menu readable in both modes
   - [ ] Mobile toggle visible and functional
4. **Promote to production** via PR staging→main

## Follow-up Issues to Create

1. **Dark palette named tokens (Issue 5):** Define `--color-victorian-evening-*` tokens instead of orphan hex values in `.dark`

---

## CRITICAL REMINDERS FOR NEXT SESSION

### 1. ALWAYS Use Superpowers Skills

**Before ANY task, check if a skill applies:**

| Task Type | Required Skill Chain |
|-----------|---------------------|
| New feature | brainstorming → using-git-worktrees → writing-plans → subagent-driven-development |
| Debugging | systematic-debugging → root-cause-tracing → defense-in-depth |
| Writing tests | test-driven-development → testing-anti-patterns |
| Code review | requesting-code-review → receiving-code-review |
| Completing work | verification-before-completion → finishing-a-development-branch |

**If you think there's even 1% chance a skill applies, READ IT. This is not optional.**

### 2. NEVER Use These (Permission Prompts)

```bash
# BAD - NEVER DO THESE:
# This is a comment before command     ❌ # comments
aws configure \                         ❌ \ continuations
  --profile foo
echo $(date +%s)                        ❌ $(...) substitution
npm test && npm build                   ❌ && chaining
git commit || exit 1                    ❌ || chaining
--password 'Test1234!'                  ❌ ! in strings
```

### 3. ALWAYS Use These (Auto-Approved)

```bash
# GOOD - Simple single-line commands:
npm run build --prefix frontend
git status
aws sts get-caller-identity

# GOOD - Separate Bash tool calls instead of &&:
# Call 1: git add .
# Call 2: git commit -m "message"
# Call 3: git push

# GOOD - Use bmx-api for all API calls:
bmx-api GET /books
bmx-api --prod GET /books/123
bmx-api POST /books '{"title":"..."}'
```

### 4. Git Workflow Reminders

- **NEVER push directly to main** - always PR to staging first
- **Watch deploy workflow** after merge: `gh run watch <id> --exit-status`
- **Use conventional commits:** feat:, fix:, test:, docs:, chore:

---

## Test Results

```text
Test Files: 12 passed
Tests: 107 passed (6 useTheme tests)
```

All TypeScript, lint, and build checks pass.
