"""Authors API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Author

router = APIRouter()


@router.get("")
def list_authors(
    search: str | None = None,
    db: Session = Depends(get_db),
):
    """List all authors, optionally filtered by search."""
    query = db.query(Author)

    if search:
        query = query.filter(Author.name.ilike(f"%{search}%"))

    authors = query.order_by(Author.name).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "birth_year": a.birth_year,
            "death_year": a.death_year,
            "era": a.era,
            "book_count": len(a.books),
        }
        for a in authors
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
