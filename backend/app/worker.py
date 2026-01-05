"""Analysis worker Lambda handler.

Processes SQS messages to generate book analysis asynchronously.
"""

import json
import logging
from datetime import UTC, datetime
from decimal import Decimal

from app.config import get_settings
from app.constants import DEFAULT_ANALYSIS_MODEL
from app.db import SessionLocal
from app.models import AnalysisJob, Book, BookAnalysis, BookImage
from app.services.analysis_parser import (
    apply_metadata_to_book,
    extract_analysis_metadata,
    strip_metadata_block,
)
from app.services.analysis_summary import (
    extract_book_updates_from_yaml,
    parse_analysis_summary,
)
from app.services.bedrock import (
    build_bedrock_messages,
    extract_structured_data,
    fetch_book_images_for_bedrock,
    fetch_source_url_content,
    get_model_id,
    invoke_bedrock,
)
from app.services.reference import get_or_create_binder
from app.services.scoring import calculate_and_persist_book_scores
from app.utils.markdown_parser import parse_analysis_markdown
from app.version import get_version

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

settings = get_settings()


def format_analysis_error(error: Exception, image_count: int = 0) -> str:
    """Format error message with helpful context for analysis failures.

    Args:
        error: The exception that occurred
        image_count: Number of images associated with the book

    Returns:
        Formatted error message with context for input-too-long errors,
        or the original error message for other errors.
    """
    from botocore.exceptions import ClientError

    error_str = str(error)

    # Check for Bedrock input size limit errors
    is_input_size_error = False
    if isinstance(error, ClientError):
        error_code = error.response.get("Error", {}).get("Code", "")
        error_message = error.response.get("Error", {}).get("Message", "")
        if error_code == "ValidationException" and "too long" in error_message.lower():
            is_input_size_error = True
    # Fallback for string representation (e.g., in tests)
    elif "Input is too long" in error_str or "ValidationException" in error_str:
        is_input_size_error = True

    if is_input_size_error:
        return (
            f"{error_str}. "
            f"This book has {image_count} images. "
            f"Try resizing images to 800px max dimension to reduce payload size."
        )

    return error_str


