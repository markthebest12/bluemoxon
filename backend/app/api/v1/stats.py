"""Statistics API endpoints."""

from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, literal
from sqlalchemy.orm import Session

from app.auth import require_viewer
from app.db import get_db
from app.models import Binder, Book, Publisher
from app.schemas.stats import DashboardResponse
from app.utils import safe_float

router = APIRouter()


@router.get("/overview")
def get_overview(db: Session = Depends(get_db), _user=Depends(require_viewer)):
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

    value_low = safe_float(primary_value_row[0]) if primary_value_row else 0.0
    value_mid = safe_float(primary_value_row[1]) if primary_value_row else 0.0
    value_high = safe_float(primary_value_row[2]) if primary_value_row else 0.0

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

    # Week delta calculation using SQL aggregation
    week_delta = (
        db.query(
            func.count(Book.id).label("count"),
            func.sum(func.coalesce(Book.volumes, 1)).label("volumes"),
            func.coalesce(func.sum(Book.value_mid), 0).label("value"),
            func.sum(case((Book.binding_authenticated.is_(True), 1), else_=0)).label(
                "authenticated"
            ),
        )
        .filter(
            on_hand_filter,
            Book.purchase_date >= one_week_ago,
        )
        .first()
    )

    # Extract values with defaults
    week_count_delta = week_delta.count or 0
    week_volumes_delta = int(week_delta.volumes or 0)
    week_value_delta = safe_float(week_delta.value)
    week_premium_delta = int(week_delta.authenticated or 0)

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
def get_collection_metrics(db: Session = Depends(get_db), _user=Depends(require_viewer)):
    """Get detailed collection metrics including Victorian %, ROI, discount averages."""
    # Victorian detection: year_start OR year_end in 1837-1901 (matches get_by_era)
    victorian_case = case(
        (
            (Book.year_start.between(1837, 1901)) | (Book.year_end.between(1837, 1901)),
            1,
        ),
        else_=0,
    )

    # Tier 1 publisher detection (combined with main query via OUTER JOIN)
    tier_1_case = case(
        (Publisher.tier == "TIER_1", 1),
        else_=0,
    )

    # Single aggregation query for all metrics (including Tier 1 via OUTER JOIN)
    result = (
        db.query(
            func.count(Book.id).label("total"),
            func.sum(victorian_case).label("victorian_count"),
            func.avg(Book.discount_pct).label("avg_discount"),
            func.avg(Book.roi_pct).label("avg_roi"),
            func.sum(Book.purchase_price).label("total_purchase"),
            func.sum(Book.value_mid).label("total_value"),
            func.sum(tier_1_case).label("tier_1_count"),
        )
        .outerjoin(Publisher)
        .filter(Book.inventory_type == "PRIMARY")
        .first()
    )

    total_count = result.total or 0

    if total_count == 0:
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

    victorian_count = result.victorian_count or 0
    victorian_pct = (victorian_count / total_count * 100) if total_count > 0 else 0

    avg_discount = safe_float(result.avg_discount)
    avg_roi = safe_float(result.avg_roi)

    total_purchase = safe_float(result.total_purchase)
    total_value = safe_float(result.total_value)
    tier_1_count = int(result.tier_1_count or 0)

    tier_1_pct = (tier_1_count / total_count * 100) if total_count > 0 else 0

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
def get_by_category(db: Session = Depends(get_db), _user=Depends(require_viewer)):
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
            "value": safe_float(row[2]),
        }
        for row in results
    ]


@router.get("/by-condition")
def get_by_condition(db: Session = Depends(get_db), _user=Depends(require_viewer)):
    """Get counts by condition grade."""
    results = (
        db.query(
            Book.condition_grade,
            func.count(Book.id),
            func.sum(Book.value_mid),
        )
        .filter(Book.inventory_type == "PRIMARY")
        .group_by(Book.condition_grade)
        .order_by(Book.condition_grade)
        .all()
    )

    return [
        {
            "condition": row[0] if row[0] is not None else "Ungraded",
            "count": row[1],
            "value": safe_float(row[2]),
        }
        for row in results
    ]


@router.get("/by-publisher")
def get_by_publisher(db: Session = Depends(get_db), _user=Depends(require_viewer)):
    """Get counts by publisher with tier info."""
    results = (
        db.query(
            Publisher.id,
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
            "publisher_id": row[0],
            "publisher": row[1],
            "tier": row[2],
            "count": row[3],
            "value": safe_float(row[4]),
            "volumes": row[5] or 0,
        }
        for row in results
    ]


