# Acquisitions Button Visual Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix button layout (left-align, compact) and add Generate/Regenerate buttons to Eval Runbook section across all 3 Acquisitions columns.

**Architecture:** Modify CSS classes on existing buttons to remove stretching/centering, add new handler function for eval runbook generation, replicate button pattern from Analysis to Eval Runbook section.

**Tech Stack:** Vue 3, TypeScript, Tailwind CSS, Pinia store

---

## Task 1: Add Eval Runbook Handler and State

**Files:**
- Modify: `frontend/src/views/AcquisitionsView.vue:205-221` (near handleGenerateAnalysis)
- Modify: `frontend/src/views/AcquisitionsView.vue:317` (near startingAnalysis ref)

**Step 1: Add startingEvalRunbook ref**

After line 317 (`const startingAnalysis = ref<number | null>(null);`), add:

```typescript
const startingEvalRunbook = ref<number | null>(null);
```

**Step 2: Add handleGenerateEvalRunbook function**

After `handleGenerateAnalysis` function (after line 221), add:

```typescript
async function handleGenerateEvalRunbook(bookId: number) {
  if (isEvalRunbookRunning(bookId) || startingEvalRunbook.value === bookId) return;

  startingEvalRunbook.value = bookId;
  try {
    await booksStore.generateEvalRunbookAsync(bookId);
  } catch (err) {
    console.error("Failed to start eval runbook generation:", err);
  } finally {
    startingEvalRunbook.value = null;
  }
}
```

**Step 3: Run lint to verify**

Run: `npm run --prefix frontend lint`
Expected: No errors

**Step 4: Commit**

```bash
git add frontend/src/views/AcquisitionsView.vue
git commit -m "feat(acquisitions): Add eval runbook generation handler (#461)"
```

---

## Task 2: Fix Layout - Evaluating Column Analysis Section

**Files:**
- Modify: `frontend/src/views/AcquisitionsView.vue:461-526`

**Step 1: Update Analysis container div**

Change line 461 from:
```html
<div class="mt-2 flex items-center gap-2">
```

To:
```html
<div class="mt-2 flex items-center justify-start gap-3">
```

**Step 2: Update View Analysis button**

Change line 466 from:
```html
class="flex-1 text-xs text-green-700 hover:text-green-900 flex items-center justify-center gap-1"
```

To:
```html
class="text-xs text-green-700 hover:text-green-900 flex items-center gap-1"
```

**Step 3: Update Analysis progress indicator**

Change line 474 from:
```html
class="flex-1 text-xs text-blue-600 flex items-center justify-center gap-1"
```

To:
```html
class="text-xs text-blue-600 flex items-center gap-1"
```

**Step 4: Update Analysis failed indicator**

Change line 488 from:
```html
class="flex-1 text-xs text-red-600 flex items-center justify-center gap-1"
```

To:
```html
class="text-xs text-red-600 flex items-center gap-1"
```

**Step 5: Update Generate Analysis button**

Change line 503 from:
```html
class="flex-1 text-xs text-blue-600 hover:text-blue-800 flex items-center justify-center gap-1 disabled:opacity-50"
```

To:
```html
class="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1 disabled:opacity-50"
```

**Step 6: Run lint to verify**

Run: `npm run --prefix frontend lint`
Expected: No errors

**Step 7: Commit**

```bash
git add frontend/src/views/AcquisitionsView.vue
git commit -m "style(acquisitions): Left-align Evaluating column analysis buttons (#461)"
```

---

## Task 3: Fix Layout & Add Buttons - Evaluating Column Eval Runbook Section

**Files:**
- Modify: `frontend/src/views/AcquisitionsView.vue:528-558`

**Step 1: Update Eval Runbook container div**

Change line 529 from:
```html
<div class="mt-1 flex items-center gap-2">
```

To:
```html
<div class="mt-1 flex items-center justify-start gap-3">
```

**Step 2: Update View Eval Runbook button**

Change line 538 from:
```html
class="flex-1 text-xs text-purple-700 hover:text-purple-900 flex items-center justify-center gap-1"
```

To:
```html
class="text-xs text-purple-700 hover:text-purple-900 flex items-center gap-1"
```

**Step 3: Update Eval Runbook progress indicator**

Change line 546 from:
```html
class="flex-1 text-xs text-purple-600 flex items-center justify-center gap-1"
```

To:
```html
class="text-xs text-purple-600 flex items-center gap-1"
```

**Step 4: Add Generate Eval Runbook button**

After line 557 (before closing `</div>`), add:

