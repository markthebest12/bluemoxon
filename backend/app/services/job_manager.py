"""Job management utilities for analysis and eval runbook jobs.

Race Condition Prevention Strategy:

1. **Database constraint (primary defense)**: Partial unique indexes ensure only one
   active job (pending/running) can exist per book_id. See migration y8901234cdef.

2. **Application-level check (secondary defense)**: `handle_stale_jobs` uses
   SELECT FOR UPDATE to lock existing active jobs before checking, preventing
   the check-then-insert race at the application level.

3. **IntegrityError handling**: Callers should catch IntegrityError on job insert
   and return 409, as the constraint may fire after the application check passed.

The database constraint is the authoritative defense - the application check is
an optimization to fail fast and provide better error messages.
"""

from datetime import UTC, datetime, timedelta
from typing import TypeVar

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import AnalysisJob, EvalRunbookJob

STALE_JOB_THRESHOLD_MINUTES = 15

JobModel = TypeVar("JobModel", AnalysisJob, EvalRunbookJob)


def _normalize_datetime(dt: datetime | None) -> datetime:
    """Ensure datetime is timezone-aware (UTC).

    Handles both naive datetimes (from legacy code using utcnow)
    and timezone-aware datetimes.

    If dt is None, returns current time. This is defensive handling for the
    edge case where a job record exists without an updated_at value (e.g.,
    database issue, test fixture). Treating None as "now" means such jobs
    are considered active, not stale - the safer default since auto-failing
    a brand-new job would be worse than letting it run.
    """
    if dt is None:
        # Defensive: treat missing timestamp as "just now" (active, not stale)
        return datetime.now(UTC)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def handle_stale_jobs(
    db: Session,
    job_model: type[JobModel],
    book_id: int,
    *,
    job_type_name: str = "Job",
    use_skip_locked: bool = False,
) -> None:
    """Check for stale jobs and auto-fail them, or raise 409 if active job exists.

    This function provides an application-level check before job creation. The
    database-level partial unique index (ix_*_jobs_unique_active_per_book) is
    the primary defense against race conditions.

    Args:
        db: Database session
        job_model: AnalysisJob or EvalRunbookJob class
        book_id: Book ID to check
        job_type_name: Human-readable job type for error messages (e.g., "Analysis job")
        use_skip_locked: Use FOR UPDATE SKIP LOCKED (for job creation endpoints).
            When True, skips locked rows so concurrent requests don't deadlock.
            The database constraint will catch any race that slips through.

    Raises:
        HTTPException: 409 if non-stale active job exists

    Note:
        Callers should still handle IntegrityError on job insert, as concurrent
        requests may pass the application check before the database constraint fires.
    """
    stale_threshold = datetime.now(UTC) - timedelta(minutes=STALE_JOB_THRESHOLD_MINUTES)

    query = db.query(job_model).filter(
        job_model.book_id == book_id,
        job_model.status.in_(["pending", "running"]),
    )

    if use_skip_locked:
        # SKIP LOCKED prevents deadlocks - if another transaction has the lock,
        # we skip and rely on the database constraint to catch duplicates
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
        # Commit stale job failures immediately so other transactions see them
        # This is safe because marking stale jobs as failed is idempotent
        db.commit()

    # Raise if active job exists
    if active_jobs:
        raise HTTPException(
            status_code=409,
            detail=f"{job_type_name} already in progress for this book",
        )
