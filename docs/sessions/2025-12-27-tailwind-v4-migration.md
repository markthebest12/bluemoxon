# Tailwind CSS v4 Migration Session Log

**Issue:** #166
**Date:** 2025-12-27 to 2025-12-28
**Plan:** `docs/plans/2025-12-27-tailwind-v4-migration.md`

---

## Postmortem: Why Border Radius Took 3 PRs to Fix

### Timeline

| PR | What Was Done | Result |
|----|---------------|--------|
| #609 | Initial migration - kept `rounded-xs` | Class existed but **generated no CSS** (silent failure) |
| #613 | Changed `rounded-xs` → `rounded-sm` | **WRONG** - doubled radius from 2px to 4px |
| #614 | Added `--radius-xs` to @theme, reverted to `rounded-xs` | **CORRECT** fix |

### Root Cause: Silent CSS Generation Failure

In Tailwind v4, utility classes only generate CSS if their underlying CSS variables are defined. The `rounded-xs` class requires:

```css
@theme {
  --radius-xs: 0.125rem;  /* Without this, rounded-xs generates NOTHING */
}
```

**The failure was silent** - no build errors, no warnings, no visible indication that `rounded-xs` wasn't working. The class was in the HTML, but the CSS rule was never generated.

### Why PR #613 Was Wrong

When investigating why `rounded-xs` wasn't working, I made a critical error:

1. **Observed:** `rounded-xs` class exists in HTML but no 2px radius visible
2. **Incorrect diagnosis:** "Tailwind v4 renamed `rounded-xs` to `rounded-sm`"
3. **Incorrect fix:** Replace all `rounded-xs` with `rounded-sm`
4. **Actual result:** Changed 2px radius to 4px radius (doubled it)

**The correct diagnosis should have been:** Tailwind v4 requires explicit `--radius-xs` definition in @theme for custom radius values.

### Contributing Factors

1. **No lint/build errors** - Tailwind v4 silently ignores undefined utilities
2. **Insufficient investigation** - Didn't check Tailwind v4 docs for custom radius tokens
3. **Confirmation bias** - Saw `rounded-sm` working, assumed it was the "new name" for `rounded-xs`
4. **Inadequate visual testing** - Didn't notice the doubled radius before merging

### Lessons Learned

1. **When a utility doesn't work in Tailwind v4, check if it needs a @theme definition first**
2. **Tailwind v4 silent failures are dangerous** - classes can exist but generate no CSS
3. **Visual regression testing must include dimensional checks** - not just "does it look similar"
4. **Don't assume renames** - check the actual Tailwind v4 default scale values

### Correct Fix (PR #614)

```css
@theme {
  /* Tailwind v4 default scale doesn't include xs - must define explicitly */
  --radius-xs: 0.125rem;  /* 2px - matches original Tailwind v3 behavior */
}
```

