"""Image processing service for async background removal."""

import json
import logging
import warnings

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ImageProcessingJob
from app.services.aws_clients import get_sqs_client

logger = logging.getLogger(__name__)

# Validate queue name at import time
_settings = get_settings()
if not _settings.image_processing_queue_name:
    warnings.warn(
        "IMAGE_PROCESSING_QUEUE_NAME not configured - image processing disabled",
        stacklevel=1,
    )

# Module-level cache for queue URL (avoids STS call on every invocation)
_queue_url_cache: str | None = None


def get_image_processing_queue_url() -> str:
    """Get the image processing SQS queue URL.

    Uses sqs.get_queue_url() API which is the proper way to get queue URL.
    Result is cached at module level to avoid repeated API calls.

    Raises:
        ValueError: If queue name not configured
    """
    global _queue_url_cache
    if _queue_url_cache is not None:
        return _queue_url_cache

    settings = get_settings()
    queue_name = settings.image_processing_queue_name
    if not queue_name:
        raise ValueError("IMAGE_PROCESSING_QUEUE_NAME environment variable not set")

    # Use get_queue_url API instead of constructing URL manually
    client = get_sqs_client()
    response = client.get_queue_url(QueueName=queue_name)
    _queue_url_cache = response["QueueUrl"]

    return _queue_url_cache


def send_image_processing_job(job_id: str, book_id: int, image_id: int) -> None:
    """Send image processing job to SQS queue.

    Args:
        job_id: UUID of the ImageProcessingJob
        book_id: Book ID
        image_id: Source image ID to process
    """
    client = get_sqs_client()
    queue_url = get_image_processing_queue_url()

    message = {
        "job_id": job_id,
        "book_id": book_id,
        "image_id": image_id,
    }

    logger.info(f"Sending image processing job to SQS: {message}")

    response = client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message),
    )

    logger.info(f"Image processing job sent, MessageId: {response['MessageId']}")


def queue_image_processing(db: Session, book_id: int, image_id: int) -> ImageProcessingJob | None:
    """Queue an image for background removal processing.

    Creates an ImageProcessingJob record and sends to SQS.
    Skips if a pending/processing job already exists for this image.

    Args:
        db: Database session
        book_id: Book ID
        image_id: Source image ID

    Returns:
        Created job, or None if skipped (duplicate)
    """
    existing = (
        db.query(ImageProcessingJob)
        .filter(
            ImageProcessingJob.book_id == book_id,
            ImageProcessingJob.source_image_id == image_id,
            ImageProcessingJob.status.in_(["pending", "processing"]),
        )
        .first()
    )

    if existing:
        logger.info(
            f"Skipping duplicate image processing for book {book_id}, "
            f"existing job {existing.id} is {existing.status}"
        )
        return None

    job = ImageProcessingJob(
        book_id=book_id,
        source_image_id=image_id,
    )
    db.add(job)
    db.flush()  # Get the ID without committing

    try:
        send_image_processing_job(str(job.id), book_id, image_id)
        db.commit()  # Only commit after SQS succeeds
    except Exception as e:
        # SQS failed - save job with queue_failed status for retry
        job.status = "queue_failed"
        job.failure_reason = str(e)[:1000]
        db.commit()
        logger.error(f"Failed to queue image processing job {job.id}: {e}")

    return job
