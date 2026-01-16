# Blue to Victorian Comprehensive Sweep

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Eliminate ALL blue Tailwind classes from the codebase, replacing with Victorian design system colors.

**Architecture:** Systematic file-by-file conversion. Group changes by category (buttons, links, inputs, spinners, progress bars) with consistent replacements. Some semantic coloring (status badges) will be converted to Victorian equivalents.

**Tech Stack:** Vue 3, Tailwind CSS v4, Victorian color palette

---

## Replacement Reference

| Blue Pattern | Victorian Replacement |
|--------------|----------------------|
| `bg-blue-600 hover:bg-blue-700` | `btn-primary` (or `bg-victorian-hunter-600 hover:bg-victorian-hunter-700`) |
| `text-blue-600 hover:text-blue-800` | `text-victorian-hunter-600 hover:text-victorian-hunter-700` |
| `focus:ring-blue-500` | `focus:ring-victorian-gold-muted` (or use `.input`/`.select` class) |
| `border-blue-600` (spinners) | `border-victorian-hunter-600` |
| `bg-blue-500` (progress) | `bg-victorian-hunter-500` |
| `bg-blue-100 text-blue-800` (badges) | `bg-victorian-hunter-100 text-victorian-hunter-800` |
| `bg-blue-50` (backgrounds) | `bg-victorian-paper-cream` |
| `border-blue-500` (active tabs) | `border-victorian-hunter-500` |
| `hover:border-blue-300` | `hover:border-victorian-gold-muted` |

---

## Task 1: PasteOrderModal.vue (5 occurrences)

**Files:**

- Modify: `frontend/src/components/PasteOrderModal.vue`

**Step 1: Fix textarea focus ring (line 145)**

Replace:

```
focus:ring-2 focus:ring-blue-500 focus:border-blue-500
```

With:

```
focus:ring-2 focus:ring-victorian-gold-muted focus:border-victorian-gold-muted
```

**Step 2: Fix Parse button (line 159)**

Replace:

```
bg-blue-600 text-white rounded-lg hover:bg-blue-700
```

With:

```
btn-primary
```

**Step 3: Fix "Parsed" badge (line 170)**

Replace:

```
text-blue-600 bg-blue-50
```

With:

```
text-victorian-hunter-600 bg-victorian-paper-cream
```

**Step 4: Fix link (line 383)**

Replace:

```
text-blue-600 hover:text-blue-800
```

With:

```
text-victorian-hunter-600 hover:text-victorian-hunter-700
```

**Step 5: Fix Submit button (line 440)**

Replace:

```
bg-blue-600 text-white rounded-lg hover:bg-blue-700
```

With:

```
btn-primary
```

**Step 6: Run checks**

```bash
npm run --prefix frontend type-check
npm run --prefix frontend lint
```

**Step 7: Commit**

```bash
git add frontend/src/components/PasteOrderModal.vue
git commit -m "fix: Convert PasteOrderModal from blue to Victorian styling"
```

---

## Task 2: EvalRunbookModal.vue (10 occurrences)

**Files:**

- Modify: `frontend/src/components/books/EvalRunbookModal.vue`

**Step 1: Fix loading spinner (line 250)**

Replace:

```
border-b-2 border-blue-600
```

With:

```
border-b-2 border-victorian-hunter-600
```

**Step 2: Fix refreshing container (line 304)**

Replace:

```
bg-blue-50 border border-blue-200
```

With:

```
bg-victorian-paper-cream border border-victorian-paper-antique
```

**Step 3: Fix refreshing spinner (line 307)**

Replace:

```
border-2 border-blue-600 border-t-transparent
```

With:

```
border-2 border-victorian-hunter-600 border-t-transparent
```

**Step 4: Fix refreshing text (lines 310-311)**

Replace:

```
text-blue-800
text-blue-600
```

With:

```
text-victorian-hunter-800
text-victorian-hunter-600
```

**Step 5: Fix progress bar (line 395)**

Replace:

```
bg-blue-500
```

With:

```
bg-victorian-hunter-500
```

**Step 6: Fix link (line 495)**

Replace:

```
text-blue-600 hover:text-blue-700
```

With:

```
text-victorian-hunter-600 hover:text-victorian-hunter-700
```

**Step 7: Fix price input focus (line 772)**

Replace:

```
focus:ring-2 focus:ring-blue-500
```

With:

```
input
```

(Use the component class instead of inline)

