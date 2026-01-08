"""Tests for job_manager service."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.models import AnalysisJob, Author, Book, EvalRunbookJob
from app.services.job_manager import (
    STALE_JOB_THRESHOLD_MINUTES,
    _normalize_datetime,
    handle_stale_jobs,
)


def create_test_book(db) -> Book:
    """Create a test book for job tests."""
    author = Author(name="Test Author")
    db.add(author)
    db.flush()

    book = Book(
        title="Test Book for Job Manager",
        author_id=author.id,
        status="EVALUATING",
    )
    db.add(book)
    db.commit()
    return book


class TestHandleStaleJobs:
    """Tests for handle_stale_jobs function."""

    def test_no_jobs_does_nothing(self, db):
        """When no jobs exist, function completes without error."""
        # Should not raise
        handle_stale_jobs(db, AnalysisJob, book_id=9999)

    def test_stale_job_gets_auto_failed(self, db):
        """Jobs older than threshold get marked as failed."""
        test_book = create_test_book(db)

        stale_time = datetime.now(UTC) - timedelta(minutes=STALE_JOB_THRESHOLD_MINUTES + 5)
        job = AnalysisJob(
            book_id=test_book.id,
            status="running",
            created_at=stale_time,
            updated_at=stale_time,
        )
        db.add(job)
        db.commit()

        # Should not raise (stale job gets auto-failed)
        handle_stale_jobs(db, AnalysisJob, book_id=test_book.id)

        db.refresh(job)
        assert job.status == "failed"
        assert "timed out" in job.error_message

    def test_active_job_raises_409(self, db):
        """Non-stale active job raises HTTPException 409."""
        test_book = create_test_book(db)

        recent_time = datetime.now(UTC) - timedelta(minutes=1)
        job = AnalysisJob(
            book_id=test_book.id,
            status="running",
            created_at=recent_time,
            updated_at=recent_time,
        )
        db.add(job)
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            handle_stale_jobs(db, AnalysisJob, book_id=test_book.id)

        assert exc_info.value.status_code == 409
        assert "already in progress" in exc_info.value.detail

    def test_works_with_eval_runbook_job(self, db):
        """Function works with EvalRunbookJob model too."""
        test_book = create_test_book(db)

        recent_time = datetime.now(UTC) - timedelta(minutes=1)
        job = EvalRunbookJob(
            book_id=test_book.id,
            status="pending",
            created_at=recent_time,
            updated_at=recent_time,
        )
        db.add(job)
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            handle_stale_jobs(db, EvalRunbookJob, book_id=test_book.id)

        assert exc_info.value.status_code == 409

    def test_pending_status_also_checked(self, db):
        """Both 'pending' and 'running' statuses are considered active."""
        test_book = create_test_book(db)

        recent_time = datetime.now(UTC) - timedelta(minutes=1)
        job = AnalysisJob(
            book_id=test_book.id,
            status="pending",
            created_at=recent_time,
            updated_at=recent_time,
        )
        db.add(job)
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            handle_stale_jobs(db, AnalysisJob, book_id=test_book.id)

        assert exc_info.value.status_code == 409

    def test_job_just_under_threshold_is_active(self, db):
        """Job just under threshold is considered active (not stale)."""
        test_book = create_test_book(db)

        # 1 second under threshold - should be active
        just_under = datetime.now(UTC) - timedelta(minutes=STALE_JOB_THRESHOLD_MINUTES, seconds=-1)
        job = AnalysisJob(
            book_id=test_book.id,
            status="running",
            created_at=just_under,
            updated_at=just_under,
        )
        db.add(job)
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            handle_stale_jobs(db, AnalysisJob, book_id=test_book.id)

        assert exc_info.value.status_code == 409
        # Job should NOT be marked failed
        db.refresh(job)
        assert job.status == "running"

    def test_job_just_over_threshold_is_stale(self, db):
        """Job just over threshold is considered stale."""
        test_book = create_test_book(db)

        # 1 second over threshold - should be stale
        just_over = datetime.now(UTC) - timedelta(minutes=STALE_JOB_THRESHOLD_MINUTES, seconds=1)
        job = AnalysisJob(
            book_id=test_book.id,
            status="running",
            created_at=just_over,
            updated_at=just_over,
        )
        db.add(job)
        db.commit()

        # Should not raise (job gets auto-failed)
        handle_stale_jobs(db, AnalysisJob, book_id=test_book.id)

        db.refresh(job)
        assert job.status == "failed"

    def test_multiple_stale_and_one_active(self, db):
        """Multiple stale jobs get failed, but active job still raises 409."""
        test_book = create_test_book(db)

        stale_time = datetime.now(UTC) - timedelta(minutes=STALE_JOB_THRESHOLD_MINUTES + 10)
        recent_time = datetime.now(UTC) - timedelta(minutes=1)

        # Two stale jobs
        stale_job1 = AnalysisJob(
            book_id=test_book.id,
            status="running",
            created_at=stale_time,
            updated_at=stale_time,
        )
        stale_job2 = AnalysisJob(
            book_id=test_book.id,
            status="pending",
            created_at=stale_time,
            updated_at=stale_time,
        )
        # One active job
        active_job = AnalysisJob(
            book_id=test_book.id,
            status="running",
            created_at=recent_time,
            updated_at=recent_time,
        )
        db.add_all([stale_job1, stale_job2, active_job])
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            handle_stale_jobs(db, AnalysisJob, book_id=test_book.id)

        assert exc_info.value.status_code == 409

        # Stale jobs should be marked failed
        db.refresh(stale_job1)
        db.refresh(stale_job2)
        db.refresh(active_job)
        assert stale_job1.status == "failed"
        assert stale_job2.status == "failed"
        # Active job unchanged
        assert active_job.status == "running"

    def test_job_type_name_in_error_message(self, db):
        """Custom job_type_name appears in error message."""
        test_book = create_test_book(db)

        recent_time = datetime.now(UTC) - timedelta(minutes=1)
        job = AnalysisJob(
            book_id=test_book.id,
            status="running",
            created_at=recent_time,
            updated_at=recent_time,
        )
        db.add(job)
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            handle_stale_jobs(db, AnalysisJob, book_id=test_book.id, job_type_name="Analysis job")

        assert "Analysis job already in progress" in exc_info.value.detail


class TestNormalizeDatetime:
    """Tests for _normalize_datetime helper function."""

    def test_none_returns_current_time(self):
        """None should be treated as 'now', not epoch (prevents auto-fail of new jobs)."""
        before = datetime.now(UTC)
        result = _normalize_datetime(None)
        after = datetime.now(UTC)

        # Result should be between before and after (i.e., approximately now)
        assert before <= result <= after
        assert result.tzinfo is not None

    def test_naive_datetime_gets_utc_timezone(self):
        """Naive datetime should get UTC timezone attached."""
        naive = datetime(2024, 1, 15, 12, 0, 0)
        result = _normalize_datetime(naive)

        assert result.tzinfo == UTC
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_aware_datetime_unchanged(self):
        """Timezone-aware datetime should pass through unchanged."""
        aware = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        result = _normalize_datetime(aware)

        assert result == aware
