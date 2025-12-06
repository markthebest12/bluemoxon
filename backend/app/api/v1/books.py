"""Books API endpoints."""

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.v1.images import get_cloudfront_url, is_production
from app.auth import require_editor
from app.config import get_settings
from app.db import get_db
from app.models import Book
from app.schemas.book import (
    BookCreate,
    BookListResponse,
    BookResponse,
    BookUpdate,
)

router = APIRouter()
settings = get_settings()


def get_api_base_url() -> str:
    """Get the API base URL for constructing absolute URLs."""
    if settings.database_secret_arn is not None:  # Production check
        return "https://api.bluemoxon.com"
    return ""  # Relative URLs for local dev


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


@router.post("", response_model=BookResponse, status_code=201)
def create_book(
    book_data: BookCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Create a new book. Requires editor role."""
    book = Book(**book_data.model_dump())

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
            bucket = os.environ.get("IMAGES_BUCKET", settings.images_bucket)

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


@router.patch("/{book_id}/status")
def update_book_status(
    book_id: int,
    status: str = Query(...),
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Update book status (IN_TRANSIT, ON_HAND, SOLD, REMOVED)."""
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

    return {"message": "Status updated", "status": status}


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
    """Get raw markdown analysis for a book."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if not book.analysis or not book.analysis.full_markdown:
        raise HTTPException(status_code=404, detail="No analysis available")

    return book.analysis.full_markdown


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
    """
    from app.models import BookAnalysis
    from app.utils.markdown_parser import parse_analysis_markdown

    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Parse markdown to extract structured fields
    parsed = parse_analysis_markdown(full_markdown)

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

    db.commit()
    return {"message": "Analysis updated"}


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
