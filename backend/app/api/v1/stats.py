"""Statistics API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import get_db
from app.models import Book, Publisher, Binder

router = APIRouter()


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """Get collection overview statistics."""
    # Total counts by inventory type
    primary = db.query(Book).filter(Book.inventory_type == "PRIMARY")
    extended = db.query(Book).filter(Book.inventory_type == "EXTENDED")
    flagged = db.query(Book).filter(Book.inventory_type == "FLAGGED")

    primary_count = primary.count()
    extended_count = extended.count()
    flagged_count = flagged.count()

    # Value sums for primary collection
    primary_value = db.query(
        func.sum(Book.value_low),
        func.sum(Book.value_mid),
        func.sum(Book.value_high),
    ).filter(Book.inventory_type == "PRIMARY").first()

    # Volume count
    total_volumes = db.query(func.sum(Book.volumes)).filter(
        Book.inventory_type == "PRIMARY"
    ).scalar() or 0

    # Authenticated bindings count
    authenticated_count = db.query(Book).filter(
        Book.binding_authenticated == True,
        Book.inventory_type == "PRIMARY",
    ).count()

    return {
        "primary": {
            "count": primary_count,
            "volumes": total_volumes,
            "value_low": float(primary_value[0] or 0),
            "value_mid": float(primary_value[1] or 0),
            "value_high": float(primary_value[2] or 0),
        },
        "extended": {
            "count": extended_count,
        },
        "flagged": {
            "count": flagged_count,
        },
        "total_items": primary_count + extended_count + flagged_count,
        "authenticated_bindings": authenticated_count,
    }


@router.get("/by-category")
def get_by_category(db: Session = Depends(get_db)):
    """Get counts by category."""
    results = db.query(
        Book.category,
        func.count(Book.id),
        func.sum(Book.value_mid),
    ).filter(
        Book.inventory_type == "PRIMARY"
    ).group_by(Book.category).all()

    return [
        {
            "category": row[0] or "Uncategorized",
            "count": row[1],
            "value": float(row[2] or 0),
        }
        for row in results
    ]


@router.get("/by-publisher")
def get_by_publisher(db: Session = Depends(get_db)):
    """Get counts by publisher with tier info."""
    results = db.query(
        Publisher.name,
        Publisher.tier,
        func.count(Book.id),
        func.sum(Book.value_mid),
    ).join(Book, Book.publisher_id == Publisher.id).filter(
        Book.inventory_type == "PRIMARY"
    ).group_by(Publisher.id).all()

    return [
        {
            "publisher": row[0],
            "tier": row[1],
            "count": row[2],
            "value": float(row[3] or 0),
        }
        for row in results
    ]


@router.get("/bindings")
def get_bindings(db: Session = Depends(get_db)):
    """Get authenticated binding counts by binder."""
    results = db.query(
        Binder.name,
        Binder.full_name,
        func.count(Book.id),
    ).join(Book, Book.binder_id == Binder.id).filter(
        Book.binding_authenticated == True,
        Book.inventory_type == "PRIMARY",
    ).group_by(Binder.id).order_by(func.count(Book.id).desc()).all()

    return [
        {
            "binder": row[0],
            "full_name": row[1],
            "count": row[2],
        }
        for row in results
    ]
