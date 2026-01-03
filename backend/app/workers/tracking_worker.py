"""Tracking worker Lambda handler.

Processes SQS messages, fetches carrier tracking information, and updates the database.
"""

import json
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Book
from app.services.carriers import get_carrier
from app.services.circuit_breaker import is_circuit_open, record_failure, record_success

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def process_tracking_job(db: Session, book_id: int) -> dict:
    """Process a single tracking job.

    Args:
        db: Database session
        book_id: ID of the book to update tracking for

    Returns:
        Dictionary with success status and tracking information

    Raises:
        Exception: If circuit is open for the carrier or on other carrier API errors

    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        logger.warning(f"Book {book_id} not found")
        return {"success": False, "error": "Book not found"}

    if not book.tracking_carrier:
        logger.warning(f"Book {book_id} has no tracking carrier")
        return {"success": False, "error": "No carrier"}

    if is_circuit_open(db, book.tracking_carrier):
        raise Exception(f"Circuit open for {book.tracking_carrier}")

    try:
        carrier = get_carrier(book.tracking_carrier)
        result = carrier.fetch_tracking(book.tracking_number)
        book.tracking_status = result.status
        book.tracking_last_checked = datetime.now(UTC)
        if result.status == "Delivered" and book.tracking_delivered_at is None:
            book.tracking_delivered_at = datetime.now(UTC)
        db.commit()
        record_success(db, book.tracking_carrier)
        logger.info(f"Book {book_id} tracking updated: {result.status}")
        return {"success": True, "status": result.status}
    except Exception as e:
        record_failure(db, book.tracking_carrier)
        logger.error(f"Failed to fetch tracking for book {book_id}: {e}")
        raise


def handler(event: dict, context) -> dict:
    """Lambda handler for SQS trigger.

    Args:
        event: SQS event with Records containing book tracking jobs
        context: Lambda context object

    Returns:
        Dictionary with batchItemFailures for failed messages (for SQS partial batch response)

    """
    batch_item_failures = []
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            book_id = body["book_id"]
            db = SessionLocal()
            try:
                process_tracking_job(db, book_id)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to process record: {e}")
            batch_item_failures.append({"itemIdentifier": record.get("messageId")})
    return {"batchItemFailures": batch_item_failures}
