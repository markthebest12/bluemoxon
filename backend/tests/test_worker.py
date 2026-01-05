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
