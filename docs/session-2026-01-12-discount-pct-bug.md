# Session: Fix discount_pct Calculation Bug (#1078)

**Date:** 2026-01-12
**Issue:** https://github.com/markthebest12/bluemoxon/issues/1078
**PR:** https://github.com/markthebest12/bluemoxon/pull/1079
**Status:** COMPLETE - Fix deployed to production

## CRITICAL REMINDERS FOR NEXT SESSION

### 1. ALWAYS Use Superpowers Skills
- **brainstorming** - Before any feature work
- **systematic-debugging** - Before any bug fix
- **test-driven-development** - RED-GREEN-REFACTOR always
- **verification-before-completion** - Before claiming done

### 2. Bash Command Formatting (NEVER use these - triggers permission prompts)
- `#` comment lines before commands
- `\` backslash line continuations
- `$(...)` command substitution
- `||` or `&&` chaining
- `!` in quoted strings

### 3. ALWAYS Use Instead
- Simple single-line commands
- Separate sequential Bash tool calls instead of `&&`
- `bmx-api` for all BlueMoxon API calls

## Problem Summary

`discount_pct` field is not being calculated/populated even when all required values (`value_mid`, `purchase_price`, `acquisition_cost`) are present.

### Expected Behavior
`discount_pct` should calculate as: `(value_mid - acquisition_cost) / value_mid * 100`

### Affected Books (Production)
- Book #606: Has all values, discount_pct is null (expected: 5.68%)
- Book #611: Has all values, discount_pct is null (expected: 34.76%)
- Book #615: Working correctly (discount_pct: 48.42)

### Key Observations
1. `roi_pct` IS calculating correctly for all books
2. `discount_pct` works for some books but not others
3. PUT requests do not trigger recalculation
4. All affected books have the same required fields populated

## Investigation Progress

### Phase 1: Locate Calculation Logic
- [ ] Find where discount_pct is calculated
- [ ] Find where roi_pct is calculated (working reference)
- [ ] Compare the two implementations

### Phase 2: Identify Root Cause
- [ ] Determine why some books calculate and others don't
- [ ] Check for conditional logic that may skip calculation

### Phase 3: Fix and Test
- [ ] Write failing test
- [ ] Implement fix
- [ ] Verify fix in staging
- [ ] Promote to production

## Session Log

### 2026-01-12 - Initial Investigation
- Fetched issue #1078 details
- Starting systematic debugging process

### Root Cause Analysis

**Found TWO bugs in `backend/app/api/v1/books.py`:**

**Bug 1: `create_book` (line 681-744) missing `recalculate_discount_pct` call**
- Line 716: `recalculate_roi_pct(book)` IS called
- NO call to `recalculate_discount_pct(book)` - MISSING!
- This explains why new books have null discount_pct but valid roi_pct

**Bug 2: `update_book` (line 800-802) incomplete trigger condition**
```python
# Current (incomplete):
if "value_mid" in update_data or "value_low" in update_data or "value_high" in update_data:
    recalculate_discount_pct(book)

# Should also include:
if "purchase_price" in update_data:  # MISSING!
    recalculate_discount_pct(book)
```

**Evidence:**
- Book #606 and #611: Created with all values but discount_pct null (Bug 1)
- Book #615: Works because updated via PUT with value_mid field
- Issue's attempted fix `PUT /books/606 '{"acquisition_cost": 448.00}'` fails because:
  1. `acquisition_cost` not in trigger list (correct - it's for roi_pct)
  2. Even `purchase_price` wouldn't work (Bug 2)

**Files to modify:**
- `backend/app/api/v1/books.py:716` - Add `recalculate_discount_pct(book)` call
- `backend/app/api/v1/books.py:800-802` - Add `purchase_price` to trigger condition

### Implementation (TDD)

**RED phase:** Wrote 4 failing tests:
- `test_create_book_calculates_discount_pct` - POST /books should calculate discount_pct
- `test_create_book_calculates_both_discount_and_roi` - Both metrics should calculate
- `test_update_purchase_price_recalculates_discount` - PUT with purchase_price should recalc
- `test_update_purchase_price_alone_triggers_discount_recalc` - Only purchase_price change triggers

**GREEN phase:** Minimal fixes:
1. Added `recalculate_discount_pct(book)` call in `create_book` (line 719)
2. Added `or "purchase_price" in update_data` to trigger condition in `update_book` (line 804-809)

**Results:**
- 19/19 discount tests pass
- 72/72 book API tests pass (no regressions)
- Linting passes

### PR Created
- **PR #1079**: https://github.com/markthebest12/bluemoxon/pull/1079
- **Target**: staging
- **Status**: Updated with code review fixes

### Code Review Fixes (commit 0c5bf81)

**P0 (Bug fixes):**
- Clear `discount_pct` when `purchase_price` or `value_mid` is null (prevents stale data)
- Clear `roi_pct` when `acquisition_cost` or `value_mid` is null (pre-existing tech debt)

**P1 (Code quality):**
- Use consistent Decimal arithmetic in `recalculate_discount_pct` (matches `roi_pct` style)
- Remove unnecessary `value_low`/`value_high` triggers (formula only uses `value_mid`)
- Fix misleading comment to match actual trigger condition

**P3 (Test coverage):**
- Add tests for clearing inputs clears calculated fields (4 tests)
- Add tests for negative discount scenarios (2 tests)
- Add tests for partial data creation workflows (2 tests)

**Final test results:**
- 27/27 discount recalculation tests pass
- 72/72 book API tests pass (no regressions)
- Linting passes

### CI Fix (commit 82d7e37)
Fixed failing `test_metrics_average_discount_and_roi` test:
- Only call `recalculate_discount_pct` on CREATE when both inputs present
- Preserves manually set values when creating books without FMV/purchase_price

## Completion Summary

### Deployment Complete
1. PR #1079 merged to staging (commit 7feea85)
2. Staging deploy succeeded, smoke tests passed
3. Verified fix in staging:
   - Book #606: discount_pct = 5.68 (was null)
   - Book #611: discount_pct = 34.76 (was null)
4. PR #1080 created and merged to main (commit c3b31d1)
5. Production deploy succeeded, smoke tests passed
6. Triggered recalculation on production:
   - Book #606: discount_pct = 5.68
   - Book #611: discount_pct = 34.76

## Worktree Location
`/Users/mark/projects/bluemoxon/.worktrees/fix-discount-pct`

## Key Files Modified
- `backend/app/api/v1/books.py` - Added discount calc on create, fixed update triggers
- `backend/app/services/scoring.py` - Clear stale values, use Decimal arithmetic
- `backend/tests/test_discount_recalculation.py` - 12 new tests added