```html
                <!-- Generate Eval Runbook button (admin only, when no runbook exists and not running) -->
                <button
                  v-if="
                    !book.has_eval_runbook &&
                    authStore.isAdmin &&
                    !isEvalRunbookRunning(book.id) &&
                    !book.eval_runbook_job_status
                  "
                  @click="handleGenerateEvalRunbook(book.id)"
                  :disabled="startingEvalRunbook === book.id"
                  class="text-xs text-purple-600 hover:text-purple-800 flex items-center gap-1 disabled:opacity-50"
                  title="Generate eval runbook"
                >
                  <span v-if="startingEvalRunbook === book.id" class="animate-spin">⏳</span>
                  <span v-else>⚡</span>
                  {{ startingEvalRunbook === book.id ? "Starting..." : "Generate Runbook" }}
                </button>
                <!-- Regenerate Eval Runbook button (admin only, when runbook exists and not running) -->
                <button
                  v-if="
                    book.has_eval_runbook &&
                    authStore.isAdmin &&
                    !isEvalRunbookRunning(book.id) &&
                    !book.eval_runbook_job_status
                  "
                  @click="handleGenerateEvalRunbook(book.id)"
                  :disabled="startingEvalRunbook === book.id"
                  class="text-xs text-purple-600 hover:text-purple-800 disabled:opacity-50"
                  title="Regenerate eval runbook"
                >
                  <span v-if="startingEvalRunbook === book.id" class="animate-spin">⏳</span>
                  <span v-else>🔄</span>
                </button>
```

**Step 5: Run lint to verify**

Run: `npm run --prefix frontend lint`
Expected: No errors

**Step 6: Commit**

```bash
git add frontend/src/views/AcquisitionsView.vue
git commit -m "feat(acquisitions): Add eval runbook buttons to Evaluating column (#461)"
```

---

## Task 4: Fix Layout - In Transit Column Analysis Section

**Files:**
- Modify: `frontend/src/views/AcquisitionsView.vue:708-774`

**Step 1: Update Analysis container div**

Change line 709 from:
```html
<div class="mt-2 flex items-center gap-2">
```

To:
```html
<div class="mt-2 flex items-center justify-start gap-3">
```

**Step 2: Update View Analysis button**

Change line 714 from:
```html
class="flex-1 text-xs text-green-700 hover:text-green-900 flex items-center justify-center gap-1"
```

To:
```html
class="text-xs text-green-700 hover:text-green-900 flex items-center gap-1"
```

**Step 3: Update Analysis progress indicator**

Change line 722 from:
```html
class="flex-1 text-xs text-blue-600 flex items-center justify-center gap-1"
```

To:
```html
class="text-xs text-blue-600 flex items-center gap-1"
```

**Step 4: Update Analysis failed indicator**

Change line 736 from:
```html
class="flex-1 text-xs text-red-600 flex items-center justify-center gap-1"
```

To:
```html
class="text-xs text-red-600 flex items-center gap-1"
```

**Step 5: Update Generate Analysis button**

Change line 751 from:
```html
class="flex-1 text-xs text-blue-600 hover:text-blue-800 flex items-center justify-center gap-1 disabled:opacity-50"
```

To:
```html
class="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1 disabled:opacity-50"
```

**Step 6: Run lint to verify**

Run: `npm run --prefix frontend lint`
Expected: No errors

**Step 7: Commit**

```bash
git add frontend/src/views/AcquisitionsView.vue
git commit -m "style(acquisitions): Left-align In Transit column analysis buttons (#461)"
```

---

## Task 5: Add Eval Runbook Section - In Transit Column

**Files:**
- Modify: `frontend/src/views/AcquisitionsView.vue` (after line 774)

**Step 1: Add Eval Runbook section**

After line 774 (after Analysis section closing `</div>`), add:

