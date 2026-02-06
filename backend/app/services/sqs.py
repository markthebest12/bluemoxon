"""SQS service for sending job messages."""

import json
import logging
import os

import boto3

from app.config import get_settings
from app.services.aws_clients import get_sqs_client

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_queue_url(queue_name: str) -> str:
    """Get a queue URL from queue name.

    Args:
        queue_name: Name of the SQS queue

    Returns:
        Full queue URL
    """
    region = os.environ.get("AWS_REGION", settings.aws_region)

    # Get account ID from STS
    sts = boto3.client("sts", region_name=region)
    account_id = sts.get_caller_identity()["Account"]

    return f"https://sqs.{region}.amazonaws.com/{account_id}/{queue_name}"


def get_analysis_queue_url() -> str:
    """Get the analysis jobs queue URL.

    Constructs URL from queue name environment variable.
    """
    queue_name = settings.analysis_queue_name
    if not queue_name:
        raise ValueError("ANALYSIS_QUEUE_NAME environment variable not set")

    return _get_queue_url(queue_name)


def get_eval_runbook_queue_url() -> str:
    """Get the eval runbook jobs queue URL.

    Constructs URL from queue name environment variable.
    """
    queue_name = settings.eval_runbook_queue_name
    if not queue_name:
        raise ValueError("EVAL_RUNBOOK_QUEUE_NAME environment variable not set")

    return _get_queue_url(queue_name)


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


def send_eval_runbook_job(job_id: str, book_id: int) -> None:
    """Send an eval runbook job message to SQS.

    Args:
        job_id: UUID of the eval runbook job
        book_id: ID of the book to evaluate

    Raises:
        Exception: If message send fails
    """
    sqs = get_sqs_client()
    queue_url = get_eval_runbook_queue_url()

    message = {
        "job_id": str(job_id),
        "book_id": book_id,
    }

    logger.info(f"Sending eval runbook job to SQS: {message}")

    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message),
    )

    logger.info(f"Eval runbook job sent, MessageId: {response['MessageId']}")


def get_profile_generation_queue_url() -> str:
    """Get the profile generation jobs queue URL."""
    queue_name = settings.profile_generation_queue_name
    if not queue_name:
        raise ValueError("PROFILE_GENERATION_QUEUE_NAME environment variable not set")
    return _get_queue_url(queue_name)


def get_entity_enrichment_queue_url() -> str:
    """Get the entity enrichment jobs queue URL."""
    queue_name = settings.entity_enrichment_queue_name
    if not queue_name:
        raise ValueError("ENTITY_ENRICHMENT_QUEUE_NAME environment variable not set")
    return _get_queue_url(queue_name)


def send_profile_generation_jobs(messages: list[dict]) -> None:
    """Send profile generation job messages to SQS in batches.

    Args:
        messages: List of dicts with keys: job_id, entity_type, entity_id
    """
    sqs = get_sqs_client()
    queue_url = get_profile_generation_queue_url()

    for i in range(0, len(messages), 10):
        batch = messages[i : i + 10]
        entries = [
            {
                "Id": str(idx),
                "MessageBody": json.dumps(msg),
            }
            for idx, msg in enumerate(batch)
        ]

        response = sqs.send_message_batch(QueueUrl=queue_url, Entries=entries)

        failed = response.get("Failed", [])
        if failed:
            logger.error("Failed to send %d profile generation messages: %s", len(failed), failed)


def send_entity_enrichment_job(entity_type: str, entity_id: int, entity_name: str) -> None:
    """Send an entity enrichment job message to SQS.

    This is fire-and-forget: failures are logged but never raised,
    so entity creation is never blocked.

    Args:
        entity_type: Type of entity ("author", "publisher", "binder")
        entity_id: ID of the newly created entity
        entity_name: Name of the entity (used in Bedrock prompt)
    """
    try:
        sqs = get_sqs_client()
        queue_url = get_entity_enrichment_queue_url()

        message = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "entity_name": entity_name,
        }

        logger.info("Sending entity enrichment job to SQS: %s", message)

        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message),
        )

        logger.info("Entity enrichment job sent, MessageId: %s", response["MessageId"])

    except Exception:
        logger.warning(
            "Failed to send entity enrichment job for %s:%s — enrichment skipped",
            entity_type,
            entity_id,
            exc_info=True,
        )
