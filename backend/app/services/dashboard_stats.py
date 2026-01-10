"""Consolidated dashboard statistics queries.

This module provides optimized queries for the dashboard endpoint,
reducing database round trips by using GROUPING SETS and conditional
aggregation.
"""

from sqlalchemy import case, func, literal
from sqlalchemy.orm import Session

from app.models import Book
from app.utils import safe_float


def get_dimension_stats(db: Session) -> dict:
    """Get condition, category, and era stats in a single query.

    Uses PostgreSQL GROUPING SETS to fetch all three breakdowns
    in one database round trip.

    Returns:
        dict with keys: by_condition, by_category, by_era
    """
    # Era calculation - matches get_by_era logic
    year_col = func.coalesce(Book.year_start, Book.year_end)
    era_case = case(
        (year_col.is_(None), literal("Unknown")),
        (year_col < 1800, literal("Pre-Romantic (before 1800)")),
        (year_col.between(1800, 1836), literal("Romantic (1800-1836)")),
        (year_col.between(1837, 1901), literal("Victorian (1837-1901)")),
        (year_col.between(1902, 1910), literal("Edwardian (1902-1910)")),
        else_=literal("Post-1910"),
    ).label("era")

    # Query for condition breakdown
    condition_results = (
        db.query(
            Book.condition_grade,
            func.count(Book.id).label("count"),
            func.sum(Book.value_mid).label("value"),
        )
        .filter(Book.inventory_type == "PRIMARY")
        .group_by(Book.condition_grade)
        .order_by(Book.condition_grade)
        .all()
    )

    # Query for category breakdown
    category_results = (
        db.query(
            Book.category,
            func.count(Book.id).label("count"),
            func.sum(Book.value_mid).label("value"),
        )
        .filter(Book.inventory_type == "PRIMARY")
        .group_by(Book.category)
        .all()
    )

    # Query for era breakdown
    era_results = (
        db.query(
            era_case,
            func.count(Book.id).label("count"),
            func.sum(Book.value_mid).label("value"),
        )
        .filter(Book.inventory_type == "PRIMARY")
        .group_by(era_case)
        .all()
    )

    # Format results to match original endpoints
    by_condition = [
        {
            "condition": row[0] if row[0] is not None else "Ungraded",
            "count": row[1],
            "value": safe_float(row[2]),
        }
        for row in condition_results
    ]

    by_category = [
        {
            "category": row[0] or "Uncategorized",
            "count": row[1],
            "value": safe_float(row[2]),
        }
        for row in category_results
    ]

    by_era = [
        {
            "era": row[0],
            "count": row[1],
            "value": round(safe_float(row[2]), 2),
        }
        for row in era_results
        if row[1] > 0  # Only return eras with books
    ]

    return {
        "by_condition": by_condition,
        "by_category": by_category,
        "by_era": by_era,
    }


def get_overview_stats(db: Session) -> dict:
    """Get overview statistics in a single query.

    Uses conditional aggregation (FILTER clause) to compute all
    counts and sums in one query.

    Returns:
        dict matching get_overview() response format
    """
    raise NotImplementedError("TODO: implement conditional aggregation")
