"""Books API endpoints."""

import logging
import os
import tempfile
import traceback
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import boto3
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import exists, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1.images import (
    LOCAL_IMAGES_PATH,
    S3_IMAGES_PREFIX,
    generate_thumbnail,
    get_cloudfront_url,
    get_thumbnail_key,
)
from app.auth import require_admin, require_editor, require_viewer
from app.cache import get_redis
from app.config import get_settings
from app.db import get_db
from app.enums import OWNED_STATUSES
from app.models import (
    AnalysisJob,
    Author,
    Binder,
    Book,
    BookAnalysis,
    BookImage,
    EvalRunbook,
    EvalRunbookJob,
    Publisher,
)
from app.schemas.analysis_job import AnalysisJobResponse
from app.schemas.book import (
    AcquireRequest,
    BookCreate,
    BookListParams,
    BookListResponse,
    BookResponse,
    BookSpotlightItem,
    BookUpdate,
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    DuplicateMatch,
    TrackingRequest,
)
from app.schemas.eval_runbook_job import EvalRunbookJobResponse
from app.services.analysis_parser import (
    apply_metadata_to_book,
    extract_analysis_metadata,
)
from app.services.archive import archive_url
from app.services.bedrock import (
    build_bedrock_messages,
    extract_structured_data,
    fetch_book_images_for_bedrock,
    fetch_source_url_content,
    get_model_id,
    invoke_bedrock,
)
from app.services.book_queries import get_other_books_by_author
from app.services.entity_validation import (
    validate_and_associate_entities,
)
from app.services.job_manager import handle_stale_jobs
from app.services.scoring import (
    author_tier_to_score,
    calculate_all_scores_with_breakdown,
    calculate_and_persist_book_scores,
    calculate_title_similarity,
    get_author_owned_book_count,
    is_duplicate_title,
    recalculate_discount_pct,
    recalculate_roi_pct,
)
from app.services.sqs import send_analysis_job, send_eval_runbook_job
from app.services.tracking import process_tracking
from app.services.tracking_poller import refresh_single_book_tracking
from app.utils.date_parser import compute_era, parse_publication_date
from app.utils.edition_parser import is_first_edition_text
from app.utils.errors import (
    ConflictError,
    ExternalServiceError,
    ValidationError,
    log_and_raise,
)
from app.utils.markdown_parser import parse_analysis_markdown, strip_structured_data

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()

# Analysis job timeout threshold (matches Lambda timeout)
STALE_JOB_THRESHOLD_MINUTES = 15


def get_api_base_url() -> str:
    """Get the API base URL for constructing absolute URLs."""
    if settings.is_production:
        return "https://api.bluemoxon.com"
    elif settings.is_aws_lambda:
        return "https://staging.api.bluemoxon.com"
    return ""  # Relative URLs for local dev


def _get_active_eval_runbook_job_status(book_id: int, db: Session) -> str | None:
    """Get the status of an active eval runbook job for a book.

    Returns 'pending' or 'running' if there's an active job, None otherwise.
    """
    active_job = (
        db.query(EvalRunbookJob)
        .filter(
            EvalRunbookJob.book_id == book_id,
            EvalRunbookJob.status.in_(["pending", "running"]),
        )
        .first()
    )
    return active_job.status if active_job else None


def _get_active_analysis_job_status(book_id: int, db: Session) -> str | None:
    """Get the status of an active analysis job for a book.

    Returns 'pending' or 'running' if there's an active job, None otherwise.
    """
    active_job = (
        db.query(AnalysisJob)
        .filter(
            AnalysisJob.book_id == book_id,
            AnalysisJob.status.in_(["pending", "running"]),
        )
        .first()
    )
    return active_job.status if active_job else None


def _get_analysis_issues(book: Book) -> list[str] | None:
    """Get list of analysis issues for a book.

    Returns a list of issue codes or None if no issues:
    - 'truncated': recommendations section missing (output token exhaustion)
    - 'degraded': Stage 2 extraction used fallback parsing
    - 'missing_condition': condition_assessment is null
    - 'missing_market': market_analysis is null
    """
    if not book.analysis:
        return None

    issues = []

    # Check for truncated output (recommendations never generated)
    if book.analysis.recommendations is None:
        issues.append("truncated")

    # Check for degraded extraction (Stage 2 fallback)
    if book.analysis.extraction_status == "degraded":
        issues.append("degraded")

    # Check for missing condition assessment
    if book.analysis.condition_assessment is None:
        issues.append("missing_condition")

    # Check for missing market analysis
    if book.analysis.market_analysis is None:
        issues.append("missing_market")

    return issues if issues else None


def _apply_extracted_data_to_book(book: Book, extracted_data: dict[str, Any]) -> list[str]:
    """Apply extracted structured data to book, return list of updated fields.

    Maps AI-extracted fields to book model attributes. Used by re-extraction
    endpoints to update book values from analysis text.

    Args:
        book: The Book model instance to update
        extracted_data: Dict with keys like valuation_low, valuation_mid, etc.
            Valid keys: valuation_low, valuation_mid, valuation_high,
            condition_grade, binding_type, has_provenance, provenance_tier,
            provenance_description, is_first_edition

    Returns:
        List of field names that were updated
    """
    fields_updated = []

    # Valuation fields - use 'is not None' to allow zero values
    if extracted_data.get("valuation_low") is not None:
        book.value_low = Decimal(str(extracted_data["valuation_low"]))
        fields_updated.append("value_low")
    if extracted_data.get("valuation_high") is not None:
        book.value_high = Decimal(str(extracted_data["valuation_high"]))
        fields_updated.append("value_high")
    if extracted_data.get("valuation_mid") is not None:
        book.value_mid = Decimal(str(extracted_data["valuation_mid"]))
        fields_updated.append("value_mid")
    elif "value_low" in fields_updated and "value_high" in fields_updated:
        book.value_mid = (book.value_low + book.value_high) / 2
        fields_updated.append("value_mid")

    # String fields - truthy check is fine (empty string means no value)
    if extracted_data.get("condition_grade"):
        book.condition_grade = extracted_data["condition_grade"]
        fields_updated.append("condition_grade")
    if extracted_data.get("binding_type"):
        book.binding_type = extracted_data["binding_type"]
        fields_updated.append("binding_type")
    if extracted_data.get("provenance_tier"):
        book.provenance_tier = extracted_data["provenance_tier"]
        fields_updated.append("provenance_tier")
    if extracted_data.get("provenance_description"):
        book.provenance = extracted_data["provenance_description"]
        fields_updated.append("provenance")

    # Boolean fields - use 'is not None' to allow explicit False values
    if extracted_data.get("has_provenance") is not None:
        book.has_provenance = extracted_data["has_provenance"]
        fields_updated.append("has_provenance")
    if extracted_data.get("is_first_edition") is not None:
        book.is_first_edition = extracted_data["is_first_edition"]
        fields_updated.append("is_first_edition")

    return fields_updated


def _build_book_response(book: Book, db: Session) -> BookResponse:
    """Build a BookResponse with all computed fields.

    This is the single source of truth for building BookResponse objects.
    All endpoints returning a BookResponse should use this helper.

    Computed fields:
    - era: Computed from year_start/year_end (Pre-Romantic, Romantic, Victorian, etc.)
    - has_analysis: Whether book has analysis
    - has_eval_runbook: Whether book has eval runbook
    - eval_runbook_job_status: Status of active eval runbook job
    - analysis_job_status: Status of active analysis job
    - analysis_issues: List of analysis quality issues
    - image_count: Number of images
    - primary_image_url: URL to primary image (CloudFront in prod, API in dev)
    """
    book_dict = BookResponse.model_validate(book).model_dump()
    book_dict["era"] = compute_era(book.year_start, book.year_end).value
    book_dict["has_analysis"] = book.analysis is not None
    book_dict["has_eval_runbook"] = book.eval_runbook is not None
    book_dict["eval_runbook_job_status"] = _get_active_eval_runbook_job_status(book.id, db)
    book_dict["analysis_job_status"] = _get_active_analysis_job_status(book.id, db)
    book_dict["analysis_issues"] = _get_analysis_issues(book)
    book_dict["image_count"] = len(book.images) if book.images else 0

    # Get primary image URL
    primary_image = None
    if book.images:
        # First try to find one marked as primary
        for img in book.images:
            if img.is_primary:
                primary_image = img
                break
        # Otherwise use first image by display order
        if not primary_image:
            primary_image = min(book.images, key=lambda x: x.display_order)

    if primary_image:
        if settings.is_aws_lambda:
            book_dict["primary_image_url"] = get_cloudfront_url(primary_image.s3_key)
        else:
            base_url = settings.base_url or "http://localhost:8000"
            book_dict["primary_image_url"] = (
                f"{base_url}/api/v1/books/{book.id}/images/{primary_image.id}/file"
            )

    return BookResponse(**book_dict)


