"""Books API endpoints."""

import logging
from datetime import datetime
from typing import Literal

import boto3
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.images import get_cloudfront_url, is_production
from app.auth import require_admin, require_editor
from app.config import get_settings
from app.db import get_db
from app.models import Book
from app.models.image import BookImage
from app.schemas.book import (
    AcquireRequest,
    BookCreate,
    BookListResponse,
    BookResponse,
    BookUpdate,
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    DuplicateMatch,
    TrackingRequest,
)
from app.services.archive import archive_url
from app.services.bedrock import (
    build_bedrock_messages,
    fetch_book_images_for_bedrock,
    fetch_source_url_content,
    get_model_id,
    invoke_bedrock,
)
from app.services.scoring import (
    calculate_all_scores,
    calculate_all_scores_with_breakdown,
    calculate_title_similarity,
    is_duplicate_title,
)

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()


def _calculate_and_persist_scores(book: Book, db: Session) -> None:
    """Calculate and persist scores for a book."""
    author_priority = 0
    publisher_tier = None
    binder_tier = None
    author_book_count = 0

    if book.author:
        author_priority = book.author.priority_score or 0
        author_book_count = (
            db.query(Book).filter(Book.author_id == book.author_id, Book.id != book.id).count()
        )

    if book.publisher:
        publisher_tier = book.publisher.tier

    if book.binder:
        binder_tier = book.binder.tier

    is_duplicate = False
    if book.author_id:
        other_books = (
            db.query(Book).filter(Book.author_id == book.author_id, Book.id != book.id).all()
        )
        for other in other_books:
            if is_duplicate_title(book.title, other.title):
                is_duplicate = True
                break

    scores = calculate_all_scores(
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
    )

    book.investment_grade = scores["investment_grade"]
    book.strategic_fit = scores["strategic_fit"]
    book.collection_impact = scores["collection_impact"]
    book.overall_score = scores["overall_score"]
    book.scores_calculated_at = datetime.now()


def get_api_base_url() -> str:
    """Get the API base URL for constructing absolute URLs."""
    if settings.database_secret_arn is not None:  # Production check
        return "https://api.bluemoxon.com"
    return ""  # Relative URLs for local dev