**Step 8: Fix notes textarea focus (line 784)**

Replace:

```
focus:ring-2 focus:ring-blue-500
```

With:

```
input
```

**Step 9: Fix bid amount input focus (line 794)**

Replace:

```
focus:ring-2 focus:ring-blue-500
```

With:

```
input
```

**Step 10: Fix Submit button (line 828)**

Replace:

```
bg-blue-600 text-white rounded-lg hover:bg-blue-700
```

With:

```
btn-primary rounded-lg
```

**Step 11: Run checks and commit**

```bash
npm run --prefix frontend type-check
npm run --prefix frontend lint
git add frontend/src/components/books/EvalRunbookModal.vue
git commit -m "fix: Convert EvalRunbookModal from blue to Victorian styling"
```

---

## Task 3: AcquisitionsView.vue (25+ occurrences)

**Files:**

- Modify: `frontend/src/views/AcquisitionsView.vue`

**Step 1: Fix "Add to Watchlist" button (line 354)**

Replace:

```
bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700
```

With:

```
btn-primary text-sm font-medium
```

**Step 2: Fix loading spinner (line 375)**

Replace:

```
border-b-2 border-blue-600
```

With:

```
border-b-2 border-victorian-hunter-600
```

**Step 3: Fix card hover (line 393)**

Replace:

```
hover:border-blue-300
```

With:

```
hover:border-victorian-gold-muted
```

**Step 4: Fix title link hovers (lines 399, 611, 892)**

Replace:

```
hover:text-blue-600
```

With:

```
hover:text-victorian-hunter-600
```

**Step 5: Fix "View Analysis" links (lines 415, 632, 690, 913)**

Replace:

```
text-blue-600 hover:text-blue-800
```

With:

```
text-victorian-hunter-600 hover:text-victorian-hunter-700
```

**Step 6: Fix "Generate Analysis" button (line 437)**

Replace:

```
bg-blue-600 text-white text-xs rounded-sm hover:bg-blue-700
```

With:

```
bg-victorian-hunter-600 text-white text-xs rounded-sm hover:bg-victorian-hunter-700
```

**Step 7: Fix analysis status links (lines 470, 751, 946)**

Replace:

```
text-blue-600
```

With:

```
text-victorian-hunter-600
```

**Step 8: Fix "Generate Analysis" text buttons (lines 499, 780, 975)**

Replace:

```
text-blue-600 hover:text-blue-800
```

With:

```
text-victorian-hunter-600 hover:text-victorian-hunter-700
```

**Step 9: Fix "Regenerate" text buttons (lines 516, 797, 992)**

Replace:

```
text-blue-600 hover:text-blue-800
```

With:

```
text-victorian-hunter-600 hover:text-victorian-hunter-700
```

**Step 10: Fix status dot (line 596)**

Replace:

```
bg-blue-400
```

With:

```
bg-victorian-hunter-400
```

**Step 11: Fix edit button hover (line 664)**

Replace:

```
hover:text-blue-600 hover:bg-blue-50
```

With:

```
hover:text-victorian-hunter-600 hover:bg-victorian-paper-cream
```

**Step 12: Fix "View Runbook" outline button (line 726)**

Replace:

```
border border-blue-600 text-blue-600 hover:bg-blue-50
```

With:

```
border border-victorian-hunter-600 text-victorian-hunter-600 hover:bg-victorian-paper-cream
```

**Step 13: Run checks and commit**

```bash
npm run --prefix frontend type-check
npm run --prefix frontend lint
git add frontend/src/views/AcquisitionsView.vue
git commit -m "fix: Convert AcquisitionsView from blue to Victorian styling"
```

---

## Task 4: AdminConfigView.vue (7 occurrences)

**Files:**

- Modify: `frontend/src/views/AdminConfigView.vue`

**Step 1: Fix active tab borders (lines 224, 235, 246, 257, 271)**

Replace all instances of:

```
border-blue-500 text-blue-600
```

With:

```
border-victorian-hunter-500 text-victorian-hunter-600
```

**Step 2: Fix Save button (line 310)**

Replace:

```
bg-blue-600 text-white rounded-sm hover:bg-blue-700
```

With:

```
btn-primary
```

**Step 3: Fix progress bar (line 777)**

Replace:

```
bg-blue-500
```

With:

```
bg-victorian-hunter-500
```

**Step 4: Run checks and commit**

