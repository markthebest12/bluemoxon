"""Tests for CleanupJob model."""

import uuid
from datetime import UTC, datetime


class TestCleanupJobModel:
    """Tests for CleanupJob database model."""

    def test_create_cleanup_job(self, db):
        """Test creating a cleanup job."""
        from app.models.cleanup_job import CleanupJob

        job = CleanupJob(
            total_count=3609,
            total_bytes=1500000000,
        )
        db.add(job)
        db.commit()

        assert job.id is not None
        assert isinstance(job.id, uuid.UUID)
        assert job.status == "pending"
        assert job.total_count == 3609
        assert job.total_bytes == 1500000000
        assert job.deleted_count == 0
        assert job.deleted_bytes == 0
        assert job.created_at is not None

    def test_cleanup_job_progress(self, db):
        """Test updating cleanup job progress."""
        from app.models.cleanup_job import CleanupJob

        job = CleanupJob(total_count=100, total_bytes=1000000)
        db.add(job)
        db.commit()

        # Update progress
        job.status = "running"
        job.deleted_count = 50
        job.deleted_bytes = 500000
        db.commit()

        assert job.status == "running"
        assert job.deleted_count == 50
        assert job.progress_pct == 50.0

    def test_cleanup_job_completion(self, db):
        """Test completing a cleanup job."""
        from app.models.cleanup_job import CleanupJob

        job = CleanupJob(total_count=100, total_bytes=1000000)
        db.add(job)
        db.commit()

        job.status = "completed"
        job.deleted_count = 100
        job.deleted_bytes = 1000000
        job.completed_at = datetime.now(UTC)
        db.commit()

        assert job.status == "completed"
        assert job.completed_at is not None
        assert job.progress_pct == 100.0
