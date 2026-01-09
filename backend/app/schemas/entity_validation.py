"""Schemas for entity validation error responses.

These schemas are used when entity name validation fails during book
creation/update or entity creation operations. They provide structured
error responses with suggestions for resolving entity conflicts.

HTTP status mapping:
- similar_entity_exists -> 409 Conflict
- unknown_entity -> 400 Bad Request
- entity_not_found -> 404 Not Found
"""

from typing import Literal

from pydantic import BaseModel


class EntitySuggestion(BaseModel):
    """A suggested entity match for resolving validation errors.

    Attributes:
        id: Database ID of the suggested entity.
        name: Display name of the entity.
        tier: Entity tier classification (A, B, C, etc.) or None if unclassified.
        match: Confidence score from 0.0 to 1.0 indicating match quality.
        book_count: Number of books associated with this entity (helps identify
            canonical entries - higher counts suggest more established entities).
    """

    id: int
    name: str
    tier: str | None
    match: float
    book_count: int


class EntityValidationError(BaseModel):
    """Structured error response for entity validation failures.

    This schema provides detailed information about why entity validation
    failed and how to resolve it. It's returned in error responses when
    creating or updating books with entity references.

    Attributes:
        error: The type of validation error that occurred.
            - similar_entity_exists: Input matches an existing entity closely.
            - unknown_entity: Entity name not found in database.
            - entity_not_found: Entity ID does not exist.
        entity_type: The type of entity that failed validation.
        input: The original input that caused the validation failure.
        suggestions: List of similar entities the user might have meant,
            or None if no suggestions are available.
        resolution: Human-readable instructions for resolving the error.
    """

    error: Literal["similar_entity_exists", "unknown_entity", "entity_not_found"]
    entity_type: Literal["publisher", "binder", "author"]
    input: str
    suggestions: list[EntitySuggestion] | None
    resolution: str
