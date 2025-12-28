# Form Styling Standardization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Standardize all form elements to use component classes, eliminating style conflicts between @tailwindcss/forms plugin and inline utility classes.

**Architecture:** The codebase has two conflicting patterns for form styling. Pattern A uses `.input`/`.select` component classes (Victorian gold focus rings). Pattern B uses inline utility classes (blue focus rings from Tailwind defaults). We'll standardize on Pattern A to ensure consistent Victorian design.

**Tech Stack:** Vue 3, Tailwind CSS v4, @tailwindcss/forms plugin

---

## Background

### The Conflict (Issue #5 Follow-up)

PR #617 adds `@tailwindcss/forms` to fix Issue #5 (preflight form reset). However, the codebase has inconsistent form styling:

| Pattern | Example Files | Focus Ring Color | Used By |
|---------|--------------|------------------|---------|
| A: Component classes | BookForm.vue, BooksView.vue | Victorian gold (`--color-victorian-gold-muted`) | ~60% of forms |
| B: Inline utilities | ComboboxWithAdd.vue, AddToWatchlistModal.vue | Tailwind blue (`focus:ring-blue-500`) | ~40% of forms |

### CSS Cascade Resolution

```
1. @layer base (Tailwind preflight) - resets to transparent
2. @layer base (@tailwindcss/forms) - adds sensible defaults with blue focus
3. @layer components (.input, .select) - Victorian styling with gold focus
4. @layer utilities (utility classes)
```

Elements using `.input` class → Victorian gold focus (correct)
Elements using inline utilities → Blue focus (incorrect for Victorian design)

### Files Needing Updates

| File | Elements | Current Pattern | Change Needed |
|------|----------|-----------------|---------------|
| `ComboboxWithAdd.vue` | input, button | Inline utilities | → .input, button styling |
| `AddToWatchlistModal.vue` | 6 inputs, 1 select, 3 buttons | Inline utilities | → .input, .select, .btn-* |
| `AddTrackingModal.vue` | TBD | Possibly inline | Audit needed |
| `EditWatchlistModal.vue` | TBD | Possibly inline | Audit needed |
| `AcquireModal.vue` | TBD | Possibly inline | Audit needed |
| `ImportListingModal.vue` | TBD | Possibly inline | Audit needed |

---

## Task 1: Audit All Modal Components

**Files:**
- Read: `frontend/src/components/AddTrackingModal.vue`
- Read: `frontend/src/components/EditWatchlistModal.vue`
- Read: `frontend/src/components/AcquireModal.vue`
- Read: `frontend/src/components/ImportListingModal.vue`
- Test: Manual inspection

**Step 1: Read each file and document form elements**

Create a checklist of all `<input>`, `<select>`, `<textarea>`, `<button>` elements and their current classes.

**Step 2: Record findings**

For each file, note:
- Total form elements
- Elements using `.input`/`.select`/`.btn-*` (Pattern A)
- Elements using inline utilities (Pattern B)

**Step 3: Update this plan**

Add specific tasks for each file that needs Pattern B → Pattern A conversion.

---

## Task 2: Update ComboboxWithAdd.vue

**Files:**
- Modify: `frontend/src/components/ComboboxWithAdd.vue`
- Test: `npm run --prefix frontend type-check`

**Step 1: Update input element**

Replace:
```vue
<input
  v-model="searchText"
  type="text"
  :placeholder="placeholder || `Select or add ${label.toLowerCase()}`"
  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
  @focus="handleFocus"
  @blur="handleBlur"
/>
```

With:
```vue
<input
  v-model="searchText"
  type="text"
  :placeholder="placeholder || `Select or add ${label.toLowerCase()}`"
  class="input"
  @focus="handleFocus"
  @blur="handleBlur"
/>
```

**Step 2: Update dropdown option buttons**

Replace:
```vue
<button
  v-for="option in filteredOptions"
  :key="option.id"
  type="button"
  data-testid="option"
  class="w-full px-3 py-2 text-left text-sm hover:bg-gray-100"
  @mousedown.prevent="selectOption(option)"
>
```

With:
```vue
<button
  v-for="option in filteredOptions"
  :key="option.id"
  type="button"
  data-testid="option"
  class="w-full px-3 py-2 text-left text-sm hover:bg-victorian-paper-aged"
  @mousedown.prevent="selectOption(option)"
>
```

**Step 3: Update "Add new" button**

Replace:
```vue
<button
  v-if="showAddNew"
  type="button"
  data-testid="add-new"
  class="w-full px-3 py-2 text-left text-sm text-blue-600 hover:bg-blue-50 border-t border-gray-200"
  @mousedown.prevent="handleAddNew"
>
```

With:
```vue
<button
  v-if="showAddNew"
  type="button"
  data-testid="add-new"
  class="w-full px-3 py-2 text-left text-sm text-victorian-hunter-700 hover:bg-victorian-paper-aged border-t border-victorian-paper-antique"
  @mousedown.prevent="handleAddNew"
>
```

**Step 4: Run type-check**

```bash
npm run --prefix frontend type-check
```

Expected: No errors

**Step 5: Commit**

```bash
git add frontend/src/components/ComboboxWithAdd.vue
git commit -m "fix: Standardize ComboboxWithAdd to use .input component class"
```

---

## Task 3: Update AddToWatchlistModal.vue

