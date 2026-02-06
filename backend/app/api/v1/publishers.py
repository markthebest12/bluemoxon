"""Publishers API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import require_editor
from app.db import get_db
from app.models import Book, Publisher
from app.schemas.entity_validation import EntityValidationError
from app.schemas.reference import (
    PublisherCreate,
    PublisherResponse,
    PublisherUpdate,
    ReassignRequest,
    ReassignResponse,
)
from app.services.entity_matching import invalidate_entity_cache
from app.services.entity_validation import validate_entity_creation
from app.services.sqs import send_entity_enrichment_job

router = APIRouter()


@router.get("")
def list_publishers(db: Session = Depends(get_db)):
    """List all publishers."""
    # Use subquery count to avoid N+1 queries for book_count
    book_count_subq = (
        db.query(func.count(Book.id))
        .filter(Book.publisher_id == Publisher.id)
        .correlate(Publisher)
        .scalar_subquery()
    )

    results = (
        db.query(Publisher, book_count_subq.label("book_count"))
        .order_by(Publisher.tier, Publisher.name)
        .all()
    )
    return [
        {
            "id": p.id,
            "name": p.name,
            "tier": p.tier,
            "founded_year": p.founded_year,
            "description": p.description,
            "preferred": p.preferred,
            "book_count": book_count,
        }
        for p, book_count in results
    ]


@router.get("/{publisher_id}")
def get_publisher(publisher_id: int, db: Session = Depends(get_db)):
    """Get a single publisher with their books."""
    publisher = db.query(Publisher).filter(Publisher.id == publisher_id).first()
    if not publisher:
        raise HTTPException(status_code=404, detail="Publisher not found")

    return {
        "id": publisher.id,
        "name": publisher.name,
        "tier": publisher.tier,
        "founded_year": publisher.founded_year,
        "description": publisher.description,
        "preferred": publisher.preferred,
        "book_count": len(publisher.books),
        "books": [
            {
                "id": b.id,
                "title": b.title,
                "author": b.author.name if b.author else None,
                "publication_date": b.publication_date,
                "value_mid": float(b.value_mid) if b.value_mid else None,
            }
            for b in publisher.books
        ],
    }


@router.post(
    "",
    response_model=PublisherResponse,
    status_code=201,
    responses={409: {"model": EntityValidationError, "description": "Similar publisher exists"}},
)
def create_publisher(
    publisher_data: PublisherCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
    force: bool = Query(
        default=False,
        description="Bypass duplicate validation and create anyway",
    ),
):
    """Create a new publisher. Requires editor role."""
    # Check for similar existing publishers (fuzzy match) unless force=true
    # Do this BEFORE exact match to catch typos that would create duplicates
    if not force:
        validation_error = validate_entity_creation(
            db=db,
            entity_type="publisher",
            name=publisher_data.name,
        )
        if validation_error:
            return JSONResponse(
                status_code=409,
                content=validation_error.model_dump(
                    include={"error", "entity_type", "input", "suggestions", "resolution"}
                ),
            )

    # Check for existing publisher with same name (exact match)
    existing = db.query(Publisher).filter(Publisher.name == publisher_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Publisher with this name already exists")

    publisher = Publisher(**publisher_data.model_dump())
    db.add(publisher)
    db.commit()
    db.refresh(publisher)

    # Invalidate cache since new publisher was created
    invalidate_entity_cache("publisher")

    # Fire-and-forget: enqueue async enrichment via Bedrock (never blocks creation)
    send_entity_enrichment_job("publisher", publisher.id, publisher.name)

    return PublisherResponse(
        id=publisher.id,
        name=publisher.name,
        tier=publisher.tier,
        founded_year=publisher.founded_year,
        description=publisher.description,
        preferred=publisher.preferred,
        book_count=len(publisher.books),
    )


@router.put("/{publisher_id}", response_model=PublisherResponse)
def update_publisher(
    publisher_id: int,
    publisher_data: PublisherUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Update a publisher. Requires editor role."""
    publisher = db.query(Publisher).filter(Publisher.id == publisher_id).first()
    if not publisher:
        raise HTTPException(status_code=404, detail="Publisher not found")

    update_data = publisher_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(publisher, field, value)

    db.commit()
    db.refresh(publisher)

    # Invalidate cache if name or tier changed (affects fuzzy matching)
    invalidate_entity_cache("publisher")

    return PublisherResponse(
        id=publisher.id,
        name=publisher.name,
        tier=publisher.tier,
        founded_year=publisher.founded_year,
        description=publisher.description,
        preferred=publisher.preferred,
        book_count=len(publisher.books),
    )


@router.delete("/{publisher_id}", status_code=204)
def delete_publisher(
    publisher_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Delete a publisher. Requires editor role. Will fail if publisher has associated books."""
    publisher = db.query(Publisher).filter(Publisher.id == publisher_id).first()
    if not publisher:
        raise HTTPException(status_code=404, detail="Publisher not found")

    if publisher.books:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete publisher with {len(publisher.books)} associated books. "
            "Remove books first or reassign them to another publisher.",
        )

    db.delete(publisher)
    db.commit()

    # Invalidate cache since publisher was deleted
    invalidate_entity_cache("publisher")


@router.post("/{publisher_id}/reassign", response_model=ReassignResponse)
def reassign_publisher_books(
    publisher_id: int,
    body: ReassignRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """
    Reassign all books from source publisher to target publisher, then delete source.
    Requires editor role.
    """
    # Validate source exists
    source = db.query(Publisher).filter(Publisher.id == publisher_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source publisher not found")

    # Validate not same entity
    if publisher_id == body.target_id:
        raise HTTPException(status_code=400, detail="Cannot reassign to same publisher")

    # Validate target exists
    target = db.query(Publisher).filter(Publisher.id == body.target_id).first()
    if not target:
        raise HTTPException(status_code=400, detail="Target publisher not found")

    # Count and reassign books
    book_count = db.query(Book).filter(Book.publisher_id == publisher_id).count()
    db.query(Book).filter(Book.publisher_id == publisher_id).update(
        {"publisher_id": body.target_id}
    )

    # Store names before deletion
    source_name = source.name
    target_name = target.name

    # Delete source publisher
    db.delete(source)
    db.commit()

    # Invalidate cache since publisher was deleted
    invalidate_entity_cache("publisher")

    return ReassignResponse(
        reassigned_count=book_count,
        deleted_entity=source_name,
        target_entity=target_name,
    )
