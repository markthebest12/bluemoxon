"""Shared parser for AI-discovered connections.

Both social_circles.py and entity_profile.py iterate over
``profile.ai_connections`` JSON with near-identical field extraction,
validation, canonical ordering, and confidence-to-strength mapping.
This module centralises that logic so both consumers stay in sync.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.schemas.social_circles import ConnectionType

logger = logging.getLogger(__name__)

# AI-discovered relationship types — exclude the book-derived ones
# (publisher, shared_publisher, binder) which are computed from library data.
_BOOK_DERIVED_TYPES = frozenset({"publisher", "shared_publisher", "binder"})
_VALID_RELATIONSHIPS: frozenset[str] = frozenset(
    ct.value for ct in ConnectionType if ct.value not in _BOOK_DERIVED_TYPES
)


@dataclass(frozen=True, slots=True)
class ParsedAIConnection:
    """Immutable result of parsing a single AI connection dict."""

    source_node_id: str
    target_node_id: str
    relationship: str
    sub_type: str | None
    strength: int
    confidence: float
    evidence: str | None
    edge_id: str


def parse_ai_connection(raw: dict) -> ParsedAIConnection | None:
    """Parse and validate a single AI connection dict.

    Returns a ``ParsedAIConnection`` if the dict is valid, or ``None``
    if required fields are missing or the relationship type is invalid.
    Node IDs are canonically ordered (lower string first) so that the
    same pair always produces the same edge_id regardless of which
    entity profile stores the connection.
    """
    source_type = raw.get("source_type")
    source_id = raw.get("source_id")
    target_type = raw.get("target_type")
    target_id = raw.get("target_id")
    relationship = raw.get("relationship")

    # All five fields are required (explicit None checks to avoid
    # rejecting falsy-but-valid values like id=0).
    if (
        source_type is None
        or source_id is None
        or target_type is None
        or target_id is None
        or relationship is None
    ):
        logger.warning(
            "Skipping AI connection with missing fields, keys=%s",
            list(raw.keys()),
        )
        return None

    # Validate relationship is an AI-discovered type
    if relationship not in _VALID_RELATIONSHIPS:
        logger.warning("Skipping AI connection with invalid type: %s", relationship)
        return None

    source_node_id = f"{source_type}:{source_id}"
    target_node_id = f"{target_type}:{target_id}"

    # Canonical ordering: lower node ID first (by string comparison)
    if source_node_id > target_node_id:
        source_node_id, target_node_id = target_node_id, source_node_id

    edge_id = f"e:{source_node_id}:{target_node_id}:{relationship}"

    # Map confidence (0-1 float) to strength (2-10 int)
    confidence: float = raw.get("confidence", 0.5)
    strength = max(2, min(int(confidence * 10), 10))

    return ParsedAIConnection(
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        relationship=relationship,
        sub_type=raw.get("sub_type"),
        strength=strength,
        confidence=confidence,
        evidence=raw.get("evidence"),
        edge_id=edge_id,
    )
