"""Entity validation service for preventing duplicate creation."""

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas.entity_validation import EntitySuggestion, EntityValidationError
from app.services.entity_matching import (
    EntityMatch,
    EntityType,
    _get_cached_entities,
    _normalize_for_entity_type,
    fuzzy_match_entity,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating an entity for book association.

    This provides visibility into what happened during validation:
    - entity_id set: Exact match found, safe to associate
    - skipped_match set: Fuzzy match found in log mode, association skipped
    - error set: Validation failed (enforce mode)
    - All None: No entity found or empty input
    """

    entity_id: int | None = None
    skipped_match: EntityMatch | None = None
    error: EntityValidationError | None = None

    @property
    def success(self) -> bool:
        """True if an entity was found and can be associated."""
        return self.entity_id is not None

    @property
    def was_skipped(self) -> bool:
        """True if association was skipped due to fuzzy match in log mode."""
        return self.skipped_match is not None


@dataclass
class EntityAssociationResult:
    """Result of validating and associating entities with a book."""

    binder: ValidationResult
    publisher: ValidationResult

    @property
    def has_errors(self) -> bool:
        """True if either binder or publisher validation returned an error."""
        return self.binder.error is not None or self.publisher.error is not None

    @property
    def has_skipped(self) -> bool:
        """True if either binder or publisher association was skipped."""
        return self.binder.was_skipped or self.publisher.was_skipped


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
) -> ValidationResult:
    """Validate entity name before associating with a book.

    Unlike validate_entity_creation(), this function is for book endpoints
    and returns a ValidationResult with the entity ID on exact match.

    Args:
        db: Database session.
        entity_type: Type of entity ("publisher", "binder", "author").
        name: Name of entity to validate.
        threshold: Fuzzy match threshold. If None, uses config value for entity type.

    Returns:
        ValidationResult with:
        - entity_id: Set if exact match found (safe to associate)
        - error: Set if validation failed (enforce mode)
        - skipped_match: Set if fuzzy match skipped (log mode) - fixes #1013
        - All None: If name is empty/None (skip validation)
    """
    # Handle empty/None input - skip validation
    if not name or not name.strip():
        return ValidationResult()

    settings = get_settings()

    # Normalize input name using type-specific normalization
    normalized_name = _normalize_for_entity_type(name, entity_type)

    # First try exact match by normalized name (no fuzzy matching ambiguity)
    exact_match = _get_entity_by_normalized_name(db, entity_type, normalized_name)
    if exact_match:
        entity_id, _ = exact_match
        return ValidationResult(entity_id=entity_id)

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
            return ValidationResult()

        return ValidationResult(
            error=EntityValidationError(
                error="unknown_entity",
                entity_type=entity_type,
                input=name,
                suggestions=None,
                resolution=f"Create the {entity_type} first, or use an existing {entity_type} name",
            )
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

    # In log mode, log warning and return skipped_match for visibility (#1013 fix)
    # Don't silently associate with different entity - that's potentially data corruption
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
        return ValidationResult(skipped_match=top_match)

    return ValidationResult(
        error=EntityValidationError(
            error="similar_entity_exists",
            entity_type=entity_type,
            input=name,
            suggestions=suggestions,
            resolution=f"Use existing {entity_type} '{top_match.name}' (ID: {top_match.entity_id}), or create a new {entity_type} first",
        )
    )


def validate_and_associate_entities(
    db: Session,
    book,  # Type: app.models.book.Book (avoid circular import)
    parsed,  # Type: app.utils.markdown_parser.ParsedAnalysis
) -> EntityAssociationResult:
    """Validate binder/publisher and associate with book if valid.

    This function consolidates the validation logic that was duplicated
    in books.py and worker.py (#1014 fix).

    Args:
        db: Database session.
        book: Book model instance to update.
        parsed: ParsedAnalysis with binder_identification and publisher_identification.

    Returns:
        EntityAssociationResult with validation results for both entities.
    """
    binder_result = ValidationResult()
    publisher_result = ValidationResult()

    # Validate and associate binder
    if parsed.binder_identification and parsed.binder_identification.get("name"):
        binder_result = validate_entity_for_book(db, "binder", parsed.binder_identification["name"])
        if binder_result.success:
            book.binder_id = binder_result.entity_id

    # Validate and associate publisher
    if parsed.publisher_identification and parsed.publisher_identification.get("name"):
        publisher_result = validate_entity_for_book(
            db, "publisher", parsed.publisher_identification["name"]
        )
        if publisher_result.success:
            book.publisher_id = publisher_result.entity_id

    return EntityAssociationResult(binder=binder_result, publisher=publisher_result)
