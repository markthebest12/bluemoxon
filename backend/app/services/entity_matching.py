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

# Thread-safe caching for each entity type
# Structure: {entity_type: [(id, name, tier, book_count), ...]}
_entity_caches: dict[str, list[tuple[int, str, str | None, int]]] = {}
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


def _get_cached_entities(
    db: Session, entity_type: EntityType
) -> list[tuple[int, str, str | None, int]]:
    """Get entities from cache or DB, with TTL-based expiration.

    Returns list of (id, name, tier, book_count) tuples for fuzzy matching.
    Thread-safe with lock protection.

    Args:
        db: Database session.
        entity_type: Type of entity to cache.

    Returns:
        List of (id, name, tier, book_count) tuples.
    """
    current_time = time.monotonic()

    # Check if cache is valid (double-checked locking pattern)
    if (
        entity_type in _entity_caches
        and (current_time - _entity_cache_times.get(entity_type, 0)) < ENTITY_CACHE_TTL_SECONDS
    ):
        return _entity_caches[entity_type]

    with _entity_cache_lock:
        # Re-check inside lock (another thread may have refreshed)
        if (
            entity_type in _entity_caches
            and (current_time - _entity_cache_times.get(entity_type, 0)) < ENTITY_CACHE_TTL_SECONDS
        ):
            return _entity_caches[entity_type]

        # Query based on entity type
        if entity_type == "publisher":
            from app.models.book import Book
            from app.models.publisher import Publisher

            # Query publishers with book counts
            entities = (
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

            entities = (
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

            entities = (
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

        # Convert to tuple list and cache
        _entity_caches[entity_type] = [(e.id, e.name, e.tier, e.book_count) for e in entities]
        _entity_cache_times[entity_type] = time.monotonic()

        return _entity_caches[entity_type]


def invalidate_entity_cache(entity_type: EntityType) -> None:
    """Invalidate the cache for a specific entity type.

    Call this when entities are created, updated, or deleted.

    Args:
        entity_type: Type of entity cache to invalidate.
    """
    with _entity_cache_lock:
        if entity_type in _entity_caches:
            del _entity_caches[entity_type]
        if entity_type in _entity_cache_times:
            del _entity_cache_times[entity_type]


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
    threshold: float = 0.80,
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
        threshold: Minimum confidence score (0.0 to 1.0). Default 0.80.
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

    # Get entities from cache
    cached_entities = _get_cached_entities(db, entity_type)

    matches = []
    for entity_id, entity_name, entity_tier, book_count in cached_entities:
        # Normalize the entity name from DB for comparison
        normalized_entity_name = _normalize_for_entity_type(entity_name, entity_type)

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
