# Entity Validation Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix three entity validation issues: TOCTOU race condition, add force parameter for analysis, and allow unknown entities in analysis context.

**Architecture:** Add `db.get()` existence check before FK assignment, add `force` query param to bypass validation, add `allow_unknown` param to `validate_entity_for_book()` for analysis context.

**Tech Stack:** Python, FastAPI, SQLAlchemy, pytest

---

## Issues Addressed

| Issue | Title | Type |
|-------|-------|------|
| #1010 | TOCTOU race - entity can vanish between validation and mutation | Bug |
| #1011 | Add force parameter to analysis entity validation | Feature |
| #1012 | Unknown entity in analysis blocks workflow | Bug |

---

## Task 1: Fix TOCTOU Race Condition (#1010)

**Files:**

- Modify: `backend/app/api/v1/books.py:29-38` (add Binder import)
- Modify: `backend/app/api/v1/books.py:1456-1466` (add existence check)
- Test: `backend/tests/api/v1/test_books_entity_validation.py` (new file)

### Step 1.1: Write failing test for TOCTOU race

```python
# backend/tests/api/v1/test_books_entity_validation.py
"""Tests for entity validation edge cases in books API."""

import pytest
from unittest.mock import patch, MagicMock


class TestTOCTOURaceCondition:
    """Test TOCTOU race condition handling when entities vanish."""

    def test_binder_vanishes_between_validation_and_mutation(
        self, client, mock_editor_auth, sample_book
    ):
        """If binder is deleted after validation, association is skipped (not crash)."""
        # Create analysis markdown with binder identification
        markdown = """## Executive Summary
Test summary

## Binder Identification
- **Name:** Vanishing Binder
- **Confidence:** HIGH
"""
        # Mock validation to return entity ID
        with patch(
            "app.api.v1.books.validate_entity_for_book",
            return_value=999,  # Return fake binder ID
        ):
            # Mock db.get to return None (binder vanished)
            with patch(
                "app.api.v1.books.Session.get",
                return_value=None,
            ):
                response = client.put(
                    f"/api/v1/books/{sample_book.id}/analysis",
                    content=markdown,
                    headers={"Content-Type": "text/plain"},
                )

        # Should succeed (skip association) not crash
        assert response.status_code == 200
        # Binder should NOT be set since it vanished
        data = response.json()
        assert data.get("binder_id") is None or data.get("binder") is None

    def test_publisher_vanishes_between_validation_and_mutation(
        self, client, mock_editor_auth, sample_book
    ):
        """If publisher is deleted after validation, association is skipped."""
        markdown = """## Executive Summary
Test summary

## Publisher Identification
- **Name:** Vanishing Publisher
- **Confidence:** HIGH
"""
        with patch(
            "app.api.v1.books.validate_entity_for_book",
            return_value=888,
        ):
            with patch(
                "app.api.v1.books.Session.get",
                return_value=None,
            ):
                response = client.put(
                    f"/api/v1/books/{sample_book.id}/analysis",
                    content=markdown,
                    headers={"Content-Type": "text/plain"},
                )

        assert response.status_code == 200
```

### Step 1.2: Run test to verify it fails

Run: `poetry run pytest backend/tests/api/v1/test_books_entity_validation.py::TestTOCTOURaceCondition -v`
Expected: FAIL (currently no existence check, test may not even match current code paths)

### Step 1.3: Add Binder to imports in books.py

Modify `backend/app/api/v1/books.py:29-38`:

```python
from app.models import (
    AnalysisJob,
    Author,
    Binder,  # ADD THIS
    Book,
    BookAnalysis,
    BookImage,
    EvalRunbook,
    EvalRunbookJob,
    Publisher,
)
```

### Step 1.4: Add existence check before FK assignment

Modify `backend/app/api/v1/books.py:1456-1466`:

