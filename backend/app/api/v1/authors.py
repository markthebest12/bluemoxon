"""Authors API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_editor
from app.db import get_db
from app.models import Author
from app.schemas.reference import AuthorCreate, AuthorResponse, AuthorUpdate

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
            "priority_score": a.priority_score,
            "tier": a.tier,
            "preferred": a.preferred,
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


@router.post("", response_model=AuthorResponse, status_code=201)
def create_author(
    author_data: AuthorCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Create a new author. Requires editor role."""
    # Check for existing author with same name
    existing = db.query(Author).filter(Author.name == author_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Author with this name already exists")

    author = Author(**author_data.model_dump())
    db.add(author)
    db.commit()
    db.refresh(author)

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
