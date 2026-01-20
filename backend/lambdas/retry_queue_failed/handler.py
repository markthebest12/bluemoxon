"""Lambda handler for retrying queue_failed image processing jobs."""

import logging

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.image_processing_job import ImageProcessingJob
from app.services.image_processing import send_image_processing_job

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BATCH_SIZE = 50


def retry_queue_failed_jobs(db: Session) -> dict:
    """Retry image processing jobs with queue_failed status.

    Queries for jobs with queue_failed status and queue_retry_count < MAX_RETRIES,
    attempts to re-send them to SQS, and updates their status accordingly.

    Args:
        db: Database session

    Returns:
        Dict with counts: retried, succeeded, still_failing, permanently_failed
    """
    jobs = (
        db.query(ImageProcessingJob)
        .filter(ImageProcessingJob.status == "queue_failed")
        .filter(ImageProcessingJob.queue_retry_count < MAX_RETRIES)
        .limit(BATCH_SIZE)
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
            job.queue_retry_count = 0
            succeeded += 1
        except Exception as e:
            job.queue_retry_count += 1
            job.failure_reason = str(e)[:1000]
            if job.queue_retry_count >= MAX_RETRIES:
                job.status = "permanently_failed"
                permanently_failed += 1
            logger.warning(f"Failed to retry job {job.id}: {e} (attempt {job.queue_retry_count})")

    db.commit()

    return {
        "retried": retried,
        "succeeded": succeeded,
        "still_failing": retried - succeeded - permanently_failed,
        "permanently_failed": permanently_failed,
    }


def handler(event: dict, context) -> dict:
    """Lambda entry point for EventBridge scheduled invocation.

    Args:
        event: EventBridge event (ignored)
        context: Lambda context (ignored)

    Returns:
        Dict with retry statistics
    """
    db = SessionLocal()
    try:
        result = retry_queue_failed_jobs(db)
        logger.info(
            f"Retry completed: {result['retried']} retried, "
            f"{result['succeeded']} succeeded, "
            f"{result['permanently_failed']} permanently failed"
        )
        return result
    finally:
        db.close()