**Files:**
- Modify: `frontend/src/components/AddToWatchlistModal.vue`
- Test: `npm run --prefix frontend type-check`

**Step 1: Update Title input (line 212-217)**

Replace inline utilities with `.input`:
```vue
<input
  v-model="form.title"
  type="text"
  class="input"
  :class="{ 'border-red-500': validationErrors.title }"
/>
```

**Step 2: Update Publication Date input (line 254-259)**

Replace inline utilities with `.input`:
```vue
<input
  v-model="form.publication_date"
  type="text"
  placeholder="1867"
  class="input"
/>
```

**Step 3: Update Volumes input (line 267-272)**

Replace inline utilities with `.input`:
```vue
<input
  v-model.number="form.volumes"
  type="number"
  min="1"
  class="input"
/>
```

**Step 4: Update Currency select (line 277-284)**

Replace inline utilities with `.select`:
```vue
<select
  v-model="selectedCurrency"
  class="select w-20"
>
```

**Step 5: Update Price input (line 287-294)**

Replace inline utilities with `.input`:
```vue
<input
  v-model.number="form.purchase_price"
  type="number"
  step="0.01"
  min="0"
  placeholder="Optional"
  class="input pl-7"
/>
```

**Step 6: Update Source URL input (line 310-315)**

Replace inline utilities with `.input`:
```vue
<input
  v-model="form.source_url"
  type="url"
  placeholder="https://ebay.com/itm/..."
  class="input flex-1"
/>
```

**Step 7: Update Open URL button (line 316-323)**

Replace inline utilities with `.btn-secondary`:
```vue
<button
  type="button"
  :disabled="!form.source_url"
  @click="openSourceUrl"
  class="btn-secondary px-3"
  title="Open URL"
>
```

**Step 8: Update Cancel button (line 337-344)**

Replace inline utilities with `.btn-secondary`:
```vue
<button
  type="button"
  @click="handleClose"
  :disabled="submitting"
  class="btn-secondary flex-1"
>
  Cancel
</button>
```

**Step 9: Update Submit button (line 345-351)**

Replace inline utilities with `.btn-primary`:
```vue
<button
  type="submit"
  :disabled="submitting"
  class="btn-primary flex-1"
>
  {{ submitting ? "Adding..." : "Add to List" }}
</button>
```

**Step 10: Run type-check**

```bash
npm run --prefix frontend type-check
```

Expected: No errors

**Step 11: Commit**

```bash
git add frontend/src/components/AddToWatchlistModal.vue
git commit -m "fix: Standardize AddToWatchlistModal to use component classes"
```

---

## Task 4: Audit and Update Remaining Modals

**Files:**
- Modify: `frontend/src/components/AddTrackingModal.vue` (if needed)
- Modify: `frontend/src/components/EditWatchlistModal.vue` (if needed)
- Modify: `frontend/src/components/AcquireModal.vue` (if needed)
- Modify: `frontend/src/components/ImportListingModal.vue` (if needed)
- Test: `npm run --prefix frontend type-check`

**Step 1: Audit each file**

Check each file for inline utility patterns on form elements.

**Step 2: Apply same pattern**

For each form element using inline utilities:
- `<input>` → `class="input"`
- `<select>` → `class="select"`
- `<textarea>` → `class="input"` (same styling)
- `<button>` → `class="btn-primary"`, `class="btn-secondary"`, or `class="btn-danger"`

**Step 3: Run type-check**

```bash
npm run --prefix frontend type-check
```

**Step 4: Commit**

```bash
git add frontend/src/components/*.vue
git commit -m "fix: Standardize remaining modals to use component classes"
```

---

## Task 5: Visual Validation

**Files:**
- Test: Browser inspection

**Step 1: Build and run dev server**

```bash
npm run --prefix frontend dev
```

**Step 2: Test each updated component**

For each updated component:
1. Open the modal/form
2. Tab through form fields
3. Verify focus ring is Victorian gold (not blue)
4. Verify hover states match Victorian design

**Step 3: Compare with production**

Open production site and compare:
- Focus ring colors
- Button styling
- Input/select borders

**Step 4: Document any remaining issues**

If any elements still show blue focus rings or non-Victorian styling, note them for additional fixes.

---

## Task 6: Create PR and Deploy

**Files:**
- None (git operations only)

**Step 1: Push changes**

```bash
git push origin fix/tailwind-v4-forms-plugin
```

Note: This is the same branch as PR #617. The form standardization fixes build on the @tailwindcss/forms plugin addition.

**Step 2: Update PR description**

Add note about form standardization to PR #617 description.

**Step 3: Wait for CI**

```bash
gh pr checks 617 --watch
```

**Step 4: Request review**

PR #617 now includes:
1. @tailwindcss/forms plugin (Issue #5 fix)
2. Form element standardization (this plan)

---

## Success Criteria

1. All form elements use `.input`/`.select`/`.btn-*` component classes
2. No inline utility classes for form styling (especially `focus:ring-blue-*`)
3. Victorian gold focus rings on all inputs
4. Type-check passes
5. Visual validation matches production styling

---

## Rollback Plan

If form standardization causes issues:
1. Revert form standardization commits
2. Keep @tailwindcss/forms plugin (PR #617 core fix)
3. Address inline utilities in separate PR
