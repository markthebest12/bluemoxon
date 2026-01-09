"""Binders API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.auth import require_editor
from app.db import get_db
from app.models import Binder, Book
from app.schemas.reference import (
    BinderCreate,
    BinderResponse,
    BinderUpdate,
    ReassignRequest,
    ReassignResponse,
)
from app.services.entity_matching import invalidate_entity_cache
from app.services.entity_validation import validate_entity_creation

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
            "tier": b.tier,
            "preferred": b.preferred,
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
        "tier": binder.tier,
        "preferred": binder.preferred,
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
def create_binder(
    binder_data: BinderCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
    force: bool = Query(
        default=False,
        description="Bypass duplicate validation and create anyway",
    ),
):
    """Create a new binder. Requires editor role."""
    # Check for existing binder with same name (exact match)
    existing = db.query(Binder).filter(Binder.name == binder_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Binder with this name already exists")

    # Check for similar existing binders (fuzzy match) unless force=true
    if not force:
        validation_error = validate_entity_creation(
            db=db,
            entity_type="binder",
            name=binder_data.name,
        )
        if validation_error:
            return JSONResponse(status_code=409, content=validation_error.model_dump())

    binder = Binder(**binder_data.model_dump())
    db.add(binder)
    db.commit()
    db.refresh(binder)
    invalidate_entity_cache("binder")

    return BinderResponse(
        id=binder.id,
        name=binder.name,
        tier=binder.tier,
        full_name=binder.full_name,
        authentication_markers=binder.authentication_markers,
        preferred=binder.preferred,
        book_count=len(binder.books),
    )


@router.put("/{binder_id}", response_model=BinderResponse)
def update_binder(
    binder_id: int,
    binder_data: BinderUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Update a binder. Requires editor role."""
    binder = db.query(Binder).filter(Binder.id == binder_id).first()
    if not binder:
        raise HTTPException(status_code=404, detail="Binder not found")

    update_data = binder_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(binder, field, value)

    db.commit()
    db.refresh(binder)
    invalidate_entity_cache("binder")

    return BinderResponse(
        id=binder.id,
        name=binder.name,
        tier=binder.tier,
        full_name=binder.full_name,
        authentication_markers=binder.authentication_markers,
        preferred=binder.preferred,
        book_count=len(binder.books),
    )


@router.delete("/{binder_id}", status_code=204)
def delete_binder(
    binder_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """Delete a binder. Requires editor role. Will fail if binder has associated books."""
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
    invalidate_entity_cache("binder")


@router.post("/{binder_id}/reassign", response_model=ReassignResponse)
def reassign_binder_books(
    binder_id: int,
    body: ReassignRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_editor),
):
    """
    Reassign all books from source binder to target binder, then delete source.
    Requires editor role.
    """
    # Validate source exists
    source = db.query(Binder).filter(Binder.id == binder_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source binder not found")

    # Validate not same entity
    if binder_id == body.target_id:
        raise HTTPException(status_code=400, detail="Cannot reassign to same binder")

    # Validate target exists
    target = db.query(Binder).filter(Binder.id == body.target_id).first()
    if not target:
        raise HTTPException(status_code=400, detail="Target binder not found")

    # Count and reassign books
    book_count = db.query(Book).filter(Book.binder_id == binder_id).count()
    db.query(Book).filter(Book.binder_id == binder_id).update({"binder_id": body.target_id})

    # Store names before deletion
    source_name = source.name
    target_name = target.name

    # Delete source binder
    db.delete(source)
    db.commit()
    invalidate_entity_cache("binder")

    return ReassignResponse(
        reassigned_count=book_count,
        deleted_entity=source_name,
        target_entity=target_name,
    )
