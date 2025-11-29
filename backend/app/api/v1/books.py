"""Books API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Book, Author, Publisher, Binder
from app.schemas.book import (
    BookCreate,
    BookUpdate,
    BookResponse,
    BookListResponse,
)

router = APIRouter()


@router.get("", response_model=BookListResponse)
def list_books(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    inventory_type: str | None = None,
    category: str | None = None,
    status: str | None = None,
    publisher_id: int | None = None,
    author_id: int | None = None,
    binder_id: int | None = None,
    binding_authenticated: bool | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    sort_by: str = "title",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
):
    """List books with filtering and pagination."""
    query = db.query(Book)

    # Apply filters
    if inventory_type:
        query = query.filter(Book.inventory_type == inventory_type)
    if category:
        query = query.filter(Book.category == category)
    if status:
        query = query.filter(Book.status == status)
    if publisher_id:
        query = query.filter(Book.publisher_id == publisher_id)
    if author_id:
        query = query.filter(Book.author_id == author_id)
    if binder_id:
        query = query.filter(Book.binder_id == binder_id)
    if binding_authenticated is not None:
        query = query.filter(Book.binding_authenticated == binding_authenticated)
    if min_value is not None:
        query = query.filter(Book.value_mid >= min_value)
    if max_value is not None:
        query = query.filter(Book.value_mid <= max_value)

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
    items = []
    for book in books:
        book_dict = BookResponse.model_validate(book).model_dump()
        book_dict["has_analysis"] = book.analysis is not None
        book_dict["image_count"] = len(book.images) if book.images else 0
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

    response = BookResponse.model_validate(book)
    response.has_analysis = book.analysis is not None
    response.image_count = len(book.images) if book.images else 0
    return response


@router.post("", response_model=BookResponse, status_code=201)
def create_book(book_data: BookCreate, db: Session = Depends(get_db)):
    """Create a new book."""
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
def update_book(book_id: int, book_data: BookUpdate, db: Session = Depends(get_db)):
    """Update a book."""
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
def delete_book(book_id: int, db: Session = Depends(get_db)):
    """Delete a book."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    db.delete(book)
    db.commit()


@router.patch("/{book_id}/status")
def update_book_status(
    book_id: int,
    status: str = Query(...),
    db: Session = Depends(get_db),
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
):
    """Bulk update status for multiple books."""
    valid_statuses = ["IN_TRANSIT", "ON_HAND", "SOLD", "REMOVED"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    updated = db.query(Book).filter(Book.id.in_(book_ids)).update(
        {Book.status: status},
        synchronize_session=False,
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
    matches = db.query(Book).filter(
        Book.title.ilike(f"%{title}%"),
        Book.inventory_type == "PRIMARY",
    ).all()

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
    full_markdown: str,
    db: Session = Depends(get_db),
):
    """Update or create analysis for a book."""
    from app.models import BookAnalysis

    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.analysis:
        book.analysis.full_markdown = full_markdown
    else:
        analysis = BookAnalysis(
            book_id=book_id,
            full_markdown=full_markdown,
        )
        db.add(analysis)

    db.commit()
    return {"message": "Analysis updated"}
