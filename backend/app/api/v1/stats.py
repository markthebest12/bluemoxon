"""Statistics API endpoints."""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Binder, Book, Publisher

router = APIRouter()

# Tier 1 Victorian publishers - these are the premium publishers
TIER_1_PUBLISHERS = [
    "Smith Elder",
    "Smith, Elder",
    "Macmillan",
    "John Murray",
    "Edward Moxon",
    "Chapman and Hall",
    "Chapman & Hall",
]


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """Get collection overview statistics.

    Returns current stats for ON_HAND books only, plus week-over-week changes.
    """
    # Base filter: PRIMARY + ON_HAND only
    on_hand_filter = (Book.inventory_type == "PRIMARY") & (Book.status == "ON_HAND")

    # Current counts (ON_HAND only)
    primary_on_hand = db.query(Book).filter(on_hand_filter)
    primary_count = primary_on_hand.count()

    # Extended and flagged (all statuses for reference)
    extended_count = db.query(Book).filter(Book.inventory_type == "EXTENDED").count()
    flagged_count = db.query(Book).filter(Book.inventory_type == "FLAGGED").count()

    # Value sums for ON_HAND books
    primary_value_row = (
        db.query(
            func.sum(Book.value_low),
            func.sum(Book.value_mid),
            func.sum(Book.value_high),
        )
        .filter(on_hand_filter)
        .first()
    )

    value_low = float(primary_value_row[0] or 0) if primary_value_row else 0.0
    value_mid = float(primary_value_row[1] or 0) if primary_value_row else 0.0
    value_high = float(primary_value_row[2] or 0) if primary_value_row else 0.0

    # Volume count (ON_HAND only)
    total_volumes = db.query(func.sum(Book.volumes)).filter(on_hand_filter).scalar() or 0

    # Authenticated bindings count (ON_HAND only)
    authenticated_count = (
        db.query(Book)
        .filter(
            on_hand_filter,
            Book.binding_authenticated.is_(True),
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

    # Calculate week-over-week changes
    # Use purchase_date to find books acquired in the last 7 days
    one_week_ago = date.today() - timedelta(days=7)

    # This week's acquisitions (books purchased in last 7 days)
    week_arrivals = (
        db.query(Book)
        .filter(
            on_hand_filter,
            Book.purchase_date >= one_week_ago,
        )
        .all()
    )

    # Calculate deltas
    week_count_delta = len(week_arrivals)
    week_volumes_delta = sum(b.volumes or 1 for b in week_arrivals)
    week_value_delta = sum(float(b.value_mid or 0) for b in week_arrivals)
    week_premium_delta = sum(1 for b in week_arrivals if b.binding_authenticated)

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
        # Week-over-week changes (positive = growth)
        "week_delta": {
            "count": week_count_delta,
            "volumes": week_volumes_delta,
            "value_mid": round(week_value_delta, 2),
            "authenticated_bindings": week_premium_delta,
        },
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
    """Get counts by author with sample book titles."""
    from app.models import Author

    results = (
        db.query(
            Author.id,
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

    # For each author, get sample book titles (up to 5)
    author_data = []
    for row in results:
        author_id, author_name, count, value, volumes = row

        # Get sample book titles for this author
        sample_books = (
            db.query(Book.title)
            .filter(Book.author_id == author_id, Book.inventory_type == "PRIMARY")
            .limit(5)
            .all()
        )
        sample_titles = [b.title for b in sample_books]

        author_data.append(
            {
                "author": author_name,
                "count": count,
                "value": float(value or 0),
                "volumes": volumes or 0,
                "sample_titles": sample_titles,
                "has_more": count > 5,
            }
        )

    return author_data


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


@router.get("/acquisitions-daily")
def get_acquisitions_daily(
    db: Session = Depends(get_db),
    reference_date: str = Query(
        default=None,
        description="Reference date in YYYY-MM-DD format (defaults to today UTC)",
    ),
    days: int = Query(default=30, ge=7, le=90, description="Number of days to look back"),
):
    """Get daily acquisition data for the last N days.

    Returns cumulative value growth day by day, useful for trend charts.
    The reference_date should be the current date in the user's timezone.
    """
    # Parse reference date or use today
    if reference_date:
        try:
            ref_date = datetime.strptime(reference_date, "%Y-%m-%d").date()
        except ValueError:
            ref_date = date.today()
    else:
        ref_date = date.today()

    # Calculate date range
    start_date = ref_date - timedelta(days=days - 1)

    # Get all primary books with purchase dates in range
    books = (
        db.query(Book.purchase_date, Book.value_mid, Book.purchase_price)
        .filter(
            Book.inventory_type == "PRIMARY",
            Book.purchase_date.isnot(None),
            Book.purchase_date >= start_date,
            Book.purchase_date <= ref_date,
        )
        .all()
    )

    # Group by date
    daily_data: dict[date, dict] = {}
    for book in books:
        d = book.purchase_date
        if d not in daily_data:
            daily_data[d] = {"count": 0, "value": 0.0, "cost": 0.0}
        daily_data[d]["count"] += 1
        daily_data[d]["value"] += float(book.value_mid or 0)
        daily_data[d]["cost"] += float(book.purchase_price or 0)

    # Build daily series with cumulative values
    result = []
    cumulative_value = 0.0
    cumulative_cost = 0.0
    cumulative_count = 0

    current_date = start_date
    while current_date <= ref_date:
        day_data = daily_data.get(current_date, {"count": 0, "value": 0.0, "cost": 0.0})
        cumulative_count += day_data["count"]
        cumulative_value += day_data["value"]
        cumulative_cost += day_data["cost"]

        result.append(
            {
                "date": current_date.isoformat(),
                "label": current_date.strftime("%b %d"),
                "count": day_data["count"],
                "value": round(day_data["value"], 2),
                "cost": round(day_data["cost"], 2),
                "cumulative_count": cumulative_count,
                "cumulative_value": round(cumulative_value, 2),
                "cumulative_cost": round(cumulative_cost, 2),
            }
        )
        current_date += timedelta(days=1)

    return result


@router.post("/fix-publisher-tiers")
def fix_publisher_tiers(db: Session = Depends(get_db)):
    """One-time fix to set Tier 1 publisher tiers in the database."""
    updated = []
    for pub_name in TIER_1_PUBLISHERS:
        publisher = db.query(Publisher).filter(Publisher.name == pub_name).first()
        if publisher and publisher.tier != "TIER_1":
            publisher.tier = "TIER_1"
            updated.append(pub_name)

    db.commit()
    return {"updated": updated, "count": len(updated)}


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