def _copy_listing_images_to_book(book_id: int, listing_s3_keys: list[str], db: Session) -> None:
    """Copy images from listing folder to book folder and create BookImage records.

    Also generates thumbnails for each image.

    Args:
        book_id: ID of the book to associate images with
        listing_s3_keys: S3 keys of images in listings/{item_id}/ format
        db: Database session
    """
    from pathlib import Path

    from app.api.v1.images import generate_thumbnail

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
            import tempfile

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
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    q: str | None = Query(default=None, description="Search query for title, author, notes"),
    inventory_type: str | None = None,
    category: str | None = None,
    status: str | None = None,
    publisher_id: int | None = None,
    publisher_tier: str | None = None,
    author_id: int | None = None,
    binder_id: int | None = None,
    binding_authenticated: bool | None = None,
    binding_type: str | None = None,
    condition_grade: str | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    year_start: int | None = None,
    year_end: int | None = None,
    has_images: bool | None = None,
    has_analysis: bool | None = None,
    has_provenance: bool | None = None,
    sort_by: str = "title",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
):
    """List books with filtering and pagination."""
    from sqlalchemy import exists

    from app.models import BookAnalysis, BookImage

    query = db.query(Book)

    # Apply search query
    if q:
        from app.models import Author

        search_term = f"%{q}%"
        query = query.outerjoin(Author, Book.author_id == Author.id).filter(
            (Book.title.ilike(search_term))
            | (Author.name.ilike(search_term))
            | (Book.notes.ilike(search_term))
            | (Book.binding_description.ilike(search_term))
        )

    # Apply filters
    if inventory_type:
        query = query.filter(Book.inventory_type == inventory_type)
    if category:
        query = query.filter(Book.category == category)
    if status:
        query = query.filter(Book.status == status)
    if publisher_id:
        query = query.filter(Book.publisher_id == publisher_id)
    if publisher_tier:
        from app.models import Publisher

        query = query.join(Publisher).filter(Publisher.tier == publisher_tier)
    if author_id:
        query = query.filter(Book.author_id == author_id)
    if binder_id:
        query = query.filter(Book.binder_id == binder_id)
    if binding_authenticated is not None:
        query = query.filter(Book.binding_authenticated == binding_authenticated)
    if binding_type:
        query = query.filter(Book.binding_type == binding_type)
    if condition_grade:
        query = query.filter(Book.condition_grade == condition_grade)
    if min_value is not None:
        query = query.filter(Book.value_mid >= min_value)
    if max_value is not None:
        query = query.filter(Book.value_mid <= max_value)
    if year_start is not None:
        query = query.filter(Book.year_start >= year_start)
    if year_end is not None:
        query = query.filter(Book.year_end <= year_end)

    # Filter by has_images
    if has_images is not None:
        image_exists = exists().where(BookImage.book_id == Book.id)
        if has_images:
            query = query.filter(image_exists)
        else:
            query = query.filter(~image_exists)

    # Filter by has_analysis
    if has_analysis is not None:
        analysis_exists = exists().where(BookAnalysis.book_id == Book.id)
        if has_analysis:
            query = query.filter(analysis_exists)
        else:
            query = query.filter(~analysis_exists)

    # Filter by has_provenance
    if has_provenance is not None:
        if has_provenance:
            query = query.filter(Book.provenance.isnot(None), Book.provenance != "")
        else:
            query = query.filter((Book.provenance.is_(None)) | (Book.provenance == ""))

    # Get total count
    total = query.count()

    # Apply sorting
    sort_column = getattr(Book, sort_by, Book.title)
    if sort_order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    # Apply pagination
    offset = (page - 1) * per_page
    books = query.offset(offset).limit(per_page).all()

    # Build response
    base_url = get_api_base_url()
    items = []
    for book in books:
        book_dict = BookResponse.model_validate(book).model_dump()
        book_dict["has_analysis"] = book.analysis is not None
        book_dict["has_eval_runbook"] = book.eval_runbook is not None
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
            if is_production():
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
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)):
    """Get a single book by ID."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book_dict = BookResponse.model_validate(book).model_dump()
    book_dict["has_analysis"] = book.analysis is not None
    book_dict["has_eval_runbook"] = book.eval_runbook is not None
    book_dict["image_count"] = len(book.images) if book.images else 0

    # Get primary image URL
    primary_image = None
    if book.images:
        for img in book.images:
            if img.is_primary:
                primary_image = img
                break
        if not primary_image:
            primary_image = min(book.images, key=lambda x: x.display_order)

    if primary_image:
        if is_production():
            book_dict["primary_image_url"] = get_cloudfront_url(primary_image.s3_key)
        else:
            base_url = settings.base_url or "http://localhost:8000"
            book_dict["primary_image_url"] = (
                f"{base_url}/api/v1/books/{book.id}/images/{primary_image.id}/file"
            )

    return BookResponse(**book_dict)


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

    # Parse year from publication_date
    if book.publication_date:
        parts = book.publication_date.split("-")
        book.year_start = int(parts[0]) if parts[0].isdigit() else None
        book.year_end = int(parts[-1]) if parts[-1].isdigit() else None

    # Auto-set binding_authenticated when binder is selected
    if book.binder_id:
        book.binding_authenticated = True

    db.add(book)
    db.commit()
    db.refresh(book)

    # Copy images from listing folder to book folder if S3 keys provided
    if listing_s3_keys:
        _copy_listing_images_to_book(book.id, listing_s3_keys, db)

    # Auto-calculate scores
    _calculate_and_persist_scores(book, db)
    db.commit()
    db.refresh(book)

    return BookResponse.model_validate(book)


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

    # Re-parse year if publication_date changed
    if "publication_date" in update_data and book.publication_date:
        parts = book.publication_date.split("-")
        book.year_start = int(parts[0]) if parts[0].isdigit() else None
        book.year_end = int(parts[-1]) if parts[-1].isdigit() else None

    # Auto-set binding_authenticated when binder is set/unset
    if "binder_id" in update_data:
        book.binding_authenticated = book.binder_id is not None

    db.commit()
    db.refresh(book)

    return BookResponse.model_validate(book)


@router.delete("/{book_id}", status_code=204)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Delete a book and all associated images/analysis. Requires editor role."""
    import logging
    import traceback

    from app.models import BookImage

    logger = logging.getLogger(__name__)

    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        # Get all images for this book before deleting
        book_images = db.query(BookImage).filter(BookImage.book_id == book_id).all()
        logger.info("Deleting book %s with %d images", book_id, len(book_images))

        # Delete physical image files from S3 (production uses S3)
        if settings.database_secret_arn is not None:
            # In production, delete from S3
            import os

            import boto3

            from app.api.v1.images import S3_IMAGES_PREFIX, get_thumbnail_key

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
            from app.api.v1.images import LOCAL_IMAGES_PATH, get_thumbnail_key

            for image in book_images:
                for key in [image.s3_key, get_thumbnail_key(image.s3_key)]:
                    file_path = LOCAL_IMAGES_PATH / key
                    if file_path.exists():
                        file_path.unlink()

        # Delete book (cascades to images and analysis in database)
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
    """Update book status (IN_TRANSIT, ON_HAND, SOLD, REMOVED).

    Returns the full book object with relationships for frontend state updates.
    """
    valid_statuses = ["IN_TRANSIT", "ON_HAND", "SOLD", "REMOVED"]
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

    # Build response with image info (matching get_book pattern)
    book_dict = BookResponse.model_validate(book).model_dump()
    book_dict["has_analysis"] = book.analysis is not None
    book_dict["has_eval_runbook"] = book.eval_runbook is not None
    book_dict["image_count"] = len(book.images) if book.images else 0

    return BookResponse(**book_dict)


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
    from datetime import UTC, datetime
    from decimal import Decimal

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
        from datetime import date as date_module

        from app.services.tracking import process_tracking

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
            book.ship_date = date_module.today()
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
    from sqlalchemy import func

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

    # Build response with image info (matching get_book pattern)
    book_dict = BookResponse.model_validate(book).model_dump()
    book_dict["has_analysis"] = book.analysis is not None
    book_dict["has_eval_runbook"] = book.eval_runbook is not None
    book_dict["image_count"] = len(book.images) if book.images else 0

    # Get primary image URL
    primary_image = None
    if book.images:
        for img in book.images:
            if img.is_primary:
                primary_image = img
                break
        if not primary_image:
            primary_image = min(book.images, key=lambda x: x.display_order)

    if primary_image:
        if is_production():
            book_dict["primary_image_url"] = get_cloudfront_url(primary_image.s3_key)
        else:
            base_url = settings.base_url or "http://localhost:8000"
            book_dict["primary_image_url"] = (
                f"{base_url}/api/v1/books/{book.id}/images/{primary_image.id}/file"
            )

    return BookResponse(**book_dict)


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
    from app.services.tracking import process_tracking

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

    # Build response with image info (matching get_book pattern)
    book_dict = BookResponse.model_validate(book).model_dump()
    book_dict["has_analysis"] = book.analysis is not None
    book_dict["has_eval_runbook"] = book.eval_runbook is not None
    book_dict["image_count"] = len(book.images) if book.images else 0

    # Get primary image URL
    primary_image = None
    if book.images:
        for img in book.images:
            if img.is_primary:
                primary_image = img
                break
        if not primary_image:
            primary_image = min(book.images, key=lambda x: x.display_order)

    if primary_image:
        if is_production():
            book_dict["primary_image_url"] = get_cloudfront_url(primary_image.s3_key)
        else:
            base_url = settings.base_url or "http://localhost:8000"
            book_dict["primary_image_url"] = (
                f"{base_url}/api/v1/books/{book.id}/images/{primary_image.id}/file"
            )

    return BookResponse(**book_dict)


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
        book_dict = BookResponse.model_validate(book).model_dump()
        book_dict["has_analysis"] = book.analysis is not None
        book_dict["has_eval_runbook"] = book.eval_runbook is not None
        book_dict["image_count"] = len(book.images) if book.images else 0
        return BookResponse(**book_dict)

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

    # Build response
    book_dict = BookResponse.model_validate(book).model_dump()
    book_dict["has_analysis"] = book.analysis is not None
    book_dict["has_eval_runbook"] = book.eval_runbook is not None
    book_dict["image_count"] = len(book.images) if book.images else 0

    return BookResponse(**book_dict)


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
    _calculate_and_persist_scores(book, db)
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
    publisher_tier = None
    publisher_name = None
    binder_tier = None
    binder_name = None
    author_book_count = 0
    duplicate_title = None

    if book.author:
        author_priority = book.author.priority_score or 0
        author_name = book.author.name
        author_book_count = (
            db.query(Book).filter(Book.author_id == book.author_id, Book.id != book.id).count()
        )

    if book.publisher:
        publisher_tier = book.publisher.tier
        publisher_name = book.publisher.name

    if book.binder:
        binder_tier = book.binder.tier
        binder_name = book.binder.name

    is_duplicate = False
    if book.author_id:
        other_books = (
            db.query(Book).filter(Book.author_id == book.author_id, Book.id != book.id).all()
        )
        for other in other_books:
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
            _calculate_and_persist_scores(book, db)
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
    valid_statuses = ["IN_TRANSIT", "ON_HAND", "SOLD", "REMOVED"]
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
def get_book_analysis(book_id: int, db: Session = Depends(get_db)):
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
    }