def _copy_listing_images_to_book(book_id: int, listing_s3_keys: list[str], db: Session) -> None:
    """Copy images from listing folder to book folder and create BookImage records.

    Also generates thumbnails for each image.

    Args:
        book_id: ID of the book to associate images with
        listing_s3_keys: S3 keys of images in listings/{item_id}/ format
        db: Database session
    """
    bucket_name = settings.images_bucket
    if not bucket_name:
        logger.warning("images_bucket not configured, skipping image copy")
        return

    if not listing_s3_keys:
        return

    s3 = boto3.client("s3")

    for idx, source_key in enumerate(listing_s3_keys):
        try:
            # Determine file extension from source key
            ext = source_key.split(".")[-1] if "." in source_key else "jpg"
            # s3_key is the relative path (used for URL generation with S3_IMAGES_PREFIX)
            s3_key = f"{book_id}/image_{idx:02d}.{ext}"
            # Full S3 path includes books/ prefix
            target_key = f"books/{s3_key}"
            thumbnail_key = f"books/thumb_{s3_key}"

            # Copy object within same bucket
            s3.copy_object(
                Bucket=bucket_name,
                CopySource={"Bucket": bucket_name, "Key": source_key},
                Key=target_key,
            )

            # Generate thumbnail: download, resize, upload
            with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp_img:
                local_path = Path(tmp_img.name)
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_thumb:
                thumb_path = Path(tmp_thumb.name)
            try:
                s3.download_file(bucket_name, target_key, str(local_path))
                success, _ = generate_thumbnail(local_path, thumb_path)
                if success and thumb_path.exists():
                    s3.upload_file(
                        str(thumb_path),
                        bucket_name,
                        thumbnail_key,
                        ExtraArgs={"ContentType": "image/jpeg"},
                    )
                    logger.info(f"Generated thumbnail -> {thumbnail_key}")
            except Exception as thumb_err:
                logger.warning(f"Thumbnail generation failed for {s3_key}: {thumb_err}")
            finally:
                # Clean up temp files
                if local_path.exists():
                    local_path.unlink()
                if thumb_path.exists():
                    thumb_path.unlink()

            # Create BookImage record (s3_key without books/ prefix)
            book_image = BookImage(
                book_id=book_id,
                s3_key=s3_key,
                display_order=idx,
                is_primary=(idx == 0),
            )
            db.add(book_image)

            logger.info(f"Copied {source_key} -> {target_key}")

        except Exception as e:
            logger.error(f"Failed to copy image {source_key}: {e}")
            # Continue with other images even if one fails

    db.commit()
    logger.info(f"Copied {len(listing_s3_keys)} images for book {book_id}")


@router.get("", response_model=BookListResponse)
def list_books(
    params: BookListParams = Depends(),
    db: Session = Depends(get_db),
    _user=Depends(require_viewer),
):
    """List books with filtering and pagination."""
    # Validate mutual exclusion: cannot pass both field and field__isnull
    if params.category is not None and params.category__isnull is not None:
        raise HTTPException(
            status_code=400,
            detail="Cannot specify both 'category' and 'category__isnull' - they are mutually exclusive",
        )
    if params.condition_grade is not None and params.condition_grade__isnull is not None:
        raise HTTPException(
            status_code=400,
            detail="Cannot specify both 'condition_grade' and 'condition_grade__isnull' - they are mutually exclusive",
        )

    query = db.query(Book)

    # Apply search query
    if params.q:
        search_term = f"%{params.q}%"
        query = query.outerjoin(Author, Book.author_id == Author.id).filter(
            (Book.title.ilike(search_term))
            | (Author.name.ilike(search_term))
            | (Book.notes.ilike(search_term))
            | (Book.binding_description.ilike(search_term))
        )

    # Apply filters
    if params.inventory_type:
        query = query.filter(Book.inventory_type == params.inventory_type)
    if params.category:
        query = query.filter(Book.category == params.category)
    if params.category__isnull is not None:
        if params.category__isnull:
            query = query.filter(Book.category.is_(None))
        else:
            query = query.filter(Book.category.isnot(None))
    if params.status:
        query = query.filter(Book.status == params.status)
    if params.publisher_id:
        query = query.filter(Book.publisher_id == params.publisher_id)
    if params.publisher_tier:
        query = query.join(Publisher).filter(Publisher.tier == params.publisher_tier)
    if params.author_id:
        query = query.filter(Book.author_id == params.author_id)
    if params.binder_id:
        query = query.filter(Book.binder_id == params.binder_id)
    if params.binding_authenticated is not None:
        query = query.filter(Book.binding_authenticated == params.binding_authenticated)
    if params.binding_type:
        query = query.filter(Book.binding_type == params.binding_type)
    if params.condition_grade:
        query = query.filter(Book.condition_grade == params.condition_grade)
    if params.condition_grade__isnull is not None:
        if params.condition_grade__isnull:
            query = query.filter(Book.condition_grade.is_(None))
        else:
            query = query.filter(Book.condition_grade.isnot(None))
    if params.min_value is not None:
        query = query.filter(Book.value_mid >= params.min_value)
    if params.max_value is not None:
        query = query.filter(Book.value_mid <= params.max_value)
    if params.year_start is not None:
        query = query.filter(Book.year_start >= params.year_start)
    if params.year_end is not None:
        query = query.filter(Book.year_end <= params.year_end)

    # Filter by date_acquired (maps to purchase_date in database)
    if params.date_acquired:
        query = query.filter(Book.purchase_date == params.date_acquired)

    # Filter by has_images
    if params.has_images is not None:
        image_exists = exists().where(BookImage.book_id == Book.id)
        if params.has_images:
            query = query.filter(image_exists)
        else:
            query = query.filter(~image_exists)

    # Filter by has_analysis
    if params.has_analysis is not None:
        analysis_exists = exists().where(BookAnalysis.book_id == Book.id)
        if params.has_analysis:
            query = query.filter(analysis_exists)
        else:
            query = query.filter(~analysis_exists)

    # Filter by has_provenance (boolean field)
    if params.has_provenance is not None:
        query = query.filter(Book.has_provenance == params.has_provenance)

    # Filter by provenance_tier
    if params.provenance_tier:
        query = query.filter(Book.provenance_tier == params.provenance_tier)

    # Filter by is_first_edition
    if params.is_first_edition is not None:
        query = query.filter(Book.is_first_edition == params.is_first_edition)

    # Filter by era (computed from year_start with year_end fallback)
    if params.era:
        from app.enums import Era

        # Use COALESCE to prefer year_start, fall back to year_end
        year_col = func.coalesce(Book.year_start, Book.year_end)
        if params.era == Era.PRE_ROMANTIC:
            query = query.filter(year_col < 1800)
        elif params.era == Era.ROMANTIC:
            query = query.filter(year_col >= 1800, year_col <= 1836)
        elif params.era == Era.VICTORIAN:
            query = query.filter(year_col >= 1837, year_col <= 1901)
        elif params.era == Era.EDWARDIAN:
            query = query.filter(year_col >= 1902, year_col <= 1910)
        elif params.era == Era.POST_1910:
            query = query.filter(year_col > 1910)
        elif params.era == Era.UNKNOWN:
            # Both year_start and year_end are NULL
            query = query.filter(Book.year_start.is_(None), Book.year_end.is_(None))

    # Get total count
    total = query.count()

    # Apply sorting
    sort_column = getattr(Book, params.sort_by, Book.title)
    if params.sort_order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    # Apply pagination
    offset = (params.page - 1) * params.per_page
    books = query.offset(offset).limit(params.per_page).all()

    # Build response
    base_url = get_api_base_url()

    # Batch fetch active job statuses to avoid N+1 queries
    book_ids = [book.id for book in books]
    active_eval_jobs = (
        db.query(EvalRunbookJob.book_id, EvalRunbookJob.status)
        .filter(
            EvalRunbookJob.book_id.in_(book_ids),
            EvalRunbookJob.status.in_(["pending", "running"]),
        )
        .all()
    )
    eval_job_status_map = {job.book_id: job.status for job in active_eval_jobs}

    active_analysis_jobs = (
        db.query(AnalysisJob.book_id, AnalysisJob.status)
        .filter(
            AnalysisJob.book_id.in_(book_ids),
            AnalysisJob.status.in_(["pending", "running"]),
        )
        .all()
    )
    analysis_job_status_map = {job.book_id: job.status for job in active_analysis_jobs}

    items = []
    for book in books:
        book_dict = BookResponse.model_validate(book).model_dump()
        book_dict["era"] = compute_era(book.year_start, book.year_end).value
        book_dict["has_analysis"] = book.analysis is not None
        book_dict["has_eval_runbook"] = book.eval_runbook is not None
        book_dict["eval_runbook_job_status"] = eval_job_status_map.get(book.id)
        book_dict["analysis_job_status"] = analysis_job_status_map.get(book.id)
        book_dict["analysis_issues"] = _get_analysis_issues(book)
        book_dict["image_count"] = len(book.images) if book.images else 0

        # Get primary image URL
        primary_image = None
        if book.images:
            # First try to find one marked as primary
            for img in book.images:
                if img.is_primary:
                    primary_image = img
                    break
            # Otherwise use first image by display order
            if not primary_image:
                primary_image = min(book.images, key=lambda x: x.display_order)

        if primary_image:
            if settings.is_aws_lambda:
                # Use CloudFront CDN URL in production
                book_dict["primary_image_url"] = get_cloudfront_url(primary_image.s3_key)
            else:
                # Use API endpoint for local development
                book_dict["primary_image_url"] = (
                    f"{base_url}/api/v1/books/{book.id}/images/{primary_image.id}/file"
                )

        items.append(BookResponse(**book_dict))

    return BookListResponse(
        items=items,
        total=total,
        page=params.page,
        per_page=params.per_page,
        pages=(total + params.per_page - 1) // params.per_page,
    )


