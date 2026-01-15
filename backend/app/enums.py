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


# Statuses representing books physically owned (in collection)
OWNED_STATUSES: tuple[BookStatus, ...] = (BookStatus.IN_TRANSIT, BookStatus.ON_HAND)


class InventoryType(StrEnum):
    """Type of inventory classification for a book."""

    PRIMARY = "PRIMARY"
    EXTENDED = "EXTENDED"
    FLAGGED = "FLAGGED"


class Tier(StrEnum):
    """Value tier classification for books."""

    TIER_1 = "Tier 1"
    TIER_2 = "Tier 2"
    TIER_3 = "Tier 3"


class ConditionGrade(StrEnum):
    """Physical condition grade for books."""

    FINE = "FINE"
    VERY_GOOD = "VERY_GOOD"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"


class SortOrder(StrEnum):
    """Sort order direction for API queries."""

    ASC = "asc"
    DESC = "desc"


class Era(StrEnum):
    """Historical era classification for books based on publication year.

    Era boundaries are based on British literary/historical periods:
    - Pre-Romantic: Before 1800
    - Romantic: 1800-1836 (Wordsworth, Coleridge, Shelley, Keats, Byron)
    - Victorian: 1837-1901 (Queen Victoria's reign)
    - Edwardian: 1902-1910 (Edward VII's reign)
    - Post-1910: After 1910
    """

    PRE_ROMANTIC = "Pre-Romantic"
    ROMANTIC = "Romantic"
    VICTORIAN = "Victorian"
    EDWARDIAN = "Edwardian"
    POST_1910 = "Post-1910"
    UNKNOWN = "Unknown"
