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
    """Physical condition grade for books.

    Order (best to worst): FINE > NEAR_FINE > VERY_GOOD > GOOD > FAIR > POOR
    """

    FINE = "FINE"
    NEAR_FINE = "NEAR_FINE"
    VERY_GOOD = "VERY_GOOD"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"

    @classmethod
    def from_alias(cls, value: str | None) -> "ConditionGrade | None":
        """Normalize raw condition grade string to enum value.

        Handles AI-generated condition grades, dealer abbreviations, and
        human-readable variants. Mappings match migration dd7f743834bc.

        Grading follows antiquarian book conventions:
        - FINE: As new, mint, pristine - no defects
        - NEAR_FINE: Almost fine, very minor wear (VG+ upgrades here)
        - VERY_GOOD: Light wear, all parts present (VG)
        - GOOD: Moderate wear, complete and readable (VG-, G+, good+)
        - FAIR: Heavy wear but readable (reading copy)
        - POOR: Significant damage (ex-library)

        Note on "F" ambiguity: ABAA uses "F" for Fine. Some dealers use
        "F" for Fair. We follow ABAA convention (F -> FINE) for consistency
        with migration and industry standard.

        Args:
            value: Raw condition grade string (case-insensitive)

        Returns:
            ConditionGrade enum value, or None if unrecognized
        """
        if value is None or not isinstance(value, str):
            return None

        import re

        normalized = value.strip().lower()
        # Replace underscores and hyphens with spaces, collapse multiple spaces
        normalized = re.sub(r"[-_]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)

        alias_map: dict[str, ConditionGrade] = {
            "as new": cls.FINE,
            "mint": cls.FINE,
            "fine": cls.FINE,
            "f": cls.FINE,
            "near fine": cls.NEAR_FINE,
            "nf": cls.NEAR_FINE,
            "vg+": cls.NEAR_FINE,
            "vg +": cls.NEAR_FINE,
            "very good": cls.VERY_GOOD,
            "vg": cls.VERY_GOOD,
            "vg ": cls.GOOD,
            "vg/g": cls.GOOD,
            "good+": cls.GOOD,
            "good +": cls.GOOD,
            "good": cls.GOOD,
            "good ": cls.GOOD,
            "g": cls.GOOD,
            "fair": cls.FAIR,
            "reading copy": cls.FAIR,
            "poor": cls.POOR,
            "ex library": cls.POOR,
            "ex lib": cls.POOR,
        }

        return alias_map.get(normalized)


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