```python
    # MUTATION PHASE: All validations passed, now apply changes
    # Apply metadata (provenance, first edition)
    metadata_updated = []
    if metadata:
        metadata_updated = apply_metadata_to_book(book, metadata)

    # Associate binder (with existence re-check for TOCTOU safety)
    binder_updated = False
    if binder_id_to_set and book.binder_id != binder_id_to_set:
        binder = db.get(Binder, binder_id_to_set)
        if binder:
            book.binder_id = binder_id_to_set
            binder_updated = True
        else:
            logger.warning(
                f"Binder ID {binder_id_to_set} vanished between validation and mutation "
                f"for book {book_id} - skipping association"
            )

    # Associate publisher (with existence re-check for TOCTOU safety)
    publisher_updated = False
    if publisher_id_to_set and book.publisher_id != publisher_id_to_set:
        publisher = db.get(Publisher, publisher_id_to_set)
        if publisher:
            book.publisher_id = publisher_id_to_set
            publisher_updated = True
        else:
            logger.warning(
                f"Publisher ID {publisher_id_to_set} vanished between validation and mutation "
                f"for book {book_id} - skipping association"
            )
```

### Step 1.5: Run test to verify it passes

Run: `poetry run pytest backend/tests/api/v1/test_books_entity_validation.py::TestTOCTOURaceCondition -v`
Expected: PASS

### Step 1.6: Commit

```bash
git add backend/app/api/v1/books.py backend/tests/api/v1/test_books_entity_validation.py
git commit -m "fix(#1010): add TOCTOU check for entity existence before FK assignment"
```

---

## Task 2: Add force Parameter to Analysis Endpoint (#1011)

**Files:**

- Modify: `backend/app/api/v1/books.py:1400-1448` (add force param, skip validation when true)
- Test: `backend/tests/api/v1/test_books_entity_validation.py`

### Step 2.1: Write failing test for force parameter

Add to `backend/tests/api/v1/test_books_entity_validation.py`:

```python
class TestForceParameterAnalysis:
    """Test force parameter bypasses entity validation in analysis."""

    def test_force_bypasses_similar_entity_409(
        self, client, mock_editor_auth, sample_book
    ):
        """With force=true, similar entity conflict is ignored."""
        from app.schemas.entity_validation import EntityValidationError, EntitySuggestion

        markdown = """## Executive Summary
Test

## Binder Identification
- **Name:** Riviere and Son
"""
        # Mock validation returning 409 conflict
        error = EntityValidationError(
            error="similar_entity_exists",
            entity_type="binder",
            input="Riviere and Son",
            suggestions=[
                EntitySuggestion(id=1, name="Riviere & Son", tier="TIER_1", match=0.95, book_count=10)
            ],
            resolution="Use existing",
        )

        with patch("app.api.v1.books.validate_entity_for_book", return_value=error):
            # Without force - should get 409
            response = client.put(
                f"/api/v1/books/{sample_book.id}/analysis",
                content=markdown,
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 409

            # With force=true - should succeed
            response = client.put(
                f"/api/v1/books/{sample_book.id}/analysis?force=true",
                content=markdown,
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 200

    def test_force_bypasses_unknown_entity_400(
        self, client, mock_editor_auth, sample_book
    ):
        """With force=true, unknown entity error is ignored."""
        from app.schemas.entity_validation import EntityValidationError

        markdown = """## Executive Summary
Test

## Binder Identification
- **Name:** Brand New Binder
"""
        error = EntityValidationError(
            error="unknown_entity",
            entity_type="binder",
            input="Brand New Binder",
            suggestions=None,
            resolution="Create first",
        )

        with patch("app.api.v1.books.validate_entity_for_book", return_value=error):
            # Without force - should get 400
            response = client.put(
                f"/api/v1/books/{sample_book.id}/analysis",
                content=markdown,
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 400

            # With force=true - should succeed (skip association)
            response = client.put(
                f"/api/v1/books/{sample_book.id}/analysis?force=true",
                content=markdown,
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 200
```

### Step 2.2: Run test to verify it fails

Run: `poetry run pytest backend/tests/api/v1/test_books_entity_validation.py::TestForceParameterAnalysis -v`
Expected: FAIL (no force parameter exists)

### Step 2.3: Add force parameter to analysis endpoint

Modify `backend/app/api/v1/books.py:1400-1406`:

```python
@router.put("/{book_id}/analysis")
def update_book_analysis(
    book_id: int,
    full_markdown: str = Body(..., media_type="text/plain"),
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
    force: bool = Query(
        default=False,
        description="Bypass entity validation errors and skip association",
    ),
):
```

### Step 2.4: Update validation logic to respect force

Modify `backend/app/api/v1/books.py:1430-1448`:

