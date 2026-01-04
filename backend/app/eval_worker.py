"""Eval Runbook worker Lambda handler.

Processes SQS messages to generate eval runbooks asynchronously with full
AI analysis and FMV lookup (operations that take 60+ seconds).
"""

import json
import logging
from datetime import UTC, datetime

from app.db import SessionLocal
from app.models import Book, EvalRunbookJob
from app.services.eval_generation import detect_garbage_images, generate_eval_runbook
from app.version import get_version

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Minimum number of images required to run garbage detection.
# Books with few images (e.g., just cover/spine) rarely have garbage,
# so we skip the expensive API call for them.
MIN_IMAGES_FOR_GARBAGE_DETECTION = 5


def handler(event: dict, context) -> dict:
    """Lambda handler for SQS eval runbook job messages.

    Also supports version check via {"version": true} payload.

    Args:
        event: SQS event containing batch of messages, or version check payload
        context: Lambda context

    Returns:
        Dict with batch item failures for partial batch response,
        or version info if version check requested
    """
    # Handle version check (for smoke tests)
    if event.get("version"):
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "version": get_version(),
                    "worker": "eval_runbook",
                }
            ),
        }

    batch_item_failures = []

    for record in event.get("Records", []):
        message_id = record.get("messageId", "unknown")

        try:
            # Parse message body
            body = json.loads(record["body"])
            job_id = body["job_id"]
            book_id = body["book_id"]

            logger.info(f"Processing eval runbook job {job_id} for book {book_id}")

            # Process the job
            process_eval_runbook_job(job_id, book_id)

            logger.info(f"Successfully processed eval runbook job {job_id}")

        except Exception as e:
            logger.error(f"Failed to process message {message_id}: {e}", exc_info=True)
            # Report this message as failed for partial batch failure
            batch_item_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_item_failures}


def process_eval_runbook_job(job_id: str, book_id: int) -> None:
    """Process a single eval runbook job.

    Args:
        job_id: UUID of the eval runbook job
        book_id: ID of the book to evaluate

    Raises:
        Exception: If processing fails
    """
    db = SessionLocal()
    job = None

    try:
        # Get the job record
        job = db.query(EvalRunbookJob).filter(EvalRunbookJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found in database")
            return

        # Update status to running
        job.status = "running"
        job.updated_at = datetime.now(UTC)
        db.commit()

        # Get book with relationships
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise ValueError(f"Book {book_id} not found")

        # Delete existing eval runbook if present (regenerating)
        if book.eval_runbook:
            logger.info(f"Deleting existing eval runbook for book {book_id}")
            db.delete(book.eval_runbook)
            db.flush()

        # Build listing_data from book's existing attributes
        # This reconstructs the data that would have been available at import time
        listing_data = {
            "price": float(book.purchase_price) if book.purchase_price else None,
            "author": book.author.name if book.author else None,
            "publisher": book.publisher.name if book.publisher else None,
            "description": book.condition_notes,  # Use condition notes as description context
        }

        # Run garbage detection BEFORE eval runbook generation
        # This removes seller promotional images, different books, etc.
        # Skip for books with few images - they rarely have garbage (usually just cover/spine)
        if book.images and len(book.images) >= MIN_IMAGES_FOR_GARBAGE_DETECTION:
            listing_title = book.title or listing_data.get("title", "")
            garbage_indices = detect_garbage_images(
                book_id=book.id,
                images=list(book.images),
                title=listing_title,
                author=book.author.name if book.author else None,
                db=db,
            )
            if garbage_indices is None:
                logger.warning(
                    f"Garbage detection failed for book {book_id}, proceeding without cleanup"
                )
            elif garbage_indices:
                logger.info(f"Removed {len(garbage_indices)} garbage images from book {book_id}")
        elif book.images:
            logger.info(
                f"Skipping garbage detection for book {book_id}: only {len(book.images)} images"
            )

        logger.info(
            f"Generating eval runbook for book {book_id} with full AI analysis and FMV lookup"
        )

        # Generate eval runbook with full analysis (AI + FMV)
        runbook = generate_eval_runbook(
            book=book,
            listing_data=listing_data,
            db=db,
            run_ai_analysis=True,
            run_fmv_lookup=True,
        )

        logger.info(
            f"Eval runbook generated for book {book_id}: "
            f"score={runbook.total_score}, recommendation={runbook.recommendation}"
        )

        # Update book fields from eval runbook data (similar to analysis worker)
        # This ensures the book's value fields reflect the FMV analysis
        updates_applied = []
        if runbook.fmv_low is not None:
            book.value_low = runbook.fmv_low
            updates_applied.append("value_low")
        if runbook.fmv_high is not None:
            book.value_high = runbook.fmv_high
            updates_applied.append("value_high")
        if runbook.fmv_low is not None and runbook.fmv_high is not None:
            book.value_mid = (runbook.fmv_low + runbook.fmv_high) / 2
            updates_applied.append("value_mid")
        if runbook.condition_grade:
            book.condition_grade = runbook.condition_grade
            updates_applied.append("condition_grade")

        # Recalculate discount_pct if FMV values changed
        if "value_mid" in updates_applied or "value_low" in updates_applied or "value_high" in updates_applied:
            from app.services.scoring import recalculate_discount_pct

            recalculate_discount_pct(book)

        if updates_applied:
            logger.info(f"Updated book {book_id} fields from eval runbook: {updates_applied}")

        # Mark job as completed
        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        job.updated_at = datetime.now(UTC)
        db.commit()

        logger.info(f"Eval runbook job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"Error processing eval runbook job {job_id}: {e}", exc_info=True)

        # Mark job as failed
        if job:
            job.status = "failed"
            job.error_message = str(e)[:1000]  # Truncate long errors
            job.updated_at = datetime.now(UTC)
            db.commit()

        raise

    finally:
        db.close()
