"""Unified entity fuzzy matching service for publishers, binders, and authors.

This module provides a unified fuzzy matching service that works across all
entity types, preventing entity proliferation by suggesting existing entities
that closely match new input.

Key features:
- Type-specific normalization before matching
- Cached entity lists for performance (5-min TTL, thread-safe)
- Uses rapidfuzz token_sort_ratio for word-order-independent matching
- Returns book counts to help identify canonical entries
"""

import threading
import time
from dataclasses import dataclass
from typing import Literal

from rapidfuzz import fuzz
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.services.author_normalization import normalize_author_name
from app.services.binder_normalization import normalize_binder_name_for_matching
from app.services.publisher_validation import auto_correct_publisher_name

# Type alias for entity types
EntityType = Literal["publisher", "binder", "author"]

# Cache TTL: 5 minutes (matches existing publisher cache)
ENTITY_CACHE_TTL_SECONDS = 300

# Fuzzy matching threshold defaults (0.0 to 1.0)
# These values were chosen based on empirical testing with Victorian-era book data:
#
# - 80% for publishers/binders: Higher threshold because names are more standardized
#   (e.g., "Macmillan" vs "MacMillan" should match at ~95%, but "Penguin" vs "Pelican"
#   at ~60% should not). Publishers and binders tend to have consistent business names.
#
# - 75% for authors: Lower threshold to catch name variations common in historical records
#   (e.g., "Charles Dickens" vs "Dickens, Charles" after normalization, or "Mrs. Gaskell"
#   vs "Elizabeth Gaskell"). Victorian-era author attribution is often inconsistent.
#
# These thresholds are configurable via environment variables in config.py:
#   BMX_ENTITY_MATCH_THRESHOLD_PUBLISHER (default: 0.80)
#   BMX_ENTITY_MATCH_THRESHOLD_BINDER (default: 0.80)
#   BMX_ENTITY_MATCH_THRESHOLD_AUTHOR (default: 0.75)
#
# The actual thresholds used at runtime come from config.get_settings() when
# entity validation endpoints call fuzzy_match_entity(). The function's default
# threshold=0.80 is a conservative fallback for direct calls.
DEFAULT_THRESHOLD_PUBLISHER = 0.80
DEFAULT_THRESHOLD_BINDER = 0.80
DEFAULT_THRESHOLD_AUTHOR = 0.75

# Thread-safe caching for each entity type
# Structure: {entity_type: [(id, name, normalized_name, tier, book_count), ...]}
# Normalized names are pre-computed at cache time to avoid O(n) normalization per query
_entity_caches: dict[str, list[tuple[int, str, str, str | None, int]]] = {}
_entity_cache_times: dict[str, float] = {}
_entity_cache_lock = threading.Lock()


@dataclass
class EntityMatch:
    """Result of fuzzy matching an entity name.

    Attributes:
        entity_id: Database ID of the matched entity.
        name: Display name of the entity.
        tier: Entity tier classification (TIER_1, TIER_2, etc.) or None.
        confidence: Match confidence score from 0.0 to 1.0.
        book_count: Number of books associated with this entity.
    """

    entity_id: int
    name: str
    tier: str | None
    confidence: float
    book_count: int


def _query_entities_from_db(db: Session, entity_type: EntityType) -> list:
    """Query entities from the database.

    This function performs the DB query without holding any locks,
    allowing other threads to proceed while the query executes.

    Args:
        db: Database session.
        entity_type: Type of entity to query.

    Returns:
        List of query result rows with id, name, tier, and book_count.

    Raises:
        ValueError: If entity_type is not a valid type.
    """
    if entity_type == "publisher":
        from app.models.book import Book
        from app.models.publisher import Publisher

        return (
            db.query(
                Publisher.id,
                Publisher.name,
                Publisher.tier,
                func.count(Book.id).label("book_count"),
            )
            .outerjoin(Book, Book.publisher_id == Publisher.id)
            .group_by(Publisher.id, Publisher.name, Publisher.tier)
            .all()
        )

    elif entity_type == "author":
        from app.models.author import Author
        from app.models.book import Book

        return (
            db.query(
                Author.id,
                Author.name,
                Author.tier,
                func.count(Book.id).label("book_count"),
            )
            .outerjoin(Book, Book.author_id == Author.id)
            .group_by(Author.id, Author.name, Author.tier)
            .all()
        )

    elif entity_type == "binder":
        from app.models.binder import Binder
        from app.models.book import Book

        return (
            db.query(
                Binder.id,
                Binder.name,
                Binder.tier,
                func.count(Book.id).label("book_count"),
            )
            .outerjoin(Book, Book.binder_id == Binder.id)
            .group_by(Binder.id, Binder.name, Binder.tier)
            .all()
        )

    else:
        raise ValueError(f"Unknown entity type: {entity_type}")