```html

              <!-- Eval Runbook Section -->
              <div class="mt-1 flex items-center justify-start gap-3">
                <!-- View Eval Runbook link -->
                <button
                  v-if="
                    book.has_eval_runbook &&
                    !isEvalRunbookRunning(book.id) &&
                    !book.eval_runbook_job_status
                  "
                  @click="openEvalRunbook(book)"
                  class="text-xs text-purple-700 hover:text-purple-900 flex items-center gap-1"
                  title="View eval runbook"
                >
                  📋 Eval Runbook
                </button>
                <!-- Eval runbook job in progress indicator -->
                <div
                  v-if="isEvalRunbookRunning(book.id) || book.eval_runbook_job_status"
                  class="text-xs text-purple-600 flex items-center gap-1"
                >
                  <span class="animate-spin">⏳</span>
                  <span>
                    {{
                      (getEvalRunbookJobStatus(book.id)?.status || book.eval_runbook_job_status) ===
                      "pending"
                        ? "Queued..."
                        : "Generating runbook..."
                    }}
                  </span>
                </div>
                <!-- Generate Eval Runbook button (admin only) -->
                <button
                  v-if="
                    !book.has_eval_runbook &&
                    authStore.isAdmin &&
                    !isEvalRunbookRunning(book.id) &&
                    !book.eval_runbook_job_status
                  "
                  @click="handleGenerateEvalRunbook(book.id)"
                  :disabled="startingEvalRunbook === book.id"
                  class="text-xs text-purple-600 hover:text-purple-800 flex items-center gap-1 disabled:opacity-50"
                  title="Generate eval runbook"
                >
                  <span v-if="startingEvalRunbook === book.id" class="animate-spin">⏳</span>
                  <span v-else>⚡</span>
                  {{ startingEvalRunbook === book.id ? "Starting..." : "Generate Runbook" }}
                </button>
                <!-- Regenerate Eval Runbook button (admin only) -->
                <button
                  v-if="
                    book.has_eval_runbook &&
                    authStore.isAdmin &&
                    !isEvalRunbookRunning(book.id) &&
                    !book.eval_runbook_job_status
                  "
                  @click="handleGenerateEvalRunbook(book.id)"
                  :disabled="startingEvalRunbook === book.id"
                  class="text-xs text-purple-600 hover:text-purple-800 disabled:opacity-50"
                  title="Regenerate eval runbook"
                >
                  <span v-if="startingEvalRunbook === book.id" class="animate-spin">⏳</span>
                  <span v-else>🔄</span>
                </button>
              </div>
```

**Step 2: Run lint to verify**

Run: `npm run --prefix frontend lint`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/views/AcquisitionsView.vue
git commit -m "feat(acquisitions): Add eval runbook section to In Transit column (#461)"
```

---

## Task 6: Fix Layout - Received Column Analysis Section

**Files:**
- Modify: `frontend/src/views/AcquisitionsView.vue:838-904`

**Step 1: Update Analysis container div**

Change line 839 from:
```html
<div class="mt-2 flex items-center gap-2">
```

To:
```html
<div class="mt-2 flex items-center justify-start gap-3">
```

**Step 2: Update View Analysis button**

Change line 844 from:
```html
class="flex-1 text-xs text-green-700 hover:text-green-900 flex items-center justify-center gap-1"
```

To:
```html
class="text-xs text-green-700 hover:text-green-900 flex items-center gap-1"
```

**Step 3: Update Analysis progress indicator**

Change line 852 from:
```html
class="flex-1 text-xs text-blue-600 flex items-center justify-center gap-1"
```

To:
```html
class="text-xs text-blue-600 flex items-center gap-1"
```

**Step 4: Update Analysis failed indicator**

Change line 866 from:
```html
class="flex-1 text-xs text-red-600 flex items-center justify-center gap-1"
```

To:
```html
class="text-xs text-red-600 flex items-center gap-1"
```

**Step 5: Update Generate Analysis button**

Change line 881 from:
```html
class="flex-1 text-xs text-blue-600 hover:text-blue-800 flex items-center justify-center gap-1 disabled:opacity-50"
```

To:
```html
class="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1 disabled:opacity-50"
```

**Step 6: Run lint to verify**

Run: `npm run --prefix frontend lint`
Expected: No errors

**Step 7: Commit**

```bash
git add frontend/src/views/AcquisitionsView.vue
git commit -m "style(acquisitions): Left-align Received column analysis buttons (#461)"
```

---

## Task 7: Add Eval Runbook Section - Received Column

**Files:**
- Modify: `frontend/src/views/AcquisitionsView.vue` (after Analysis section ~line 904)

**Step 1: Add Eval Runbook section**

After the Analysis section closing `</div>` in Received column, add:

```html

              <!-- Eval Runbook Section -->
              <div class="mt-1 flex items-center justify-start gap-3">
                <!-- View Eval Runbook link -->
                <button
                  v-if="
                    book.has_eval_runbook &&
                    !isEvalRunbookRunning(book.id) &&
                    !book.eval_runbook_job_status
                  "
                  @click="openEvalRunbook(book)"
                  class="text-xs text-purple-700 hover:text-purple-900 flex items-center gap-1"
                  title="View eval runbook"
                >
                  📋 Eval Runbook
                </button>
                <!-- Eval runbook job in progress indicator -->
                <div
                  v-if="isEvalRunbookRunning(book.id) || book.eval_runbook_job_status"
                  class="text-xs text-purple-600 flex items-center gap-1"
                >
                  <span class="animate-spin">⏳</span>
                  <span>
                    {{
                      (getEvalRunbookJobStatus(book.id)?.status || book.eval_runbook_job_status) ===
                      "pending"
                        ? "Queued..."
                        : "Generating runbook..."
                    }}
                  </span>
                </div>
                <!-- Generate Eval Runbook button (admin only) -->
                <button
                  v-if="
                    !book.has_eval_runbook &&
                    authStore.isAdmin &&
                    !isEvalRunbookRunning(book.id) &&
                    !book.eval_runbook_job_status
                  "
                  @click="handleGenerateEvalRunbook(book.id)"
                  :disabled="startingEvalRunbook === book.id"
                  class="text-xs text-purple-600 hover:text-purple-800 flex items-center gap-1 disabled:opacity-50"
                  title="Generate eval runbook"
                >
                  <span v-if="startingEvalRunbook === book.id" class="animate-spin">⏳</span>
                  <span v-else>⚡</span>
                  {{ startingEvalRunbook === book.id ? "Starting..." : "Generate Runbook" }}
                </button>
                <!-- Regenerate Eval Runbook button (admin only) -->
                <button
                  v-if="
                    book.has_eval_runbook &&
                    authStore.isAdmin &&
                    !isEvalRunbookRunning(book.id) &&
                    !book.eval_runbook_job_status
                  "
                  @click="handleGenerateEvalRunbook(book.id)"
                  :disabled="startingEvalRunbook === book.id"
                  class="text-xs text-purple-600 hover:text-purple-800 disabled:opacity-50"
                  title="Regenerate eval runbook"
                >
                  <span v-if="startingEvalRunbook === book.id" class="animate-spin">⏳</span>
                  <span v-else>🔄</span>
                </button>
              </div>
