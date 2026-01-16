# OWNED_STATUSES Constant Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace magic strings `["IN_TRANSIT", "ON_HAND"]` with a typed `OWNED_STATUSES` constant for type safety and maintainability.

**Architecture:** Add a module-level constant `OWNED_STATUSES` in `app/enums.py` that contains the list of `BookStatus` values representing books physically owned (in transit or on hand). Update all 5 call sites to use this constant.

**Tech Stack:** Python 3.12, SQLAlchemy, pytest

---

## Task 1: Add OWNED_STATUSES Constant to Enums

**Files:**

- Modify: `backend/app/enums.py:16` (after BookStatus class)
- Test: `backend/tests/test_enums.py` (create)

**Step 1: Write the failing test**

Create `backend/tests/test_enums.py`:

```python
"""Tests for centralized enum definitions."""

from app.enums import BookStatus, OWNED_STATUSES


def test_owned_statuses_contains_in_transit_and_on_hand():
    """OWNED_STATUSES should contain exactly IN_TRANSIT and ON_HAND."""
    assert len(OWNED_STATUSES) == 2
    assert BookStatus.IN_TRANSIT in OWNED_STATUSES
    assert BookStatus.ON_HAND in OWNED_STATUSES


def test_owned_statuses_excludes_evaluating_and_removed():
    """OWNED_STATUSES should NOT contain EVALUATING or REMOVED."""
    assert BookStatus.EVALUATING not in OWNED_STATUSES
    assert BookStatus.REMOVED not in OWNED_STATUSES


def test_owned_statuses_is_tuple():
    """OWNED_STATUSES should be immutable (tuple, not list)."""
    assert isinstance(OWNED_STATUSES, tuple)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && poetry run pytest tests/test_enums.py -v`
Expected: FAIL with `ImportError: cannot import name 'OWNED_STATUSES'`

**Step 3: Write minimal implementation**

Add to `backend/app/enums.py` after line 15 (after BookStatus class):

```python
# Statuses representing books physically owned (in collection)
OWNED_STATUSES: tuple[BookStatus, ...] = (BookStatus.IN_TRANSIT, BookStatus.ON_HAND)
```

**Step 4: Run test to verify it passes**

Run: `cd backend && poetry run pytest tests/test_enums.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add backend/app/enums.py backend/tests/test_enums.py
git commit -m "feat(enums): add OWNED_STATUSES constant for owned book filtering"
```

---

## Task 2: Update books.py (Line 132)

**Files:**

- Modify: `backend/app/api/v1/books.py:132`

**Step 1: Verify existing tests pass before change**

Run: `cd backend && poetry run pytest tests/test_books.py -v -x`
Expected: PASS

**Step 2: Update the import**

At top of `backend/app/api/v1/books.py`, add `OWNED_STATUSES` to existing import:

```python
from app.enums import BookStatus, OWNED_STATUSES, ...
```

**Step 3: Replace magic string at line 132**

Change:

```python
Book.status.in_(["IN_TRANSIT", "ON_HAND"]),
```

To:

```python
Book.status.in_(OWNED_STATUSES),
```

**Step 4: Run tests to verify no regression**