@router.get("/top", response_model=list[BookSpotlightItem])
def get_top_books(
    limit: int = Query(default=34, ge=1, le=100, description="Number of top books to return"),
    inventory_type: str = Query(default="PRIMARY", description="Inventory type filter"),
    db: Session = Depends(get_db),
    _user=Depends(require_viewer),
):
    """Get top books by value for Collection Spotlight feature.

    Returns lightweight book data optimized for spotlight display.
    Results are cached for 5 minutes in Redis.

    Args:
        limit: Number of books to return (default 34, ~20% of ~170 books)
        inventory_type: Filter by inventory type (default PRIMARY)
    """
    cache_key = f"books:top:{inventory_type}:{limit}"
    client = get_redis()

    if client:
        try:
            cached_value = client.get(cache_key)
            if cached_value:
                logger.debug(f"Top books cache HIT: {cache_key}")
                import json

                cached_data = json.loads(cached_value)
                return [BookSpotlightItem(**item) for item in cached_data]
        except Exception as e:
            logger.warning(f"Top books cache GET failed: {e}")

    logger.debug(f"Top books cache MISS: {cache_key}")

    books = (
        db.query(Book)
        .outerjoin(Author, Book.author_id == Author.id)
        .outerjoin(Binder, Book.binder_id == Binder.id)
        .outerjoin(Publisher, Book.publisher_id == Publisher.id)
        .filter(
            Book.inventory_type == inventory_type,
            Book.value_mid > 0,
            Book.status.in_(OWNED_STATUSES),
        )
        .order_by(Book.value_mid.desc())
        .limit(limit)
        .all()
    )

    items = []
    for book in books:
        primary_image_url = None
        if book.images:
            primary_image = None
            for img in book.images:
                if img.is_primary:
                    primary_image = img
                    break
            if not primary_image:
                primary_image = min(book.images, key=lambda x: x.display_order)

            if primary_image:
                if settings.is_aws_lambda:
                    primary_image_url = get_cloudfront_url(primary_image.s3_key)
                else:
                    base_url = settings.base_url or "http://localhost:8000"
                    primary_image_url = (
                        f"{base_url}/api/v1/books/{book.id}/images/{primary_image.id}/file"
                    )

        items.append(
            BookSpotlightItem(
                id=book.id,
                title=book.title,
                author_name=book.author.name if book.author else None,
                value_mid=book.value_mid,
                primary_image_url=primary_image_url,
                binder_name=book.binder.name if book.binder else None,
                binding_authenticated=book.binding_authenticated,
                binding_type=book.binding_type,
                year_start=book.year_start,
                year_end=book.year_end,
                publisher_name=book.publisher.name if book.publisher else None,
                category=book.category,
            )
        )

    if client:
        try:
            import json

            serialized = json.dumps([item.model_dump(mode="json") for item in items])
            client.setex(cache_key, 300, serialized)
            logger.debug(f"Top books cached: {cache_key}")
        except Exception as e:
            logger.warning(f"Top books cache SET failed: {e}")

    return items


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db), _user=Depends(require_viewer)):
    """Get a single book by ID."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    return _build_book_response(book, db)


@router.post("/check-duplicate", response_model=DuplicateCheckResponse)
def check_duplicate(
    request: DuplicateCheckRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Check for potential duplicate books before creating a new one.

    Returns books with similar titles, optionally filtered by same author.
    Uses token-based Jaccard similarity with 0.7 threshold.
    """
    similarity_threshold = 0.7

    # Query existing books
    query = db.query(Book)

    # If author specified, check for same author
    if request.author_id:
        query = query.filter(Book.author_id == request.author_id)

    existing_books = query.all()

    matches = []
    for book in existing_books:
        similarity = calculate_title_similarity(request.title, book.title)
        if similarity >= similarity_threshold:
            matches.append(
                DuplicateMatch(
                    id=book.id,
                    title=book.title,
                    author_name=book.author.name if book.author else None,
                    status=book.status,
                    similarity_score=round(similarity, 2),
                )
            )

    # Sort by similarity descending
    matches.sort(key=lambda m: m.similarity_score, reverse=True)

    return DuplicateCheckResponse(
        has_duplicates=len(matches) > 0,
        matches=matches[:10],  # Limit to top 10 matches
    )


