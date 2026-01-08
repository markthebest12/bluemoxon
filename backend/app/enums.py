"""Centralized enum definitions for the BlueMoxon application.

These enums use StrEnum for automatic string serialization in API responses.
"""

from enum import StrEnum


class BookStatus(StrEnum):
    """Status of a book in the inventory pipeline."""

    EVALUATING = "EVALUATING"
    IN_TRANSIT = "IN_TRANSIT"
    ON_HAND = "ON_HAND"
    REMOVED = "REMOVED"


class InventoryType(StrEnum):
    """Type of inventory classification for a book."""

    PRIMARY = "PRIMARY"
    EXTENDED = "EXTENDED"
    FLAGGED = "FLAGGED"


class Tier(StrEnum):
    """Value tier classification for books."""

    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"


class ConditionGrade(StrEnum):
    """Physical condition grade for books."""

    FINE = "FINE"
    NEAR_FINE = "NEAR_FINE"
    VERY_GOOD = "VERY_GOOD"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"


class SortOrder(StrEnum):
    """Sort order direction for API queries."""

    ASC = "asc"
    DESC = "desc"