Run: `cd backend && poetry run pytest tests/test_books.py -v -x`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/api/v1/books.py
git commit -m "refactor(books): use OWNED_STATUSES constant at line 132"
```

---

## Task 3: Update books.py (Line 1373)

**Files:**

- Modify: `backend/app/api/v1/books.py:1373`

**Step 1: Replace magic string at line 1373**

Change:

```python
Book.status.in_(["IN_TRANSIT", "ON_HAND"]),
```

To:

```python
Book.status.in_(OWNED_STATUSES),
```

**Step 2: Run tests to verify no regression**

Run: `cd backend && poetry run pytest tests/test_books.py -v -x`
Expected: PASS

**Step 3: Commit**

```bash
git add backend/app/api/v1/books.py
git commit -m "refactor(books): use OWNED_STATUSES constant at line 1373"
```

---

## Task 4: Update eval_generation.py (Line 590)

**Files:**

- Modify: `backend/app/services/eval_generation.py:590`

**Step 1: Add import**

At top of `backend/app/services/eval_generation.py`, add:

```python
from app.enums import OWNED_STATUSES
```

**Step 2: Replace magic string at line 590**

Change:

```python
Book.status.in_(["IN_TRANSIT", "ON_HAND"]),
```

To:

```python
Book.status.in_(OWNED_STATUSES),
```

**Step 3: Run tests to verify no regression**

Run: `cd backend && poetry run pytest tests/test_eval_generation.py -v -x`
Expected: PASS

**Step 4: Commit**

```bash
git add backend/app/services/eval_generation.py
git commit -m "refactor(eval_generation): use OWNED_STATUSES constant"
```

---

## Task 5: Update scoring.py (Line 685)

**Files:**

- Modify: `backend/app/services/scoring.py:685`

**Step 1: Add import**

At top of `backend/app/services/scoring.py`, add:

```python
from app.enums import OWNED_STATUSES
```

**Step 2: Replace magic string at line 685**

Change:

```python
BookModel.status.in_(["IN_TRANSIT", "ON_HAND"]),
```

To:

```python
BookModel.status.in_(OWNED_STATUSES),
```

**Step 3: Run tests to verify no regression**

Run: `cd backend && poetry run pytest tests/test_scoring.py -v -x`
Expected: PASS

**Step 4: Commit**

```bash
git add backend/app/services/scoring.py
git commit -m "refactor(scoring): use OWNED_STATUSES constant"
```

---

## Task 6: Update test_dashboard_consolidation.py (Line 263)

**Files:**

- Modify: `backend/tests/test_dashboard_consolidation.py:263`

**Step 1: Add import**

At top of `backend/tests/test_dashboard_consolidation.py`, add:

```python
from app.enums import OWNED_STATUSES
```

**Step 2: Replace magic string at line 263**

Change:

```python
Book.status.in_(["ON_HAND", "IN_TRANSIT"]),
```

To:

```python
Book.status.in_(OWNED_STATUSES),
```

**Step 3: Run test to verify no regression**

Run: `cd backend && poetry run pytest tests/test_dashboard_consolidation.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add backend/tests/test_dashboard_consolidation.py
git commit -m "refactor(tests): use OWNED_STATUSES constant in dashboard tests"
```

---

## Task 7: Final Validation

**Step 1: Run full linting**

Run: `cd backend && poetry run ruff check .`
Expected: No errors

Run: `cd backend && poetry run ruff format --check .`
Expected: No formatting issues

**Step 2: Run full test suite**

Run: `cd backend && poetry run pytest -v`
Expected: All tests pass

**Step 3: Verify no magic strings remain**

Run: `grep -r "IN_TRANSIT.*ON_HAND\|ON_HAND.*IN_TRANSIT" backend/`
Expected: No output (no matches)

**Step 4: Final commit (if any uncommitted changes)**

Only if linting made auto-fixes.

---

## Task 8: Create PR to Staging

**Step 1: Push branch**

```bash
git push -u origin refactor/owned-statuses-constant
```

**Step 2: Create PR targeting staging**

```bash
gh pr create --base staging --title "refactor: Replace magic status strings with OWNED_STATUSES constant (fixes #1114)" --body "## Summary
- Adds \`OWNED_STATUSES\` constant to \`app/enums.py\`
- Replaces 5 occurrences of magic strings \`[\"IN_TRANSIT\", \"ON_HAND\"]\`
- Adds tests for the new constant

## Files Changed
- \`backend/app/enums.py\` - Added constant
- \`backend/app/api/v1/books.py\` - 2 occurrences
- \`backend/app/services/eval_generation.py\` - 1 occurrence
- \`backend/app/services/scoring.py\` - 1 occurrence
- \`backend/tests/test_dashboard_consolidation.py\` - 1 occurrence
- \`backend/tests/test_enums.py\` - New test file

## Test Plan
- [x] New unit tests for OWNED_STATUSES constant
- [x] All existing tests pass
- [x] No magic strings remain

Fixes #1114"
```

**Step 3: Wait for user review before merging**

USER REVIEW REQUIRED before merge to staging.

---

## Task 9: Merge to Staging (After User Approval)

**Step 1: Merge PR**

```bash
gh pr merge <pr-number> --squash --delete-branch
```

**Step 2: Verify staging deployment**

Watch CI/deploy workflow.

---

## Task 10: Create PR from Staging to Main (Production)

**Step 1: Create promotion PR**

```bash
gh pr create --base main --head staging --title "chore: Promote staging to production (OWNED_STATUSES refactor)"
```

**Step 2: Wait for user review before merging**

USER REVIEW REQUIRED before merge to main.

---

## Task 11: Merge to Main and Close Issue

**Step 1: Merge PR (after user approval)**

```bash
gh pr merge <pr-number> --squash
```

**Step 2: Watch deploy**

```bash
gh run list --workflow Deploy --limit 1
```

**Step 3: Close issue**

```bash
gh issue close 1114 --comment "Completed in PR #<staging-pr-number>"
```
