"""Image processing service for async background removal."""

import json
import logging
import os

import boto3
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ImageProcessingJob

logger = logging.getLogger(__name__)


def get_sqs_client():
    """Get SQS client."""
    settings = get_settings()
    region = os.environ.get("AWS_REGION", settings.aws_region)
    return boto3.client("sqs", region_name=region)


def get_image_processing_queue_url() -> str:
    """Get the image processing SQS queue URL.

    Constructs URL from queue name environment variable.

    Raises:
        ValueError: If queue name not configured
    """
    settings = get_settings()
    queue_name = settings.image_processing_queue_name
    if not queue_name:
        raise ValueError("IMAGE_PROCESSING_QUEUE_NAME environment variable not set")

    region = os.environ.get("AWS_REGION", settings.aws_region)

    # Get account ID from STS
    sts = boto3.client("sts", region_name=region)
    account_id = sts.get_caller_identity()["Account"]

    return f"https://sqs.{region}.amazonaws.com/{account_id}/{queue_name}"


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
    db.commit()

    send_image_processing_job(str(job.id), book_id, image_id)

    return job
