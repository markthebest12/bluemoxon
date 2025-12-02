"""Statistics API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Binder, Book, Publisher

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
    primary_value_row = (
        db.query(
            func.sum(Book.value_low),
            func.sum(Book.value_mid),
            func.sum(Book.value_high),
        )
        .filter(Book.inventory_type == "PRIMARY")
        .first()
    )

    # Extract values with None handling
    value_low = float(primary_value_row[0] or 0) if primary_value_row else 0.0
    value_mid = float(primary_value_row[1] or 0) if primary_value_row else 0.0
    value_high = float(primary_value_row[2] or 0) if primary_value_row else 0.0

    # Volume count
    total_volumes = (
        db.query(func.sum(Book.volumes)).filter(Book.inventory_type == "PRIMARY").scalar() or 0
    )

    # Authenticated bindings count
    authenticated_count = (
        db.query(Book)
        .filter(
            Book.binding_authenticated.is_(True),
            Book.inventory_type == "PRIMARY",
        )
        .count()
    )

    # In-transit count
    in_transit_count = (
        db.query(Book)
        .filter(
            Book.status == "IN_TRANSIT",
            Book.inventory_type == "PRIMARY",
        )
        .count()
    )

    return {
        "primary": {
            "count": primary_count,
            "volumes": total_volumes,
            "value_low": value_low,
            "value_mid": value_mid,
            "value_high": value_high,
        },
        "extended": {
            "count": extended_count,
        },
        "flagged": {
            "count": flagged_count,
        },
        "total_items": primary_count + extended_count + flagged_count,
        "authenticated_bindings": authenticated_count,
        "in_transit": in_transit_count,
    }


@router.get("/metrics")
def get_collection_metrics(db: Session = Depends(get_db)):
    """Get detailed collection metrics including Victorian %, ROI, discount averages."""
    primary_books = db.query(Book).filter(Book.inventory_type == "PRIMARY").all()

    if not primary_books:
        return {
            "victorian_percentage": 0,
            "average_discount": 0,
            "average_roi": 0,
            "tier_1_count": 0,
            "tier_1_percentage": 0,
            "complete_sets": 0,
            "total_purchase_cost": 0,
            "total_current_value": 0,
        }

    total_count = len(primary_books)

    # Victorian/Romantic era books (1800-1901)
    victorian_count = 0
    for book in primary_books:
        if book.year_start and 1800 <= book.year_start <= 1901:
            victorian_count += 1
        elif book.year_end and 1800 <= book.year_end <= 1901:
            victorian_count += 1

    victorian_pct = (victorian_count / total_count * 100) if total_count > 0 else 0

    # Average discount and ROI
    discounts = [float(b.discount_pct) for b in primary_books if b.discount_pct is not None]
    rois = [float(b.roi_pct) for b in primary_books if b.roi_pct is not None]

    avg_discount = sum(discounts) / len(discounts) if discounts else 0
    avg_roi = sum(rois) / len(rois) if rois else 0

    # Tier 1 publisher count
    tier_1_count = (
        db.query(Book)
        .join(Publisher)
        .filter(
            Book.inventory_type == "PRIMARY",
            Publisher.tier == "TIER_1",
        )
        .count()
    )

    tier_1_pct = (tier_1_count / total_count * 100) if total_count > 0 else 0

    # Total purchase cost and current value
    total_purchase = sum(float(b.purchase_price) for b in primary_books if b.purchase_price)
    total_value = sum(float(b.value_mid) for b in primary_books if b.value_mid)

    return {
        "victorian_percentage": round(victorian_pct, 1),
        "average_discount": round(avg_discount, 1),
        "average_roi": round(avg_roi, 1),
        "tier_1_count": tier_1_count,
        "tier_1_percentage": round(tier_1_pct, 1),
        "total_purchase_cost": round(total_purchase, 2),
        "total_current_value": round(total_value, 2),
        "total_items": total_count,
    }


@router.get("/by-category")
def get_by_category(db: Session = Depends(get_db)):
    """Get counts by category."""
    results = (
        db.query(
            Book.category,
            func.count(Book.id),
            func.sum(Book.value_mid),
        )
        .filter(Book.inventory_type == "PRIMARY")
        .group_by(Book.category)
        .all()
    )

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
    results = (
        db.query(
            Publisher.name,
            Publisher.tier,
            func.count(Book.id),
            func.sum(Book.value_mid),
            func.sum(Book.volumes),
        )
        .join(Book, Book.publisher_id == Publisher.id)
        .filter(Book.inventory_type == "PRIMARY")
        .group_by(Publisher.id)
        .order_by(Publisher.tier, func.count(Book.id).desc())
        .all()
    )

    return [
        {
            "publisher": row[0],
            "tier": row[1],
            "count": row[2],
            "value": float(row[3] or 0),
            "volumes": row[4] or 0,
        }
        for row in results
    ]


@router.get("/by-author")
def get_by_author(db: Session = Depends(get_db)):
    """Get counts by author."""
    from app.models import Author

    results = (
        db.query(
            Author.name,
            func.count(Book.id),
            func.sum(Book.value_mid),
            func.sum(Book.volumes),
        )
        .join(Book, Book.author_id == Author.id)
        .filter(Book.inventory_type == "PRIMARY")
        .group_by(Author.id)
        .order_by(func.count(Book.id).desc())
        .all()
    )

    return [
        {
            "author": row[0],
            "count": row[1],
            "value": float(row[2] or 0),
            "volumes": row[3] or 0,
        }
        for row in results
    ]


@router.get("/bindings")
def get_bindings(db: Session = Depends(get_db)):
    """Get authenticated binding counts by binder."""
    results = (
        db.query(
            Binder.name,
            Binder.full_name,
            func.count(Book.id),
            func.sum(Book.value_mid),
        )
        .join(Book, Book.binder_id == Binder.id)
        .filter(
            Book.binding_authenticated.is_(True),
            Book.inventory_type == "PRIMARY",
        )
        .group_by(Binder.id)
        .order_by(func.count(Book.id).desc())
        .all()
    )

    return [
        {
            "binder": row[0],
            "full_name": row[1],
            "count": row[2],
            "value": float(row[3] or 0),
        }
        for row in results
    ]


@router.get("/by-era")
def get_by_era(db: Session = Depends(get_db)):
    """Get counts by era (Victorian, Romantic, etc.)."""
    primary_books = db.query(Book).filter(Book.inventory_type == "PRIMARY").all()

    era_counts = {
        "Romantic (1800-1837)": 0,
        "Victorian (1837-1901)": 0,
        "Edwardian (1901-1910)": 0,
        "Post-1910": 0,
        "Unknown": 0,
    }

    era_values = dict.fromkeys(era_counts.keys(), 0.0)

    for book in primary_books:
        year = book.year_start or book.year_end
        value = float(book.value_mid) if book.value_mid else 0

        if not year:
            era_counts["Unknown"] += 1
            era_values["Unknown"] += value
        elif 1800 <= year < 1837:
            era_counts["Romantic (1800-1837)"] += 1
            era_values["Romantic (1800-1837)"] += value
        elif 1837 <= year <= 1901:
            era_counts["Victorian (1837-1901)"] += 1
            era_values["Victorian (1837-1901)"] += value
        elif 1901 < year <= 1910:
            era_counts["Edwardian (1901-1910)"] += 1
            era_values["Edwardian (1901-1910)"] += value
        else:
            era_counts["Post-1910"] += 1
            era_values["Post-1910"] += value

    return [
        {
            "era": era,
            "count": count,
            "value": round(era_values[era], 2),
        }
        for era, count in era_counts.items()
        if count > 0
    ]


@router.get("/pending-deliveries")
def get_pending_deliveries(db: Session = Depends(get_db)):
    """Get list of books currently in transit."""
    books = (
        db.query(Book)
        .filter(
            Book.status == "IN_TRANSIT",
            Book.inventory_type == "PRIMARY",
        )
        .all()
    )

    return {
        "count": len(books),
        "items": [
            {
                "id": b.id,
                "title": b.title,
                "author": b.author.name if b.author else None,
                "purchase_date": b.purchase_date.isoformat() if b.purchase_date else None,
                "value_mid": float(b.value_mid) if b.value_mid else None,
            }
            for b in books
        ],
    }


@router.get("/acquisitions-by-month")
def get_acquisitions_by_month(db: Session = Depends(get_db)):
    """Get acquisition counts and values by month for trend analysis."""
    from sqlalchemy import extract

    # Get all primary books with purchase dates
    results = (
        db.query(
            extract("year", Book.purchase_date).label("year"),
            extract("month", Book.purchase_date).label("month"),
            func.count(Book.id).label("count"),
            func.sum(Book.value_mid).label("value"),
            func.sum(Book.purchase_price).label("cost"),
        )
        .filter(
            Book.inventory_type == "PRIMARY",
            Book.purchase_date.isnot(None),
        )
        .group_by(
            extract("year", Book.purchase_date),
            extract("month", Book.purchase_date),
        )
        .order_by(
            extract("year", Book.purchase_date),
            extract("month", Book.purchase_date),
        )
        .all()
    )

    return [
        {
            "year": int(row.year),
            "month": int(row.month),
            "label": f"{int(row.year)}-{int(row.month):02d}",
            "count": row.count,
            "value": float(row.value or 0),
            "cost": float(row.cost or 0),
        }
        for row in results
    ]


@router.get("/value-by-category")
def get_value_by_category(db: Session = Depends(get_db)):
    """Get value distribution by major categories for pie chart."""
    # Get premium binding value
    premium_value = (
        db.query(func.sum(Book.value_mid))
        .filter(
            Book.inventory_type == "PRIMARY",
            Book.binding_authenticated.is_(True),
        )
        .scalar()
        or 0
    )

    # Get Tier 1 publisher value (excluding premium bindings to avoid double counting)
    tier1_value = (
        db.query(func.sum(Book.value_mid))
        .join(Publisher)
        .filter(
            Book.inventory_type == "PRIMARY",
            Publisher.tier == "TIER_1",
            Book.binding_authenticated.is_not(True),
        )
        .scalar()
        or 0
    )

    # Get remaining value
    total_value = (
        db.query(func.sum(Book.value_mid)).filter(Book.inventory_type == "PRIMARY").scalar() or 0
    )

    other_value = float(total_value) - float(premium_value) - float(tier1_value)

    return [
        {"category": "Premium Bindings", "value": float(premium_value)},
        {"category": "Tier 1 Publishers", "value": float(tier1_value)},
        {"category": "Other", "value": max(0, other_value)},
    ]
