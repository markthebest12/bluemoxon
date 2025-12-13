"""SQS service for sending analysis job messages."""

import json
import logging
import os

import boto3

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_sqs_client():
    """Get SQS client."""
    region = os.environ.get("AWS_REGION", settings.aws_region)
    return boto3.client("sqs", region_name=region)


def get_analysis_queue_url() -> str:
    """Get the analysis jobs queue URL.

    Constructs URL from queue name environment variable.
    """
    queue_name = os.environ.get("ANALYSIS_QUEUE_NAME")
    if not queue_name:
        raise ValueError("ANALYSIS_QUEUE_NAME environment variable not set")

    region = os.environ.get("AWS_REGION", settings.aws_region)

    # Get account ID from STS
    sts = boto3.client("sts", region_name=region)
    account_id = sts.get_caller_identity()["Account"]

    return f"https://sqs.{region}.amazonaws.com/{account_id}/{queue_name}"


def send_analysis_job(job_id: str, book_id: int, model: str) -> None:
    """Send an analysis job message to SQS.

    Args:
        job_id: UUID of the analysis job
        book_id: ID of the book to analyze
        model: Model to use (sonnet or opus)

    Raises:
        Exception: If message send fails
    """
    sqs = get_sqs_client()
    queue_url = get_analysis_queue_url()

    message = {
        "job_id": str(job_id),
        "book_id": book_id,
        "model": model,
    }

    logger.info(f"Sending analysis job to SQS: {message}")

    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message),
    )

    logger.info(f"Analysis job sent, MessageId: {response['MessageId']}")
