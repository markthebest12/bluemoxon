# Entity Validation Phases 2-4 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add entity validation to prevent duplicate creation via API endpoints

**Architecture:** Extend Phase 1 fuzzy matching infrastructure to validate entity creation at API level. Entity endpoints get `?force=true` bypass. Book endpoints require ID references for existing entities.

**Tech Stack:** FastAPI, Pydantic, rapidfuzz (Phase 1), pytest

**Issues:** #967 (Phase 2), #968 (Phase 3), #969 (Phase 4)

---

## Task 1: Add validation helper function

**Files:**

- Create: `backend/app/services/entity_validation.py`
- Test: `backend/tests/services/test_entity_validation_service.py`

**Step 1: Write the failing test**

```python
# backend/tests/services/test_entity_validation_service.py
"""Tests for entity validation service."""

import pytest
from unittest.mock import MagicMock, patch

from app.services.entity_validation import validate_entity_creation
from app.services.entity_matching import EntityMatch


class TestValidateEntityCreation:
    """Test validate_entity_creation function."""

    def test_returns_none_when_no_matches(self):
        """No matches means validation passes."""
        db = MagicMock()
        with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[]):
            result = validate_entity_creation(db, "publisher", "Totally New Press")
        assert result is None

    def test_returns_error_when_similar_exists(self):
        """Similar match returns EntityValidationError."""
        db = MagicMock()
        match = EntityMatch(
            entity_id=5,
            name="Macmillan and Co.",
            tier="TIER_1",
            confidence=0.94,
            book_count=12,
        )
        with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[match]):
            result = validate_entity_creation(db, "publisher", "Macmilan")

        assert result is not None
        assert result.error == "similar_entity_exists"
        assert result.entity_type == "publisher"
        assert result.input == "Macmilan"
        assert len(result.suggestions) == 1
        assert result.suggestions[0].id == 5
        assert result.suggestions[0].match == 0.94

    def test_returns_none_when_exact_match_only(self):
        """Exact match (1.0 confidence) should still return error."""
        db = MagicMock()
        match = EntityMatch(
            entity_id=5,
            name="Macmillan and Co.",
            tier="TIER_1",
            confidence=1.0,
            book_count=12,
        )
        with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[match]):
            result = validate_entity_creation(db, "publisher", "Macmillan and Co.")

        # Even exact match should return error - entity already exists
        assert result is not None
        assert result.error == "similar_entity_exists"
```

**Step 2: Run test to verify it fails**

Run: `poetry run pytest backend/tests/services/test_entity_validation_service.py -v`
Expected: FAIL with "No module named 'app.services.entity_validation'"

**Step 3: Write minimal implementation**

```python
# backend/app/services/entity_validation.py
"""Entity validation service for preventing duplicate creation."""

from sqlalchemy.orm import Session

from app.schemas.entity_validation import EntitySuggestion, EntityValidationError
from app.services.entity_matching import EntityType, fuzzy_match_entity


def validate_entity_creation(
    db: Session,
    entity_type: EntityType,
    name: str,
    threshold: float = 0.80,
) -> EntityValidationError | None:
    """Validate that creating an entity won't create a duplicate.

    Args:
        db: Database session.
        entity_type: Type of entity ("publisher", "binder", "author").
        name: Name of entity to create.
        threshold: Fuzzy match threshold (default 0.80).

    Returns:
        EntityValidationError if similar entity exists, None if creation is safe.
    """
    matches = fuzzy_match_entity(db, entity_type, name, threshold=threshold)

    if not matches:
        return None

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

    return EntityValidationError(
        error="similar_entity_exists",
        entity_type=entity_type,
        input=name,
        suggestions=suggestions,
        resolution=f"Use existing {entity_type} ID, or add force=true to create anyway",
    )
```

**Step 4: Run test to verify it passes**

Run: `poetry run pytest backend/tests/services/test_entity_validation_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/services/entity_validation.py backend/tests/services/test_entity_validation_service.py
git commit -m "feat(#967): add entity validation helper service"
```

