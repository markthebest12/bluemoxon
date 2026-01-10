# Group D Entity Validation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix entity validation issues - consolidate duplicate logic, use consistent Result pattern, surface skipped matches to users.

**Architecture:** Single `ValidationResult` dataclass returned from validation. Shared `validate_and_associate_entities()` function used by both HTTP and worker. Callers decide how to surface errors/warnings.

**Tech Stack:** Python dataclasses, SQLAlchemy, FastAPI

**Issues:** #1013, #1014, #1015

---

## Data Structures

### ValidationResult
```python
@dataclass
class ValidationResult:
    """Result of validating an entity for book association."""
    entity_id: int | None = None
    skipped_match: EntityMatch | None = None
    error: EntityValidationError | None = None

    @property
    def success(self) -> bool:
        return self.entity_id is not None

    @property
    def was_skipped(self) -> bool:
        return self.skipped_match is not None
```

### EntityAssociationResult
```python
@dataclass
class EntityAssociationResult:
    """Result of validating and associating entities with a book."""
    binder: ValidationResult
    publisher: ValidationResult

    @property
    def has_errors(self) -> bool:
        return self.binder.error is not None or self.publisher.error is not None

    @property
    def has_skipped(self) -> bool:
        return self.binder.was_skipped or self.publisher.was_skipped
```

---

## Tasks

### Task 1: Add ValidationResult dataclass

**Files:**
- Modify: `backend/app/services/entity_validation.py`
- Test: `backend/tests/test_entity_validation.py`

**Step 1: Write failing test for ValidationResult**
```python
def test_validation_result_success_state():
    result = ValidationResult(entity_id=123)
    assert result.success is True
    assert result.was_skipped is False
    assert result.error is None

def test_validation_result_skipped_state():
    match = EntityMatch(id=456, name="Similar", confidence=0.85, book_count=10)
    result = ValidationResult(skipped_match=match)
    assert result.success is False
    assert result.was_skipped is True
```

**Step 2: Run test to verify it fails**
```bash
cd /Users/mark/projects/bluemoxon/.worktrees/perf-1001-query-consolidation/backend
poetry run pytest tests/test_entity_validation.py::test_validation_result_success_state -v
```

**Step 3: Implement ValidationResult dataclass**
Add to `entity_validation.py` after existing imports and before functions.

**Step 4: Run tests to verify pass**

**Step 5: Commit**
```bash
git add backend/app/services/entity_validation.py backend/tests/test_entity_validation.py
git commit -m "feat: Add ValidationResult dataclass (#1015)"
```

---

### Task 2: Add EntityAssociationResult dataclass

**Files:**
- Modify: `backend/app/services/entity_validation.py`
- Test: `backend/tests/test_entity_validation.py`

**Step 1: Write failing test**
```python
def test_entity_association_result_has_errors():
    error = EntityValidationError(error="unknown_entity", message="Not found", suggestions=[])
    result = EntityAssociationResult(
        binder=ValidationResult(error=error),
        publisher=ValidationResult(entity_id=123)
    )
    assert result.has_errors is True
    assert result.has_skipped is False

def test_entity_association_result_has_skipped():
    match = EntityMatch(id=456, name="Similar", confidence=0.85, book_count=10)
    result = EntityAssociationResult(
        binder=ValidationResult(skipped_match=match),
        publisher=ValidationResult(entity_id=123)
    )
    assert result.has_errors is False
    assert result.has_skipped is True
```

**Step 2-5:** Run, implement, verify, commit

---

### Task 3: Modify validate_entity_for_book() to return ValidationResult

**Files:**
- Modify: `backend/app/services/entity_validation.py`
- Test: `backend/tests/test_entity_validation.py`

**Changes:**
- Return `ValidationResult(entity_id=id)` for exact matches
- Return `ValidationResult(error=error)` for rejections
- Return `ValidationResult(skipped_match=match)` for log mode fuzzy skips
- Return `ValidationResult()` for no-op cases

**Step 1: Update existing tests to expect ValidationResult**

**Step 2: Update function signature and implementation**

**Step 3: Commit**
```bash
git commit -m "refactor: Return ValidationResult from validate_entity_for_book (#1015)"
```

---

### Task 4: Add validate_and_associate_entities() function

**Files:**
- Modify: `backend/app/services/entity_validation.py`
- Test: `backend/tests/test_entity_validation.py`

**Step 1: Write failing test**
```python
def test_validate_and_associate_entities_sets_ids(db_session, book, binder, publisher):
    parsed = ParsedBookAnalysis(
        binder_identification={"name": binder.name},
        publisher_identification={"name": publisher.name}
    )
    result = validate_and_associate_entities(db_session, book, parsed)

    assert result.binder.entity_id == binder.id
    assert result.publisher.entity_id == publisher.id
    assert book.binder_id == binder.id
    assert book.publisher_id == publisher.id
```

**Step 2-5:** Run, implement, verify, commit

---

### Task 5: Update books.py to use shared function

**Files:**
- Modify: `backend/app/api/v1/books.py`
- Test: `backend/tests/test_books.py`

**Step 1: Write test for Warning header**
```python
def test_book_analysis_returns_warning_header_on_skipped_match(client, db_session):
    # Setup: Create similar binder, set log mode
    # Act: Submit analysis with fuzzy binder name
    # Assert: Response has Warning header with skipped match info
```

**Step 2: Replace duplicate validation code with:**
```python
from app.services.entity_validation import validate_and_associate_entities

result = validate_and_associate_entities(db, book, parsed)
if result.has_errors:
    error = result.binder.error or result.publisher.error
    status_code = 409 if error.error == "similar_entity_exists" else 400
    raise HTTPException(status_code=status_code, detail=error.model_dump())

# Add Warning header if matches were skipped
headers = {}
if result.has_skipped:
    headers["Warning"] = _format_skipped_warnings(result)
```

**Step 3: Commit**
```bash
git commit -m "refactor: Use shared validation in books.py (#1014)"
```

---

### Task 6: Update worker.py to use shared function

**Files:**
- Modify: `backend/app/services/worker.py`
- Test: `backend/tests/test_worker.py`

**Step 1: Write test for skipped match logging**
```python
def test_worker_logs_skipped_match(db_session, book, caplog):
    # Setup: Create similar binder, set log mode
    # Act: Process book with fuzzy binder name
    # Assert: Log contains skipped match info
```

**Step 2: Replace duplicate validation code with:**
```python
result = validate_and_associate_entities(db, book, parsed)
if result.has_errors:
    raise ValueError(_format_validation_errors(result))

if result.binder.was_skipped:
    logger.info(f"Skipped binder: fuzzy match '{result.binder.skipped_match.name}'")
if result.publisher.was_skipped:
    logger.info(f"Skipped publisher: fuzzy match '{result.publisher.skipped_match.name}'")
```

**Step 3: Commit**
```bash
git commit -m "refactor: Use shared validation in worker.py (#1014, #1013)"
```

---

## Verification

After all tasks:
```bash
cd backend
poetry run pytest tests/test_entity_validation.py tests/test_books.py tests/test_worker.py -v
poetry run ruff check .
poetry run ruff format --check .
```

## Closes

- #1013 - Log mode now surfaces skipped matches via Warning header / logs
- #1014 - Duplicate logic extracted to `validate_and_associate_entities()`
- #1015 - Consistent `ValidationResult` type, caller decides error handling