def handler(event: dict, context) -> dict:
    """Lambda handler for SQS analysis job messages.

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
                    "worker": "analysis",
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
            model = body.get("model", DEFAULT_ANALYSIS_MODEL)

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
            "binder_tier": book.binder.tier if book.binder else None,
            "binder_authentication_markers": book.binder.authentication_markers
            if book.binder
            else None,
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

        # Extract metadata BEFORE stripping (so we can still parse it)
        metadata = extract_analysis_metadata(analysis_text)

        # Strip metadata block from analysis for clean storage and display
        clean_analysis_text, was_stripped = strip_metadata_block(analysis_text)
        if was_stripped:
            chars_removed = len(analysis_text) - len(clean_analysis_text)
            logger.info(
                f"Stripped metadata block ({chars_removed} chars removed), "
                f"{len(clean_analysis_text)} chars remaining"
            )
        else:
            logger.warning("No metadata block found to strip")

        # Stage 2: Extract structured data with focused prompt
        logger.info(f"Extracting structured data for book {book_id}")
        extracted_data = extract_structured_data(clean_analysis_text, model="sonnet")
        if extracted_data:
            logger.info(f"Extracted {len(extracted_data)} fields for book {book_id}")
        else:
            logger.warning(f"No structured data extracted for book {book_id}")

        # Parse markdown to extract structured fields
        parsed = parse_analysis_markdown(clean_analysis_text)

        # Prefer Stage 2 extraction, fall back to parsing analysis text
        # Track extraction status for UI indicator
        extraction_status = None  # Will be set based on extraction path
        if extracted_data:
            # Map extracted fields to book update format
            book_updates = {}
            if extracted_data.get("valuation_low"):
                book_updates["value_low"] = Decimal(str(extracted_data["valuation_low"]))
            if extracted_data.get("valuation_high"):
                book_updates["value_high"] = Decimal(str(extracted_data["valuation_high"]))
            if extracted_data.get("valuation_mid"):
                book_updates["value_mid"] = Decimal(str(extracted_data["valuation_mid"]))
            elif "value_low" in book_updates and "value_high" in book_updates:
                book_updates["value_mid"] = (
                    book_updates["value_low"] + book_updates["value_high"]
                ) / 2
            if extracted_data.get("condition_grade"):
                book_updates["condition_grade"] = extracted_data["condition_grade"]
            if extracted_data.get("binding_type"):
                book_updates["binding_type"] = extracted_data["binding_type"]
            # Provenance fields
            if extracted_data.get("has_provenance") is True:
                book_updates["has_provenance"] = True
            if extracted_data.get("provenance_tier"):
                book_updates["provenance_tier"] = extracted_data["provenance_tier"]
            if extracted_data.get("provenance_description"):
                book_updates["provenance"] = extracted_data["provenance_description"]
            if extracted_data.get("is_first_edition") is not None:
                book_updates["is_first_edition"] = extracted_data["is_first_edition"]

            logger.info(f"Using extracted data for book {book_id}: {list(book_updates.keys())}")
            extraction_status = "success"
        else:
            # Fall back to parsing analysis text directly
            yaml_data = parse_analysis_summary(clean_analysis_text)
            book_updates = extract_book_updates_from_yaml(yaml_data)
            logger.info(f"Fell back to YAML parsing for book {book_id}")
            extraction_status = "degraded"

        # Delete existing analysis if present
        if book.analysis:
            db.delete(book.analysis)
            db.flush()

        # Create new analysis (using clean text without metadata block)
        analysis = BookAnalysis(
            book_id=book_id,
            full_markdown=clean_analysis_text,
            executive_summary=parsed.executive_summary,
            historical_significance=parsed.historical_significance,
            condition_assessment=parsed.condition_assessment,
            market_analysis=parsed.market_analysis,
            recommendations=parsed.recommendations,
            extraction_status=extraction_status,
            model_id=get_model_id(model),
        )
        db.add(analysis)

        # Apply metadata (already extracted before stripping)
        if metadata:
            updated_fields = apply_metadata_to_book(book, metadata)
            if updated_fields:
                logger.info(
                    f"Applied analysis metadata to book {book_id}: {', '.join(updated_fields)}"
                )

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

            # Recalculate discount_pct if FMV values changed
            if (
                "value_mid" in book_updates
                or "value_low" in book_updates
                or "value_high" in book_updates
            ):
                from app.services.scoring import recalculate_discount_pct

                recalculate_discount_pct(book)

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

            # Update provenance fields (from two-stage extraction)
            if "has_provenance" in book_updates:
                book.has_provenance = book_updates["has_provenance"]
            if "provenance_tier" in book_updates:
                book.provenance_tier = book_updates["provenance_tier"]
            if "is_first_edition" in book_updates:
                book.is_first_edition = book_updates["is_first_edition"]

        # Extract binder identification and associate with book
        if parsed.binder_identification:
            binder = get_or_create_binder(db, parsed.binder_identification)
            if binder and book.binder_id != binder.id:
                logger.info(
                    f"Associating binder {binder.name} (tier={binder.tier}) with book {book_id}"
                )
                book.binder_id = binder.id

        # Calculate and persist scores after analysis updates
        logger.info(f"Calculating scores for book {book_id}")
        scores = calculate_and_persist_book_scores(book, db)
        logger.info(f"Scores calculated for book {book_id}: overall={scores['overall_score']}")

        # Mark job as completed
        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        job.updated_at = datetime.now(UTC)
        db.commit()

        logger.info(f"Analysis job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}", exc_info=True)

        # Mark job as failed - Issue #815: must set completed_at too
        if job:
            job.status = "failed"
            image_count = db.query(BookImage).filter(BookImage.book_id == book_id).count()
            job.error_message = format_analysis_error(e, image_count)[:1000]
            job.completed_at = datetime.now(UTC)
            job.updated_at = datetime.now(UTC)
            db.commit()

        raise

    finally:
        db.close()
