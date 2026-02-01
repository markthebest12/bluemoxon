"""Tests for connection list capping in AI prompt generation."""

from app.services.entity_profile import _MAX_PROMPT_CONNECTIONS


def test_max_prompt_connections_is_15():
    """Cap should be 15 to balance prompt quality vs token cost."""
    assert _MAX_PROMPT_CONNECTIONS == 15