def _get_cached_entities(
    db: Session, entity_type: EntityType
) -> list[tuple[int, str, str, str | None, int]]:
    """Get entities from cache or DB, with TTL-based expiration.

    Returns list of (id, name, normalized_name, tier, book_count) tuples.
    Normalized names are pre-computed at cache time to avoid O(n) normalization per query.
    Thread-safe with lock protection.

    IMPORTANT: DB queries are performed OUTSIDE the lock to avoid blocking
    other requests. Only cache read/write operations hold the lock.

    Args:
        db: Database session.
        entity_type: Type of entity to cache.

    Returns:
        List of (id, name, normalized_name, tier, book_count) tuples.
    """
    current_time = time.monotonic()

    # Fast path: check cache without lock first
    if (
        entity_type in _entity_caches
        and (current_time - _entity_cache_times.get(entity_type, 0)) < ENTITY_CACHE_TTL_SECONDS
    ):
        return _entity_caches[entity_type]

    # Slow path: need to refresh cache
    # Do DB query OUTSIDE the lock to avoid blocking other requests
    entities = _query_entities_from_db(db, entity_type)

    # Now acquire lock just for cache update
    with _entity_cache_lock:
        # Double-check another thread didn't populate while we queried
        if (
            entity_type in _entity_caches
            and (time.monotonic() - _entity_cache_times.get(entity_type, 0))
            < ENTITY_CACHE_TTL_SECONDS
        ):
            return _entity_caches[entity_type]

        # Convert to tuple list with pre-computed normalized names and cache
        # This avoids O(n) normalization per query
        _entity_caches[entity_type] = [
            (
                e.id,
                e.name,
                _normalize_for_entity_type(e.name, entity_type),
                e.tier,
                e.book_count,
            )
            for e in entities
        ]
        _entity_cache_times[entity_type] = time.monotonic()

        return _entity_caches[entity_type]


def invalidate_entity_cache(entity_type: EntityType) -> None:
    """Invalidate the cache for a specific entity type.

    Call this when entities are created, updated, or deleted.
    For publishers, also invalidates the legacy publisher_validation cache
    to maintain consistency across both caching systems.

    Args:
        entity_type: Type of entity cache to invalidate.
    """
    with _entity_cache_lock:
        if entity_type in _entity_caches:
            del _entity_caches[entity_type]
        if entity_type in _entity_cache_times:
            del _entity_cache_times[entity_type]

    # Also invalidate legacy publisher cache for backwards compatibility
    # TODO(#971): Consolidate publisher caching into single system
    if entity_type == "publisher":
        from app.services.publisher_validation import invalidate_publisher_cache

        invalidate_publisher_cache()


def _normalize_for_entity_type(name: str, entity_type: EntityType) -> str:
    """Apply type-specific normalization to a name.

    Args:
        name: Raw entity name.
        entity_type: Type of entity for normalization rules.

    Returns:
        Normalized name for matching.
    """
    if entity_type == "publisher":
        return auto_correct_publisher_name(name)
    elif entity_type == "author":
        return normalize_author_name(name)
    elif entity_type == "binder":
        return normalize_binder_name_for_matching(name)
    else:
        raise ValueError(f"Unknown entity type: {entity_type}")


def fuzzy_match_entity(
    db: Session,
    entity_type: EntityType,
    name: str,
    threshold: float = DEFAULT_THRESHOLD_PUBLISHER,  # 0.80: conservative default, see config.py for per-type settings
    max_results: int = 5,
) -> list[EntityMatch]:
    """Find existing entities that fuzzy-match the given name.

    Uses cached entity lists to avoid O(n) DB queries per lookup.
    Cache expires after ENTITY_CACHE_TTL_SECONDS.

    The matching process:
    1. Apply type-specific normalization to input name
    2. Query all entities of the type (cached, 5-min TTL)
    3. Score with rapidfuzz token_sort_ratio (word-order independent)
    4. Return matches above threshold, sorted by confidence descending

    Args:
        db: Database session.
        entity_type: Type of entity to match ("publisher", "binder", "author").
        name: Entity name to match.
        threshold: Minimum confidence score (0.0 to 1.0). Default 0.80 (publisher
            threshold). Callers should use config.get_settings() to get the
            appropriate threshold for each entity type. See DEFAULT_THRESHOLD_*
            constants and config.py for environment variable overrides.
        max_results: Maximum number of matches to return. Default 5.

    Returns:
        List of EntityMatch objects, sorted by confidence descending.

    Raises:
        ValueError: If entity_type is not a valid type.
    """
    # Validate entity type
    if entity_type not in ("publisher", "binder", "author"):
        raise ValueError(f"Unknown entity type: {entity_type}")

    # Handle empty input
    if not name or not name.strip():
        return []

    # Apply type-specific normalization before matching
    normalized_name = _normalize_for_entity_type(name, entity_type)

    if not normalized_name:
        return []

    # Get entities from cache (includes pre-computed normalized names)
    cached_entities = _get_cached_entities(db, entity_type)

    matches = []
    for entity_id, entity_name, normalized_entity_name, entity_tier, book_count in cached_entities:
        # Use pre-computed normalized name from cache (avoids O(n) normalization per query)
        # Calculate similarity using token_sort_ratio (word-order independent)
        # rapidfuzz returns 0-100 scale, normalize to 0.0-1.0
        confidence = (
            fuzz.token_sort_ratio(normalized_name.lower(), normalized_entity_name.lower()) / 100.0
        )

        if confidence >= threshold:
            matches.append(
                EntityMatch(
                    entity_id=entity_id,
                    name=entity_name,  # Return original name, not normalized
                    tier=entity_tier,
                    confidence=confidence,
                    book_count=book_count,
                )
            )

    # Sort by confidence descending, take top N
    matches.sort(key=lambda m: m.confidence, reverse=True)
    return matches[:max_results]