---

## Task 2: Add validation to POST /publishers

**Files:**

- Modify: `backend/app/api/v1/publishers.py:68-97`
- Test: `backend/tests/api/v1/test_publishers.py`

**Step 1: Write the failing test**

```python
# Add to backend/tests/api/v1/test_publishers.py

class TestPublisherValidation:
    """Test entity validation on publisher creation."""

    def test_create_publisher_returns_409_when_similar_exists(self, client, db_session, editor_auth):
        """Creating publisher with similar name returns 409 with suggestions."""
        # Create existing publisher
        from app.models import Publisher
        existing = Publisher(name="Macmillan and Co.", tier="TIER_1")
        db_session.add(existing)
        db_session.commit()
        db_session.refresh(existing)

        # Try to create similar
        response = client.post(
            "/api/v1/publishers",
            json={"name": "Macmilan", "tier": "TIER_2"},
            headers=editor_auth,
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"] == "similar_entity_exists"
        assert data["entity_type"] == "publisher"
        assert data["input"] == "Macmilan"
        assert len(data["suggestions"]) >= 1
        assert data["suggestions"][0]["id"] == existing.id

    def test_create_publisher_with_force_bypasses_validation(self, client, db_session, editor_auth):
        """force=true allows creation despite similar entity."""
        from app.models import Publisher
        existing = Publisher(name="Macmillan and Co.", tier="TIER_1")
        db_session.add(existing)
        db_session.commit()

        response = client.post(
            "/api/v1/publishers?force=true",
            json={"name": "Macmilan", "tier": "TIER_2"},
            headers=editor_auth,
        )

        assert response.status_code == 201
        assert response.json()["name"] == "Macmilan"

    def test_create_publisher_succeeds_when_no_similar(self, client, db_session, editor_auth):
        """Creating unique publisher succeeds."""
        response = client.post(
            "/api/v1/publishers",
            json={"name": "Totally Unique Press", "tier": "TIER_3"},
            headers=editor_auth,
        )

        assert response.status_code == 201
        assert response.json()["name"] == "Totally Unique Press"
```

**Step 2: Run test to verify it fails**

Run: `poetry run pytest backend/tests/api/v1/test_publishers.py::TestPublisherValidation -v`
Expected: FAIL (409 not returned, gets 201 or 400)

**Step 3: Write minimal implementation**

Modify `backend/app/api/v1/publishers.py`:

```python
# Add import at top
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.services.entity_validation import validate_entity_creation

# Modify create_publisher function (lines 68-97)
@router.post("", response_model=PublisherResponse, status_code=201)
def create_publisher(
    publisher_data: PublisherCreate,
    force: bool = Query(default=False, description="Bypass similar entity validation"),
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Create a new publisher. Requires editor role."""
    # Validate for similar entities unless force=true
    if not force:
        validation_error = validate_entity_creation(db, "publisher", publisher_data.name)
        if validation_error:
            return JSONResponse(
                status_code=409,
                content=validation_error.model_dump(),
            )

    # Check for existing publisher with same name (exact match)
    existing = db.query(Publisher).filter(Publisher.name == publisher_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Publisher with this name already exists")

    publisher = Publisher(**publisher_data.model_dump())
    db.add(publisher)
    db.commit()
    db.refresh(publisher)

    # Invalidate cache since new publisher was created
    invalidate_publisher_cache()
    invalidate_entity_cache("publisher")

    return PublisherResponse(
        id=publisher.id,
        name=publisher.name,
        tier=publisher.tier,
        founded_year=publisher.founded_year,
        description=publisher.description,
        preferred=publisher.preferred,
        book_count=len(publisher.books),
    )
```

**Step 4: Run test to verify it passes**

Run: `poetry run pytest backend/tests/api/v1/test_publishers.py::TestPublisherValidation -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/api/v1/publishers.py backend/tests/api/v1/test_publishers.py
git commit -m "feat(#967): add validation to POST /publishers with force bypass"
```

