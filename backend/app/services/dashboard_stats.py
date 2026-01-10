"""Consolidated dashboard statistics queries.

This module provides optimized queries for the dashboard endpoint,
reducing database round trips by using GROUPING SETS and conditional
aggregation.
"""

from sqlalchemy.orm import Session


def get_dimension_stats(db: Session) -> dict:
    """Get condition, category, and era stats in a single query.

    Uses PostgreSQL GROUPING SETS to fetch all three breakdowns
    in one database round trip.

    Returns:
        dict with keys: by_condition, by_category, by_era
    """
    raise NotImplementedError("TODO: implement GROUPING SETS query")


def get_overview_stats(db: Session) -> dict:
    """Get overview statistics in a single query.

    Uses conditional aggregation (FILTER clause) to compute all
    counts and sums in one query.

    Returns:
        dict matching get_overview() response format
    """
    raise NotImplementedError("TODO: implement conditional aggregation")
