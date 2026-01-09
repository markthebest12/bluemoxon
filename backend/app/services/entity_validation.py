"""Entity validation service for preventing duplicate creation."""

import logging

from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas.entity_validation import EntitySuggestion, EntityValidationError
from app.services.entity_matching import (
    EntityType,
    _get_cached_entities,
    _normalize_for_entity_type,
    fuzzy_match_entity,
)

logger = logging.getLogger(__name__)


def _get_entity_by_normalized_name(
    db: Session, entity_type: EntityType, normalized_name: str
) -> tuple[int, str] | None:
    """Find entity by exact normalized name match (case-insensitive).

    Uses the entity cache which stores pre-computed normalized names, ensuring
    consistent normalization between input and stored values. This is important
    because normalization may do more than case-folding (e.g., stripping
    parentheticals, location suffixes, diacritics).

    Args:
        db: Database session.
        entity_type: Type of entity.
        normalized_name: Pre-normalized entity name.

    Returns:
        Tuple of (entity_id, entity_name) if found, None otherwise.
    """
    # Use the cached entities which have pre-computed normalized names
    # Cache format: (id, name, normalized_name, tier, book_count)
    cached_entities = _get_cached_entities(db, entity_type)
    normalized_lower = normalized_name.lower()

    for entity_id, name, cached_normalized, _tier, _book_count in cached_entities:
        if cached_normalized.lower() == normalized_lower:
            return (entity_id, name)

    return None


def validate_entity_creation(
    db: Session,
    entity_type: EntityType,
    name: str,
    threshold: float | None = None,
) -> EntityValidationError | None:
    """Validate that creating an entity won't create a duplicate.

    Args:
        db: Database session.
        entity_type: Type of entity ("publisher", "binder", "author").
        name: Name of entity to create.
        threshold: Fuzzy match threshold. If None, uses config value for entity type.

    Returns:
        EntityValidationError if similar entity exists and mode is "enforce".
        None if creation is safe or mode is "log".
    """
    settings = get_settings()

    # Get threshold from config if not provided
    if threshold is None:
        threshold_attr = f"entity_match_threshold_{entity_type}"
        threshold = getattr(settings, threshold_attr, 0.80)

    matches = fuzzy_match_entity(db, entity_type, name, threshold=threshold)

    if not matches:
        return None

    suggestions = [
        EntitySuggestion(
            id=m.entity_id,
            name=m.name,
            tier=m.tier,
            match=m.confidence,
            book_count=m.book_count,
        )
        for m in matches
    ]

    # In log mode, log warning but allow creation
    if settings.entity_validation_mode == "log":
        top_match = matches[0]
        logger.warning(
            "Entity validation would reject: %s '%s' matches '%s' at %.0f%% (book_count: %d)",
            entity_type,
            name,
            top_match.name,
            top_match.confidence * 100,
            top_match.book_count,
        )
        return None

    return EntityValidationError(
        error="similar_entity_exists",
        entity_type=entity_type,
        input=name,
        suggestions=suggestions,
        resolution=f"Use existing {entity_type} ID, or add force=true to create anyway",
    )


def validate_entity_for_book(
    db: Session,
    entity_type: EntityType,
    name: str | None,
    threshold: float | None = None,
) -> int | EntityValidationError | None:
    """Validate entity name before associating with a book.

    Unlike validate_entity_creation(), this function is for book endpoints
    and returns the entity ID on exact match (allowing direct association).

    Args:
        db: Database session.
        entity_type: Type of entity ("publisher", "binder", "author").
        name: Name of entity to validate.
        threshold: Fuzzy match threshold. If None, uses config value for entity type.

    Returns:
        int: Entity ID if exact match found (safe to associate).
        EntityValidationError: If similar match (409) or unknown (400).
        None: If name is empty/None (skip validation).
    """
    # Handle empty/None input - skip validation
    if not name or not name.strip():
        return None

    settings = get_settings()

    # Normalize input name using type-specific normalization
    normalized_name = _normalize_for_entity_type(name, entity_type)

    # First try exact match by normalized name (no fuzzy matching ambiguity)
    exact_match = _get_entity_by_normalized_name(db, entity_type, normalized_name)
    if exact_match:
        entity_id, _ = exact_match
        return entity_id

    # No exact match - use fuzzy matching to find similar entities
    if threshold is None:
        threshold_attr = f"entity_match_threshold_{entity_type}"
        threshold = getattr(settings, threshold_attr, 0.80)

    matches = fuzzy_match_entity(db, entity_type, name, threshold=threshold)

    # No matches at all - entity not found
    if not matches:
        if settings.entity_validation_mode == "log":
            logger.warning(
                "Entity validation: %s '%s' not found in database",
                entity_type,
                name,
            )
            return None

        return EntityValidationError(
            error="unknown_entity",
            entity_type=entity_type,
            input=name,
            suggestions=None,
            resolution=f"Create the {entity_type} first, or use an existing {entity_type} name",
        )

    # Fuzzy matches found - similar entity exists
    top_match = matches[0]
    suggestions = [
        EntitySuggestion(
            id=m.entity_id,
            name=m.name,
            tier=m.tier,
            match=m.confidence,
            book_count=m.book_count,
        )
        for m in matches
    ]

    # In log mode, log warning but return None (don't silently associate with different entity)
    # Returning the fuzzy match would silently "correct" the name, which is potentially data corruption
    if settings.entity_validation_mode == "log":
        logger.warning(
            "Entity validation would reject: %s '%s' fuzzy matches '%s' at %.0f%% (book_count: %d) - "
            "skipping association (use exact name or create entity first)",
            entity_type,
            name,
            top_match.name,
            top_match.confidence * 100,
            top_match.book_count,
        )
        return None

    return EntityValidationError(
        error="similar_entity_exists",
        entity_type=entity_type,
        input=name,
        suggestions=suggestions,
        resolution=f"Use existing {entity_type} '{top_match.name}' (ID: {top_match.entity_id}), or create a new {entity_type} first",
    )