---

## Task 3: Add validation to POST /binders

**Files:**

- Modify: `backend/app/api/v1/binders.py:67-93`
- Test: `backend/tests/api/v1/test_binders.py`

**Step 1: Write the failing test**

```python
# Add to backend/tests/api/v1/test_binders.py

class TestBinderValidation:
    """Test entity validation on binder creation."""

    def test_create_binder_returns_409_when_similar_exists(self, client, db_session, editor_auth):
        """Creating binder with similar name returns 409 with suggestions."""
        from app.models import Binder
        existing = Binder(name="Sangorski & Sutcliffe", tier="TIER_1")
        db_session.add(existing)
        db_session.commit()
        db_session.refresh(existing)

        response = client.post(
            "/api/v1/binders",
            json={"name": "Sangorski Sutcliffe", "tier": "TIER_1"},
            headers=editor_auth,
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"] == "similar_entity_exists"
        assert data["entity_type"] == "binder"
        assert len(data["suggestions"]) >= 1

    def test_create_binder_with_force_bypasses_validation(self, client, db_session, editor_auth):
        """force=true allows creation despite similar entity."""
        from app.models import Binder
        existing = Binder(name="Sangorski & Sutcliffe", tier="TIER_1")
        db_session.add(existing)
        db_session.commit()

        response = client.post(
            "/api/v1/binders?force=true",
            json={"name": "Sangorski Sutcliffe", "tier": "TIER_1"},
            headers=editor_auth,
        )

        assert response.status_code == 201

    def test_create_binder_succeeds_when_no_similar(self, client, db_session, editor_auth):
        """Creating unique binder succeeds."""
        response = client.post(
            "/api/v1/binders",
            json={"name": "Unique Bindery", "tier": "TIER_3"},
            headers=editor_auth,
        )

        assert response.status_code == 201
```

**Step 2: Run test to verify it fails**

Run: `poetry run pytest backend/tests/api/v1/test_binders.py::TestBinderValidation -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Modify `backend/app/api/v1/binders.py`:

```python
# Add imports at top
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.services.entity_validation import validate_entity_creation

