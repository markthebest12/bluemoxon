# Postmortem: Tailwind CSS v4 Migration

**Date:** 2025-12-28
**Issue:** #166
**Severity:** Critical - Production visual regressions
**Duration:** 2 days (2025-12-27 to 2025-12-28)

---

## Summary

The Tailwind CSS v4 migration (PR #609) was merged claiming "no visual regressions" but actually broke the entire component library. Cards had no padding or borders. Buttons had missing styles. The migration required 6 additional PRs to fix.

---

## Timeline

| PR | Description | Impact |
|----|-------------|--------|
| #609 | Initial migration | Merged with catastrophic breakage |
| #612 | Navbar logo height | Fixed h-14 override |
| #613 | Wrong radius fix | Made radius WORSE (doubled) |
| #614 | Correct radius fix | Added --radius-xs to @theme |
| #615 | space-* to gap-* | Partial fix for specificity |
| #616 | @utility to @layer components | TRUE root cause fix |

---

## Issues Identified

### Issue 1: Navbar Logo Height Override

**Symptom:** Logo appeared wrong size after migration.

**Root Cause:** Tailwind v4 height classes needed explicit override.

**Fix:** Used explicit height class.

---

### Issue 2: Custom Radius Not Defined

**Symptom:** Elements using rounded-xs had incorrect border radius (2x too large).

**Root Cause:** Tailwind v4 renamed default radius scale.

**False Fix (PR #613):** Added --radius-xs to :root - this DOUBLED the radius because it stacked with Tailwind default.

**Correct Fix (PR #614):** Added --radius-xs: 0.125rem to @theme block, which properly registers it with Tailwind theme system.

**Lesson:** In Tailwind v4, custom CSS variables MUST be defined in @theme, not :root or elsewhere.

---

### Issue 3: space-* Utility Specificity

**Symptom:** Flex containers with space-x-* had collapsed spacing.

**Root Cause:** Tailwind v4 wraps legacy space-* utilities in :where() giving zero specificity:

    /* v4 output - zero specificity, gets overridden by anything */
    :where(.space-x-6>:not(:last-child)) { margin-right: 1.5rem; }

    /* gap-* has normal specificity */
    .gap-6 { gap: 1.5rem; }

**Fix:** Replace all space-x-* and space-y-* with gap-* on flex/grid containers.

---

### Issue 4: @utility with @apply Silent Failure

**Symptom:** Component classes (.card, .input, .btn-*) rendered with border: 0px, padding: 0px instead of intended styles.

**Root Cause:** Tailwind v4 @utility directive does NOT work correctly with @apply for component-style classes. Some properties (like background-color) may work while others (border, padding) silently fail to generate CSS.

**Evidence:**

| Element | Staging (broken) | Production (correct) |
|---------|------------------|---------------------|
| .card   | padding: 0px     | padding: 24px       |
| .input  | border: 0px      | border: 1px solid   |

**Fix:** Convert ALL @utility blocks to @layer components with explicit CSS properties:

    /* BROKEN in v4 */
    @utility card {
      @apply bg-victorian-paper-cream rounded-xs border border-victorian-paper-antique p-6;
    }

    /* WORKS in v4 */
    @layer components {
      .card {
        background-color: var(--color-victorian-paper-cream);
        border-radius: var(--radius-xs);
        border: 1px solid var(--color-victorian-paper-antique);
        padding: 1.5rem;
      }
    }

**Components Affected:**
- .btn-primary, .btn-secondary, .btn-danger, .btn-accent
- .card, .card-static
- .input, .select
- All .badge-* variants
- .divider-flourish, .section-header

---

## Root Cause Analysis

### Why Did PR #609 Pass Review?

1. **Inadequate testing methodology** - No side-by-side visual comparison of staging vs production
2. **Trust in migration tools** - The Tailwind upgrade tool ran without errors, so it was assumed to be working
3. **Silent failures** - CSS compiled without errors, but output was incomplete
4. **No computed style verification** - Nobody checked actual rendered CSS values

### What Should Have Been Done

1. **Visual regression testing** - Screenshot comparison of key pages before/after
2. **Computed style spot-checks** - Use DevTools to verify padding, borders, shadows on component classes
3. **Staged rollout** - Deploy to staging and manually verify before promoting to production
4. **Component library audit** - Systematically verify each custom component class

---

## Prevention Measures

1. **Add visual regression tests** to CI pipeline
2. **Create component style verification script** that checks computed styles
3. **Document Tailwind v4 breaking changes** for future reference
4. **Require staging validation** before any major dependency upgrades
5. **Add CSS output diff** to PR review process for style changes

---

## Lessons Learned

1. **Migration tools do not catch everything** - Tailwind upgrade tool did not warn about @utility + @apply issues
2. **Silent failures are the worst failures** - No errors, just broken output
3. **No regressions claims require evidence** - Screenshots, not just it compiles
4. **Custom component classes need explicit CSS in v4** - Do not rely on @apply inside @utility
5. **Test the actual rendered output** - Not just does it compile

---

## Related Documentation

- Session Log: docs/sessions/2025-12-27-tailwind-v4-migration.md
- Tailwind v4 Migration Guide: https://tailwindcss.com/docs/upgrade-guide
