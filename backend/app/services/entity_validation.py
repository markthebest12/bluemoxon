"""Entity validation service for preventing duplicate creation."""

import logging
from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas.entity_validation import EntitySuggestion, EntityValidationError
from app.services.entity_matching import EntityType, fuzzy_match_entity

logger = logging.getLogger(__name__)


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