# Modify create_binder function
@router.post("", response_model=BinderResponse, status_code=201)
def create_binder(
    binder_data: BinderCreate,
    force: bool = Query(default=False, description="Bypass similar entity validation"),
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Create a new binder. Requires editor role."""
    # Validate for similar entities unless force=true
    if not force:
        validation_error = validate_entity_creation(db, "binder", binder_data.name)
        if validation_error:
            return JSONResponse(
                status_code=409,
                content=validation_error.model_dump(),
            )

    # Check for existing binder with same name
    existing = db.query(Binder).filter(Binder.name == binder_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Binder with this name already exists")

    binder = Binder(**binder_data.model_dump())
    db.add(binder)
    db.commit()
    db.refresh(binder)
    invalidate_entity_cache("binder")

    return BinderResponse(
        id=binder.id,
        name=binder.name,
        tier=binder.tier,
        full_name=binder.full_name,
        authentication_markers=binder.authentication_markers,
        preferred=binder.preferred,
        book_count=len(binder.books),
    )
```

**Step 4: Run test to verify it passes**

Run: `poetry run pytest backend/tests/api/v1/test_binders.py::TestBinderValidation -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/api/v1/binders.py backend/tests/api/v1/test_binders.py
git commit -m "feat(#967): add validation to POST /binders with force bypass"
```

---

## Task 4: Add validation to POST /authors

**Files:**

- Modify: `backend/app/api/v1/authors.py:76-105`
- Test: `backend/tests/api/v1/test_authors.py`

**Step 1: Write the failing test**

```python
# Add to backend/tests/api/v1/test_authors.py

class TestAuthorValidation:
    """Test entity validation on author creation."""

    def test_create_author_returns_409_when_similar_exists(self, client, db_session, editor_auth):
        """Creating author with similar name returns 409 with suggestions."""
        from app.models import Author
        existing = Author(name="Charles Dickens", tier="TIER_1")
        db_session.add(existing)
        db_session.commit()
        db_session.refresh(existing)

        # Try with reversed name order
        response = client.post(
            "/api/v1/authors",
            json={"name": "Dickens, Charles"},
            headers=editor_auth,
        )

        assert response.status_code == 409
        data = response.json()
        assert data["error"] == "similar_entity_exists"
        assert data["entity_type"] == "author"
        assert len(data["suggestions"]) >= 1

    def test_create_author_with_force_bypasses_validation(self, client, db_session, editor_auth):
        """force=true allows creation despite similar entity."""
        from app.models import Author
        existing = Author(name="Charles Dickens", tier="TIER_1")
        db_session.add(existing)
        db_session.commit()

        response = client.post(
            "/api/v1/authors?force=true",
            json={"name": "Dickens, Charles"},
            headers=editor_auth,
        )

        assert response.status_code == 201

    def test_create_author_succeeds_when_no_similar(self, client, db_session, editor_auth):
        """Creating unique author succeeds."""
        response = client.post(
            "/api/v1/authors",
            json={"name": "Totally Unique Author"},
            headers=editor_auth,
        )

        assert response.status_code == 201
```

**Step 2: Run test to verify it fails**

Run: `poetry run pytest backend/tests/api/v1/test_authors.py::TestAuthorValidation -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Modify `backend/app/api/v1/authors.py`:

```python
# Add imports at top
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.services.entity_validation import validate_entity_creation

# Modify create_author function
@router.post("", response_model=AuthorResponse, status_code=201)
def create_author(
    author_data: AuthorCreate,
    force: bool = Query(default=False, description="Bypass similar entity validation"),
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Create a new author. Requires editor role."""
    # Validate for similar entities unless force=true
    # Use lower threshold for authors due to name format variations
    if not force:
        validation_error = validate_entity_creation(db, "author", author_data.name, threshold=0.75)
        if validation_error:
            return JSONResponse(
                status_code=409,
                content=validation_error.model_dump(),
            )

    # Check for existing author with same name
    existing = db.query(Author).filter(Author.name == author_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Author with this name already exists")

    author = Author(**author_data.model_dump())
    db.add(author)
    db.commit()
    db.refresh(author)
    invalidate_entity_cache("author")

    return AuthorResponse(
        id=author.id,
        name=author.name,
        birth_year=author.birth_year,
        death_year=author.death_year,
        era=author.era,
        first_acquired_date=author.first_acquired_date,
        priority_score=author.priority_score,
        tier=author.tier,
        preferred=author.preferred,
        book_count=len(author.books),
    )
```

**Step 4: Run test to verify it passes**

Run: `poetry run pytest backend/tests/api/v1/test_authors.py::TestAuthorValidation -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/api/v1/authors.py backend/tests/api/v1/test_authors.py
git commit -m "feat(#967): add validation to POST /authors with force bypass"
```

---

## Task 5: Run full test suite and close Phase 2

**Step 1: Run all entity validation tests**

Run: `poetry run pytest backend/tests/ -k "validation" -v`
Expected: All tests pass

**Step 2: Run full backend test suite**

Run: `poetry run pytest backend/`
Expected: All tests pass (should be 1363+ tests)

**Step 3: Commit and create PR**

```bash
git push -u origin feat/955-entity-validation-phase2
gh pr create --base staging --title "feat(#967): Add entity validation to creation endpoints (Phase 2)" --body "## Summary
- Add fuzzy matching validation to POST /publishers, /binders, /authors
- Return 409 Conflict with suggestions when similar entity exists
- Add ?force=true query param to bypass validation

Closes #967

## Test Plan
- [x] Unit tests for validation service
- [x] Integration tests for each endpoint
- [x] Force bypass tests
- [x] Full test suite passes"
```

---

## Task 6: Add validation mode config (Phase 4)

**Files:**

- Modify: `backend/app/config.py`
- Modify: `backend/app/services/entity_validation.py`
- Test: `backend/tests/services/test_entity_validation_service.py`

**Step 1: Write the failing test**

```python
# Add to backend/tests/services/test_entity_validation_service.py

class TestValidationMode:
    """Test log-only vs enforce validation modes."""

    def test_log_mode_returns_none_but_logs(self, caplog):
        """In log mode, validation passes but logs warning."""
        import logging
        from app.services.entity_validation import validate_entity_creation
        from unittest.mock import MagicMock, patch

        db = MagicMock()
        match = EntityMatch(
            entity_id=5,
            name="Macmillan and Co.",
            tier="TIER_1",
            confidence=0.94,
            book_count=12,
        )

        with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[match]):
            with patch("app.services.entity_validation.get_settings") as mock_settings:
                mock_settings.return_value.entity_validation_mode = "log"
                with caplog.at_level(logging.WARNING):
                    result = validate_entity_creation(db, "publisher", "Macmilan")

        assert result is None  # Log mode returns None (allows creation)
        assert "would reject" in caplog.text
        assert "Macmilan" in caplog.text
```

**Step 2: Run test to verify it fails**

Run: `poetry run pytest backend/tests/services/test_entity_validation_service.py::TestValidationMode -v`
Expected: FAIL

**Step 3: Add config settings**

Modify `backend/app/config.py`:

```python
# Add to Settings class
entity_validation_mode: str = "enforce"  # "log" or "enforce"
entity_match_threshold_publisher: float = 0.80
entity_match_threshold_binder: float = 0.80
entity_match_threshold_author: float = 0.75
```

**Step 4: Update validation service**

Modify `backend/app/services/entity_validation.py`:

```python
"""Entity validation service for preventing duplicate creation."""

import logging
from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas.entity_validation import EntitySuggestion, EntityValidationError
from app.services.entity_matching import EntityType, fuzzy_match_entity

logger = logging.getLogger(__name__)


def validate_entity_creation(
    db: Session,
    entity_type: EntityType,
    name: str,
    threshold: float | None = None,
) -> EntityValidationError | None:
    """Validate that creating an entity won't create a duplicate.

    Args:
        db: Database session.
        entity_type: Type of entity ("publisher", "binder", "author").
        name: Name of entity to create.
        threshold: Fuzzy match threshold. If None, uses config value for entity type.

    Returns:
        EntityValidationError if similar entity exists and mode is "enforce".
        None if creation is safe or mode is "log".
    """
    settings = get_settings()

    # Get threshold from config if not provided
    if threshold is None:
        threshold = getattr(
            settings,
            f"entity_match_threshold_{entity_type}",
            0.80,
        )

    matches = fuzzy_match_entity(db, entity_type, name, threshold=threshold)

    if not matches:
        return None

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

    # In log mode, log warning but allow creation
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
        return None

    return EntityValidationError(
        error="similar_entity_exists",
        entity_type=entity_type,
        input=name,
        suggestions=suggestions,
        resolution=f"Use existing {entity_type} ID, or add force=true to create anyway",
    )
```

**Step 5: Run test to verify it passes**

Run: `poetry run pytest backend/tests/services/test_entity_validation_service.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/app/config.py backend/app/services/entity_validation.py backend/tests/services/test_entity_validation_service.py
git commit -m "feat(#969): add entity validation mode config (log vs enforce)"
```

---

## Task 7: Add Terraform environment variables

**Files:**

- Modify: `infra/terraform/modules/lambda/variables.tf`
- Modify: `infra/terraform/modules/lambda/main.tf`
- Modify: `infra/terraform/envs/staging.tfvars`
- Modify: `infra/terraform/envs/production.tfvars`

**Step 1: Add variables**

Add to `infra/terraform/modules/lambda/variables.tf`:

```hcl
variable "entity_validation_mode" {
  description = "Entity validation mode: 'log' or 'enforce'"
  type        = string
  default     = "enforce"
}

variable "entity_match_threshold_publisher" {
  description = "Fuzzy match threshold for publishers (0.0-1.0)"
  type        = number
  default     = 0.80
}

variable "entity_match_threshold_binder" {
  description = "Fuzzy match threshold for binders (0.0-1.0)"
  type        = number
  default     = 0.80
}

variable "entity_match_threshold_author" {
  description = "Fuzzy match threshold for authors (0.0-1.0)"
  type        = number
  default     = 0.75
}
```

**Step 2: Add to Lambda environment**

Add to Lambda environment block in `infra/terraform/modules/lambda/main.tf`:

```hcl
ENTITY_VALIDATION_MODE             = var.entity_validation_mode
ENTITY_MATCH_THRESHOLD_PUBLISHER   = tostring(var.entity_match_threshold_publisher)
ENTITY_MATCH_THRESHOLD_BINDER      = tostring(var.entity_match_threshold_binder)
ENTITY_MATCH_THRESHOLD_AUTHOR      = tostring(var.entity_match_threshold_author)
```

**Step 3: Set staging values (log mode for testing)**

Add to `infra/terraform/envs/staging.tfvars`:

```hcl
entity_validation_mode           = "log"
entity_match_threshold_publisher = 0.80
entity_match_threshold_binder    = 0.80
entity_match_threshold_author    = 0.75
```

**Step 4: Set production values (enforce mode)**

Add to `infra/terraform/envs/production.tfvars`:

```hcl
entity_validation_mode           = "enforce"
entity_match_threshold_publisher = 0.80
entity_match_threshold_binder    = 0.80
entity_match_threshold_author    = 0.75
```

**Step 5: Commit**

```bash
git add infra/terraform/
git commit -m "feat(#969): add entity validation env vars to Terraform"
```

---

## Task 8: Final integration test and deployment

**Step 1: Run full test suite**

Run: `poetry run pytest backend/`
Expected: All tests pass

**Step 2: Run linting**

Run: `poetry run ruff check backend/`
Run: `poetry run ruff format --check backend/`
Expected: No errors

**Step 3: Create final PR**

```bash
git push -u origin feat/955-entity-validation-phases-2-4
gh pr create --base staging --title "feat: Entity validation Phases 2-4 (#967, #968, #969)" --body "## Summary
Implements entity validation to prevent duplicate creation:

**Phase 2 (#967):**
- POST /publishers returns 409 if similar exists
- POST /binders returns 409 if similar exists
- POST /authors returns 409 if similar exists
- All support ?force=true bypass

**Phase 4 (#969):**
- Add ENTITY_VALIDATION_MODE config (log vs enforce)
- Add per-entity-type threshold config
- Staging starts in 'log' mode for monitoring

**Phase 3 (#968):**
Deferred - book endpoints use get_or_create which needs larger refactor.

## Test Plan
- [x] Unit tests for validation service
- [x] Integration tests for each endpoint
- [x] Force bypass tests
- [x] Log mode tests
- [x] Full test suite passes

Closes #967, #969"
```

---

## Notes

**Phase 3 (Book Endpoints) Deferred:**
The book endpoints use `get_or_create_publisher()` and `get_or_create_binder()` which automatically create entities. Proper validation requires changing the book creation flow to:

1. Require entity IDs upfront, OR
2. Return validation errors before auto-creation

This is a larger refactor that should be its own PR after Phases 2 and 4 are validated in production.

**Rollout Plan:**

1. Deploy with `ENTITY_VALIDATION_MODE=log` in staging
2. Monitor CloudWatch logs for "would reject" warnings
3. Tune thresholds based on false positive rate
4. Enable `ENTITY_VALIDATION_MODE=enforce` in staging
5. Validate behavior, then enable in production

---

*Plan created: 2026-01-09*
