"""Publishers API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Publisher

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
        }
        for p in publishers
    ]


@router.get("/{publisher_id}")
def get_publisher(publisher_id: int, db: Session = Depends(get_db)):
    """Get a single publisher."""
    publisher = db.query(Publisher).filter(Publisher.id == publisher_id).first()
    if not publisher:
        raise HTTPException(status_code=404, detail="Publisher not found")

    return {
        "id": publisher.id,
        "name": publisher.name,
        "tier": publisher.tier,
        "founded_year": publisher.founded_year,
        "description": publisher.description,
        "book_count": len(publisher.books),
    }
