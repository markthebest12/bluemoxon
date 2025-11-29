"""Binders API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Binder
from app.schemas.reference import BinderCreate, BinderResponse, BinderUpdate

router = APIRouter()


@router.get("")
def list_binders(db: Session = Depends(get_db)):
    """List all authenticated binding houses."""
    binders = db.query(Binder).order_by(Binder.name).all()
    return [
        {
            "id": b.id,
            "name": b.name,
            "full_name": b.full_name,
            "authentication_markers": b.authentication_markers,
            "book_count": len(b.books),
        }
        for b in binders
    ]


@router.get("/{binder_id}")
def get_binder(binder_id: int, db: Session = Depends(get_db)):
    """Get a single binder with their books."""
    binder = db.query(Binder).filter(Binder.id == binder_id).first()
    if not binder:
        raise HTTPException(status_code=404, detail="Binder not found")

    return {
        "id": binder.id,
        "name": binder.name,
        "full_name": binder.full_name,
        "authentication_markers": binder.authentication_markers,
        "book_count": len(binder.books),
        "books": [
            {
                "id": b.id,
                "title": b.title,
                "author": b.author.name if b.author else None,
                "publication_date": b.publication_date,
                "value_mid": float(b.value_mid) if b.value_mid else None,
            }
            for b in binder.books
        ],
    }


@router.post("", response_model=BinderResponse, status_code=201)
def create_binder(binder_data: BinderCreate, db: Session = Depends(get_db)):
    """Create a new binder."""
    # Check for existing binder with same name
    existing = db.query(Binder).filter(Binder.name == binder_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Binder with this name already exists")

    binder = Binder(**binder_data.model_dump())
    db.add(binder)
    db.commit()
    db.refresh(binder)

    return BinderResponse(
        id=binder.id,
        name=binder.name,
        full_name=binder.full_name,
        authentication_markers=binder.authentication_markers,
        book_count=len(binder.books),
    )


@router.put("/{binder_id}", response_model=BinderResponse)
def update_binder(binder_id: int, binder_data: BinderUpdate, db: Session = Depends(get_db)):
    """Update a binder."""
    binder = db.query(Binder).filter(Binder.id == binder_id).first()
    if not binder:
        raise HTTPException(status_code=404, detail="Binder not found")

    update_data = binder_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(binder, field, value)

    db.commit()
    db.refresh(binder)

    return BinderResponse(
        id=binder.id,
        name=binder.name,
        full_name=binder.full_name,
        authentication_markers=binder.authentication_markers,
        book_count=len(binder.books),
    )


@router.delete("/{binder_id}", status_code=204)
def delete_binder(binder_id: int, db: Session = Depends(get_db)):
    """Delete a binder. Will fail if binder has associated books."""
    binder = db.query(Binder).filter(Binder.id == binder_id).first()
    if not binder:
        raise HTTPException(status_code=404, detail="Binder not found")

    if binder.books:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete binder with {len(binder.books)} associated books. "
            "Remove books first or reassign them to another binder.",
        )

    db.delete(binder)
    db.commit()