```bash
npm run --prefix frontend type-check
npm run --prefix frontend lint
git add frontend/src/views/AdminConfigView.vue
git commit -m "fix: Convert AdminConfigView from blue to Victorian styling"
```

---

## Task 5: BookDetailView.vue (5 occurrences)

**Files:**

- Modify: `frontend/src/views/BookDetailView.vue`

**Step 1: Fix status badge function (line 302)**

Replace:

```
return "bg-blue-100 text-blue-800";
```

With:

```
return "bg-victorian-hunter-100 text-victorian-hunter-800";
```

**Step 2: Fix IN_TRANSIT badge (line 508)**

Replace:

```
bg-blue-100 text-blue-800
```

With:

```
bg-victorian-hunter-100 text-victorian-hunter-800
```

**Step 3: Fix analysis card (line 686)**

Replace:

```
bg-blue-50 border-blue-200
```

With:

```
bg-victorian-paper-cream border-victorian-paper-antique
```

**Step 4: Fix Generate Analysis button (line 697)**

Replace:

```
bg-blue-600 text-white rounded-lg hover:bg-blue-700
```

With:

```
btn-primary rounded-lg
```

**Step 5: Fix analysis status link (line 720)**

Replace:

```
text-blue-600
```

With:

```
text-victorian-hunter-600
```

**Step 6: Run checks and commit**

```bash
npm run --prefix frontend type-check
npm run --prefix frontend lint
git add frontend/src/views/BookDetailView.vue
git commit -m "fix: Convert BookDetailView from blue to Victorian styling"
```

---

## Task 6: ImportListingModal.vue (4 occurrences)

**Files:**

- Modify: `frontend/src/components/ImportListingModal.vue`

**Step 1: Fix loading spinner (line 512)**

Replace:

```
border-4 border-blue-600 border-t-transparent
```

With:

```
border-4 border-victorian-hunter-600 border-t-transparent
```

**Step 2: Fix processing spinner (line 754)**

Replace:

```
border-4 border-blue-600 border-t-transparent
```

With:

```
border-4 border-victorian-hunter-600 border-t-transparent
```

**Step 3: Fix small spinner (line 782)**

Replace:

```
border-2 border-blue-600 border-t-transparent
```

With:

```
border-2 border-victorian-hunter-600 border-t-transparent
```

**Step 4: Fix active step text (line 793)**

Replace:

```
text-blue-600 font-medium
```

With:

```
text-victorian-hunter-600 font-medium
```

**Step 5: Run checks and commit**

```bash
npm run --prefix frontend type-check
npm run --prefix frontend lint
git add frontend/src/components/ImportListingModal.vue
git commit -m "fix: Convert ImportListingModal from blue to Victorian styling"
```

---

## Task 7: ScoreCard.vue (4 occurrences)

**Files:**

- Modify: `frontend/src/components/ScoreCard.vue`

**Step 1: Fix progress bar (line 135)**

Replace:

```
bg-blue-500
```

With:

```
bg-victorian-hunter-500
```

**Step 2: Fix links (lines 175, 184)**

Replace:

```
text-blue-600 hover:text-blue-800
```

With:

```
text-victorian-hunter-600 hover:text-victorian-hunter-700
```

**Step 3: Fix header (line 197)**

Replace:

```
text-blue-600
```

With:

```
text-victorian-hunter-600
```

**Step 4: Run checks and commit**

```bash
npm run --prefix frontend type-check
npm run --prefix frontend lint
git add frontend/src/components/ScoreCard.vue
git commit -m "fix: Convert ScoreCard from blue to Victorian styling"
```

---

## Task 8: BookForm.vue (5 occurrences)

**Files:**

- Modify: `frontend/src/components/books/BookForm.vue`

**Step 1: Fix input focus (line 484)**

Replace:

```
focus:ring-2 focus:ring-blue-500 focus:border-blue-500
```

With:

```
focus:ring-2 focus:ring-victorian-gold-muted focus:border-victorian-gold-muted
```

**Step 2: Fix links (lines 510, 533)**

Replace:

```
text-blue-600
```

With:

```
text-victorian-hunter-600
```

**Step 3: Fix IN_TRANSIT status badge (line 657)**

Replace:

```
'bg-blue-100 text-blue-800': match.status === 'IN_TRANSIT'
```

With:

```
'bg-victorian-hunter-100 text-victorian-hunter-800': match.status === 'IN_TRANSIT'
```

**Step 4: Run checks and commit**

