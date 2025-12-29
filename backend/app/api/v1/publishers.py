"""Publishers API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_editor
from app.db import get_db
from app.models import Publisher
from app.schemas.reference import PublisherCreate, PublisherResponse, PublisherUpdate

router = APIRouter()


@router.get("")
def list_publishers(db: Session = Depends(get_db)):
    """List all publishers."""
    publishers = db.query(Publisher).order_by(Publisher.tier, Publisher.name).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "tier": p.tier,
            "founded_year": p.founded_year,
            "description": p.description,
            "preferred": p.preferred,
            "book_count": len(p.books),
        }
        for p in publishers
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


@router.post("", response_model=PublisherResponse, status_code=201)
def create_publisher(
    publisher_data: PublisherCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Create a new publisher. Requires editor role."""
    # Check for existing publisher with same name
    existing = db.query(Publisher).filter(Publisher.name == publisher_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Publisher with this name already exists")

    publisher = Publisher(**publisher_data.model_dump())
    db.add(publisher)
    db.commit()
    db.refresh(publisher)

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
