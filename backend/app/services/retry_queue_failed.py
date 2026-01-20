"""Service for retrying queue_failed image processing jobs.

This module provides the core retry logic used by both the scheduled Lambda
and the admin API endpoint. It handles race conditions using SELECT FOR UPDATE
SKIP LOCKED to prevent duplicate processing when multiple workers run concurrently.
"""

import logging

from sqlalchemy.orm import Session, lazyload

from app.models.image_processing_job import ImageProcessingJob
from app.services.image_processing import send_image_processing_job

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BATCH_SIZE = 50


def retry_queue_failed_jobs(db: Session) -> dict:
    """Retry image processing jobs with queue_failed status.

    Uses SELECT FOR UPDATE SKIP LOCKED to prevent race conditions when
    Lambda and admin endpoint run concurrently. Commits after each job
    to prevent rollback of successful retries if later jobs fail.

    Args:
        db: Database session

    Returns:
        Dict with counts: retried, succeeded, still_failing, permanently_failed
    """
    # Query with FOR UPDATE SKIP LOCKED to prevent race conditions
    # Order by created_at to prevent starvation of older jobs
    # Use lazyload('*') to prevent eager loading which conflicts with FOR UPDATE
    # (PostgreSQL: "FOR UPDATE cannot be applied to the nullable side of an outer join")
    jobs = (
        db.query(ImageProcessingJob)
        .options(lazyload("*"))
        .filter(ImageProcessingJob.status == "queue_failed")
        .filter(ImageProcessingJob.queue_retry_count < MAX_RETRIES)
        .order_by(ImageProcessingJob.created_at.asc())
        .limit(BATCH_SIZE)
        .with_for_update(skip_locked=True, of=ImageProcessingJob)
        .all()
    )

    retried = 0
    succeeded = 0
    permanently_failed = 0

    for job in jobs:
        retried += 1
        try:
            send_image_processing_job(str(job.id), job.book_id, job.source_image_id)
            job.status = "pending"
            # Reset counter on success. This tracks consecutive queue failures,
            # not lifetime failures. If a job later fails at a different stage
            # and becomes queue_failed again, it gets another 3 attempts.
            # This is intentional for handling transient SQS issues.
            job.queue_retry_count = 0
            succeeded += 1
        except Exception as e:
            job.queue_retry_count += 1
            job.failure_reason = str(e)[:1000]
            if job.queue_retry_count >= MAX_RETRIES:
                job.status = "permanently_failed"
                permanently_failed += 1
            logger.warning(f"Failed to retry job {job.id}: {e} (attempt {job.queue_retry_count})")

        # Commit after each job to prevent rollback of successful retries
        # if a later commit fails. This ensures SQS sends and DB status stay in sync.
        db.commit()

    return {
        "retried": retried,
        "succeeded": succeeded,
        "still_failing": retried - succeeded - permanently_failed,
        "permanently_failed": permanently_failed,
    }