```python
    if parsed.binder_identification and parsed.binder_identification.get("name"):
        binder_name = parsed.binder_identification["name"]
        binder_result = validate_entity_for_book(db, "binder", binder_name)

        if isinstance(binder_result, EntityValidationError):
            if force:
                logger.info(
                    f"Skipping binder validation error due to force=true: {binder_result.error}"
                )
            else:
                status_code = 409 if binder_result.error == "similar_entity_exists" else 400
                raise HTTPException(status_code=status_code, detail=binder_result.model_dump())
        else:
            binder_id_to_set = binder_result

    if parsed.publisher_identification and parsed.publisher_identification.get("name"):
        publisher_name = parsed.publisher_identification["name"]
        publisher_result = validate_entity_for_book(db, "publisher", publisher_name)

        if isinstance(publisher_result, EntityValidationError):
            if force:
                logger.info(
                    f"Skipping publisher validation error due to force=true: {publisher_result.error}"
                )
            else:
                status_code = 409 if publisher_result.error == "similar_entity_exists" else 400
                raise HTTPException(status_code=status_code, detail=publisher_result.model_dump())
        else:
            publisher_id_to_set = publisher_result
```

### Step 2.5: Run test to verify it passes

Run: `poetry run pytest backend/tests/api/v1/test_books_entity_validation.py::TestForceParameterAnalysis -v`
Expected: PASS

### Step 2.6: Commit

```bash
git add backend/app/api/v1/books.py backend/tests/api/v1/test_books_entity_validation.py
git commit -m "feat(#1011): add force parameter to analysis endpoint for validation bypass"
```

---

## Task 3: Allow Unknown Entities in Analysis Context (#1012)

**Files:**

- Modify: `backend/app/services/entity_validation.py:112-172` (add allow_unknown param)
- Modify: `backend/app/api/v1/books.py:1432,1442` (pass allow_unknown=True)
- Test: `backend/tests/services/test_entity_validation_service.py`

### Step 3.1: Write failing test for allow_unknown parameter

Add to `backend/tests/services/test_entity_validation_service.py`:

```python
class TestAllowUnknownParameter:
    """Test allow_unknown parameter for analysis context."""

    def test_allow_unknown_returns_none_instead_of_error(self):
        """With allow_unknown=True, unknown entity returns None (not error)."""
        from app.services.entity_validation import validate_entity_for_book

        db = MagicMock()
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name", return_value=None
        ):
            with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[]):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "enforce"
                    mock_settings.return_value.entity_match_threshold_publisher = 0.80

                    # Default behavior - returns error
                    result = validate_entity_for_book(db, "publisher", "Unknown Press")
                    assert isinstance(result, EntityValidationError)
                    assert result.error == "unknown_entity"

                    # With allow_unknown=True - returns None
                    result = validate_entity_for_book(
                        db, "publisher", "Unknown Press", allow_unknown=True
                    )
                    assert result is None

    def test_allow_unknown_still_returns_id_on_exact_match(self):
        """allow_unknown doesn't affect exact matches - still returns ID."""
        from app.services.entity_validation import validate_entity_for_book

        db = MagicMock()
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=(5, "Macmillan and Co."),
        ):
            result = validate_entity_for_book(
                db, "publisher", "Macmillan and Co.", allow_unknown=True
            )
        assert result == 5

    def test_allow_unknown_still_returns_error_on_fuzzy_match(self):
        """allow_unknown doesn't affect fuzzy matches - still returns 409 error."""
        from app.services.entity_validation import validate_entity_for_book

        db = MagicMock()
        match = EntityMatch(
            entity_id=5,
            name="Macmillan and Co.",
            tier="TIER_1",
            confidence=0.94,
            book_count=12,
        )
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name", return_value=None
        ):
            with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[match]):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "enforce"
                    mock_settings.return_value.entity_match_threshold_publisher = 0.80

                    result = validate_entity_for_book(
                        db, "publisher", "Macmilan", allow_unknown=True
                    )

        # Fuzzy match still returns error (similar_entity_exists)
        assert isinstance(result, EntityValidationError)
        assert result.error == "similar_entity_exists"
```

### Step 3.2: Run test to verify it fails

