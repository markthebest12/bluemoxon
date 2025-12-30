# Session: Cleanup Lambda Implementation (Issues #189, #190, #191)

**Date**: 2025-12-29
**Issues**: #189, #190, #191
**Branch**: `feat/cleanup-lambda`
**PR**: https://github.com/markthebest12/bluemoxon/pull/682

---

## CRITICAL RULES FOR CONTINUATION

### 1. ALWAYS Use Superpowers Skills

**Invoke relevant skills BEFORE any response or action.** Even 1% chance = invoke.

Required skills:
- `superpowers:test-driven-development` - For ALL implementation
- `superpowers:using-superpowers` - At session start
- `superpowers:verification-before-completion` - Before claiming done
- `superpowers:systematic-debugging` - For any bugs/failures

### 2. Bash Command Rules (NEVER VIOLATE)

**NEVER use (trigger permission prompts):**
```bash
# This is a comment - NEVER
command \
  --option  # NEVER - backslash continuation
result=$(command)  # NEVER - command substitution
cmd1 && cmd2  # NEVER - chaining
cmd1 || cmd2  # NEVER - chaining
echo 'Test1234!'  # NEVER - ! in quotes
```

**ALWAYS use:**
```bash
# Simple single-line commands only
command --option value

# Make SEPARATE Bash tool calls for each command
# NOT chained with &&

# For API calls:
bmx-api GET /books
bmx-api --prod GET /books
```

### 3. Workflow Rules
- PRs reviewed before staging merge
- PRs reviewed before prod merge
- TDD for all implementation
- Staging-first workflow

---

## Current Status: P6 IN PROGRESS

### Completed This Session

| Task | Status |
|------|--------|
| P0: Async handler fix | **DONE** - `handler.py` updated |
| P1: S3 pagination | **DONE** - uses paginator |
| P2: Database session | **DONE** - uses `SessionLocal()` |
| P3: Network errors | **DONE** - transient errors not marked expired |
| P4: Alembic chain | **VERIFIED** |
| P5: Batch limits | **DONE** - 25/10 batch sizes |
| Handler tests sync | **DONE** - 28 tests pass |
| P6: Move cleanup panel | **IN PROGRESS** |
| P7: Emoji accessibility | **TODO** |

### Handler Tests Updated

Changed `TestCleanupHandler` class from async to sync:
- Removed `@pytest.mark.asyncio` decorators
- Changed `async def` to `def`
- Removed `await` from handler calls
- Changed mock from `get_db` to `SessionLocal`
- Added `mock_db.close.assert_called_once()` verification

**All 28 tests pass:**
```
tests/test_cleanup.py - 28 passed
```

---

## P6 Progress: Move Cleanup Panel

### What's Done

Added to `AdminConfigView.vue`:
1. Extended tab type to include `"maintenance"`
2. Added cleanup state variables (`cleanupLoading`, `cleanupResult`, `cleanupError`)
3. Added `runCleanup()` function

### What's Left

1. Add "Maintenance" tab button to navigation (after "Costs" tab)
2. Add Maintenance tab content with cleanup UI
3. Remove cleanup panel from `AcquisitionsView.vue` (lines 316-348 state, 1117-1280 template)
4. Fix P7: Add `aria-hidden="true"` to decorative emojis

### Key Files

| File | What to Do |
|------|------------|
| `frontend/src/views/AdminConfigView.vue` | Add tab navigation + content (state already added) |
| `frontend/src/views/AcquisitionsView.vue` | Remove cleanup panel code |

---

## P7: Emoji Accessibility

All decorative emojis need `aria-hidden="true"`:

```html
<!-- Current (bad for screen readers) -->
<span class="text-lg">🧹</span>

<!-- Fixed -->
<span class="text-lg" aria-hidden="true">🧹</span>
```

Emojis to fix in cleanup panel: 🧹 🔄 📦 🔗 🗄️ 🔍 🗑️

---

## NEXT STEPS (In Order)

### 1. Complete P6 - Add Maintenance Tab UI

Add tab button after Costs in AdminConfigView.vue navigation:
```vue
<button
  @click="activeTab = 'maintenance'"
  :class="[/* same pattern as other tabs */]"
>
  Maintenance
</button>
```

Add tab content section with cleanup UI (copy from AcquisitionsView lines 1117-1280, add aria-hidden to emojis).

### 2. Remove Cleanup from AcquisitionsView.vue

Remove:
- Lines 316-329: cleanup state variables
- Lines 331-348: `runCleanup()` function
- Lines 1117-1280: cleanup panel template

### 3. Run Validation

```bash
cd /Users/mark/projects/bluemoxon/frontend
```
```bash
npm run lint
```
```bash
npm run type-check
```
```bash
cd /Users/mark/projects/bluemoxon/backend
```
```bash
poetry run ruff check .
```
```bash
poetry run ruff format --check .
```

### 4. Commit and Push

```bash
git add -A
```
```bash
git commit -m "fix(cleanup): Address code review issues P0-P7"
```
```bash
git push
```

### 5. Watch CI

```bash
gh pr checks 682 --watch
```

---

## Key Files Summary

| File | Status |
|------|--------|
| `backend/lambdas/cleanup/handler.py` | **DONE** - P0-P5 fixes applied |
| `backend/tests/test_cleanup.py` | **DONE** - sync tests, 28 passing |
| `backend/app/api/v1/health.py` | **DONE** - migrations registered |
| `frontend/src/views/AdminConfigView.vue` | **IN PROGRESS** - state added, need tab UI |
| `frontend/src/views/AcquisitionsView.vue` | **TODO** - remove cleanup panel |

---

## Current Todo List

```
1. [completed] Fix P0-P5 in handler.py
2. [completed] Update handler tests to sync pattern
3. [completed] Run tests - 28 passing
4. [in_progress] Fix P6: Add Maintenance tab UI to AdminConfigView
5. [pending] Fix P6: Remove cleanup panel from AcquisitionsView
6. [pending] Fix P7: Add aria-hidden to emojis
7. [pending] Run frontend lint/type-check
8. [pending] Run backend lint
9. [pending] Commit and push
10. [pending] Watch CI
```