```bash
npm run --prefix frontend type-check
npm run --prefix frontend lint
git add frontend/src/components/books/BookForm.vue
git commit -m "fix: Convert BookForm from blue to Victorian styling"
```

---

## Task 9: AdminView.vue (2 occurrences)

**Files:**

- Modify: `frontend/src/views/AdminView.vue`

**Step 1: Fix editor role badge (line 302)**

Replace:

```
'bg-blue-100 text-blue-800': user.role === 'editor'
```

With:

```
'bg-victorian-hunter-100 text-victorian-hunter-800': user.role === 'editor'
```

**Step 2: Fix button (line 352)**

Replace:

```
border border-blue-300 text-blue-700 hover:bg-blue-50
```

With:

```
border border-victorian-hunter-300 text-victorian-hunter-700 hover:bg-victorian-paper-cream
```

**Step 3: Run checks and commit**

```bash
npm run --prefix frontend type-check
npm run --prefix frontend lint
git add frontend/src/views/AdminView.vue
git commit -m "fix: Convert AdminView from blue to Victorian styling"
```

---

## Task 10: ArchiveStatusBadge.vue (1 occurrence)

**Files:**

- Modify: `frontend/src/components/ArchiveStatusBadge.vue`

**Step 1: Fix link (line 89)**

Replace:

```
text-blue-600 hover:text-blue-800
```

With:

```
text-victorian-hunter-600 hover:text-victorian-hunter-700
```

**Step 2: Run checks and commit**

```bash
npm run --prefix frontend type-check
npm run --prefix frontend lint
git add frontend/src/components/ArchiveStatusBadge.vue
git commit -m "fix: Convert ArchiveStatusBadge from blue to Victorian styling"
```

---

## Task 11: LoginView.vue - SKIP (Intentional)

**Decision:** Keep blue for info boxes (lines 189, 273). Blue is the standard UX color for informational messages. This is semantic, not brand-specific.

---

## Task 12: Final Verification

**Step 1: Run comprehensive search**

```bash
cd frontend && grep -r "blue-" src/ --include="*.vue" | grep -v "node_modules"
```

Expected: Only LoginView.vue info boxes remain.

**Step 2: Run full lint and type-check**

```bash
npm run --prefix frontend type-check
npm run --prefix frontend lint
```

**Step 3: Run Prettier**

```bash
npx prettier --write src/
```

**Step 4: Final commit if needed**

```bash
git add -A
git commit -m "style: Fix Prettier formatting after blue-to-Victorian sweep"
```

---

## Task 13: Create PR

**Step 1: Push branch**

```bash
git push -u origin fix/blue-to-victorian-sweep
```

**Step 2: Create PR**

```bash
gh pr create --base staging --title "fix: Comprehensive blue-to-Victorian styling sweep" --body "## Summary
Complete elimination of blue Tailwind classes from the codebase (except LoginView info boxes).

## Scope
- 10 files modified
- 60+ blue class occurrences converted
- Consistent Victorian design system

## Categories Converted
- Primary buttons: bg-blue-600 → btn-primary
- Text links: text-blue-600 → text-victorian-hunter-600
- Input focus: focus:ring-blue-500 → focus:ring-victorian-gold-muted
- Spinners: border-blue-600 → border-victorian-hunter-600
- Progress bars: bg-blue-500 → bg-victorian-hunter-500
- Status badges: bg-blue-100 → bg-victorian-hunter-100
- Tab borders: border-blue-500 → border-victorian-hunter-500

## Files Changed
- PasteOrderModal.vue
- EvalRunbookModal.vue
- AcquisitionsView.vue
- AdminConfigView.vue
- BookDetailView.vue
- ImportListingModal.vue
- ScoreCard.vue
- BookForm.vue
- AdminView.vue
- ArchiveStatusBadge.vue

## Test Plan
- [ ] All modals render correctly
- [ ] Focus rings are Victorian gold
- [ ] Buttons are Victorian green
- [ ] Progress bars are Victorian green
- [ ] No blue styling visible (except login info boxes)

## Related
Closes the Tailwind v4 styling standardization effort (PRs #614-#618)."
```

---

## Success Criteria

1. `grep -r "blue-" src/ --include="*.vue"` returns only LoginView.vue
2. All type-check and lint passes
3. Visual inspection shows consistent Victorian styling
4. No regression in functionality

---

## Rollback Plan

If issues arise:

1. `git revert <commit>` for specific file
2. Or `git reset --hard origin/staging` to abandon all changes
