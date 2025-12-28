# Session: Form Styling Standardization for Tailwind v4

**Date:** 2025-12-28
**Branch:** fix/tailwind-v4-forms-plugin (merged to staging)
**PR:** #617
**Related Issues:** #5, #166

---

## Background

### The Problem
Tailwind CSS v4 migration introduced conflicting form styling patterns:

| Pattern | Focus Ring | Used By |
|---------|-----------|---------|
| A: Component classes (`.input`, `.select`, `.btn-*`) | Victorian gold | ~60% of forms |
| B: Inline utilities (`focus:ring-blue-500`) | Tailwind blue | ~40% of forms |

The `@tailwindcss/forms` plugin was needed to fix Issue #5 (preflight form reset), but exposed the inconsistency.

### CSS Cascade Resolution
```
1. @layer base (Tailwind preflight) - resets to transparent
2. @layer base (@tailwindcss/forms) - adds sensible defaults with blue focus
3. @layer components (.input, .select) - Victorian styling with gold focus
4. @layer utilities (utility classes)
```

Elements using `.input` class get Victorian gold focus (correct).
Elements using inline utilities get blue focus (incorrect for Victorian design).

---

## What Was Done

### Files Modified (6 components)
- `ComboboxWithAdd.vue` - input, dropdown buttons
- `AddToWatchlistModal.vue` - 5 inputs, 1 select, 3 buttons
- `AddTrackingModal.vue` - 3 inputs, 1 select, 4 buttons (including toggle)
- `EditWatchlistModal.vue` - 7 inputs, 1 select, 1 checkbox, 3 buttons
- `AcquireModal.vue` - 6 inputs, 3 selects, 3 buttons
- `ImportListingModal.vue` - ~10 inputs, 5+ buttons

### Changes Applied
- All `<input>` elements → `class="input"`
- All `<select>` elements → `class="select"`
- All action buttons → `class="btn-primary"` or `class="btn-secondary"`
- Toggle buttons → `bg-victorian-hunter-600` active state
- Checkbox → `text-victorian-hunter-600 focus:ring-victorian-gold-muted`
- Dropdown options → `hover:bg-victorian-paper-aged`

### Commits
1. `16e51f6` - Add @tailwindcss/forms plugin
2. `5e93af1` - Standardize ComboboxWithAdd
3. `335b9d4` - Standardize AddToWatchlistModal
4. `1ed5c91` - Standardize remaining modals
5. `df9fd61` - Fix Prettier formatting

---

## Next Steps

1. **Validate on staging** - https://staging.app.bluemoxon.com
   - Open each modal
   - Tab through form fields
   - Verify Victorian gold focus rings (not blue)

2. **If validation passes** - Create PR from staging → main

3. **If issues found** - Fix on new branch targeting staging

---

## CRITICAL: Superpowers Skills Usage

**MANDATORY:** Check and use Superpowers skills at ALL stages of work.

### Required Workflow Chains
| Task Type | Skill Chain |
|-----------|-------------|
| New feature | brainstorming → using-git-worktrees → writing-plans → subagent-driven-development |
| Debugging | systematic-debugging → root-cause-tracing → defense-in-depth |
| Writing tests | test-driven-development → condition-based-waiting → testing-anti-patterns |
| Code review | requesting-code-review → receiving-code-review |
| Completing work | verification-before-completion → finishing-a-development-branch |
| Executing plans | executing-plans (with TodoWrite for all checklist items) |

### Skills Used This Session
- `superpowers:executing-plans` - Task-by-task plan execution
- `superpowers:finishing-a-development-branch` - Merge workflow

**If a skill applies, you MUST use it. No exceptions.**

---

## CRITICAL: Bash Command Formatting

### NEVER use (triggers permission prompts):
```bash
# Comment lines before commands
command \
  --with-continuations
$(command substitution)
cmd1 || cmd2
cmd1 && cmd2
echo "password with ! character"
```

### ALWAYS use:
```bash
# Simple single-line commands only
command --with-flags value

# Separate sequential Bash tool calls instead of &&
# Call 1:
git add file.vue
# Call 2:
git commit -m "message"

# Use bmx-api for all BlueMoxon API calls
bmx-api GET /books
bmx-api --prod GET /books/123
```

### Why This Matters
Complex shell syntax causes permission prompts that cannot be auto-approved. Each prompt requires manual intervention, creating significant toil. Simple commands are auto-approved.

---

## Files Reference

| Purpose | Location |
|---------|----------|
| Component classes | `frontend/src/assets/main.css` |
| Session logs | `docs/sessions/` |
| Implementation plan | `docs/plans/2025-12-28-form-styling-standardization.md` |
| Tailwind v4 migration notes | `docs/sessions/2025-12-27-tailwind-v4-migration.md` |
