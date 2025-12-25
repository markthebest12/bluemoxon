"""Publisher validation service for normalizing and matching publisher names."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rapidfuzz import fuzz
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models.publisher import Publisher

# Location suffixes to remove (case-insensitive)
LOCATION_SUFFIXES = [
    r",?\s+New York\s*$",
    r",?\s+London\s*$",
    r",?\s+Philadelphia\s*$",
    r",?\s+Boston\s*$",
    r",?\s+Chicago\s*$",
    r",?\s+Edinburgh\s*$",
    r",?\s+Leipzig\s*$",
    r",?\s+Wien\s*$",
    r",?\s+Fleet-Street\s*$",
    r",?\s+St\.?\s*Paul\s*$",
    r",?\s+Keene\s+NH\s*$",
    r",?\s+San Francisco\s*$",
]

# Known abbreviation expansions
ABBREVIATION_EXPANSIONS = {
    "D. Bogue": "David Bogue",
    "Wm.": "William",
    "Chas.": "Charles",
    "Thos.": "Thomas",
    "Jas.": "James",
    "Jno.": "John",
}

# Dual publisher patterns - which to keep
# Format: (pattern, replacement) - replacement can reference groups
DUAL_PUBLISHER_RULES = [
    # Keep Oxford University Press over Henry Frowde
    (r"Henry Frowde\s*/\s*Oxford University Press", "Oxford University Press"),
    # Keep Humphrey Milford variant -> Oxford University Press
    (r"Oxford University Press\s*/\s*Humphrey Milford", "Oxford University Press"),
    # Default: keep first publisher before slash
    (r"^([^/]+?)\s*/\s*.+$", r"\1"),
]


def auto_correct_publisher_name(name: str) -> str:
    """Apply auto-correction rules to normalize a publisher name.

    Rules applied (in order):
    1. Strip whitespace
    2. Remove parenthetical content (edition info, series names)
    3. Handle dual publishers (keep primary)
    4. Remove location suffixes
    5. Expand known abbreviations
    6. Normalize punctuation (& Co -> & Co.)

    Args:
        name: Raw publisher name

    Returns:
        Normalized publisher name
    """
    if not name:
        return name

    # Strip whitespace
    result = name.strip()

    # Remove parenthetical content
    result = re.sub(r"\s*\([^)]+\)\s*", " ", result).strip()

    # Handle dual publishers
    for pattern, replacement in DUAL_PUBLISHER_RULES:
        result = re.sub(pattern, replacement, result).strip()

    # Remove location suffixes
    for suffix_pattern in LOCATION_SUFFIXES:
        result = re.sub(suffix_pattern, "", result, flags=re.IGNORECASE).strip()

    # Expand known abbreviations
    for abbrev, expansion in ABBREVIATION_EXPANSIONS.items():
        if result == abbrev or result.startswith(abbrev + " "):
            result = result.replace(abbrev, expansion, 1)

    # Normalize "& Co" to "& Co."
    result = re.sub(r"&\s*Co(?!\.)(\s|$)", r"& Co.\1", result)

    # Final whitespace cleanup
    result = " ".join(result.split())

    return result


# Publisher tier mappings based on market recognition and historical significance
# Maps variant names to (canonical_name, tier)
TIER_1_PUBLISHERS = {
    # Major Victorian/Edwardian publishers
    "Macmillan and Co.": "Macmillan and Co.",
    "Macmillan": "Macmillan and Co.",
    "Chapman & Hall": "Chapman & Hall",
    "Chapman and Hall": "Chapman & Hall",
    "Smith, Elder & Co.": "Smith, Elder & Co.",
    "Smith Elder": "Smith, Elder & Co.",
    "John Murray": "John Murray",
    "Murray": "John Murray",
    "William Blackwood and Sons": "William Blackwood and Sons",
    "Blackwood": "William Blackwood and Sons",
    "Edward Moxon and Co.": "Edward Moxon and Co.",
    "Moxon": "Edward Moxon and Co.",
    "Oxford University Press": "Oxford University Press",
    "OUP": "Oxford University Press",
    "Clarendon Press": "Clarendon Press",
    "Longmans, Green & Co.": "Longmans, Green & Co.",
    "Longmans": "Longmans, Green & Co.",
    "Longman": "Longmans, Green & Co.",
    "Harper & Brothers": "Harper & Brothers",
    "Harper": "Harper & Brothers",
    "D. Appleton and Company": "D. Appleton and Company",
    "Appleton": "D. Appleton and Company",
    "Little, Brown, and Company": "Little, Brown, and Company",
    "Little Brown": "Little, Brown, and Company",
    "Richard Bentley": "Richard Bentley",
    "Bentley": "Richard Bentley",
}

TIER_2_PUBLISHERS = {
    "Chatto and Windus": "Chatto and Windus",
    "Chatto & Windus": "Chatto and Windus",
    "George Allen": "George Allen",
    "Cassell": "Cassell, Petter & Galpin",
    "Cassell, Petter & Galpin": "Cassell, Petter & Galpin",
    "Routledge": "Routledge",
    "Ward, Lock & Co.": "Ward, Lock & Co.",
    "Ward Lock": "Ward, Lock & Co.",
    "Hurst & Company": "Hurst & Company",
    "Grosset & Dunlap": "Grosset & Dunlap",
}


def normalize_publisher_name(name: str) -> tuple[str, str | None]:
    """Normalize publisher name and determine tier.

    Applies auto-correction rules first, then matches against known publishers.

    Args:
        name: Raw publisher name from analysis

    Returns:
        Tuple of (canonical_name, tier) where tier is TIER_1, TIER_2, or None
    """
    # Apply auto-correction first
    corrected = auto_correct_publisher_name(name)

    # Check Tier 1 first (exact match only, case-insensitive)
    for variant, canonical in TIER_1_PUBLISHERS.items():
        if variant.lower() == corrected.lower():
            return canonical, "TIER_1"

    # Check Tier 2 (exact match only, case-insensitive)
    for variant, canonical in TIER_2_PUBLISHERS.items():
        if variant.lower() == corrected.lower():
            return canonical, "TIER_2"

    # Unknown publisher - return corrected name with no tier
    return corrected, None


@dataclass
class PublisherMatch:
    """Result of fuzzy matching a publisher name."""

    publisher_id: int
    name: str
    tier: str | None
    confidence: float  # 0.0 to 1.0


def fuzzy_match_publisher(
    db: Session,
    name: str,
    threshold: float = 0.6,
    max_results: int = 3,
) -> list[PublisherMatch]:
    """Find existing publishers that fuzzy-match the given name.

    Args:
        db: Database session
        name: Publisher name to match
        threshold: Minimum confidence score (0.0 to 1.0)
        max_results: Maximum number of matches to return

    Returns:
        List of PublisherMatch objects, sorted by confidence descending
    """
    from app.models.publisher import Publisher

    # Apply auto-correction before matching
    corrected_name = auto_correct_publisher_name(name)

    # Get all publishers
    publishers = db.query(Publisher).all()

    matches = []
    for pub in publishers:
        # Calculate similarity ratio (0-100 scale from rapidfuzz)
        ratio = fuzz.ratio(corrected_name.lower(), pub.name.lower()) / 100.0

        # Also try token sort ratio for word order independence
        token_ratio = fuzz.token_sort_ratio(corrected_name.lower(), pub.name.lower()) / 100.0

        # Use the higher of the two scores
        confidence = max(ratio, token_ratio)

        if confidence >= threshold:
            matches.append(
                PublisherMatch(
                    publisher_id=pub.id,
                    name=pub.name,
                    tier=pub.tier,
                    confidence=confidence,
                )
            )

    # Sort by confidence descending, take top N
    matches.sort(key=lambda m: m.confidence, reverse=True)
    return matches[:max_results]


def get_or_create_publisher(
    db: Session,
    name: str | None,
    high_confidence_threshold: float = 0.90,
) -> "Publisher | None":
    """Look up or create a publisher from a name string.

    Applies auto-correction, checks for existing matches via fuzzy matching,
    and creates new publisher if no good match found.

    Args:
        db: Database session
        name: Raw publisher name
        high_confidence_threshold: Confidence above which to auto-accept match

    Returns:
        Publisher instance or None if name is empty
    """
    from app.models.publisher import Publisher

    if not name or not name.strip():
        return None

    # Normalize name and get suggested tier
    canonical_name, tier = normalize_publisher_name(name)

    # Try exact match first
    publisher = db.query(Publisher).filter(Publisher.name == canonical_name).first()

    if publisher:
        # Update tier if we have new information and current tier is null
        if tier and not publisher.tier:
            publisher.tier = tier
        return publisher

    # Try fuzzy match
    matches = fuzzy_match_publisher(db, canonical_name, threshold=high_confidence_threshold)
    if matches and matches[0].confidence >= high_confidence_threshold:
        # High confidence match - use existing
        publisher = db.query(Publisher).filter(Publisher.id == matches[0].publisher_id).first()
        if publisher and tier and not publisher.tier:
            publisher.tier = tier
        return publisher

    # No good match - create new publisher
    # Use savepoint to handle race condition without affecting caller's transaction
    publisher = Publisher(
        name=canonical_name,
        tier=tier,
    )

    try:
        with db.begin_nested():  # Savepoint - only rolls back this block on error
            db.add(publisher)
            db.flush()
    except IntegrityError as e:
        # Only handle unique constraint violation on name column
        # Re-raise if it's a different constraint (tier enum, future columns, etc.)
        error_str = str(e.orig) if e.orig else str(e)
        if "publishers_name_key" not in error_str and "UNIQUE constraint" not in error_str:
            raise

        # Another request created this publisher - fetch the existing one
        # Savepoint was rolled back, but parent transaction is intact
        publisher = db.query(Publisher).filter(Publisher.name == canonical_name).first()
        if publisher is None:
            # Should not happen, but guard against it
            raise RuntimeError(
                f"Race condition in publisher creation for '{canonical_name}' "
                "but could not find existing record"
            ) from e

    return publisher
