"""Entity validation service for preventing duplicate creation.

This module provides entity validation functionality to prevent duplicate
entity creation and to validate entity associations with books.

Key components:
- validate_entity_creation: Validates entity creation to prevent duplicates
- validate_entity_for_book: Validates entity name before associating with a book
- validate_entities: Shared function for validating multiple entities at once
  (extracted from books.py and worker.py for #1014)
- ValidationResult: Result type for single entity validation (internal)
- EntityValidationResult: Result type for validate_entities (also aliased as
  EntityAssociationResult for backward compatibility)
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas.entity_validation import EntitySuggestion, EntityValidationError
from app.services.entity_matching import (
    EntityType,
    _get_cached_entities,
    _normalize_for_entity_type,
    fuzzy_match_entity,
)


@dataclass
class ValidationResult:
    """Result of single entity validation with full context.

    This type preserves the validation context (including skipped fuzzy matches)
    to avoid re-querying in the shared validation function (#1014 fix).

    Attributes:
        entity_id: Matched entity ID, or None if no match.
        error: Validation error if in enforce mode with match/unknown.
        skipped_match: Fuzzy match that was skipped (log mode), for warnings (#1013).
    """

    entity_id: int | None = None
    error: EntityValidationError | None = None
    skipped_match: EntitySuggestion | None = None


@dataclass
class EntityValidationResult:
    """Result of validating multiple entities for book association.

    This is used by validate_entities() to return structured results instead
    of raising exceptions, allowing callers to decide how to handle errors
    (#1015 - inconsistent error types).

    Also provides warnings for log mode visibility (#1013 - log mode silently
    skips associations).

    Attributes:
        binder_id: ID of validated binder, or None if not validated/found.
        publisher_id: ID of validated publisher, or None if not validated/found.
        errors: List of validation errors (similar_entity_exists or unknown_entity).
        warnings: List of warning messages for skipped associations.
    """

    binder_id: int | None = None
    publisher_id: int | None = None
    errors: list[EntityValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Return True if there are any validation errors."""
        return len(self.errors) > 0


# Keep old name for backward compatibility
EntityAssociationResult = EntityValidationResult


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


def _validate_entity_with_context(
    db: Session,
    entity_type: EntityType,
    name: str | None,
    threshold: float | None = None,
    allow_unknown: bool = False,
) -> ValidationResult:
    """Internal validation function that preserves full context.

    Unlike validate_entity_for_book(), this returns a structured result that
    includes information about skipped fuzzy matches, avoiding the need for
    re-querying to generate warnings.

    Args:
        db: Database session.
        entity_type: Type of entity ("publisher", "binder", "author").
        name: Name of entity to validate.
        threshold: Fuzzy match threshold. If None, uses config value for entity type.
        allow_unknown: If True, don't return error for unknown entities.

    Returns:
        ValidationResult with entity_id, error, and/or skipped_match.
    """
    result = ValidationResult()

    # Handle empty/None input - skip validation
    if not name or not name.strip():
        return result

    settings = get_settings()

    # Normalize input name using type-specific normalization
    normalized_name = _normalize_for_entity_type(name, entity_type)

    # First try exact match by normalized name (no fuzzy matching ambiguity)
    exact_match = _get_entity_by_normalized_name(db, entity_type, normalized_name)
    if exact_match:
        entity_id, _ = exact_match
        result.entity_id = entity_id
        return result

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
            return result

        if allow_unknown:
            logger.info(
                "Entity validation: %s '%s' not found, allow_unknown=True - skipping",
                entity_type,
                name,
            )
            return result

        result.error = EntityValidationError(
            error="unknown_entity",
            entity_type=entity_type,
            input=name,
            suggestions=None,
            resolution=f"Create the {entity_type} first, or use an existing {entity_type} name",
        )
        return result

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

    # In log mode, log warning and preserve context for caller
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
        # Store the skipped match so caller can generate warnings without re-querying
        result.skipped_match = EntitySuggestion(
            id=top_match.entity_id,
            name=top_match.name,
            tier=top_match.tier,
            match=top_match.confidence,
            book_count=top_match.book_count,
        )
        return result

    result.error = EntityValidationError(
        error="similar_entity_exists",
        entity_type=entity_type,
        input=name,
        suggestions=suggestions,
        resolution=f"Use existing {entity_type} '{top_match.name}' (ID: {top_match.entity_id}), or create a new {entity_type} first",
    )
    return result


def validate_entity_for_book(
    db: Session,
    entity_type: EntityType,
    name: str | None,
    threshold: float | None = None,
    allow_unknown: bool = False,
) -> int | EntityValidationError | None:
    """Validate entity name before associating with a book.

    Unlike validate_entity_creation(), this function is for book endpoints
    and returns the entity ID on exact match (allowing direct association).

    Args:
        db: Database session.
        entity_type: Type of entity ("publisher", "binder", "author").
        name: Name of entity to validate.
        threshold: Fuzzy match threshold. If None, uses config value for entity type.
        allow_unknown: If True, return None instead of unknown_entity error when
            entity is not found. Useful for analysis workflows that may discover
            new entities not yet in the database.

    Returns:
        int: Entity ID if exact match found (safe to associate).
        EntityValidationError: If similar match (409) or unknown (400, unless allow_unknown).
        None: If name is empty/None (skip validation), or if allow_unknown=True and not found.
    """
    # Use internal function and convert result to legacy return type
    result = _validate_entity_with_context(db, entity_type, name, threshold, allow_unknown)

    if result.entity_id is not None:
        return result.entity_id
    if result.error is not None:
        return result.error
    # skipped_match or no match - return None
    return None


def _format_entity_warning(
    entity_type: str, name: str, skipped_match: EntitySuggestion | None
) -> str:
    """Format consistent warning message for skipped entity association.

    Args:
        entity_type: Type of entity ("binder", "publisher").
        name: Input entity name.
        skipped_match: The fuzzy match that was skipped, or None if unknown entity.

    Returns:
        Formatted warning message.
    """
    if skipped_match:
        return (
            f"{entity_type.title()} '{name}' fuzzy matches '{skipped_match.name}' "
            f"({skipped_match.match:.0%}) - association skipped"
        )
    return f"{entity_type.title()} '{name}' not found in database - association skipped"


def validate_entities(
    db: Session,
    binder_name: str | None = None,
    publisher_name: str | None = None,
) -> EntityValidationResult:
    """Validate multiple entities for book association.

    This function extracts common validation logic from books.py and worker.py
    (#1014 - duplicate validation logic). It validates all entities at once
    and returns a structured result, allowing callers to decide how to handle
    errors (#1015 - inconsistent error types).

    In log mode, warnings are collected for visibility instead of silently
    returning None (#1013 - log mode silently skips associations).

    Note: This function does NOT do the actual association - callers are responsible
    for setting book.binder_id and book.publisher_id from the returned IDs.

    Args:
        db: Database session.
        binder_name: Name of binder to validate, or None to skip.
        publisher_name: Name of publisher to validate, or None to skip.

    Returns:
        EntityValidationResult with entity IDs, errors, and warnings.
    """
    result = EntityValidationResult()

    # Validate binder if name provided
    if binder_name and binder_name.strip():
        binder_result = _validate_entity_with_context(db, "binder", binder_name, allow_unknown=True)

        if binder_result.entity_id is not None:
            result.binder_id = binder_result.entity_id
        elif binder_result.error is not None:
            result.errors.append(binder_result.error)
        elif binder_result.skipped_match is not None or binder_result.entity_id is None:
            # Skipped match (log mode) or unknown entity - generate warning
            result.warnings.append(
                _format_entity_warning("binder", binder_name, binder_result.skipped_match)
            )

    # Validate publisher if name provided
    if publisher_name and publisher_name.strip():
        publisher_result = _validate_entity_with_context(
            db, "publisher", publisher_name, allow_unknown=True
        )

        if publisher_result.entity_id is not None:
            result.publisher_id = publisher_result.entity_id
        elif publisher_result.error is not None:
            result.errors.append(publisher_result.error)
        elif publisher_result.skipped_match is not None or publisher_result.entity_id is None:
            # Skipped match (log mode) or unknown entity - generate warning
            result.warnings.append(
                _format_entity_warning("publisher", publisher_name, publisher_result.skipped_match)
            )

    return result


# Keep old name for backward compatibility
def validate_and_associate_entities(
    db: Session,
    binder_name: str | None = None,
    publisher_name: str | None = None,
) -> EntityValidationResult:
    """Deprecated: Use validate_entities() instead.

    This function is kept for backward compatibility.
    """
    return validate_entities(db, binder_name, publisher_name)
