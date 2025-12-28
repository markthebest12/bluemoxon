# Tailwind CSS v4 Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate from Tailwind CSS v3.4.x to v4.x with zero visual regressions.

**Architecture:** Use official upgrade tool for bulk conversion, then manually verify and fix custom Victorian theme. Screenshot comparison validates visual parity.

**Tech Stack:** Tailwind CSS v4, @tailwindcss/vite plugin, Vite 7, Vue 3

---

## Task 1: Capture Baseline Screenshots

**Files:**
- Create: `frontend/.tmp/screenshots/before/` (directory)

**Step 1: Create screenshots directory**

```bash
mkdir -p frontend/.tmp/screenshots/before
```

**Step 2: Start dev server**

```bash
cd frontend && npm run dev
```

Leave running in background.

**Step 3: Capture desktop screenshots (1280x800)**

Using Playwright MCP, navigate to each page and screenshot:

| Page | URL | Filename |
|------|-----|----------|
| Home | http://localhost:5173/ | `home-desktop.png` |
| Books | http://localhost:5173/books | `books-desktop.png` |
| Book Detail | http://localhost:5173/books/1 | `detail-desktop.png` |
| Login | http://localhost:5173/login | `login-desktop.png` |
| Book Create | http://localhost:5173/books/new | `create-desktop.png` |
| Book Edit | http://localhost:5173/books/1/edit | `edit-desktop.png` |

**Step 4: Capture mobile screenshots (390x844)**

Resize viewport and capture same pages with `-mobile.png` suffix.

**Step 5: Stop dev server**

Kill the background dev server process.

**Step 6: Verify screenshots**

```bash
ls -la frontend/.tmp/screenshots/before/
```

Expected: 12 PNG files.

---

## Task 2: Run Tailwind Upgrade Tool

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/postcss.config.js`
- Modify: `frontend/tailwind.config.js`
- Modify: `frontend/src/assets/main.css`

**Step 1: Run the upgrade tool**

```bash
cd frontend && npx @tailwindcss/upgrade@latest
```

This will prompt for confirmation. Accept the changes.

**Step 2: Review what changed**

```bash
git diff --stat
git diff frontend/package.json
git diff frontend/vite.config.ts
```

Document what the tool modified.

**Step 3: Install new dependencies**

```bash
cd frontend && npm install
```

**Step 4: Attempt build**

```bash
cd frontend && npm run build
```

If build fails, note the errors for Task 3.

---

## Task 3: Fix Build Errors (if any)

**Files:**
- Modify: Files identified from build errors

**Step 1: Review build errors**

If Task 2 Step 4 failed, analyze errors:
- Missing dependencies → `npm install <package>`
- Syntax errors in CSS → Fix in `main.css`
- Config issues → Fix in `vite.config.ts`

**Step 2: Fix each error one at a time**

Make minimal fix, run build, repeat.

**Step 3: Verify build succeeds**

```bash
cd frontend && npm run build
```

Expected: Build completes without errors.

---

## Task 4: Verify Victorian Theme Colors

**Files:**
- Modify: `frontend/src/assets/main.css` (if needed)

**Step 1: Check theme conversion**

The upgrade tool should have converted `tailwind.config.js` colors to CSS `@theme` syntax in `main.css`. Verify these colors exist:

```css
@theme {
  /* Moxon palette (10 shades) */
  --color-moxon-50: #f0f5f3;
  --color-moxon-100: #dae8e2;
  /* ... through 900 */

  /* Victorian hunter (5 shades) */
  --color-victorian-hunter-900: #0f2318;
  /* ... */

  /* Victorian gold (4 variants) */
  --color-victorian-gold-light: #d4af37;
  --color-victorian-gold: #c9a227;
  /* ... */

  /* Victorian burgundy (3 variants) */
  --color-victorian-burgundy-light: #8b3a42;
  /* ... */

  /* Victorian paper (4 variants) */
  --color-victorian-paper-white: #fdfcfa;
  /* ... */

  /* Victorian ink (3 variants) */
  --color-victorian-ink-black: #1a1a18;
  /* ... */

  /* Navy (5 shades) */
  --color-navy-900: #0a0f1a;
  /* ... */

  /* Fonts */
  --font-display: "Cormorant Garamond", Georgia, serif;
  --font-sans: "Inter", system-ui, sans-serif;
}
```

**Step 2: Fix any missing colors**

If colors are missing, add them manually to the `@theme` block.

**Step 3: Verify custom components still work**

Check that `@layer components` section with `.btn-primary`, `.card`, etc. is intact.

---

## Task 5: Fix Deprecated Utility Classes

**Files:**
- Modify: Vue components in `frontend/src/`

**Step 1: Search for known deprecated utilities**

```bash
cd frontend && grep -r "break-words" src/
```

If found, replace with `break-word` (v4 syntax).

**Step 2: Search for other potential issues**

```bash
cd frontend && grep -rE "text-opacity-|bg-opacity-" src/
```

These may need conversion to `text-<color>/<opacity>` syntax.

**Step 3: Run build to catch other issues**

```bash
cd frontend && npm run build
```

---

## Task 6: Run Test Suite

**Files:**
- None (verification only)

**Step 1: Run type check**

```bash
cd frontend && npm run type-check
```

Expected: No errors.

**Step 2: Run unit tests**

```bash
cd frontend && npm run test:run
```

Expected: All 84 tests pass.

**Step 3: Run lint**

```bash
cd frontend && npm run lint
```

Expected: No errors (warnings OK).

---

## Task 7: Capture After Screenshots

**Files:**
- Create: `frontend/.tmp/screenshots/after/` (directory)

**Step 1: Create screenshots directory**

```bash
mkdir -p frontend/.tmp/screenshots/after
```

**Step 2: Start dev server**

```bash
cd frontend && npm run dev
```

**Step 3: Capture desktop screenshots (1280x800)**

Same 6 pages as Task 1, save to `after/` directory.

**Step 4: Capture mobile screenshots (390x844)**

Same 6 pages with `-mobile.png` suffix.

**Step 5: Stop dev server**

Kill the background dev server process.

---

## Task 8: Compare Screenshots

**Files:**
- None (verification only)

**Step 1: Visual comparison**

Open before/after screenshots side by side:
- `frontend/.tmp/screenshots/before/home-desktop.png`
- `frontend/.tmp/screenshots/after/home-desktop.png`

Compare all 12 pairs.

**Step 2: Document any differences**

Note any visual regressions:
- Color differences
- Font changes
- Layout shifts
- Missing styles

**Step 3: Fix regressions (if any)**

If differences found, investigate and fix in `main.css` or component files.

---

## Task 9: Clean Up Obsolete Files

**Files:**
- Delete: `frontend/tailwind.config.js` (if still exists)
- Modify: `frontend/postcss.config.js` (simplify if needed)

**Step 1: Check for obsolete config**

```bash
ls frontend/tailwind.config.js 2>/dev/null
```

If exists and empty/unused, delete it.

**Step 2: Simplify postcss.config.js**

With `@tailwindcss/vite`, PostCSS may only need autoprefixer:

```javascript
export default {
  plugins: {
    autoprefixer: {},
  },
};
```

Or remove entirely if Vite handles it.

**Step 3: Verify build still works**

```bash
cd frontend && npm run build
```

---

## Task 10: Final Verification and Commit

**Files:**
- All modified files

**Step 1: Run full validation**

```bash
cd frontend && npm run type-check
cd frontend && npm run test:run
cd frontend && npm run build
```

All must pass.

**Step 2: Review all changes**

```bash
git diff --stat
git diff
```

**Step 3: Stage and commit**

```bash
git add -A
git commit -m "feat: Migrate to Tailwind CSS v4

