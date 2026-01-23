"""Tracking dispatcher Lambda handler.

Queries active tracking books and dispatches their IDs to SQS for processing.
"""

import json
import logging
import os
from functools import lru_cache

import boto3
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Book

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@lru_cache(maxsize=1)
def get_sqs_client():
    """Get SQS client for queue operations."""
    return boto3.client("sqs")


def dispatch_tracking_jobs(db: Session, queue_url: str) -> dict:
    """Query active tracking books and send their IDs to SQS.

    Args:
        db: Database session
        queue_url: SQS queue URL for tracking jobs

    Returns:
        Dictionary with dispatch count

    """
    sqs = get_sqs_client()

    books = (
        db.query(Book.id)
        .filter(
            Book.tracking_active,
            Book.tracking_number.isnot(None),
        )
        .all()
    )

    dispatched = 0
    for (book_id,) in books:
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({"book_id": book_id}),
        )
        dispatched += 1

    logger.info(f"Dispatched {dispatched} tracking jobs to SQS")
    return {"dispatched": dispatched}


def handler(event: dict, context) -> dict:
    """Lambda handler for EventBridge trigger.

    Args:
        event: EventBridge event (unused, dispatcher runs on schedule)
        context: Lambda context object

    Returns:
        Dictionary with dispatch results

    Raises:
        ValueError: If TRACKING_QUEUE_URL environment variable not set

    """
    queue_url = os.environ.get("TRACKING_QUEUE_URL")
    if not queue_url:
        raise ValueError("TRACKING_QUEUE_URL environment variable not set")

    db = SessionLocal()
    try:
        return dispatch_tracking_jobs(db, queue_url)
    finally:
        db.close()