@router.post("", response_model=BookResponse, status_code=201)
def create_book(
    book_data: BookCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Create a new book. Requires editor role."""
    # Extract listing_s3_keys before creating book (not a Book model field)
    listing_s3_keys = book_data.listing_s3_keys
    book_dict = book_data.model_dump(exclude={"listing_s3_keys"})
    book = Book(**book_dict)

    # Auto-parse year_start/year_end from publication_date if not explicitly provided
    # Uses enhanced parser that handles formats like: 1851, 1867-1880, 1880s, c.1890, etc.
    if book.publication_date and book.year_start is None and book.year_end is None:
        year_start, year_end = parse_publication_date(book.publication_date)
        book.year_start = year_start
        book.year_end = year_end

    # Auto-infer is_first_edition from edition text if not explicitly set
    # Only infer if is_first_edition is None (don't override explicit user choices)
    if book.is_first_edition is None and book.edition:
        inferred = is_first_edition_text(book.edition)
        if inferred is not None:
            book.is_first_edition = inferred

    # Auto-set binding_authenticated when binder is selected
    if book.binder_id:
        book.binding_authenticated = True

    db.add(book)
    db.commit()
    db.refresh(book)

    # Calculate ROI if both value_mid and acquisition_cost are provided
    # Only call if inputs exist to preserve any manually set values
    if book.value_mid is not None and book.acquisition_cost is not None:
        recalculate_roi_pct(book)

    # Calculate discount_pct if both value_mid and purchase_price are provided
    # Only call if inputs exist to preserve any manually set values
    if book.value_mid is not None and book.purchase_price is not None:
        recalculate_discount_pct(book)

    # Copy images from listing folder to book folder if S3 keys provided
    if listing_s3_keys:
        _copy_listing_images_to_book(book.id, listing_s3_keys, db)

    # Auto-calculate scores
    calculate_and_persist_book_scores(book, db)
    db.commit()
    db.refresh(book)

    # Queue async eval runbook job for new books with source_url (imported from eBay)
    # This runs full AI analysis + FMV lookup in a background Lambda worker
    if book.source_url:
        try:
            # Create eval runbook job for async processing
            job = EvalRunbookJob(book_id=book.id)
            db.add(job)
            db.commit()
            db.refresh(job)

            # Send job to SQS queue for background processing
            send_eval_runbook_job(job_id=str(job.id), book_id=book.id)
            logger.info(f"Queued eval runbook job {job.id} for book {book.id}")
        except Exception as e:
            # Log but don't fail book creation if job queuing fails
            logger.warning(f"Failed to queue eval runbook job for book {book.id}: {e}")

    return _build_book_response(book, db)


@router.put("/{book_id}", response_model=BookResponse)
def update_book(
    book_id: int,
    book_data: BookUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Update a book. Requires editor role."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    update_data = book_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(book, field, value)

    # Auto-parse year_start/year_end if publication_date changed but year fields not explicitly set
    # Uses enhanced parser that handles formats like: 1851, 1867-1880, 1880s, c.1890, etc.
    if (
        "publication_date" in update_data
        and book.publication_date
        and "year_start" not in update_data
        and "year_end" not in update_data
    ):
        year_start, year_end = parse_publication_date(book.publication_date)
        book.year_start = year_start
        book.year_end = year_end

    # Auto-set binding_authenticated when binder is set/unset
    if "binder_id" in update_data:
        book.binding_authenticated = book.binder_id is not None

    # Auto-set has_provenance when provenance text is set/cleared
    # Only auto-derive if has_provenance wasn't explicitly set in this update
    if "provenance" in update_data and "has_provenance" not in update_data:
        book.has_provenance = bool(book.provenance and book.provenance.strip())
        # Clear tier if provenance is now empty
        if not book.has_provenance:
            book.provenance_tier = None

    # Auto-infer is_first_edition from edition text when edition is updated
    # Only infer if is_first_edition wasn't explicitly set in this update
    # and the book doesn't already have an explicit is_first_edition value
    if (
        "edition" in update_data
        and book.edition
        and "is_first_edition" not in update_data
        and book.is_first_edition is None
    ):
        inferred = is_first_edition_text(book.edition)
        if inferred is not None:
            book.is_first_edition = inferred

    # Recalculate discount_pct if relevant values changed (value_mid or purchase_price)
    # Formula: (value_mid - purchase_price) / value_mid - only these two inputs matter
    if "value_mid" in update_data or "purchase_price" in update_data:
        recalculate_discount_pct(book)

    # Recalculate roi_pct if relevant values changed (value_mid or acquisition_cost)
    if "value_mid" in update_data or "acquisition_cost" in update_data:
        recalculate_roi_pct(book)

    db.commit()
    db.refresh(book)

    return _build_book_response(book, db)


@router.delete("/{book_id}", status_code=204)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Delete a book and all associated images/analysis. Requires editor role."""
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        # Get all images for this book before deleting
        book_images = db.query(BookImage).filter(BookImage.book_id == book_id).all()
        logger.info("Deleting book %s with %d images", book_id, len(book_images))

        # Defense-in-depth: Explicitly delete all related records before deleting book
        # This prevents orphaned records even if CASCADE deletes are misconfigured
        jobs_deleted = db.query(AnalysisJob).filter(AnalysisJob.book_id == book_id).delete()
        eval_jobs_deleted = (
            db.query(EvalRunbookJob).filter(EvalRunbookJob.book_id == book_id).delete()
        )
        analyses_deleted = db.query(BookAnalysis).filter(BookAnalysis.book_id == book_id).delete()
        runbooks_deleted = db.query(EvalRunbook).filter(EvalRunbook.book_id == book_id).delete()
        images_deleted = db.query(BookImage).filter(BookImage.book_id == book_id).delete()
        logger.info(
            "Pre-delete cleanup for book %s: %d jobs, %d eval_jobs, %d analyses, "
            "%d runbooks, %d images",
            book_id,
            jobs_deleted,
            eval_jobs_deleted,
            analyses_deleted,
            runbooks_deleted,
            images_deleted,
        )

        # Delete physical image files from S3 (production uses S3)
        if settings.is_aws_lambda:
            # In production, delete from S3
            region = os.environ.get("AWS_REGION", settings.aws_region)
            s3 = boto3.client("s3", region_name=region)
            bucket = settings.images_bucket

            for image in book_images:
                # Delete original and thumbnail from S3
                for key in [image.s3_key, get_thumbnail_key(image.s3_key)]:
                    try:
                        full_key = f"{S3_IMAGES_PREFIX}{key}"
                        logger.info("Deleting S3 object: %s/%s", bucket, full_key)
                        s3.delete_object(Bucket=bucket, Key=full_key)
                    except Exception as e:
                        logger.warning("Failed to delete S3 object %s: %s", key, str(e))
        else:
            # In development, delete from local filesystem
            for image in book_images:
                for key in [image.s3_key, get_thumbnail_key(image.s3_key)]:
                    file_path = LOCAL_IMAGES_PATH / key
                    if file_path.exists():
                        file_path.unlink()

        # Delete book (related records already explicitly deleted above)
        logger.info("Deleting book %s from database", book_id)
        db.delete(book)
        db.commit()
        logger.info("Successfully deleted book %s", book_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting book %s: %s\n%s", book_id, str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to delete book: {str(e)}") from e


@router.patch("/{book_id}/status", response_model=BookResponse)
def update_book_status(
    book_id: int,
    status: str = Query(...),
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Update book status (EVALUATING, IN_TRANSIT, ON_HAND, REMOVED).

    Returns the full book object with relationships for frontend state updates.
    """
    valid_statuses = ["EVALUATING", "IN_TRANSIT", "ON_HAND", "REMOVED"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book.status = status
    db.commit()
    db.refresh(book)

    return _build_book_response(book, db)


@router.patch("/{book_id}/inventory-type")
def update_book_inventory_type(
    book_id: int,
    inventory_type: str = Query(...),
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Move book between inventory types (PRIMARY, EXTENDED, FLAGGED)."""
    valid_types = ["PRIMARY", "EXTENDED", "FLAGGED"]
    if inventory_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid inventory type. Must be one of: {', '.join(valid_types)}",
        )

    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    old_type = book.inventory_type
    book.inventory_type = inventory_type
    db.commit()

    return {
        "message": "Inventory type updated",
        "old_type": old_type,
        "new_type": inventory_type,
    }


@router.patch("/{book_id}/acquire", response_model=BookResponse)
def acquire_book(
    book_id: int,
    acquire_data: AcquireRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """
    Acquire a book - transition from EVALUATING to IN_TRANSIT.

    Calculates discount percentage and creates scoring snapshot.
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.status != "EVALUATING":
        raise HTTPException(
            status_code=400,
            detail=f"Book must be in EVALUATING status to acquire (current: {book.status})",
        )

    # Update acquisition fields
    book.purchase_price = acquire_data.purchase_price
    book.purchase_date = acquire_data.purchase_date
    book.purchase_source = acquire_data.place_of_purchase
    book.status = "IN_TRANSIT"

    if acquire_data.estimated_delivery:
        book.estimated_delivery = acquire_data.estimated_delivery

    # Process tracking information if provided
    if acquire_data.tracking_number or acquire_data.tracking_url:
        try:
            tracking_number, tracking_carrier, tracking_url = process_tracking(
                acquire_data.tracking_number,
                acquire_data.tracking_carrier,
                acquire_data.tracking_url,
            )
            book.tracking_number = tracking_number
            book.tracking_carrier = tracking_carrier
            book.tracking_url = tracking_url

            # Set ship_date to today when tracking is added
            book.ship_date = date.today()
        except ValueError as e:
            # If tracking processing fails, log but don't fail the acquisition
            logger.warning(f"Failed to process tracking for book {book_id}: {e}")

    # Store order number in notes (or create order_number field later)
    if book.notes:
        book.notes = f"Order: {acquire_data.order_number}\n{book.notes}"
    else:
        book.notes = f"Order: {acquire_data.order_number}"

    # Calculate discount percentage
    if book.value_mid and acquire_data.purchase_price:
        discount = (
            (float(book.value_mid) - float(acquire_data.purchase_price))
            / float(book.value_mid)
            * 100
        )
        book.discount_pct = Decimal(str(round(discount, 2)))

    # Get collection stats for scoring
    collection_stats = (
        db.query(
            func.count(Book.id).label("items"),
            func.sum(Book.volumes).label("volumes"),
        )
        .filter(
            Book.inventory_type == "PRIMARY",
            Book.status == "ON_HAND",
        )
        .first()
    )

    # Create scoring snapshot
    book.scoring_snapshot = {
        "captured_at": datetime.now(UTC).isoformat(),
        "purchase_price": float(acquire_data.purchase_price),
        "fmv_at_purchase": {
            "low": float(book.value_low) if book.value_low else None,
            "mid": float(book.value_mid) if book.value_mid else None,
            "high": float(book.value_high) if book.value_high else None,
        },
        "discount_pct": float(book.discount_pct) if book.discount_pct else 0,
        "collection_position": {
            "items_before": collection_stats.items if collection_stats else 0,
            "volumes_before": (
                int(collection_stats.volumes)
                if collection_stats and collection_stats.volumes
                else 0
            ),
        },
    }

    db.commit()
    db.refresh(book)

    return _build_book_response(book, db)


@router.patch("/{book_id}/tracking", response_model=BookResponse)
def add_tracking(
    book_id: int,
    tracking_data: TrackingRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """
    Add shipment tracking to an IN_TRANSIT book.

    Auto-detects carrier from tracking number format if not provided.
    Generates tracking URL based on carrier.

    Accepts either:
    - tracking_number + optional tracking_carrier (URL auto-generated)
    - tracking_url directly (for unsupported carriers)
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.status != "IN_TRANSIT":
        raise HTTPException(
            status_code=400,
            detail=f"Can only add tracking to IN_TRANSIT books. Current status: {book.status}",
        )

    # Validate input: need either tracking_number or tracking_url
    if not tracking_data.tracking_number and not tracking_data.tracking_url:
        raise HTTPException(
            status_code=400,
            detail="Must provide either tracking_number or tracking_url",
        )

    try:
        tracking_number, tracking_carrier, tracking_url = process_tracking(
            tracking_data.tracking_number,
            tracking_data.tracking_carrier,
            tracking_data.tracking_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    book.tracking_number = tracking_number
    book.tracking_carrier = tracking_carrier
    book.tracking_url = tracking_url

    db.commit()
    db.refresh(book)

    return _build_book_response(book, db)


@router.post("/{book_id}/tracking/refresh", response_model=BookResponse)
def refresh_tracking(
    book_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """
    Refresh tracking status from carrier API.

    Fetches the latest tracking status and updates estimated delivery date
    if available from the carrier. Activates tracking polling if not already active.
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if not book.tracking_number or not book.tracking_carrier:
        raise HTTPException(
            status_code=400,
            detail="Book has no tracking number or carrier set",
        )

    try:
        refresh_single_book_tracking(db, book_id)
        # Refresh the book to get updated values
        db.refresh(book)
    except ValueError as e:
        log_and_raise(
            ValidationError("tracking", str(e)),
            context={"book_id": book_id},
        )
    except KeyError:
        log_and_raise(
            ValidationError("tracking_carrier", f"Unsupported carrier: {book.tracking_carrier}"),
            context={"book_id": book_id},
        )
    except Exception as e:
        log_and_raise(
            ExternalServiceError("Tracking API", str(e)),
            context={"book_id": book_id, "carrier": book.tracking_carrier},
        )

    return _build_book_response(book, db)


@router.post("/{book_id}/archive-source", response_model=BookResponse)
async def archive_book_source(
    book_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """
    Archive the book's source URL to the Wayback Machine.

    Returns existing archive if already successfully archived.
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if not book.source_url:
        raise HTTPException(
            status_code=400,
            detail="Book has no source_url to archive",
        )

    # If already successfully archived, return existing
    if book.archive_status == "success" and book.source_archived_url:
        return _build_book_response(book, db)

    # Set pending status
    book.archive_status = "pending"
    db.commit()

    # Attempt archive
    result = await archive_url(book.source_url)

    book.archive_status = result["status"]
    if result["status"] == "success":
        book.source_archived_url = result["archived_url"]

    db.commit()
    db.refresh(book)

    return _build_book_response(book, db)


@router.post("/{book_id}/scores/calculate")
def calculate_book_scores(
    book_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Calculate and persist scores for a book."""
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Use shared helper function
    calculate_and_persist_book_scores(book, db)
    db.commit()
    db.refresh(book)

    return {
        "investment_grade": book.investment_grade,
        "strategic_fit": book.strategic_fit,
        "collection_impact": book.collection_impact,
        "overall_score": book.overall_score,
    }


@router.get("/{book_id}/scores/breakdown")
def get_book_score_breakdown(
    book_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_viewer),
):
    """
    Get detailed score breakdown explaining why each score was calculated.

    Returns score values plus breakdown with factors and explanations.
    """
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Gather all inputs for scoring
    author_priority = 0
    author_name = None
    author_tier = None
    publisher_tier = None
    publisher_name = None
    binder_tier = None
    binder_name = None
    author_book_count = 0
    duplicate_title = None

    if book.author:
        author_priority = author_tier_to_score(book.author.tier)
        author_name = book.author.name
        author_tier = book.author.tier
        author_book_count = get_author_owned_book_count(db, book.author_id, book.id)

    if book.publisher:
        publisher_tier = book.publisher.tier
        publisher_name = book.publisher.name

    if book.binder:
        binder_tier = book.binder.tier
        binder_name = book.binder.name

    is_duplicate = False
    for other in get_other_books_by_author(book, db):
        if is_duplicate_title(book.title, other.title):
            is_duplicate = True
            duplicate_title = other.title
            break

    result = calculate_all_scores_with_breakdown(
        purchase_price=book.purchase_price,
        value_mid=book.value_mid,
        publisher_tier=publisher_tier,
        binder_tier=binder_tier,
        year_start=book.year_start,
        is_complete=book.is_complete,
        condition_grade=book.condition_grade,
        author_priority_score=author_priority,
        author_book_count=author_book_count,
        is_duplicate=is_duplicate,
        completes_set=False,
        volume_count=book.volumes or 1,
        author_name=author_name,
        publisher_name=publisher_name,
        binder_name=binder_name,
        duplicate_title=duplicate_title,
        author_tier=author_tier,
    )

    return result


@router.post("/scores/calculate-all")
def calculate_all_book_scores(
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Calculate scores for all books. Admin only."""
    books = db.query(Book).all()
    updated = 0
    errors = []

    for book in books:
        try:
            calculate_and_persist_book_scores(book, db)
            updated += 1
        except Exception as e:
            errors.append({"book_id": book.id, "error": str(e)})

    db.commit()

    return {"updated_count": updated, "errors": errors}


@router.post("/bulk/status")
def bulk_update_status(
    book_ids: list[int],
    status: str = Query(...),
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Bulk update status for multiple books."""
    valid_statuses = ["EVALUATING", "IN_TRANSIT", "ON_HAND", "REMOVED"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    updated = (
        db.query(Book)
        .filter(Book.id.in_(book_ids))
        .update(
            {Book.status: status},
            synchronize_session=False,
        )
    )
    db.commit()

    return {"message": f"Updated {updated} books", "status": status}


@router.get("/duplicates/check")
def check_duplicate_title(
    title: str = Query(...),
    db: Session = Depends(get_db),
):
    """Check if a title already exists in the collection (duplicate detection)."""
    # Search for similar titles (case-insensitive)
    matches = (
        db.query(Book)
        .filter(
            Book.title.ilike(f"%{title}%"),
            Book.inventory_type == "PRIMARY",
        )
        .all()
    )

    return {
        "query": title,
        "matches_found": len(matches),
        "matches": [
            {
                "id": b.id,
                "title": b.title,
                "author": b.author.name if b.author else None,
                "binder": b.binder.name if b.binder else None,
                "value_mid": float(b.value_mid) if b.value_mid else None,
            }
            for b in matches
        ],
    }


# Analysis endpoints
@router.get("/{book_id}/analysis")
def get_book_analysis(book_id: int, db: Session = Depends(get_db), _user=Depends(require_viewer)):
    """Get parsed analysis for a book."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if not book.analysis:
        raise HTTPException(status_code=404, detail="No analysis available")

    return {
        "id": book.analysis.id,
        "book_id": book_id,
        "executive_summary": book.analysis.executive_summary,
        "condition_assessment": book.analysis.condition_assessment,
        "binding_elaborateness_tier": book.analysis.binding_elaborateness_tier,
        "market_analysis": book.analysis.market_analysis,
        "historical_significance": book.analysis.historical_significance,
        "recommendations": book.analysis.recommendations,
        "risk_factors": book.analysis.risk_factors,
        "source_filename": book.analysis.source_filename,
        "extraction_status": book.analysis.extraction_status,
        "model_id": book.analysis.model_id,
        "generated_at": (
            book.analysis.updated_at.replace(tzinfo=UTC)
            if book.analysis.updated_at and book.analysis.updated_at.tzinfo is None
            else book.analysis.updated_at
        ).isoformat()
        if book.analysis.updated_at
        else None,
    }


@router.get("/{book_id}/analysis/raw")
def get_book_analysis_raw(
    book_id: int, db: Session = Depends(get_db), _user=Depends(require_viewer)
):
    """Get raw markdown analysis for a book.

    Returns the analysis with structured data block stripped for display.
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if not book.analysis or not book.analysis.full_markdown:
        raise HTTPException(status_code=404, detail="No analysis available")

    return strip_structured_data(book.analysis.full_markdown)


@router.put("/{book_id}/analysis")
def update_book_analysis(
    book_id: int,
    response: Response,
    full_markdown: str = Body(..., media_type="text/plain"),
    force: bool = Query(
        default=False,
        description="Bypass entity validation errors and skip association",
    ),
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Update or create analysis for a book.

    Accepts raw markdown text in the request body.
    Automatically parses markdown to extract structured fields.
    If valuation data is found, updates book's FMV and recalculates scores.
    If binder is identified, associates binder with book.
    If metadata block is present, extracts provenance and first edition info.

    Response includes X-BMX-Warning header with semicolon-separated warnings about:
    - Unknown entities not found in database (association skipped)
    - Validation errors bypassed due to force=true
    - TOCTOU race conditions where entity vanished between validation and mutation
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Parse markdown to extract structured fields
    parsed = parse_analysis_markdown(full_markdown)

    # Extract metadata (but don't apply yet - validate entities first)
    metadata = extract_analysis_metadata(full_markdown)

    # Warnings list for response - tracks skipped associations
    warnings: list[str] = []

    # VALIDATION PHASE: Validate ALL entities upfront before any mutations
    # This uses the shared validation function (#1014 - extracted duplicate logic)
    binder_name = parsed.binder_identification.get("name") if parsed.binder_identification else None
    publisher_name = (
        parsed.publisher_identification.get("name") if parsed.publisher_identification else None
    )

    validation_result = validate_and_associate_entities(
        db,
        binder_name=binder_name,
        publisher_name=publisher_name,
    )

    # Add warnings from validation (log mode visibility - #1013)
    warnings.extend(validation_result.warnings)

    # Handle validation errors
    if validation_result.has_errors and not force:
        # Surface all errors - return 409 if any is similar_entity_exists, else 400
        all_errors = validation_result.errors
        status_code = 409 if any(e.error == "similar_entity_exists" for e in all_errors) else 400
        if len(all_errors) == 1:
            raise HTTPException(status_code=status_code, detail=all_errors[0].model_dump())
        else:
            raise HTTPException(
                status_code=status_code,
                detail={
                    "error": "multiple_validation_errors",
                    "errors": [e.model_dump() for e in all_errors],
                },
            )

    # If force=True, append warnings for bypassed errors with fuzzy match details
    if force and validation_result.has_errors:
        for error in validation_result.errors:
            if error.suggestions:
                top = error.suggestions[0]
                warnings.append(
                    f"{error.entity_type.capitalize()} '{error.input}' fuzzy matches '{top.name}' "
                    f"({top.match:.0%}) - skipped due to force=true"
                )
            else:
                warnings.append(
                    f"{error.entity_type.capitalize()} '{error.input}' validation skipped due to force=true "
                    f"({error.error})"
                )

    # Get entity IDs from validation result
    binder_id_to_set = validation_result.binder_id
    publisher_id_to_set = validation_result.publisher_id

    # MUTATION PHASE: All validations passed, now apply changes
    # Apply metadata (provenance, first edition)
    metadata_updated = []
    if metadata:
        metadata_updated = apply_metadata_to_book(book, metadata)

    # Associate binder (with existence re-check for TOCTOU safety)
    # ALWAYS verify existence, even if book.binder_id == binder_id_to_set
    # because the entity could have been deleted in another transaction
    binder_updated = False
    if binder_id_to_set:
        binder = db.get(Binder, binder_id_to_set)
        if binder:
            if book.binder_id != binder_id_to_set:
                book.binder_id = binder_id_to_set
                binder_updated = True
        else:
            warnings.append(f"Binder ID {binder_id_to_set} vanished - association skipped")
            # Clear stale FK if it pointed to the vanished entity
            if book.binder_id == binder_id_to_set:
                book.binder_id = None

    # Associate publisher (with existence re-check for TOCTOU safety)
    # ALWAYS verify existence, even if book.publisher_id == publisher_id_to_set
    publisher_updated = False
    if publisher_id_to_set:
        publisher = db.get(Publisher, publisher_id_to_set)
        if publisher:
            if book.publisher_id != publisher_id_to_set:
                book.publisher_id = publisher_id_to_set
                publisher_updated = True
        else:
            warnings.append(f"Publisher ID {publisher_id_to_set} vanished - association skipped")
            # Clear stale FK if it pointed to the vanished entity
            if book.publisher_id == publisher_id_to_set:
                book.publisher_id = None

    if book.analysis:
        book.analysis.full_markdown = full_markdown
        book.analysis.executive_summary = parsed.executive_summary
        book.analysis.historical_significance = parsed.historical_significance
        book.analysis.condition_assessment = parsed.condition_assessment
        book.analysis.market_analysis = parsed.market_analysis
        book.analysis.recommendations = parsed.recommendations
    else:
        analysis = BookAnalysis(
            book_id=book_id,
            full_markdown=full_markdown,
            executive_summary=parsed.executive_summary,
            historical_significance=parsed.historical_significance,
            condition_assessment=parsed.condition_assessment,
            market_analysis=parsed.market_analysis,
            recommendations=parsed.recommendations,
        )
        db.add(analysis)

    # Check if valuation data was extracted and update book's FMV if different
    values_changed = False
    if parsed.market_analysis and "valuation" in parsed.market_analysis:
        valuation = parsed.market_analysis["valuation"]
        if "low" in valuation:
            new_low = Decimal(valuation["low"])
            if book.value_low != new_low:
                book.value_low = new_low
                values_changed = True
        if "mid" in valuation:
            new_mid = Decimal(valuation["mid"])
            if book.value_mid != new_mid:
                book.value_mid = new_mid
                values_changed = True
        if "high" in valuation:
            new_high = Decimal(valuation["high"])
            if book.value_high != new_high:
                book.value_high = new_high
                values_changed = True

    # Recalculate discount_pct if FMV values changed
    if values_changed:
        recalculate_discount_pct(book)

    # Always recalculate scores when analysis is created/updated
    # Analysis content affects scoring (condition, market data, comparables)
    calculate_and_persist_book_scores(book, db)

    db.commit()

    # Add X-BMX-Warning header if there are warnings
    if warnings:
        response.headers["X-BMX-Warning"] = "; ".join(warnings)

    return {
        "message": "Analysis updated",
        "values_updated": values_changed,
        "binder_updated": binder_updated,
        "publisher_updated": publisher_updated,
        "metadata_updated": metadata_updated,
        "scores_recalculated": True,
        "warnings": warnings,
    }


@router.delete("/{book_id}/analysis")
def delete_book_analysis(
    book_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Delete analysis for a book. Requires editor role."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if not book.analysis:
        raise HTTPException(status_code=404, detail="No analysis to delete")

    db.delete(book.analysis)
    db.commit()
    return {"message": "Analysis deleted"}


@router.post("/{book_id}/analysis/reparse")
def reparse_book_analysis(
    book_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Re-parse existing analysis markdown to populate structured fields.

    Use this to backfill parsed fields for analyses uploaded before
    automatic parsing was implemented.
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if not book.analysis or not book.analysis.full_markdown:
        raise HTTPException(status_code=404, detail="No analysis markdown to parse")

    # Re-parse the existing markdown
    parsed = parse_analysis_markdown(book.analysis.full_markdown)

    # Update structured fields
    book.analysis.executive_summary = parsed.executive_summary
    book.analysis.historical_significance = parsed.historical_significance
    book.analysis.condition_assessment = parsed.condition_assessment
    book.analysis.market_analysis = parsed.market_analysis
    book.analysis.recommendations = parsed.recommendations

    # Recalculate scores when analysis is reparsed
    calculate_and_persist_book_scores(book, db)

    db.commit()
    return {
        "message": "Analysis re-parsed",
        "fields_populated": {
            "executive_summary": parsed.executive_summary is not None,
            "historical_significance": parsed.historical_significance is not None,
            "condition_assessment": parsed.condition_assessment is not None,
            "market_analysis": parsed.market_analysis is not None,
            "recommendations": parsed.recommendations is not None,
        },
        "scores_recalculated": True,
    }


class GenerateAnalysisRequest(BaseModel):
    """Request body for analysis generation."""

    model: Literal["sonnet", "opus"] = "opus"


@router.post("/{book_id}/analysis/generate")
def generate_analysis(
    book_id: int,
    request: GenerateAnalysisRequest = Body(default=GenerateAnalysisRequest()),
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    """Generate Napoleon-style analysis using AWS Bedrock.

    Requires admin role. Replaces existing analysis if present.
    """
    # Get book with relationships
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Build book metadata dict
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
    source_content = fetch_source_url_content(book.source_url)

    # Fetch images
    images = fetch_book_images_for_bedrock(book.images)

    # Build messages and invoke Bedrock
    messages = build_bedrock_messages(book_data, images, source_content)
    model_id = get_model_id(request.model)

    logger.warning(f"Starting Bedrock invocation for book {book_id}, model={request.model}")
    try:
        analysis_text = invoke_bedrock(messages, model=request.model)
        logger.warning(f"Bedrock returned {len(analysis_text)} chars for book {book_id}")
    except Exception as e:
        logger.error(f"Bedrock invocation failed for book {book_id}: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Bedrock invocation failed: {str(e)}",
        ) from e

    # Parse markdown to extract structured fields
    parsed = parse_analysis_markdown(analysis_text)

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
        model_id=model_id,
    )
    db.add(analysis)

    # Check if valuation data was extracted and update book's FMV if different
    values_changed = False
    if parsed.market_analysis and "valuation" in parsed.market_analysis:
        valuation = parsed.market_analysis["valuation"]
        if "low" in valuation:
            new_low = Decimal(valuation["low"])
            if book.value_low != new_low:
                book.value_low = new_low
                values_changed = True
        if "mid" in valuation:
            new_mid = Decimal(valuation["mid"])
            if book.value_mid != new_mid:
                book.value_mid = new_mid
                values_changed = True
        if "high" in valuation:
            new_high = Decimal(valuation["high"])
            if book.value_high != new_high:
                book.value_high = new_high
                values_changed = True

    # Recalculate discount_pct if FMV values changed
    if values_changed:
        recalculate_discount_pct(book)

    # Always recalculate scores when analysis is generated
    # Analysis content affects scoring (condition, market data, comparables)
    calculate_and_persist_book_scores(book, db)

    db.commit()
    db.refresh(analysis)

    return {
        "id": analysis.id,
        "book_id": book_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "model_used": model_id,
        "full_markdown": analysis_text,
        "executive_summary": analysis.executive_summary,
        "condition_assessment": analysis.condition_assessment,
        "market_analysis": analysis.market_analysis,
        "historical_significance": analysis.historical_significance,
        "recommendations": analysis.recommendations,
        "values_updated": values_changed,
        "scores_recalculated": True,
    }


@router.post("/analysis/reparse-all")
def reparse_all_analyses(
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Re-parse all existing analyses to populate structured fields.

    Batch operation to backfill parsed fields for all analyses.
    """
    analyses = db.query(BookAnalysis).filter(BookAnalysis.full_markdown.isnot(None)).all()

    results = []
    for analysis in analyses:
        parsed = parse_analysis_markdown(analysis.full_markdown)

        analysis.executive_summary = parsed.executive_summary
        analysis.historical_significance = parsed.historical_significance
        analysis.condition_assessment = parsed.condition_assessment
        analysis.market_analysis = parsed.market_analysis
        analysis.recommendations = parsed.recommendations

        results.append(
            {
                "book_id": analysis.book_id,
                "executive_summary_populated": parsed.executive_summary is not None,
            }
        )

    db.commit()
    return {"message": f"Re-parsed {len(results)} analyses", "results": results}


@router.post("/{book_id}/re-extract")
def re_extract_structured_data(
    book_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Re-run Stage 2 structured data extraction for a book.

    Uses existing analysis text without regenerating the full analysis.
    Useful for fixing 'degraded' extractions after throttling issues resolve.
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if not book.analysis or not book.analysis.full_markdown:
        raise HTTPException(status_code=404, detail="Book has no analysis to re-extract")

    analysis = book.analysis
    analysis_text = analysis.full_markdown

    # Run Stage 2 extraction
    extracted_data = extract_structured_data(analysis_text, model="sonnet")

    if not extracted_data:
        raise HTTPException(
            status_code=503,
            detail="Extraction failed - AI service may be throttled. Try again later.",
        )

    # Map extracted fields to book
    fields_updated = _apply_extracted_data_to_book(book, extracted_data)

    # Update extraction status
    analysis.extraction_status = "success"

    # Recalculate discount_pct if FMV values changed
    if (
        "value_mid" in fields_updated
        or "value_low" in fields_updated
        or "value_high" in fields_updated
    ):
        recalculate_discount_pct(book)

    # Recalculate scores with new values
    calculate_and_persist_book_scores(book, db)

    db.commit()

    return {
        "message": "Extraction successful",
        "book_id": book_id,
        "fields_updated": fields_updated,
        "extraction_status": "success",
    }


@router.post("/re-extract-degraded")
def re_extract_all_degraded(
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    """Re-run Stage 2 extraction for all books with degraded status.

    Processes books one at a time to avoid overwhelming Bedrock quota.
    Returns summary of successes and failures.
    """
    # Find all degraded analyses
    degraded_analyses = (
        db.query(BookAnalysis).filter(BookAnalysis.extraction_status == "degraded").all()
    )

    if not degraded_analyses:
        return {
            "message": "No degraded extractions found",
            "total": 0,
            "succeeded": 0,
            "failed": 0,
            "results": [],
        }

    results = []
    succeeded = 0
    failed = 0

    for analysis in degraded_analyses:
        book = analysis.book
        if not book or not analysis.full_markdown:
            results.append(
                {
                    "book_id": analysis.book_id,
                    "status": "skipped",
                    "reason": "No book or analysis text",
                }
            )
            continue

        # Run Stage 2 extraction
        extracted_data = extract_structured_data(analysis.full_markdown, model="sonnet")

        if not extracted_data:
            failed += 1
            results.append(
                {
                    "book_id": analysis.book_id,
                    "title": book.title[:50] if book.title else None,
                    "status": "failed",
                    "reason": "Extraction returned no data (likely throttled)",
                }
            )
            continue

        # Map extracted fields to book
        fields_updated = _apply_extracted_data_to_book(book, extracted_data)

        # Update extraction status
        analysis.extraction_status = "success"

        # Recalculate discount_pct if FMV values changed
        if (
            "value_mid" in fields_updated
            or "value_low" in fields_updated
            or "value_high" in fields_updated
        ):
            recalculate_discount_pct(book)

        # Recalculate scores
        calculate_and_persist_book_scores(book, db)

        succeeded += 1
        results.append(
            {
                "book_id": analysis.book_id,
                "title": book.title[:50] if book.title else None,
                "status": "success",
                "fields_updated": fields_updated,
            }
        )

        # Commit after each successful extraction to save progress
        db.commit()

    return {
        "message": f"Re-extracted {succeeded}/{len(degraded_analyses)} degraded analyses",
        "total": len(degraded_analyses),
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
    }


# =============================================================================
# Async Analysis Job Endpoints
# =============================================================================


class GenerateAnalysisAsyncRequest(BaseModel):
    """Request body for async analysis generation."""

    model: Literal["sonnet", "opus"] = "opus"


@router.post("/{book_id}/analysis/generate-async", status_code=202)
def generate_analysis_async(
    book_id: int,
    request: GenerateAnalysisAsyncRequest = Body(default=GenerateAnalysisAsyncRequest()),
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    """Start async analysis generation using AWS Bedrock.

    Returns immediately with job ID. Poll /analysis/status for progress.
    Requires admin role.
    """
    # Verify book exists
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Auto-fail stale jobs and check for active jobs
    handle_stale_jobs(db, AnalysisJob, book_id, job_type_name="Analysis job", use_skip_locked=True)

    # Create job record
    job = AnalysisJob(
        book_id=book_id,
        model=request.model,
        status="pending",
    )

    try:
        db.add(job)
        db.commit()
        db.refresh(job)
    except IntegrityError:
        db.rollback()
        log_and_raise(
            ConflictError("Analysis job already in progress for this book"),
            context={"book_id": book_id},
        )

    # Send message to SQS
    try:
        send_analysis_job(job.id, book_id, request.model)
    except Exception as e:
        # If SQS send fails, mark job as failed - Issue #815
        job.status = "failed"
        job.error_message = f"Failed to queue job: {e}"
        job.completed_at = datetime.now(UTC)
        db.commit()
        log_and_raise(
            ExternalServiceError("SQS", f"Failed to queue analysis job: {e}"),
            context={"book_id": book_id, "job_id": str(job.id)},
        )

    return AnalysisJobResponse.from_orm_model(job)


@router.get("/{book_id}/analysis/status")
def get_analysis_job_status(
    book_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    """Get status of the latest analysis job for a book.

    Requires admin role.

    Automatically detects and marks stale jobs as failed. A job is considered
    stale if it has been in "running" status for more than 15 minutes without
    updates, indicating the worker likely crashed or timed out.
    """
    # Verify book exists
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Get latest job for this book
    job = (
        db.query(AnalysisJob)
        .filter(AnalysisJob.book_id == book_id)
        .order_by(AnalysisJob.created_at.desc())
        .first()
    )

    if not job:
        raise HTTPException(status_code=404, detail="No analysis job found for this book")

    # Detect and auto-fail stale "running" jobs
    # This handles cases where the worker Lambda timed out or crashed
    if job.status == "running":
        stale_threshold = datetime.now(UTC) - timedelta(minutes=STALE_JOB_THRESHOLD_MINUTES)
        if job.updated_at < stale_threshold:
            job.status = "failed"
            job.error_message = (
                f"Job timed out after {STALE_JOB_THRESHOLD_MINUTES} minutes "
                "(worker likely crashed or timed out)"
            )
            job.completed_at = datetime.now(UTC)
            job.updated_at = datetime.now(UTC)
            db.commit()

    return AnalysisJobResponse.from_orm_model(job)


# Threshold for detecting stale "running" eval runbook jobs
STALE_EVAL_JOB_THRESHOLD_MINUTES = 15


@router.post("/{book_id}/eval-runbook/generate")
def generate_eval_runbook_job(
    book_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_editor),
):
    """Start async eval runbook generation with full AI analysis and FMV lookup.

    Returns immediately with job ID. Poll /eval-runbook/status for progress.
    Requires editor role.
    """
    # Verify book exists
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Auto-fail stale jobs and check for active jobs
    # Uses SELECT FOR UPDATE SKIP LOCKED to prevent race conditions
    handle_stale_jobs(
        db, EvalRunbookJob, book_id, job_type_name="Eval runbook job", use_skip_locked=True
    )

    # Create job record
    job = EvalRunbookJob(
        book_id=book_id,
        status="pending",
    )

    try:
        db.add(job)
        db.commit()
        db.refresh(job)
    except IntegrityError:
        db.rollback()
        log_and_raise(
            ConflictError("Eval runbook job already in progress for this book"),
            context={"book_id": book_id},
        )

    # Send message to SQS
    try:
        send_eval_runbook_job(str(job.id), book_id)
    except Exception as e:
        # If SQS send fails, mark job as failed - Issue #815
        job.status = "failed"
        job.error_message = f"Failed to queue job: {e}"
        job.completed_at = datetime.now(UTC)
        db.commit()
        log_and_raise(
            ExternalServiceError("SQS", f"Failed to queue eval runbook job: {e}"),
            context={"book_id": book_id, "job_id": str(job.id)},
        )

    return EvalRunbookJobResponse.from_orm_model(job)


@router.get("/{book_id}/eval-runbook/status")
def get_eval_runbook_job_status(
    book_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_editor),
):
    """Get status of the latest eval runbook job for a book.

    Requires editor role.

    Automatically detects and marks stale jobs as failed. A job is considered
    stale if it has been in "running" status for more than 15 minutes without
    updates, indicating the worker likely crashed or timed out.
    """
    # Verify book exists
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Get latest job for this book
    job = (
        db.query(EvalRunbookJob)
        .filter(EvalRunbookJob.book_id == book_id)
        .order_by(EvalRunbookJob.created_at.desc())
        .first()
    )

    if not job:
        raise HTTPException(status_code=404, detail="No eval runbook job found for this book")

    # Detect and auto-fail stale "running" jobs
    # This handles cases where the worker Lambda timed out or crashed
    if job.status == "running":
        stale_threshold = datetime.now(UTC) - timedelta(minutes=STALE_EVAL_JOB_THRESHOLD_MINUTES)
        if job.updated_at < stale_threshold:
            job.status = "failed"
            job.error_message = (
                f"Job timed out after {STALE_EVAL_JOB_THRESHOLD_MINUTES} minutes "
                "(worker likely crashed or timed out)"
            )
            job.completed_at = datetime.now(UTC)
            job.updated_at = datetime.now(UTC)
            db.commit()

    return EvalRunbookJobResponse.from_orm_model(job)