- Upgrade from Tailwind CSS 3.4.x to 4.x
- Convert tailwind.config.js to CSS @theme syntax
- Switch from PostCSS plugin to @tailwindcss/vite
- Update import syntax to @import 'tailwindcss'
- Preserve all Victorian theme colors and custom components
- All 84 tests passing, visual regression verified

Issue: #166"
```

**Step 4: Push branch**

```bash
git push -u origin feat/tailwind-v4-migration
```

---

## Task 11: Create PR to Staging

**Files:**
- None (GitHub operation)

**Step 1: Create PR**

```bash
gh pr create --base staging --title "feat: Migrate to Tailwind CSS v4" --body "## Summary
- Upgrades Tailwind CSS from 3.4.x to 4.x
- Uses new CSS-first configuration (@theme syntax)
- Switches to @tailwindcss/vite plugin for faster builds
- All Victorian theme colors preserved
- Visual regression tested with before/after screenshots

## Benefits
- 5x faster full builds
- 100x+ faster incremental builds
- 35% smaller package size
- Container queries now built-in
- 3D transform utilities available

## Test Plan
- [x] All 84 unit tests passing
- [x] Build succeeds
- [x] Type check passes
- [x] Visual comparison of 6 pages (desktop + mobile)
- [ ] CI passes
- [ ] Manual review in staging

## Screenshots
Before/after comparisons available in .tmp/screenshots/

Issue: #166"
```

**Step 2: Wait for user to review PR**

STOP here and wait for user approval before merging.

---

## Task 12: Merge to Staging and Validate

**Files:**
- None (GitHub/AWS operation)

**Step 1: Merge PR after approval**

```bash
gh pr merge <pr-number> --squash
```

**Step 2: Watch staging deploy**

```bash
gh run list --workflow "Deploy Staging" --limit 1
gh run watch <run-id> --exit-status
```

**Step 3: Validate staging**

Visit https://staging.app.bluemoxon.com and verify:
- Home page loads correctly
- Victorian styling intact
- Forms render properly
- No console errors related to CSS

---

## Task 13: Create PR to Production

**Files:**
- None (GitHub operation)

**Step 1: Create promotion PR**

```bash
gh pr create --base main --head staging --title "chore: Promote Tailwind v4 migration to production" --body "## Summary
Promotes Tailwind CSS v4 migration from staging to production.

## Validated in Staging
- All pages render correctly
- Victorian theme intact
- No visual regressions
- Performance improved

## Risk
Low - visual-only change, no backend impact.

Issue: #166"
```

**Step 2: Wait for user to review PR**

STOP here and wait for user approval before merging to production.

---

## Completion Checklist

- [ ] Task 1: Baseline screenshots captured (12 files)
- [ ] Task 2: Upgrade tool run
- [ ] Task 3: Build errors fixed
- [ ] Task 4: Victorian theme verified
- [ ] Task 5: Deprecated utilities fixed
- [ ] Task 6: Test suite passing
- [ ] Task 7: After screenshots captured
- [ ] Task 8: Visual comparison done
- [ ] Task 9: Obsolete files cleaned
- [ ] Task 10: Changes committed
- [ ] Task 11: PR to staging created (PAUSE for review)
- [ ] Task 12: Staging validated
- [ ] Task 13: PR to production created (PAUSE for review)
