"""Binders API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Binder

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
