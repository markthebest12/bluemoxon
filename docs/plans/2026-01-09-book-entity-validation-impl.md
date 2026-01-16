# Book Entity Validation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add entity validation to book endpoints to prevent duplicate entity proliferation when uploading analysis.

**Architecture:** New `validate_entity_for_book()` function checks entity names before association. Returns entity ID on exact match, 409 error on fuzzy match (80%+), 400 error on unknown. Applied to `update_book_analysis()` endpoint and `worker.py`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, pytest, rapidfuzz

---

## Task 1: Add `validate_entity_for_book()` function

**Files:**

- Modify: `backend/app/services/entity_validation.py:75` (end of file)
- Test: `backend/tests/services/test_entity_validation_service.py`

### Step 1: Write the failing tests

Add to `backend/tests/services/test_entity_validation_service.py`:

```python
class TestValidateEntityForBook:
    """Test validate_entity_for_book function for book endpoint validation."""

    def test_exact_match_returns_entity_id(self):
        """Exact match in DB returns entity ID (not error)."""
        from app.services.entity_validation import validate_entity_for_book

        db = MagicMock()
        # Mock exact match query returning a publisher
        mock_publisher = MagicMock()
        mock_publisher.id = 5
        db.query.return_value.filter.return_value.first.return_value = mock_publisher

        result = validate_entity_for_book(db, "publisher", "Macmillan and Co.")

        assert result == 5  # Returns entity ID

    def test_fuzzy_match_returns_409_error(self):
        """Fuzzy match (80%+) returns EntityValidationError with similar_entity_exists."""
        from app.services.entity_validation import validate_entity_for_book

        db = MagicMock()
        # Mock no exact match
        db.query.return_value.filter.return_value.first.return_value = None

        match = EntityMatch(
            entity_id=5,
            name="Macmillan and Co.",
            tier="TIER_1",
            confidence=0.88,
            book_count=12,
        )
        with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[match]):
            with patch("app.services.entity_validation.get_settings") as mock_settings:
                mock_settings.return_value.entity_validation_mode = "enforce"
                mock_settings.return_value.entity_match_threshold_publisher = 0.80
                result = validate_entity_for_book(db, "publisher", "Macmilan")

        assert isinstance(result, EntityValidationError)
        assert result.error == "similar_entity_exists"
        assert result.entity_type == "publisher"
        assert len(result.suggestions) == 1
        assert result.suggestions[0].id == 5

    def test_no_match_returns_400_error(self):
        """No match at all returns EntityValidationError with unknown_entity."""
        from app.services.entity_validation import validate_entity_for_book

        db = MagicMock()
        # Mock no exact match
        db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[]):
            with patch("app.services.entity_validation.get_settings") as mock_settings:
                mock_settings.return_value.entity_validation_mode = "enforce"
                mock_settings.return_value.entity_match_threshold_publisher = 0.80
                result = validate_entity_for_book(db, "publisher", "Totally New Press")

        assert isinstance(result, EntityValidationError)
        assert result.error == "unknown_entity"
        assert result.entity_type == "publisher"
        assert result.suggestions is None
        assert "Create via POST /publishers" in result.resolution

    def test_empty_name_returns_none(self):
        """Empty or None name returns None (skip validation)."""
        from app.services.entity_validation import validate_entity_for_book

        db = MagicMock()

        assert validate_entity_for_book(db, "publisher", "") is None
        assert validate_entity_for_book(db, "publisher", "   ") is None
        assert validate_entity_for_book(db, "binder", None) is None

    def test_log_mode_returns_entity_id_on_fuzzy_match(self, caplog):
        """In log mode, fuzzy match logs warning but returns entity ID."""
        import logging

        from app.services.entity_validation import validate_entity_for_book

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        match = EntityMatch(
            entity_id=5,
            name="Macmillan and Co.",
            tier="TIER_1",
            confidence=0.88,
            book_count=12,
        )
        with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[match]):
            with patch("app.services.entity_validation.get_settings") as mock_settings:
                mock_settings.return_value.entity_validation_mode = "log"
                mock_settings.return_value.entity_match_threshold_publisher = 0.80
                with caplog.at_level(logging.WARNING):
                    result = validate_entity_for_book(db, "publisher", "Macmilan")

        # Log mode returns top match ID instead of error
        assert result == 5
        assert "would reject" in caplog.text

    def test_binder_validation(self):
        """Binder validation works with binder-specific normalization."""
        from app.services.entity_validation import validate_entity_for_book

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        match = EntityMatch(
            entity_id=3,
            name="Bayntun",
            tier="TIER_1",
            confidence=0.85,
            book_count=5,
        )
        with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[match]):
            with patch("app.services.entity_validation.get_settings") as mock_settings:
                mock_settings.return_value.entity_validation_mode = "enforce"
                mock_settings.return_value.entity_match_threshold_binder = 0.80
                result = validate_entity_for_book(db, "binder", "Bayntun (of Bath)")

        assert isinstance(result, EntityValidationError)
        assert result.error == "similar_entity_exists"
        assert result.entity_type == "binder"
```

