"""Publisher validation service for normalizing and matching publisher names."""

import re
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rapidfuzz import fuzz
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.publisher_alias import PublisherAlias

if TYPE_CHECKING:
    from app.models.publisher import Publisher


# Publisher cache for fuzzy matching - avoids O(n) DB queries per lookup
# Cache is thread-safe and expires after 5 minutes
_publisher_cache: list[tuple[int, str, str | None]] | None = None
_publisher_cache_time: float = 0.0
_publisher_cache_lock = threading.Lock()
PUBLISHER_CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_cached_publishers(db: Session) -> list[tuple[int, str, str | None]]:
    """Get publishers from cache or DB, with TTL-based expiration.

    Returns list of (id, name, tier) tuples for fuzzy matching.
    Thread-safe with lock protection.
    """
    global _publisher_cache, _publisher_cache_time

    current_time = time.monotonic()

    # Check if cache is valid (double-checked locking pattern)
    if (
        _publisher_cache is not None
        and (current_time - _publisher_cache_time) < PUBLISHER_CACHE_TTL_SECONDS
    ):
        return _publisher_cache

    with _publisher_cache_lock:
        # Re-check inside lock (another thread may have refreshed)
        if (
            _publisher_cache is not None
            and (current_time - _publisher_cache_time) < PUBLISHER_CACHE_TTL_SECONDS
        ):
            return _publisher_cache

        from app.models.publisher import Publisher

        # Query only the fields needed for fuzzy matching (more efficient)
        publishers = db.query(Publisher.id, Publisher.name, Publisher.tier).all()
        _publisher_cache = [(p.id, p.name, p.tier) for p in publishers]
        _publisher_cache_time = time.monotonic()

        return _publisher_cache


def invalidate_publisher_cache() -> None:
    """Invalidate the publisher cache.

    Call this when publishers are created, updated, or deleted.
    """
    global _publisher_cache, _publisher_cache_time

    with _publisher_cache_lock:
        _publisher_cache = None
        _publisher_cache_time = 0.0


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


def normalize_publisher_name(db: Session, name: str) -> tuple[str, str | None]:
    """Normalize publisher name and determine tier from database.

    Applies auto-correction rules first, then looks up alias in database.

    Args:
        db: Database session
        name: Raw publisher name from analysis

    Returns:
        Tuple of (canonical_name, tier) where tier is TIER_1, TIER_2, or None
    """
    # Apply auto-correction first
    corrected = auto_correct_publisher_name(name)

    # Look up alias in database (case-insensitive) with eager loading
    alias = (
        db.query(PublisherAlias)
        .options(joinedload(PublisherAlias.publisher))
        .filter(func.lower(PublisherAlias.alias_name) == corrected.lower())
        .first()
    )

    if alias:
        return alias.publisher.name, alias.publisher.tier

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

    Uses cached publisher list to avoid O(n) DB queries per lookup.
    Cache expires after PUBLISHER_CACHE_TTL_SECONDS.

    Args:
        db: Database session
        name: Publisher name to match
        threshold: Minimum confidence score (0.0 to 1.0)
        max_results: Maximum number of matches to return

    Returns:
        List of PublisherMatch objects, sorted by confidence descending
    """
    # Apply auto-correction before matching
    corrected_name = auto_correct_publisher_name(name)

    # Get publishers from cache (avoids repeated DB queries)
    cached_publishers = _get_cached_publishers(db)

    matches = []
    for pub_id, pub_name, pub_tier in cached_publishers:
        # Calculate similarity ratio (0-100 scale from rapidfuzz)
        ratio = fuzz.ratio(corrected_name.lower(), pub_name.lower()) / 100.0

        # Also try token sort ratio for word order independence
        token_ratio = fuzz.token_sort_ratio(corrected_name.lower(), pub_name.lower()) / 100.0

        # Use the higher of the two scores
        confidence = max(ratio, token_ratio)

        if confidence >= threshold:
            matches.append(
                PublisherMatch(
                    publisher_id=pub_id,
                    name=pub_name,
                    tier=pub_tier,
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
    canonical_name, tier = normalize_publisher_name(db, name)

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
        # New publisher created - invalidate cache so next lookup includes it
        invalidate_publisher_cache()
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
