"""Analysis worker Lambda handler.

Processes SQS messages to generate book analysis asynchronously.
"""

import json
import logging
from datetime import UTC, datetime

from app.config import get_settings
from app.db import SessionLocal
from app.models import AnalysisJob, Book, BookAnalysis
from app.services.analysis_summary import (
    extract_book_updates_from_yaml,
    parse_analysis_summary,
)
from app.services.bedrock import (
    build_bedrock_messages,
    fetch_book_images_for_bedrock,
    fetch_source_url_content,
    invoke_bedrock,
)
from app.services.reference import get_or_create_binder
from app.utils.markdown_parser import parse_analysis_markdown

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

settings = get_settings()


def handler(event: dict, context) -> dict:
    """Lambda handler for SQS analysis job messages.

    Args:
        event: SQS event containing batch of messages
        context: Lambda context

    Returns:
        Dict with batch item failures for partial batch response
    """
    batch_item_failures = []

    for record in event.get("Records", []):
        message_id = record.get("messageId", "unknown")

        try:
            # Parse message body
            body = json.loads(record["body"])
            job_id = body["job_id"]
            book_id = body["book_id"]
            model = body.get("model", "sonnet")

            logger.info(f"Processing job {job_id} for book {book_id}, model={model}")

            # Process the job
            process_analysis_job(job_id, book_id, model)

            logger.info(f"Successfully processed job {job_id}")

        except Exception as e:
            logger.error(f"Failed to process message {message_id}: {e}", exc_info=True)
            # Report this message as failed for partial batch failure
            batch_item_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_item_failures}


def process_analysis_job(job_id: str, book_id: int, model: str) -> None:
    """Process a single analysis job.

    Args:
        job_id: UUID of the analysis job
        book_id: ID of the book to analyze
        model: Model to use (sonnet or opus)

    Raises:
        Exception: If processing fails
    """
    db = SessionLocal()
    job = None

    try:
        # Get the job record
        job = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
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

        # Build book metadata dict (same as sync endpoint)
        book_data = {
            "title": book.title,
            "author": book.author.name if book.author else None,
            "publisher": book.publisher.name if book.publisher else None,
            "publisher_tier": book.publisher.tier if book.publisher else None,
            "publication_date": book.publication_date,
            "volumes": book.volumes,
            "binding_type": book.binding_type,
            "binder": book.binder.name if book.binder else None,
            "condition_notes": book.condition_notes,
            "purchase_price": float(book.purchase_price) if book.purchase_price else None,
        }

        # Fetch source URL content if available
        logger.info(f"Fetching source URL content for book {book_id}")
        source_content = fetch_source_url_content(book.source_url)

        # Fetch images
        logger.info(f"Fetching images for book {book_id}")
        images = fetch_book_images_for_bedrock(book.images)

        # Build messages and invoke Bedrock
        logger.info(f"Building Bedrock messages for book {book_id}")
        messages = build_bedrock_messages(book_data, images, source_content)

        logger.info(f"Invoking Bedrock for book {book_id}, model={model}")
        analysis_text = invoke_bedrock(messages, model=model)
        logger.info(f"Bedrock returned {len(analysis_text)} chars for book {book_id}")

        # Parse markdown to extract structured fields
        parsed = parse_analysis_markdown(analysis_text)

        # Parse YAML summary block to extract book field updates
        yaml_data = parse_analysis_summary(analysis_text)
        book_updates = extract_book_updates_from_yaml(yaml_data)

        # Delete existing analysis if present
        if book.analysis:
            db.delete(book.analysis)
            db.flush()

        # Create new analysis
        analysis = BookAnalysis(
            book_id=book_id,
            full_markdown=analysis_text,
            executive_summary=parsed.executive_summary,
            historical_significance=parsed.historical_significance,
            condition_assessment=parsed.condition_assessment,
            market_analysis=parsed.market_analysis,
            recommendations=parsed.recommendations,
        )
        db.add(analysis)

        # Update book fields from YAML summary
        if book_updates:
            logger.info(
                f"Updating book {book_id} with YAML summary data: {list(book_updates.keys())}"
            )

            # Update value fields
            if "value_low" in book_updates:
                book.value_low = book_updates["value_low"]
            if "value_high" in book_updates:
                book.value_high = book_updates["value_high"]
            if "value_mid" in book_updates:
                book.value_mid = book_updates["value_mid"]

            # Update condition_grade
            if "condition_grade" in book_updates:
                book.condition_grade = book_updates["condition_grade"]

            # Update acquisition_cost only if not already set by user
            if "acquisition_cost" in book_updates and book.acquisition_cost is None:
                book.acquisition_cost = book_updates["acquisition_cost"]
            # If no acquisition_cost in YAML and book has none, use purchase_price
            elif book.acquisition_cost is None and book.purchase_price is not None:
                book.acquisition_cost = book.purchase_price

            # Update provenance
            if "provenance" in book_updates:
                book.provenance = book_updates["provenance"]

            # Update binding_type
            if "binding_type" in book_updates:
                book.binding_type = book_updates["binding_type"]

            # Update edition
            if "edition" in book_updates:
                book.edition = book_updates["edition"]

        # Extract binder identification and associate with book
        if parsed.binder_identification:
            binder = get_or_create_binder(db, parsed.binder_identification)
            if binder and book.binder_id != binder.id:
                logger.info(
                    f"Associating binder {binder.name} (tier={binder.tier}) with book {book_id}"
                )
                book.binder_id = binder.id

        # Mark job as completed
        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        job.updated_at = datetime.now(UTC)
        db.commit()

        logger.info(f"Analysis job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}", exc_info=True)

        # Mark job as failed
        if job:
            job.status = "failed"
            job.error_message = str(e)[:1000]  # Truncate long errors
            job.updated_at = datetime.now(UTC)
            db.commit()

        raise

    finally:
        db.close()
