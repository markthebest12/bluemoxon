"""Tests for job_manager service."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.models import AnalysisJob, Author, Book, EvalRunbookJob
from app.services.job_manager import STALE_JOB_THRESHOLD_MINUTES, handle_stale_jobs


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