Run: `poetry run pytest backend/tests/services/test_entity_validation_service.py::TestAllowUnknownParameter -v`
Expected: FAIL (allow_unknown parameter doesn't exist)

### Step 3.3: Add allow_unknown parameter to validate_entity_for_book

Modify `backend/app/services/entity_validation.py:112-172`:

```python
def validate_entity_for_book(
    db: Session,
    entity_type: EntityType,
    name: str | None,
    threshold: float | None = None,
    allow_unknown: bool = False,
) -> int | EntityValidationError | None:
    """Validate entity name before associating with a book.

    Unlike validate_entity_creation(), this function is for book endpoints
    and returns the entity ID on exact match (allowing direct association).

    Args:
        db: Database session.
        entity_type: Type of entity ("publisher", "binder", "author").
        name: Name of entity to validate.
        threshold: Fuzzy match threshold. If None, uses config value for entity type.
        allow_unknown: If True, return None instead of error for unknown entities.
            Useful in analysis context where AI may discover new entities.

    Returns:
        int: Entity ID if exact match found (safe to associate).
        EntityValidationError: If similar match (409) or unknown (400, unless allow_unknown).
        None: If name is empty/None, or if allow_unknown and entity not found.
    """
    # ... existing code until line 156 ...

    # No matches at all - entity not found
    if not matches:
        if settings.entity_validation_mode == "log":
            logger.warning(
                "Entity validation: %s '%s' not found in database",
                entity_type,
                name,
            )
            return None

        # In analysis context (allow_unknown=True), just skip association
        if allow_unknown:
            logger.info(
                "Entity validation: %s '%s' not found, allow_unknown=True - skipping",
                entity_type,
                name,
            )
            return None

        return EntityValidationError(
            error="unknown_entity",
            entity_type=entity_type,
            input=name,
            suggestions=None,
            resolution=f"Create the {entity_type} first, or use an existing {entity_type} name",
        )
```

### Step 3.4: Run test to verify it passes

Run: `poetry run pytest backend/tests/services/test_entity_validation_service.py::TestAllowUnknownParameter -v`
Expected: PASS

### Step 3.5: Update books.py to use allow_unknown for analysis

Modify `backend/app/api/v1/books.py:1432,1442`:

```python
        binder_result = validate_entity_for_book(db, "binder", binder_name, allow_unknown=True)
        # ...
        publisher_result = validate_entity_for_book(db, "publisher", publisher_name, allow_unknown=True)
```

### Step 3.6: Run all entity validation tests

Run: `poetry run pytest backend/tests/services/test_entity_validation_service.py backend/tests/api/v1/test_books_entity_validation.py -v`
Expected: ALL PASS

### Step 3.7: Commit

```bash
git add backend/app/services/entity_validation.py backend/app/api/v1/books.py backend/tests/services/test_entity_validation_service.py
git commit -m "fix(#1012): allow unknown entities in analysis context with allow_unknown param"
```

---

## Task 4: Run Full Test Suite and Lint

### Step 4.1: Run linters

```bash
poetry run ruff check backend/
poetry run ruff format --check backend/
```

### Step 4.2: Fix any lint issues

### Step 4.3: Run full test suite

```bash
poetry run pytest backend/
```

### Step 4.4: Final commit if needed

```bash
git add -A
git commit -m "chore: lint fixes"
```

---

## Task 5: Create PR to Staging

### Step 5.1: Push branch

```bash
git push -u origin fix/entity-validation-1010-1011-1012
```

### Step 5.2: Create PR

```bash
gh pr create --base staging --title "fix: Entity validation fixes #1010 #1011 #1012" --body "## Summary
- Fix TOCTOU race condition by adding existence check before FK assignment (#1010)
- Add force parameter to analysis endpoint for validation bypass (#1011)
- Allow unknown entities in analysis context with allow_unknown param (#1012)

## Test Plan
- [ ] Unit tests pass
- [ ] Manual test: upload analysis with fuzzy-match entity name
- [ ] Manual test: upload analysis with unknown entity name

Closes #1010, #1011, #1012"
```

### Step 5.3: Wait for CI

```bash
gh pr checks <pr-number> --watch
```

---

## Execution Notes

**Parallelism opportunity:** Tasks 1, 2, and 3 modify different sections of code and could theoretically be done in parallel worktrees if desired. However, they build on each other logically:

- Task 1 (TOCTOU) is independent
- Task 2 (force param) is independent
- Task 3 (allow_unknown) depends on understanding how Task 2's force interacts

**Recommended approach:** Execute sequentially in one worktree to maintain context, using TDD discipline for each task.
