"""Job management utilities for analysis and eval runbook jobs."""

from datetime import UTC, datetime, timedelta
from typing import TypeVar

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import AnalysisJob, EvalRunbookJob

STALE_JOB_THRESHOLD_MINUTES = 15

JobModel = TypeVar("JobModel", AnalysisJob, EvalRunbookJob)


def _normalize_datetime(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware (UTC).

    Handles both naive datetimes (from legacy code using utcnow)
    and timezone-aware datetimes.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def handle_stale_jobs(
    db: Session,
    job_model: type[JobModel],
    book_id: int,
    *,
    use_skip_locked: bool = False,
) -> None:
    """Check for stale jobs and auto-fail them, or raise 409 if active job exists.

    Args:
        db: Database session
        job_model: AnalysisJob or EvalRunbookJob class
        book_id: Book ID to check
        use_skip_locked: Use FOR UPDATE SKIP LOCKED (for job creation endpoints)

    Raises:
        HTTPException: 409 if non-stale active job exists
    """
    stale_threshold = datetime.now(UTC) - timedelta(minutes=STALE_JOB_THRESHOLD_MINUTES)

    query = db.query(job_model).filter(
        job_model.book_id == book_id,
        job_model.status.in_(["pending", "running"]),
    )

    if use_skip_locked:
        query = query.with_for_update(skip_locked=True)

    jobs = query.all()

    stale_jobs = [j for j in jobs if _normalize_datetime(j.updated_at) < stale_threshold]
    active_jobs = [j for j in jobs if _normalize_datetime(j.updated_at) >= stale_threshold]

    # Auto-fail stale jobs
    for job in stale_jobs:
        job.status = "failed"
        job.error_message = f"Job timed out after {STALE_JOB_THRESHOLD_MINUTES} minutes"
        job.completed_at = datetime.now(UTC)

    if stale_jobs:
        db.commit()

    # Raise if active job exists
    if active_jobs:
        raise HTTPException(status_code=409, detail="Job already in progress for this book")