### Step 2: Run tests to verify they fail

Run: `poetry run pytest backend/tests/services/test_entity_validation_service.py::TestValidateEntityForBook -v`
Expected: FAIL with "cannot import name 'validate_entity_for_book'"

### Step 3: Implement `validate_entity_for_book()`

Add to `backend/app/services/entity_validation.py` after line 75:

```python
def validate_entity_for_book(
    db: Session,
    entity_type: EntityType,
    name: str | None,
    threshold: float | None = None,
) -> int | EntityValidationError | None:
    """Validate entity name before associating with a book.

    Unlike validate_entity_creation(), this function is for book endpoints
    and returns the entity ID on exact match (allowing direct association).

    Args:
        db: Database session.
        entity_type: Type of entity ("publisher", "binder", "author").
        name: Name of entity to validate.
        threshold: Fuzzy match threshold. If None, uses config value for entity type.

    Returns:
        int: Entity ID if exact match found (safe to associate).
        EntityValidationError: If similar match (409) or unknown (400).
        None: If name is empty/None (skip validation).
    """
    # Handle empty input
    if not name or not name.strip():
        return None

    settings = get_settings()

    # Get threshold from config if not provided
    if threshold is None:
        threshold_attr = f"entity_match_threshold_{entity_type}"
        threshold = getattr(settings, threshold_attr, 0.80)

    # Apply type-specific normalization
    from app.services.entity_matching import _normalize_for_entity_type

    normalized_name = _normalize_for_entity_type(name, entity_type)

    # Check for exact match first
    entity = _get_entity_by_name(db, entity_type, normalized_name)
    if entity:
        return entity.id

    # No exact match - check for fuzzy matches
    matches = fuzzy_match_entity(db, entity_type, name, threshold=threshold)

    if matches:
        # Similar entity exists - return 409 error (or log and return best match)
        suggestions = [
            EntitySuggestion(
                id=m.entity_id,
                name=m.name,
                tier=m.tier,
                match=m.confidence,
                book_count=m.book_count,
            )
            for m in matches
        ]

        if settings.entity_validation_mode == "log":
            top_match = matches[0]
            logger.warning(
                "Entity validation would reject: %s '%s' matches '%s' at %.0f%% (book_count: %d)",
                entity_type,
                name,
                top_match.name,
                top_match.confidence * 100,
                top_match.book_count,
            )
            return top_match.entity_id  # Return best match ID in log mode

        return EntityValidationError(
            error="similar_entity_exists",
            entity_type=entity_type,
            input=name,
            suggestions=suggestions,
            resolution=f"Use existing {entity_type} ID, or create new via POST /{entity_type}s?force=true",
        )

    # No match at all - return 400 error (or log and return None)
    if settings.entity_validation_mode == "log":
        logger.warning(
            "Entity validation would reject: %s '%s' not found (no matches)",
            entity_type,
            name,
        )
        return None  # Allow caller to decide what to do

    return EntityValidationError(
        error="unknown_entity",
        entity_type=entity_type,
        input=name,
        suggestions=None,
        resolution=f"Create via POST /{entity_type}s first, then retry analysis upload",
    )


def _get_entity_by_name(db: Session, entity_type: EntityType, name: str):
    """Get entity by exact normalized name match.

    Args:
        db: Database session.
        entity_type: Type of entity.
        name: Normalized entity name.

    Returns:
        Entity object or None.
    """
    from sqlalchemy import func

    if entity_type == "publisher":
        from app.models.publisher import Publisher

        return db.query(Publisher).filter(func.lower(Publisher.name) == name.lower()).first()
    elif entity_type == "binder":
        from app.models.binder import Binder

        return db.query(Binder).filter(func.lower(Binder.name) == name.lower()).first()
    elif entity_type == "author":
        from app.models.author import Author

        return db.query(Author).filter(func.lower(Author.name) == name.lower()).first()
    else:
        raise ValueError(f"Unknown entity type: {entity_type}")
```