```

**Step 2: Run lint to verify**

Run: `npm run --prefix frontend lint`
Expected: No errors

**Step 3: Commit**

```bash
git add frontend/src/views/AcquisitionsView.vue
git commit -m "feat(acquisitions): Add eval runbook section to Received column (#461)"
```

---

## Task 8: Run Type Check and Verify

**Step 1: Run type check**

Run: `npm run --prefix frontend type-check`
Expected: No errors

**Step 2: Run full lint**

Run: `npm run --prefix frontend lint`
Expected: No errors

**Step 3: Run Prettier**

Run: `npm run --prefix frontend lint -- --fix`
Expected: Files formatted

**Step 4: Commit any formatting fixes**

```bash
git add frontend/src/views/AcquisitionsView.vue
git commit -m "style: Format AcquisitionsView.vue (#461)"
```

---

## Task 9: Manual Testing Checklist

**Step 1: Start dev server**

Run: `npm run --prefix frontend dev`

**Step 2: Navigate to Acquisitions view**

Open: `http://localhost:5173/acquisitions`

**Step 3: Verify Evaluating column**

- [ ] Analysis buttons are left-aligned (not centered/spread)
- [ ] View Analysis button shows for books with analysis
- [ ] Regenerate (🔄) button shows next to View Analysis (admin only)
- [ ] Generate Analysis button shows for books without analysis (admin only)
- [ ] Eval Runbook View button shows for books with runbook
- [ ] Eval Runbook Regenerate (🔄) button shows next to View (admin only)
- [ ] Eval Runbook Generate button shows for books without runbook (admin only)

**Step 4: Verify In Transit column**

- [ ] Same checks as Evaluating column

**Step 5: Verify Received column**

- [ ] Same checks as Evaluating column

**Step 6: Test generation**

- [ ] Click Generate/Regenerate Analysis - shows loading spinner, then completes
- [ ] Click Generate/Regenerate Eval Runbook - shows loading spinner, then completes

---

## Task 10: Push to Staging and Create PR

**Step 1: Push branch**

```bash
git push -u origin feat/acquisitions-button-cleanup
```

**Step 2: Create PR**

```bash
gh pr create --base staging --title "feat(acquisitions): Button visual cleanup and eval runbook buttons (#461)" --body "$(cat <<'EOF'
## Summary
- Left-align analysis and eval runbook buttons (remove flex-1/justify-center)
- Add Generate/Regenerate buttons to Eval Runbook section (admin only)
- Apply changes to all 3 columns: Evaluating, In Transit, Received

## Test Plan
- [ ] Buttons are left-aligned and compact
- [ ] Generate/Regenerate visible to admin only
- [ ] Click Generate triggers job and shows progress
- [ ] CI passes

Closes #461

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**Step 3: Watch CI**

```bash
gh pr checks --watch
```

**Step 4: Merge when CI passes**

```bash
gh pr merge --squash --delete-branch
```