@router.get("/{book_id}/analysis/raw")
def get_book_analysis_raw(book_id: int, db: Session = Depends(get_db)):
    """Get raw markdown analysis for a book.

    Returns the analysis with structured data block stripped for display.
    """
    from app.utils.markdown_parser import strip_structured_data

    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if not book.analysis or not book.analysis.full_markdown:
        raise HTTPException(status_code=404, detail="No analysis available")

    return strip_structured_data(book.analysis.full_markdown)


@router.put("/{book_id}/analysis")
def update_book_analysis(
    book_id: int,
    full_markdown: str = Body(..., media_type="text/plain"),
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Update or create analysis for a book.

    Accepts raw markdown text in the request body.
    Automatically parses markdown to extract structured fields.
    If valuation data is found, updates book's FMV and recalculates scores.
    If binder is identified, associates binder with book.
    """
    from decimal import Decimal

    from app.models import BookAnalysis
    from app.services.reference import get_or_create_binder
    from app.utils.markdown_parser import parse_analysis_markdown

    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Parse markdown to extract structured fields
    parsed = parse_analysis_markdown(full_markdown)

    # Extract binder identification and associate with book
    binder_updated = False
    if parsed.binder_identification:
        binder = get_or_create_binder(db, parsed.binder_identification)
        if binder and book.binder_id != binder.id:
            book.binder_id = binder.id
            binder_updated = True

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

    # Always recalculate scores when analysis is created/updated
    # Analysis content affects scoring (condition, market data, comparables)
    _calculate_and_persist_scores(book, db)

    db.commit()
    return {
        "message": "Analysis updated",
        "values_updated": values_changed,
        "binder_updated": binder_updated,
        "scores_recalculated": True,
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
    from app.utils.markdown_parser import parse_analysis_markdown

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
    _calculate_and_persist_scores(book, db)

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

    model: Literal["sonnet", "opus"] = "sonnet"


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
    from datetime import UTC, datetime

    from app.models import BookAnalysis
    from app.utils.markdown_parser import parse_analysis_markdown

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

    import logging

    logger = logging.getLogger(__name__)

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
    )
    db.add(analysis)

    # Check if valuation data was extracted and update book's FMV if different
    from decimal import Decimal

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

    # Always recalculate scores when analysis is generated
    # Analysis content affects scoring (condition, market data, comparables)
    _calculate_and_persist_scores(book, db)

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
    from app.models import BookAnalysis
    from app.utils.markdown_parser import parse_analysis_markdown

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


# =============================================================================
# Async Analysis Job Endpoints
# =============================================================================


class GenerateAnalysisAsyncRequest(BaseModel):
    """Request body for async analysis generation."""

    model: Literal["sonnet", "opus"] = "sonnet"


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
    from sqlalchemy.exc import IntegrityError

    from app.models import AnalysisJob
    from app.schemas.analysis_job import AnalysisJobResponse
    from app.services.sqs import send_analysis_job

    # Verify book exists
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Check for existing active job
    active_job = (
        db.query(AnalysisJob)
        .filter(
            AnalysisJob.book_id == book_id,
            AnalysisJob.status.in_(["pending", "running"]),
        )
        .first()
    )
    if active_job:
        raise HTTPException(
            status_code=409,
            detail="Analysis job already in progress for this book",
        )

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
        raise HTTPException(
            status_code=409,
            detail="Analysis job already in progress for this book",
        ) from None

    # Send message to SQS
    try:
        send_analysis_job(job.id, book_id, request.model)
    except Exception as e:
        # If SQS send fails, mark job as failed
        job.status = "failed"
        job.error_message = f"Failed to queue job: {e}"
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Failed to queue analysis job: {e}",
        ) from None

    return AnalysisJobResponse.from_orm_model(job)


# Threshold for detecting stale "running" jobs (worker likely crashed/timed out)
STALE_JOB_THRESHOLD_MINUTES = 15


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
    from datetime import UTC, datetime, timedelta

    from app.models import AnalysisJob
    from app.schemas.analysis_job import AnalysisJobResponse

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
            job.updated_at = datetime.now(UTC)
            db.commit()

    return AnalysisJobResponse.from_orm_model(job)