### Step 4: Run tests to verify they pass

Run: `poetry run pytest backend/tests/services/test_entity_validation_service.py::TestValidateEntityForBook -v`
Expected: PASS (all 6 tests)

### Step 5: Commit

```bash
git add backend/app/services/entity_validation.py backend/tests/services/test_entity_validation_service.py
git commit -m "feat: add validate_entity_for_book() for book endpoint validation

Part of #968 - Phase 3 entity validation for book endpoints.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Update `update_book_analysis()` endpoint

**Files:**

- Modify: `backend/app/api/v1/books.py:1428-1442`
- Test: `backend/tests/api/v1/test_books.py`

### Step 1: Write the failing tests

Add to `backend/tests/api/v1/test_books.py`:

```python
class TestAnalysisEntityValidation:
    """Test entity validation in analysis upload endpoint."""

    def test_analysis_with_similar_binder_returns_409(self, client, db_session, test_book):
        """Analysis with fuzzy-matching binder name returns 409 Conflict."""
        from app.models.binder import Binder

        # Create existing binder
        binder = Binder(name="Bayntun", tier="TIER_1")
        db_session.add(binder)
        db_session.commit()

        # Analysis markdown with similar binder name
        analysis = """# Analysis
## Binder Identification
**Binder:** Bayntun (of Bath)
**Confidence:** High
"""
        response = client.put(
            f"/api/v1/books/{test_book.id}/analysis",
            content=analysis,
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"] == "similar_entity_exists"
        assert data["entity_type"] == "binder"
        assert len(data["suggestions"]) >= 1
        assert data["suggestions"][0]["name"] == "Bayntun"

    def test_analysis_with_unknown_publisher_returns_400(self, client, db_session, test_book):
        """Analysis with unknown publisher name returns 400 Bad Request."""
        # Analysis markdown with unknown publisher
        analysis = """# Analysis
## Publisher Identification
**Publisher:** Totally Unknown Press Ltd
"""
        response = client.put(
            f"/api/v1/books/{test_book.id}/analysis",
            content=analysis,
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "unknown_entity"
        assert data["entity_type"] == "publisher"
        assert "Create via POST /publishers" in data["resolution"]

    def test_analysis_with_exact_match_binder_succeeds(self, client, db_session, test_book):
        """Analysis with exact binder name match succeeds."""
        from app.models.binder import Binder

        # Create existing binder
        binder = Binder(name="Sangorski & Sutcliffe", tier="TIER_1")
        db_session.add(binder)
        db_session.commit()

        # Analysis markdown with exact binder name
        analysis = """# Analysis
## Binder Identification
**Binder:** Sangorski & Sutcliffe
"""
        response = client.put(
            f"/api/v1/books/{test_book.id}/analysis",
            content=analysis,
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["binder_updated"] is True

        # Verify binder was associated
        db_session.refresh(test_book)
        assert test_book.binder_id == binder.id
```

### Step 2: Run tests to verify they fail

Run: `poetry run pytest backend/tests/api/v1/test_books.py::TestAnalysisEntityValidation -v`
Expected: FAIL (tests fail because validation not implemented yet)

### Step 3: Update `update_book_analysis()` endpoint

Modify `backend/app/api/v1/books.py` lines 1428-1442:

Replace:

```python
    # Extract binder identification and associate with book
    binder_updated = False
    if parsed.binder_identification:
        binder = get_or_create_binder(db, parsed.binder_identification)
        if binder and book.binder_id != binder.id:
            book.binder_id = binder.id
            binder_updated = True

    # Extract publisher identification and associate with book
    publisher_updated = False
    if parsed.publisher_identification and parsed.publisher_identification.get("name"):
        publisher = get_or_create_publisher(db, parsed.publisher_identification["name"])
        if publisher and book.publisher_id != publisher.id:
            book.publisher_id = publisher.id
            publisher_updated = True
```

With:

```python
    # Validate and associate binder
    binder_updated = False
    if parsed.binder_identification and parsed.binder_identification.get("name"):
        binder_name = parsed.binder_identification["name"]
        binder_result = validate_entity_for_book(db, "binder", binder_name)

        if isinstance(binder_result, EntityValidationError):
            status_code = 409 if binder_result.error == "similar_entity_exists" else 400
            raise HTTPException(status_code=status_code, detail=binder_result.model_dump())

        if binder_result and book.binder_id != binder_result:
            book.binder_id = binder_result
            binder_updated = True

    # Validate and associate publisher
    publisher_updated = False
    if parsed.publisher_identification and parsed.publisher_identification.get("name"):
        publisher_name = parsed.publisher_identification["name"]
        publisher_result = validate_entity_for_book(db, "publisher", publisher_name)

        if isinstance(publisher_result, EntityValidationError):
            status_code = 409 if publisher_result.error == "similar_entity_exists" else 400
            raise HTTPException(status_code=status_code, detail=publisher_result.model_dump())

        if publisher_result and book.publisher_id != publisher_result:
            book.publisher_id = publisher_result
            publisher_updated = True
```

Also add import at top of file:

```python
from app.services.entity_validation import validate_entity_for_book
from app.schemas.entity_validation import EntityValidationError
```

### Step 4: Run tests to verify they pass

Run: `poetry run pytest backend/tests/api/v1/test_books.py::TestAnalysisEntityValidation -v`
Expected: PASS (all 3 tests)

### Step 5: Commit

```bash
git add backend/app/api/v1/books.py backend/tests/api/v1/test_books.py
git commit -m "feat: add entity validation to update_book_analysis endpoint

Returns 409 Conflict for fuzzy matches (80%+), 400 Bad Request for unknown entities.
Part of #968 - Phase 3 entity validation for book endpoints.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Update `worker.py` for async analysis jobs

**Files:**

- Modify: `backend/app/worker.py:343-350`
- Test: `backend/tests/test_worker.py`

### Step 1: Write the failing tests

Add to `backend/tests/test_worker.py`:

```python
class TestWorkerEntityValidation:
    """Test entity validation in async analysis worker."""

    def test_worker_fails_job_on_similar_binder(self, db_session, test_book):
        """Worker fails job with descriptive error when binder fuzzy-matches."""
        from unittest.mock import MagicMock, patch

        from app.models.analysis_job import AnalysisJob
        from app.models.binder import Binder
        from app.worker import process_analysis_job

        # Create existing binder
        binder = Binder(name="Bayntun", tier="TIER_1")
        db_session.add(binder)

        # Create analysis job
        job = AnalysisJob(book_id=test_book.id, model="opus", status="pending")
        db_session.add(job)
        db_session.commit()

        # Mock Bedrock to return analysis with similar binder
        mock_analysis = """# Analysis
## Binder Identification
**Binder:** Bayntun (of Bath)
"""
        with patch("app.worker.invoke_bedrock", return_value=mock_analysis):
            with patch("app.worker.fetch_book_images_for_bedrock", return_value=[]):
                with patch("app.worker.fetch_source_url_content", return_value=None):
                    with patch("app.services.entity_validation.get_settings") as mock_settings:
                        mock_settings.return_value.entity_validation_mode = "enforce"
                        mock_settings.return_value.entity_match_threshold_binder = 0.80

                        # Process should raise exception
                        try:
                            process_analysis_job(str(job.id), test_book.id, "opus")
                        except Exception:
                            pass

        # Verify job was marked as failed
        db_session.refresh(job)
        assert job.status == "failed"
        assert "Entity validation failed" in job.error_message
        assert "Bayntun" in job.error_message
```

### Step 2: Run tests to verify they fail

Run: `poetry run pytest backend/tests/test_worker.py::TestWorkerEntityValidation -v`
Expected: FAIL (validation not implemented in worker yet)

### Step 3: Update `worker.py`

Modify `backend/app/worker.py` lines 343-350:

Replace:

```python
        # Extract binder identification and associate with book
        if parsed.binder_identification:
            binder = get_or_create_binder(db, parsed.binder_identification)
            if binder and book.binder_id != binder.id:
                logger.info(
                    f"Associating binder {binder.name} (tier={binder.tier}) with book {book_id}"
                )
                book.binder_id = binder.id
```

With:

```python
        # Validate and associate binder
        if parsed.binder_identification and parsed.binder_identification.get("name"):
            binder_name = parsed.binder_identification["name"]
            binder_result = validate_entity_for_book(db, "binder", binder_name)

            if isinstance(binder_result, EntityValidationError):
                # Fail job with descriptive error
                top_match = binder_result.suggestions[0] if binder_result.suggestions else None
                if top_match:
                    error_msg = (
                        f"Entity validation failed: binder '{binder_name}' matches existing "
                        f"'{top_match.name}' ({top_match.match:.0%}). "
                        f"Use existing ID or create new via POST /binders?force=true"
                    )
                else:
                    error_msg = (
                        f"Entity validation failed: binder '{binder_name}' not found. "
                        f"Create via POST /binders first."
                    )
                raise ValueError(error_msg)

            if binder_result and book.binder_id != binder_result:
                # binder_result is entity ID - fetch binder for logging
                binder = db.query(Binder).get(binder_result)
                if binder:
                    logger.info(
                        f"Associating binder {binder.name} (tier={binder.tier}) with book {book_id}"
                    )
                book.binder_id = binder_result
```

Also add imports at top of file:

```python
from app.services.entity_validation import validate_entity_for_book
from app.schemas.entity_validation import EntityValidationError
```

### Step 4: Run tests to verify they pass

Run: `poetry run pytest backend/tests/test_worker.py::TestWorkerEntityValidation -v`
Expected: PASS

### Step 5: Commit

```bash
git add backend/app/worker.py backend/tests/test_worker.py
git commit -m "feat: add entity validation to analysis worker

Fails jobs with descriptive error when entity validation fails.
Part of #968 - Phase 3 entity validation for book endpoints.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Run full test suite and verify

**Files:**

- All modified files

### Step 1: Run backend linting

Run: `poetry run ruff check backend/`
Expected: No errors

### Step 2: Run backend formatting check

Run: `poetry run ruff format --check backend/`
Expected: No errors

### Step 3: Run full test suite

Run: `poetry run pytest backend/tests/ -v --tb=short`
Expected: All tests pass

### Step 4: Create PR

```bash
git push -u origin feat/968-book-entity-validation
gh pr create --base staging --title "feat: Add entity validation to book endpoints (#968)" --body "$(cat <<'EOF'
## Summary
- Add `validate_entity_for_book()` function for book endpoint validation
- Update `update_book_analysis()` to validate before entity association
- Update `worker.py` to validate before entity association
- Returns 409 Conflict for fuzzy matches (80%+)
- Returns 400 Bad Request for unknown entities

## Test plan
- [x] Unit tests for `validate_entity_for_book()`
- [x] Integration tests for analysis endpoint
- [x] Worker validation tests
- [x] Full test suite passes
- [ ] Manual test in staging

Closes #968

## Related
- Part of #955 (Entity Proliferation Prevention)
- Depends on Phase 2 (#967) - already complete

---
Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

*Plan complete. Total: 4 tasks, ~20 steps.*
