"""Lambda handler for retrying queue_failed image processing jobs."""

import logging

from app.db.session import SessionLocal
from app.services.retry_queue_failed import retry_queue_failed_jobs

logger = logging.getLogger(__name__)

# Re-export for tests that import from handler
from app.services.retry_queue_failed import BATCH_SIZE, MAX_RETRIES  # noqa: E402, F401


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