Then keep using `rounded-xs` (don't change to `rounded-sm`).

### Process Improvements Needed

1. **Before changing any utility class:** Check Tailwind v4 docs for that specific utility
2. **For any "deprecated" class:** Verify the actual CSS values, not just the class names
3. **User review before staging merge:** Don't auto-merge PRs without user approval

---

## Current Status (2025-12-28 ~15:30 UTC)

**Staging:** PR #614 deploying (run 20555611770) - correct fix with `--radius-xs` in @theme
**Production:** BLOCKED - awaiting user validation of staging

### What's Deployed
- PR #614 adds `--radius-xs: 0.125rem` to @theme block
- Reverts all `rounded-sm` back to `rounded-xs`
- This is the CORRECT fix (preserves 2px radius)

### Next Steps When Resuming

1. **Check deploy completed:**
   ```bash
   gh run view 20555611770 --json status,conclusion
   ```

2. **User validates staging:** https://staging.app.bluemoxon.com
   - Check buttons, cards, inputs have subtle 2px radius (not chunky 4px)
   - Run through test cases from issue #166

3. **If validation passes:** Create PR staging → main for production promotion

4. **If issues found:** Create new fix PR, wait for user review before merging

### CRITICAL ISSUES

#### 1. PR #613 `rounded-xs → rounded-sm` Fix Was WRONG

The fix incorrectly replaced `rounded-xs` with `rounded-sm`, which DOUBLES the border radius:

| Class | Tailwind v4 Value |
|-------|-------------------|
| `rounded-xs` | 2px (0.125rem) - **This is what we want** |
| `rounded-sm` | 4px (0.25rem) - **WRONG - too large** |

**Root Cause:** `rounded-xs` wasn't generating CSS because it doesn't exist in Tailwind v4's default scale.

**Correct Fix:** Add custom radius to `@theme` block in `main.css`:
```css
@theme {
  --radius-xs: 0.125rem;  /* 2px - preserves original styling */
}
```

#### 2. PR #609 "NO REGRESSIONS" Claim Was False

PR #609 stated visual regression testing found "NO REGRESSIONS", but user testing revealed:
- A1: Hamburger menu broken
- A2: Compressed tab links
- B1-B3: Dashboard layout/font/spacing issues
- C1-C5: Books page issues (search bar, badges, modals)

**Lesson:** Automated screenshot comparison was inadequate. Manual user testing is required.

#### 3. Changes Not Visible on Staging

After PR #613 merge, user reported "no changes whatsoever" on staging v2025.12.28-4e093da.

**Possible causes to investigate:**
- CloudFront cache not invalidated properly
- CSS not being regenerated correctly
- Classes still not generating due to missing @theme definitions

### Next Steps to Resume

1. **Revert PR #613** or create new fix PR
2. **Add proper @theme definitions:**
   ```css
   @theme {
     --radius-xs: 0.125rem;
   }
   ```
3. **Keep `rounded-xs` class** (don't change to rounded-sm)
4. **Investigate other missing utilities** - check if gradients, outline, etc. need @theme additions
5. **Manual user testing required** before any production promotion

---

## MANDATORY: Skill and Command Requirements

### 1. ALWAYS Use Superpowers Skills (NON-NEGOTIABLE)

**Before ANY task, you MUST:**
1. Check if a Superpowers skill applies
2. Use the Skill tool to invoke it
3. Announce: "I'm using the [skill-name] skill to [what you're doing]"

**Key skills for this work:**
| Skill | When to Use |
|-------|-------------|
| `superpowers:executing-plans` | Implementing any plan |
| `superpowers:systematic-debugging` | Investigating ANY issue |
| `superpowers:verification-before-completion` | Before claiming ANYTHING works |
| `superpowers:requesting-code-review` | After completing significant code |

**FAILURE TO USE SKILLS = FAILURE AT TASK**

### 2. NEVER Use These Bash Patterns (Trigger Permission Prompts)

| Pattern | Example | Why It Fails |
|---------|---------|--------------|
| `#` comments | `# Check status` then `git status` | Comment triggers prompt |
| `\` continuations | `curl -s \ -X GET` | Multi-line triggers prompt |
| `$(...)` substitution | `echo $(date)` | Subshell triggers prompt |
| `||` or `&&` chaining | `git add . && git commit` | Chaining triggers prompt |
| `!` in strings | `--password 'Test1234!'` | History expansion corrupts |

### 3. ALWAYS Use These Patterns

| Pattern | Example |
|---------|---------|
| Simple single-line | `git status` |
| Separate Bash calls | Call 1: `git add .` then Call 2: `git commit -m "msg"` |
| bmx-api for API | `bmx-api GET /books` (no permission prompts) |

**Correct Examples:**
```bash
git status
git add .
git commit -m "fix: something"
curl -s https://example.com
bmx-api GET /health/deep
```

**WRONG - Never do this:**
```bash
# This comment triggers a prompt
git add . && git commit -m "fix: something"
curl -s $(echo "url")
aws logs --start-time $(date +%s000)
```

### 4. ALWAYS Wait for User Review Before Merging PRs

**Process:**
1. Create PR
2. Watch CI pass
3. **STOP - Ask user to review**
4. Only merge after user approval

**Do NOT auto-merge PRs without explicit user approval.**

---

## PRs in This Migration

| PR | Title | Status | Notes |
|----|-------|--------|-------|
| #609 | feat: Upgrade to Tailwind CSS v4 | ✅ Merged | Initial migration - had hidden bugs |
| #611 | chore: Promote staging to production | ❌ Blocked | Has merge conflicts, staging broken |
| #612 | fix: Navbar logo height | ✅ Merged | Added !h-14 for logo |
| #613 | fix: Tailwind v4 deprecated classes | ⚠️ WRONG | rounded-xs→rounded-sm DOUBLES radius |
| #614 | fix: Add --radius-xs to @theme | ✅ Merged | CORRECT fix - adds @theme variable, reverts to rounded-xs |

---

## Background: What Was Done (For Context)

### PR #609 Changes (Initial Migration)
- Tailwind CSS upgraded from v3.4.x to v4.1.18
- PostCSS plugin migrated to @tailwindcss/postcss
- tailwind.config.js converted to CSS @theme block
- @reference directive added for Vue scoped styles
- autoprefixer removed (built into v4)

### PR #612 Fix (Navbar Logo)
- Changed `h-14` to `!h-14` for navbar logo
- Fixed CSS cascade layer conflict where base layer reset was overriding utility

### PR #613 Fix (INCORRECT - Needs Revert)
- Changed `rounded-xs` → `rounded-sm` (WRONG - doubles radius)
- Changed `bg-linear-to-bl` → `bg-gradient-to-bl` (may be correct)
- Changed `focus:outline-hidden` → `focus:outline-none` (may be correct)

---

## Watermark Bug - Root Cause Analysis

### Symptoms
Giant "BLUE MOXON" logo (959x642px) appeared as watermark over entire dashboard content on staging after Tailwind v4 migration.

### Root Cause
**CSS Cascade Layers conflict in Tailwind v4:**

1. Tailwind v4 uses CSS `@layer` for organizing styles
2. Base layer reset includes: `img, video { height: auto; }`
3. Utility layer has: `.h-14 { height: calc(var(--spacing)*14); }`
4. Despite utilities layer having higher cascade priority, the base rule was winning

**The specific issue:** NavBar.vue line 48 had:
```html
<img src="/bluemoxon-classic-logo.png" alt="BlueMoxon" class="h-14 w-auto" />
```

The `h-14` class wasn't being applied to images due to the cascade layer conflict.

### Fix Applied
Changed to use Tailwind v4's `!` important modifier:
```html
<img src="/bluemoxon-classic-logo.png" alt="BlueMoxon" class="!h-14 w-auto" />
```

This generates: `.!h-14{height:calc(var(--spacing)*14)!important}`

**File:** `frontend/src/components/layout/NavBar.vue:48`
**Commit:** `da6b63e`

---

## Progress Summary

### Completed Tasks (1-12)

| Task | Status | Notes |
|------|--------|-------|
| 1. Capture Baseline Screenshots | ✅ | 12 screenshots from staging |
| 2. Run Tailwind Upgrade Tool | ✅ | `npx @tailwindcss/upgrade@latest` successful |
| 3. Fix Build Errors | ✅ | Added `@reference` directive to AnalysisViewer.vue |
| 4. Verify Victorian Theme Colors | ✅ | All colors in `@theme` block |
| 5. Fix Deprecated Utility Classes | ✅ | Fixed `blur` → `blur-sm` event handler bug |
| 6. Run Test Suite | ✅ | 84/84 tests passing, lint clean |
| 7. Capture After Screenshots | ✅ | 12 screenshots from local dev |
| 8. Compare Screenshots | ✅ | NO visual regressions detected |
| 9. Clean Up Obsolete Files | ✅ | `tailwind.config.js` deleted |
| 10. Final Verification and Commit | ✅ | Committed as `103776e` |
| 11. Create PR to Staging | ✅ | PR #609 merged |
| 12. Validate Staging Deployment | ⚠️ | Deployed but watermark bug found |

### Current Task (13) - In Progress

**Task 13: Promote to Production** - BLOCKED

Substeps:
1. ✅ Identify watermark bug root cause (CSS cascade layers)
2. ✅ Create fix (PR #612)
3. ⏳ Wait for CI on PR #612
4. ⏳ Merge PR #612 to staging
5. ⏳ Validate fix on staging
6. ⏳ Resolve merge conflicts on PR #611 (staging → main)
7. ⏳ Merge to production
8. ⏳ Validate production deployment

---

## Next Steps to Resume

1. **Check PR #612 CI status:**
   ```bash
   gh pr checks 612
   ```

2. **If CI passed, merge to staging:**
   ```bash
   gh pr merge 612 --squash --delete-branch
   ```

3. **Wait for staging deploy (2-3 min) then validate:**
   ```bash
   bmx-api GET /health/deep
   ```
   Then navigate to https://staging.app.bluemoxon.com and verify navbar logo is 56px height.

4. **Close or update PR #611** - may need to recreate after staging fix is merged

5. **Create new PR staging → main** after validation

6. **Merge to production and validate**

7. **Close issue #166**

---

## Key Technical Changes Made

### 1. Dependencies (`package.json`)
- `tailwindcss`: `^3.4.0` → `^4.1.18`
- Added: `@tailwindcss/postcss: ^4.1.18`
- Removed: `autoprefixer`

### 2. PostCSS Config (`postcss.config.js`)
```javascript
// Before
{ tailwindcss: {}, autoprefixer: {} }
// After
{ '@tailwindcss/postcss': {} }
```

### 3. CSS (`main.css`)
- Changed `@tailwind base/components/utilities` to `@import 'tailwindcss'`
- All custom colors now in `@theme { }` block
- Custom utilities now use `@utility` directive (e.g., `@utility btn-primary`)

### 4. Vue Scoped Styles (`AnalysisViewer.vue`)
Added `@reference` directive for scoped styles using `@apply`:
```css
<style scoped>
@reference "../../assets/main.css";
/* ... existing styles ... */
</style>
```

### 5. Test Fix (`ComboboxWithAdd.spec.ts`)
Upgrade tool incorrectly converted DOM `blur` events to `blur-sm`. Reverted:
- `await input.trigger("blur-sm")` → `await input.trigger("blur")`

### 6. NavBar Logo Fix (`NavBar.vue`)
Added `!important` modifier to override base layer reset:
- `class="h-14 w-auto"` → `class="!h-14 w-auto"`

---

## Related PRs

| PR | Title | Status |
|----|-------|--------|
| #609 | feat: Upgrade to Tailwind CSS v4 (#166) | ✅ Merged to staging |
| #611 | chore: Promote staging to production | ⏳ Blocked - needs staging fix first |
| #612 | fix: Navbar logo height override for Tailwind v4 | ⏳ CI running |

---

## Worktree Location

All work is in git worktree:
```
/Users/mark/projects/bluemoxon/.worktrees/tailwind-v4/
```

Current branch: `fix/tailwind-v4-navbar-height`

---

## Visual Bug Analysis (2025-12-28)

### Bug Categories from Issue #166

**A. NavBar Issues:**
| ID | Issue | Severity |
|----|-------|----------|
| A1 | Menu broken - missing hamburger on mobile, menu items missing | HIGH |
| A2 | Compressed tab links | MEDIUM |

**B. Dashboard Issues:**
| ID | Issue | Severity |
|----|-------|----------|
| B1 | Left-justified instead of centered | HIGH |
| B2 | Fonts wrong (not rendering Cormorant Garamond) | HIGH |
| B3 | Browse collection/premium bindings links not properly spaced | MEDIUM |

**C. /books AND Book View Issues:**
| ID | Issue | Severity |
|----|-------|----------|
| C1 | Compressed search bar/add button, colors missing | HIGH |
| C2 | Left-justified instead of centered | HIGH |
| C3 | Fonts wrong | HIGH |
| C4 | Tagged items boxes compressed (binder, multi-volume, analysis) | MEDIUM |
| C5 | Modals broken | HIGH |

---

## File Modification Plan

### Root Causes Identified

| Cause | Tailwind v3 Syntax | Tailwind v4 Syntax | Affected Files |
|-------|-------------------|-------------------|----------------|
| Border radius removed | `rounded-xs` | `rounded-sm` | main.css (9), BookThumbnail.vue (2) |
| Gradient syntax changed | `bg-linear-to-bl` | `bg-gradient-to-bl` | HomeView.vue (4) |
| Outline keyword changed | `focus:outline-hidden` | `focus:outline-none` | main.css (2), AnalysisViewer.vue (1), NavBar.vue (1) |
| CSS cascade layers | `h-14` on images | `!h-14` (important) | NavBar.vue (1) ✅ FIXED |

### Changes Required

#### 1. `frontend/src/assets/main.css` (11 changes)

**Replace `rounded-xs` → `rounded-sm` (9 occurrences):**
- Line 82: btn-primary utility
- Line 93: btn-secondary utility
- Line 104: btn-danger utility
- Line 116: btn-accent utility
- Line 122: card utility
- Line 132: card-static utility
- Line 142: input utility
- Line 155: select utility
- Line 165: badge-binder utility

**Replace `focus:outline-hidden` → `focus:outline-none` (2 occurrences):**
- Line 143: input utility
- Line 156: select utility

#### 2. `frontend/src/views/HomeView.vue` (4 changes)

**Replace `bg-linear-to-bl` → `bg-gradient-to-bl`:**
- Line 87: On Hand card gradient
- Line 117: Volumes card gradient
- Line 144: Est. Value card gradient
- Line 179: Premium card gradient

#### 3. `frontend/src/components/books/BookThumbnail.vue` (2 changes)

**Replace `rounded-xs` → `rounded-sm`:**
- Line 42: thumbnail container
- Line 59: multi-volume badge

#### 4. `frontend/src/components/books/AnalysisViewer.vue` (1 change)

**Replace `focus:outline-hidden` → `focus:outline-none`:**
- Line 680: textarea focus state

#### 5. `frontend/src/components/layout/NavBar.vue` (1 change)

**Replace `focus:outline-hidden` → `focus:outline-none`:**
- Line 155: hamburger button focus state

### Summary of Changes

| File | Changes | Lines Affected |
|------|---------|----------------|
| main.css | 11 | 82, 93, 104, 116, 122, 132, 142, 143, 155, 156, 165 |
| HomeView.vue | 4 | 87, 117, 144, 179 |
| BookThumbnail.vue | 2 | 42, 59 |
| AnalysisViewer.vue | 1 | 680 |
| NavBar.vue | 1 | 155 |
| **TOTAL** | **19 changes** | |

---

## Test Plan

### Pre-Implementation Verification

1. **Verify staging is on latest code:**
   ```bash
   curl -s https://staging.api.bluemoxon.com/api/v1/health/version
   ```
   Expected: `2025.12.28-75f3bd7`

### Test Cases by Bug Category

#### A. NavBar Tests

| Test ID | Description | Steps | Expected Result |
|---------|-------------|-------|-----------------|
| A1-1 | Hamburger menu visible on mobile | 1. Open staging on mobile viewport (<768px) 2. Check for hamburger icon | Three horizontal bars visible in top-right |
| A1-2 | Mobile menu opens | 1. Click hamburger 2. Check menu items | Dashboard, Collection, Reports links visible |
| A1-3 | Mobile menu closes | 1. Open menu 2. Click outside | Menu closes |
| A2-1 | Desktop nav links spacing | 1. Open staging on desktop (>768px) 2. Check nav link spacing | Links have visible gaps (~24px between) |
| A2-2 | Desktop user dropdown | 1. Click user name 2. Check dropdown | Dropdown appears with Profile, Sign Out |

#### B. Dashboard Tests

| Test ID | Description | Steps | Expected Result |
|---------|-------------|-------|-----------------|
| B1-1 | Dashboard centered | 1. Navigate to / 2. Check content alignment | Stats cards centered within viewport |
| B2-1 | Heading font | 1. Check "Collection Dashboard" heading | Cormorant Garamond font, ~36px size |
| B2-2 | Card numbers font | 1. Check stat numbers in cards | Cormorant Garamond font for numbers |
| B3-1 | Quick links spacing | 1. Check "Browse Collection" and "Premium Bindings" buttons | Buttons have visible gaps, proper padding |
| B-GRAD | Gradient decorations | 1. Inspect card top-right corners | Subtle gradient overlay visible |

#### C. Books Page Tests

| Test ID | Description | Steps | Expected Result |
|---------|-------------|-------|-----------------|
| C1-1 | Search bar width | 1. Navigate to /books 2. Check search input | Full width input, not compressed |
| C1-2 | Add button styling | 1. Check Add Book button | Green background, white text, rounded corners |
| C2-1 | Books grid centered | 1. Check book cards layout | Cards centered within container |
| C3-1 | Book titles font | 1. Check book card titles | Proper font rendering |
| C4-1 | Binder badge | 1. Find book with binder tag | Badge has proper padding, rounded corners |
| C4-2 | Multi-volume badge | 1. Find multi-volume book | Badge visible, not compressed |
| C4-3 | Analysis badge | 1. Find book with analysis | Badge properly styled |
| C5-1 | Add book modal | 1. Click Add Book 2. Check modal | Modal centered, form inputs visible and styled |
| C5-2 | Edit book modal | 1. Click Edit on any book | Modal opens, form inputs styled correctly |
| C5-3 | Image upload modal | 1. Open image upload | Modal functional, upload area visible |

#### D. Other Pages Tests

| Test ID | Description | Steps | Expected Result |
|---------|-------------|-------|-----------------|
| D1-1 | Insurance report layout | 1. Navigate to /reports/insurance | Content centered, fonts correct |
| D1-2 | Report table styling | 1. Check table headers and cells | Borders visible, text aligned |
| D2-1 | Book detail view | 1. Navigate to /books/533 (or any book) | Layout centered, images display |
| D2-2 | Book detail badges | 1. Check tags/badges on detail view | Properly styled with rounded corners |

### Post-Implementation Verification

1. **Run frontend lint:**
   ```bash
   npm run --prefix frontend lint
   ```

2. **Run frontend type-check:**
   ```bash
   npm run --prefix frontend type-check
   ```

3. **Run frontend tests:**
   ```bash
   npm run --prefix frontend test
   ```

4. **Build frontend:**
   ```bash
   npm run --prefix frontend build
   ```

5. **Verify generated CSS contains fixes:**
   ```bash
   grep -c "rounded-sm" frontend/dist/assets/*.css
   grep -c "bg-gradient-to-bl" frontend/dist/assets/*.css
   grep -c "outline-none" frontend/dist/assets/*.css
   ```

### Staging Deployment Checklist

- [ ] All 19 file changes committed
- [ ] PR created targeting staging
- [ ] CI passes
- [ ] PR merged to staging
- [ ] Deploy workflow completes
- [ ] Smoke tests pass
- [ ] A1-1 through A2-2 pass (NavBar)
- [ ] B1-1 through B-GRAD pass (Dashboard)
- [ ] C1-1 through C5-3 pass (Books)
- [ ] D1-1 through D2-2 pass (Other pages)

### Production Promotion Criteria

**DO NOT promote to production until:**
1. All test cases above pass on staging
2. User (Mark) confirms visual appearance matches production
3. No new visual regressions introduced

---

## Implementation Commands

```bash
# 1. Ensure on correct branch from staging
git fetch origin staging
git checkout -b fix/tailwind-v4-visual-bugs origin/staging

# 2. Make all 19 changes (use Edit tool)

# 3. Verify changes
npm run --prefix frontend lint
npm run --prefix frontend type-check
npm run --prefix frontend build

# 4. Commit
git add -A
git commit -m "fix: Tailwind v4 compatibility - update deprecated classes (#166)"

# 5. Push and create PR
git push -u origin fix/tailwind-v4-visual-bugs
gh pr create --base staging --title "fix: Tailwind v4 compatibility - update deprecated classes (#166)" --body "..."

# 6. Wait for CI, merge, validate staging
```
