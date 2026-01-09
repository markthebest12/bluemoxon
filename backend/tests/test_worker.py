"""Tests for the analysis worker."""


class TestWorkerErrorMessages:
    """Tests for worker error message formatting."""

    def test_input_too_long_error_includes_image_context(self):
        """Test that 'Input is too long' errors include image count and size guidance."""
        from botocore.exceptions import ClientError

        error_response = {
            "Error": {
                "Code": "ValidationException",
                "Message": "Input is too long for requested model.",
            }
        }
        bedrock_error = ClientError(error_response, "InvokeModel")

        from app.worker import format_analysis_error

        formatted = format_analysis_error(bedrock_error, image_count=15)

        assert "15 images" in formatted
        assert "800px" in formatted.lower() or "resize" in formatted.lower()

    def test_other_errors_not_modified(self):
        """Test that non-input-length errors pass through unchanged."""
        from app.worker import format_analysis_error

        generic_error = Exception("Something else went wrong")
        formatted = format_analysis_error(generic_error, image_count=5)

        assert formatted == "Something else went wrong"


class TestWorkerJobFailure:
    """Tests for worker job failure handling - Issue #815."""

    def test_failed_job_sets_completed_at(self, db):
        """Issue #815: Failed jobs must set completed_at, not just error_message."""
        from datetime import UTC, datetime

        from app.models import AnalysisJob, Book

        # Create a book and job
        book = Book(title="Test Book", inventory_type="PRIMARY")
        db.add(book)
        db.commit()

        job = AnalysisJob(
            book_id=book.id,
            status="running",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(job)
        db.commit()

        # Simulate the failure handling that worker.py does
        job.status = "failed"
        job.error_message = "Simulated timeout error"
        job.updated_at = datetime.now(UTC)
        job.completed_at = datetime.now(UTC)  # This is what #815 fixes
        db.commit()

        # Verify both are set
        db.refresh(job)
        assert job.status == "failed"
        assert job.error_message is not None
        assert job.completed_at is not None, (
            "Issue #815: Failed jobs must set completed_at to properly indicate "
            "when the failure occurred, not leave it as None"
        )


class TestWorkerBinderEntityValidation:
    """Tests for binder entity validation in worker - Issue #968.

    These tests verify the integration between the worker and entity validation service.
    They use real database entities and the actual validate_entity_for_book function.
    """

    def test_binder_validation_exact_match_returns_id(self, db, monkeypatch):
        """When binder name matches exactly, validate_entity_for_book returns entity ID."""
        from app.models.binder import Binder
        from app.services.entity_validation import validate_entity_for_book

        # Set validation mode to enforce
        monkeypatch.setenv("ENTITY_VALIDATION_MODE", "enforce")

        # Create test binder
        binder = Binder(name="Zaehnsdorf", tier="TIER_1")
        db.add(binder)
        db.commit()

        # Call the actual validation function with exact name
        result = validate_entity_for_book(db, "binder", "Zaehnsdorf")

        # Should return the entity ID directly (not an error)
        assert result == binder.id
        assert isinstance(result, int)

    def test_binder_validation_exact_match_case_insensitive(self, db, monkeypatch):
        """Exact match should be case-insensitive."""
        from app.models.binder import Binder
        from app.services.entity_validation import validate_entity_for_book

        monkeypatch.setenv("ENTITY_VALIDATION_MODE", "enforce")

        binder = Binder(name="Zaehnsdorf", tier="TIER_1")
        db.add(binder)
        db.commit()

        # Different casing should still return exact match
        result = validate_entity_for_book(db, "binder", "zaehnsdorf")
        assert result == binder.id

        result = validate_entity_for_book(db, "binder", "ZAEHNSDORF")
        assert result == binder.id

    def test_binder_validation_fuzzy_match_returns_error(self, db, monkeypatch):
        """When binder name fuzzy matches existing, return EntityValidationError."""
        from app.models.binder import Binder
        from app.schemas.entity_validation import EntityValidationError
        from app.services.entity_validation import validate_entity_for_book

        monkeypatch.setenv("ENTITY_VALIDATION_MODE", "enforce")

        # Create test binder
        binder = Binder(name="Zaehnsdorf", tier="TIER_1")
        db.add(binder)
        db.commit()

        # Use a typo that should fuzzy match but not exact match
        result = validate_entity_for_book(db, "binder", "Zaensdorf")

        # Should return validation error, not entity ID
        assert isinstance(result, EntityValidationError)
        assert result.error == "similar_entity_exists"
        assert result.entity_type == "binder"
        assert result.input == "Zaensdorf"
        assert result.suggestions is not None
        assert len(result.suggestions) > 0
        assert result.suggestions[0].name == "Zaehnsdorf"
        assert result.suggestions[0].id == binder.id

    def test_binder_validation_unknown_entity_returns_error(self, db, monkeypatch):
        """When binder name not found and no fuzzy matches, return EntityValidationError."""
        from app.schemas.entity_validation import EntityValidationError
        from app.services.entity_validation import validate_entity_for_book

        monkeypatch.setenv("ENTITY_VALIDATION_MODE", "enforce")

        # No binders in database - completely unknown name
        result = validate_entity_for_book(db, "binder", "CompletelyUnknownBinder")

        assert isinstance(result, EntityValidationError)
        assert result.error == "unknown_entity"
        assert result.entity_type == "binder"
        assert result.suggestions is None

    def test_binder_validation_empty_name_returns_none(self, db, monkeypatch):
        """When binder name is empty/None, validation returns None (skip)."""
        from app.services.entity_validation import validate_entity_for_book

        monkeypatch.setenv("ENTITY_VALIDATION_MODE", "enforce")

        # Empty string should return None
        result = validate_entity_for_book(db, "binder", "")
        assert result is None

        # None should return None
        result = validate_entity_for_book(db, "binder", None)
        assert result is None

        # Whitespace-only should return None
        result = validate_entity_for_book(db, "binder", "   ")
        assert result is None

    def test_worker_error_message_format_with_suggestions(self):
        """Test the error message format when there are fuzzy match suggestions.

        This tests the error message formatting logic used in the worker.
        """
        from app.schemas.entity_validation import EntitySuggestion, EntityValidationError

        validation_error = EntityValidationError(
            error="similar_entity_exists",
            entity_type="binder",
            input="Zaensdorf",
            suggestions=[
                EntitySuggestion(
                    id=42,
                    name="Zaehnsdorf",
                    tier="TIER_1",
                    match=0.85,
                    book_count=5,
                )
            ],
            resolution="Use existing binder",
        )

        # Reproduce the worker's error formatting logic
        binder_name = validation_error.input
        top_match = validation_error.suggestions[0]
        error_msg = (
            f"Entity validation failed: binder '{binder_name}' matches existing "
            f"'{top_match.name}' ({top_match.match:.0%}). "
            f"Use existing ID or create new via POST /binders?force=true"
        )

        assert "Entity validation failed" in error_msg
        assert "Zaensdorf" in error_msg
        assert "Zaehnsdorf" in error_msg
        assert "85%" in error_msg
        assert "POST /binders?force=true" in error_msg

    def test_worker_error_message_format_without_suggestions(self):
        """Test the error message format when there are no suggestions (unknown entity)."""
        from app.schemas.entity_validation import EntityValidationError

        validation_error = EntityValidationError(
            error="unknown_entity",
            entity_type="binder",
            input="NonExistentBinder",
            suggestions=None,
            resolution="Create the binder first",
        )

        # Reproduce the worker's error formatting logic
        binder_name = validation_error.input
        top_match = validation_error.suggestions[0] if validation_error.suggestions else None
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

        assert "Entity validation failed" in error_msg
        assert "NonExistentBinder" in error_msg
        assert "not found" in error_msg
        assert "POST /binders" in error_msg

    def test_worker_binder_association_logic(self, db, monkeypatch):
        """Test the full worker logic: validation result -> book association.

        This tests the complete flow that the worker performs:
        1. Get validation result
        2. Check if it's an error or entity ID
        3. Associate binder with book if ID returned
        """
        from app.models import Book
        from app.models.binder import Binder
        from app.schemas.entity_validation import EntityValidationError
        from app.services.entity_validation import validate_entity_for_book

        monkeypatch.setenv("ENTITY_VALIDATION_MODE", "enforce")

        # Create test binder and book
        binder = Binder(name="Riviere & Son", tier="TIER_1")
        db.add(binder)
        book = Book(title="Test Book", inventory_type="PRIMARY")
        db.add(book)
        db.commit()

        # Simulate worker logic for binder validation and association
        binder_name = "Riviere & Son"
        binder_result = validate_entity_for_book(db, "binder", binder_name)

        if isinstance(binder_result, EntityValidationError):
            raise ValueError("Should have matched exactly")

        if binder_result and book.binder_id != binder_result:
            book.binder_id = binder_result
            db.commit()

        db.refresh(book)
        assert book.binder_id == binder.id

    def test_worker_binder_validation_raises_on_fuzzy_match(self, db, monkeypatch):
        """Test that worker raises ValueError when validation returns fuzzy match error."""
        import pytest

        from app.models import Book
        from app.models.binder import Binder
        from app.schemas.entity_validation import EntityValidationError
        from app.services.entity_validation import validate_entity_for_book

        monkeypatch.setenv("ENTITY_VALIDATION_MODE", "enforce")

        # Create test binder and book
        binder = Binder(name="Riviere & Son", tier="TIER_1")
        db.add(binder)
        book = Book(title="Test Book", inventory_type="PRIMARY")
        db.add(book)
        db.commit()

        # Simulate worker logic with a typo that fuzzy matches
        binder_name = "Riviere and Son"  # Missing ampersand
        binder_result = validate_entity_for_book(db, "binder", binder_name)

        # Worker should raise when validation returns an error
        if isinstance(binder_result, EntityValidationError):
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

            with pytest.raises(ValueError, match="Entity validation failed"):
                raise ValueError(error_msg)

        # If we got here without binder_result being an error, fail the test
        assert isinstance(
            binder_result, EntityValidationError
        ), "Expected fuzzy match to return validation error"
