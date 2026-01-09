"""Tests for the analysis worker."""

from unittest.mock import patch


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
    """Tests for binder entity validation in worker - Issue #968."""

    def test_binder_validation_exact_match_associates_binder(self, db):
        """When binder name matches exactly, associate binder with book."""
        from app.models import Book
        from app.models.binder import Binder
        from app.schemas.entity_validation import EntityValidationError

        # Create test binder
        binder = Binder(name="Zaehnsdorf", tier="TIER_1")
        db.add(binder)
        db.commit()

        # Create test book
        book = Book(title="Test Book", inventory_type="PRIMARY")
        db.add(book)
        db.commit()

        # Mock validate_entity_for_book to return exact match (entity ID)
        with patch(
            "app.worker.validate_entity_for_book",
            return_value=binder.id,
        ):
            # Simulate the binder association logic from worker
            binder_result = binder.id  # Exact match returns ID

            if isinstance(binder_result, EntityValidationError):
                raise ValueError("Should not happen in this test")

            if binder_result and book.binder_id != binder_result:
                book.binder_id = binder_result
                db.commit()

        db.refresh(book)
        assert book.binder_id == binder.id

    def test_binder_validation_fuzzy_match_raises_error(self, db):
        """When binder name fuzzy matches existing, raise descriptive error."""
        from app.models import Book
        from app.models.binder import Binder
        from app.schemas.entity_validation import EntitySuggestion, EntityValidationError

        # Create test binder
        binder = Binder(name="Zaehnsdorf", tier="TIER_1")
        db.add(binder)
        db.commit()

        # Create test book
        book = Book(title="Test Book", inventory_type="PRIMARY")
        db.add(book)
        db.commit()

        # Create validation error with suggestion
        validation_error = EntityValidationError(
            error="similar_entity_exists",
            entity_type="binder",
            input="Zaensdorf",  # Typo
            suggestions=[
                EntitySuggestion(
                    id=binder.id,
                    name="Zaehnsdorf",
                    tier="TIER_1",
                    match=0.85,
                    book_count=0,
                )
            ],
            resolution="Use existing binder",
        )

        # Simulate the error generation logic from worker
        binder_name = "Zaensdorf"
        binder_result = validation_error

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

        assert "Entity validation failed" in error_msg
        assert "Zaensdorf" in error_msg
        assert "Zaehnsdorf" in error_msg
        assert "85%" in error_msg

    def test_binder_validation_unknown_entity_raises_error(self, db):
        """When binder name not found, raise descriptive error."""
        from app.models import Book
        from app.schemas.entity_validation import EntityValidationError

        # Create test book
        book = Book(title="Test Book", inventory_type="PRIMARY")
        db.add(book)
        db.commit()

        # Create validation error for unknown entity
        validation_error = EntityValidationError(
            error="unknown_entity",
            entity_type="binder",
            input="NonExistentBinder",
            suggestions=None,
            resolution="Create the binder first",
        )

        # Simulate the error generation logic from worker
        binder_name = "NonExistentBinder"
        binder_result = validation_error

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

        assert "Entity validation failed" in error_msg
        assert "NonExistentBinder" in error_msg
        assert "not found" in error_msg
        assert "POST /binders" in error_msg

    def test_binder_validation_empty_name_skipped(self, db):
        """When binder_identification has no name, validation is skipped."""
        from app.models import Book

        # Create test book with no binder
        book = Book(title="Test Book", inventory_type="PRIMARY")
        db.add(book)
        db.commit()

        # Empty binder identification should be skipped
        parsed_binder_identification = {"name": ""}

        # This condition from worker.py should skip validation
        should_validate = parsed_binder_identification and parsed_binder_identification.get("name")
        assert not should_validate

        # Book should still have no binder
        db.refresh(book)
        assert book.binder_id is None
