"""Authors API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import require_editor
from app.db import get_db
from app.models import Author, Book
from app.schemas.entity_validation import EntityValidationError
from app.schemas.reference import (
    AuthorCreate,
    AuthorResponse,
    AuthorUpdate,
    ReassignRequest,
    ReassignResponse,
)
from app.services.entity_matching import invalidate_entity_cache
from app.services.entity_validation import validate_entity_creation
from app.services.sqs import send_entity_enrichment_job

router = APIRouter()


@router.get("")
def list_authors(
    search: str | None = None,
    db: Session = Depends(get_db),
):
    """List all authors, optionally filtered by search."""
    # Use subquery count to avoid N+1 queries for book_count
    book_count_subq = (
        db.query(func.count(Book.id))
        .filter(Book.author_id == Author.id)
        .correlate(Author)
        .scalar_subquery()
    )

    query = db.query(Author, book_count_subq.label("book_count"))

    if search:
        query = query.filter(Author.name.ilike(f"%{search}%"))

    results = query.order_by(Author.name).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "birth_year": a.birth_year,
            "death_year": a.death_year,
            "era": a.era,
            "priority_score": a.priority_score,
            "tier": a.tier,
            "preferred": a.preferred,
            "book_count": book_count,
        }
        for a, book_count in results
    ]


@router.get("/{author_id}")
def get_author(author_id: int, db: Session = Depends(get_db)):
    """Get a single author with their books."""
    author = db.query(Author).filter(Author.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    return {
        "id": author.id,
        "name": author.name,
        "birth_year": author.birth_year,
        "death_year": author.death_year,
        "era": author.era,
        "first_acquired_date": author.first_acquired_date,
        "preferred": author.preferred,
        "books": [
            {
                "id": b.id,
                "title": b.title,
                "publication_date": b.publication_date,
                "value_mid": float(b.value_mid) if b.value_mid else None,
            }
            for b in author.books
        ],
    }


@router.post(
    "",
    response_model=AuthorResponse,
    status_code=201,
    responses={409: {"model": EntityValidationError, "description": "Similar author exists"}},
)
def create_author(
    author_data: AuthorCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
    force: bool = Query(
        default=False,
        description="Bypass duplicate validation and create anyway",
    ),
):
    """Create a new author. Requires editor role."""
    # Check for similar existing authors (fuzzy match) unless force=true
    # Do this BEFORE exact match to catch typos that would create duplicates
    if not force:
        validation_error = validate_entity_creation(
            db=db,
            entity_type="author",
            name=author_data.name,
        )
        if validation_error:
            return JSONResponse(
                status_code=409,
                content=validation_error.model_dump(
                    include={"error", "entity_type", "input", "suggestions", "resolution"}
                ),
            )

    # Check for existing author with same name (exact match)
    existing = db.query(Author).filter(Author.name == author_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Author with this name already exists")

    author = Author(**author_data.model_dump())
    db.add(author)
    db.commit()
    db.refresh(author)
    invalidate_entity_cache("author")

    # Fire-and-forget: enqueue async enrichment via Bedrock (never blocks creation)
    send_entity_enrichment_job("author", author.id, author.name)

    return AuthorResponse(
        id=author.id,
        name=author.name,
        birth_year=author.birth_year,
        death_year=author.death_year,
        era=author.era,
        first_acquired_date=author.first_acquired_date,
        priority_score=author.priority_score,
        tier=author.tier,
        preferred=author.preferred,
        book_count=len(author.books),
    )


@router.put("/{author_id}", response_model=AuthorResponse)
def update_author(
    author_id: int,
    author_data: AuthorUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Update an author. Requires editor role."""
    author = db.query(Author).filter(Author.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    update_data = author_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(author, field, value)

    db.commit()
    db.refresh(author)
    invalidate_entity_cache("author")

    return AuthorResponse(
        id=author.id,
        name=author.name,
        birth_year=author.birth_year,
        death_year=author.death_year,
        era=author.era,
        first_acquired_date=author.first_acquired_date,
        priority_score=author.priority_score,
        tier=author.tier,
        preferred=author.preferred,
        book_count=len(author.books),
    )


@router.delete("/{author_id}", status_code=204)
def delete_author(
    author_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Delete an author. Requires editor role. Will fail if author has associated books."""
    author = db.query(Author).filter(Author.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    if author.books:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete author with {len(author.books)} associated books. "
            "Remove books first or reassign them to another author.",
        )

    db.delete(author)
    db.commit()
    invalidate_entity_cache("author")


@router.post("/{author_id}/reassign", response_model=ReassignResponse)
def reassign_author_books(
    author_id: int,
    body: ReassignRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """
    Reassign all books from source author to target author, then delete source.
    Requires editor role.
    """
    # Validate source exists
    source = db.query(Author).filter(Author.id == author_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source author not found")

    # Validate not same entity
    if author_id == body.target_id:
        raise HTTPException(status_code=400, detail="Cannot reassign to same author")

    # Validate target exists
    target = db.query(Author).filter(Author.id == body.target_id).first()
    if not target:
        raise HTTPException(status_code=400, detail="Target author not found")

    # Count and reassign books
    book_count = db.query(Book).filter(Book.author_id == author_id).count()
    db.query(Book).filter(Book.author_id == author_id).update({"author_id": body.target_id})

    # Store names before deletion
    source_name = source.name
    target_name = target.name

    # Delete source author
    db.delete(source)
    db.commit()
    invalidate_entity_cache("author")

    return ReassignResponse(
        reassigned_count=book_count,
        deleted_entity=source_name,
        target_entity=target_name,
    )