@router.get("/by-author")
def get_by_author(db: Session = Depends(get_db), _user=Depends(require_viewer)):
    """Get counts by author with sample book titles.

    Returns:
        - count: Number of book records (a 24-volume set counts as 1)
        - total_volumes: Sum of all volumes (a 24-volume set contributes 24)
        - titles: Same as count, number of distinct book records

    Performance: Uses 2 batch queries instead of N+1 (one query per author).
    """
    from app.models import Author

    # Query 1: Aggregation (unchanged)
    results = (
        db.query(
            Author.id,
            Author.name,
            func.count(Book.id),  # Number of book records
            func.sum(Book.value_mid),
            func.sum(Book.volumes),  # Total volumes across all records
        )
        .join(Book, Book.author_id == Author.id)
        .filter(Book.inventory_type == "PRIMARY")
        .group_by(Author.id)
        .order_by(func.sum(Book.volumes).desc())  # Order by total volumes
        .all()
    )

    # Collect author IDs
    author_ids = [row[0] for row in results]

    if not author_ids:
        return []

    # Query 2: Batch fetch sample titles using window function
    subq = (
        db.query(
            Book.author_id,
            Book.title,
            func.row_number().over(partition_by=Book.author_id, order_by=Book.id).label("rn"),
        )
        .filter(
            Book.author_id.in_(author_ids),
            Book.inventory_type == "PRIMARY",
        )
        .subquery()
    )

    sample_titles_rows = db.query(subq.c.author_id, subq.c.title).filter(subq.c.rn <= 5).all()

    # Build lookup dict: author_id -> [titles]
    titles_by_author = defaultdict(list)
    for author_id, title in sample_titles_rows:
        titles_by_author[author_id].append(title)

    # Build response using the lookup
    author_data = []
    for row in results:
        author_id, author_name, record_count, value, volumes = row
        sample_titles = titles_by_author.get(author_id, [])

        author_data.append(
            {
                "author_id": author_id,
                "author": author_name,
                "count": volumes or 0,  # Total individual books (volumes)
                "value": safe_float(value),
                "volumes": volumes or 0,  # Backward compat with frontend
                "total_volumes": volumes or 0,  # New field, same value
                "titles": record_count,  # Number of distinct titles/sets
                "sample_titles": sample_titles,
                "has_more": record_count > 5,
            }
        )

    return author_data


@router.get("/bindings")
def get_bindings(db: Session = Depends(get_db), _user=Depends(require_viewer)):
    """Get authenticated binding counts by binder."""
    results = (
        db.query(
            Binder.id,
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
            "binder_id": row[0],
            "binder": row[1],
            "full_name": row[2],
            "count": row[3],
            "value": safe_float(row[4]),
        }
        for row in results
    ]


@router.get("/by-era")
def get_by_era(db: Session = Depends(get_db), _user=Depends(require_viewer)):
    """Get counts by era (Victorian, Romantic, etc.)."""
    # Use COALESCE to prefer year_start, fall back to year_end
    year_col = func.coalesce(Book.year_start, Book.year_end)

    era_case = case(
        (year_col.is_(None), literal("Unknown")),
        (year_col < 1800, literal("Pre-Romantic (before 1800)")),
        (year_col.between(1800, 1836), literal("Romantic (1800-1836)")),
        (year_col.between(1837, 1901), literal("Victorian (1837-1901)")),
        (year_col.between(1902, 1910), literal("Edwardian (1902-1910)")),
        else_=literal("Post-1910"),
    ).label("era")

    results = (
        db.query(
            era_case,
            func.count(Book.id).label("count"),
            func.sum(Book.value_mid).label("value"),
        )
        .filter(Book.inventory_type == "PRIMARY")
        .group_by(era_case)
        .all()
    )

    return [
        {
            "era": row[0],
            "count": row[1],
            "value": round(safe_float(row[2]), 2),
        }
        for row in results
        if row[1] > 0  # Only return eras with books
    ]


@router.get("/pending-deliveries")
def get_pending_deliveries(db: Session = Depends(get_db), _user=Depends(require_viewer)):
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
def get_acquisitions_by_month(db: Session = Depends(get_db), _user=Depends(require_viewer)):
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
            "value": safe_float(row.value),
            "cost": safe_float(row.cost),
        }
        for row in results
    ]


@router.get("/acquisitions-daily")
def get_acquisitions_daily(
    db: Session = Depends(get_db),
    _user=Depends(require_viewer),
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
        daily_data[d]["value"] += safe_float(book.value_mid)
        daily_data[d]["cost"] += safe_float(book.purchase_price)

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


@router.get("/value-by-category")
def get_value_by_category(db: Session = Depends(get_db), _user=Depends(require_viewer)):
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

    other_value = safe_float(total_value) - safe_float(premium_value) - safe_float(tier1_value)

    return [
        {"category": "Premium Bindings", "value": safe_float(premium_value)},
        {"category": "Tier 1 Publishers", "value": safe_float(tier1_value)},
        {"category": "Other", "value": max(0, other_value)},
    ]


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    _user=Depends(require_viewer),
    reference_date: str = Query(
        default=None,
        description="Reference date in YYYY-MM-DD format (defaults to today UTC)",
    ),
    days: int = Query(default=30, ge=7, le=90, description="Number of days for acquisitions"),
) -> DashboardResponse:
    """Get all dashboard statistics in a single request.

    Combines: overview, bindings, by-era, by-publisher, by-author, by-condition,
    by-category, acquisitions-daily.
    This reduces multiple API calls to 1 for the dashboard.

    Optimized: Uses consolidated queries to reduce DB round trips from ~14 to ~7.
    """
    from app.services.dashboard_stats import get_dashboard_optimized

    return get_dashboard_optimized(db, reference_date, days)
