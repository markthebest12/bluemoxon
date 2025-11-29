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
    """Update book status."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book.status = status
    db.commit()

    return {"message": "Status updated", "status": status}
