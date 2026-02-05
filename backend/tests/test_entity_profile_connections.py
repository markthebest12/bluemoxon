"""Tests for connection list capping in AI prompt generation."""

from unittest.mock import MagicMock, patch

from app.models.author import Author
from app.models.user import User
from app.services.ai_profile_generator import GeneratorConfig
from app.services.entity_profile import (
    _MAX_PROMPT_CONNECTIONS,
    generate_and_cache_profile,
)


def test_max_prompt_connections_is_15():
    """Cap should be 15 to balance prompt quality vs token cost."""
    assert _MAX_PROMPT_CONNECTIONS == 15


def _make_graph_node(
    node_id,
    entity_id,
    name,
    node_type="author",
    era=None,
    birth_year=None,
    death_year=None,
    founded_year=None,
    closed_year=None,
    tier=None,
    book_count=0,
    book_ids=None,
):
    """Create a mock SocialCircleNode."""
    node = MagicMock()
    node.id = node_id
    node.entity_id = entity_id
    node.name = name
    node.type = MagicMock()
    node.type.value = node_type
    node.era = MagicMock() if era else None
    if era:
        node.era.value = era
    node.birth_year = birth_year
    node.death_year = death_year
    node.founded_year = founded_year
    node.closed_year = closed_year
    node.tier = tier
    node.book_count = book_count
    node.book_ids = book_ids or []
    return node


def _make_graph_edge(
    source, target, edge_type="author_publisher", strength=5, shared_book_ids=None
):
    """Create a mock SocialCircleEdge."""
    edge = MagicMock()
    edge.id = f"e:{source}:{target}"
    edge.source = source
    edge.target = target
    edge.type = MagicMock()
    edge.type.value = edge_type
    edge.strength = strength
    edge.shared_book_ids = shared_book_ids
    return edge


class TestConnectionCapBehavior:
    """Behavioral tests for connection cap in generate_and_cache_profile (#1654)."""

    @patch("app.services.entity_profile.strip_invalid_markers", side_effect=lambda t, _ids: t)
    @patch(
        "app.services.entity_profile.GeneratorConfig.resolve",
        return_value=GeneratorConfig(model_id="claude-3-haiku"),
    )
    @patch("app.services.entity_profile.generate_connection_narrative")
    @patch("app.services.entity_profile.generate_relationship_story")
    @patch("app.services.entity_profile.classify_connection", return_value=None)
    @patch("app.services.entity_profile.generate_bio_and_stories")
    @patch("app.services.entity_profile.get_or_build_graph")
    def test_connections_capped_sorted_and_valid_ids_complete(
        self,
        mock_graph,
        mock_bio,
        mock_classify,
        mock_story,
        mock_narrative,
        _mock_model,
        mock_strip,
        db,
    ):
        """generate_and_cache_profile caps prompt connections at 15, keeps
        them in descending strength order, and passes ALL entity IDs to
        strip_invalid_markers for cross-link validation.
        """
        # -- arrange --
        user = User(cognito_sub="test-cap", email="cap@example.com", role="editor")
        db.add(user)
        db.flush()
        author = Author(name="Cap Author", birth_year=1800, death_year=1880)
        db.add(author)
        db.flush()
        db.commit()

        total_connections = 20
        source = _make_graph_node(
            f"author:{author.id}", author.id, "Cap Author", birth_year=1800, death_year=1880
        )
        targets = [
            _make_graph_node(f"publisher:{i}", i, f"Publisher {i}", node_type="publisher")
            for i in range(1, total_connections + 1)
        ]
        # Each edge has a unique strength from 1..20 so ordering is deterministic
        edges = [
            _make_graph_edge(
                f"author:{author.id}",
                f"publisher:{i}",
                strength=i,
            )
            for i in range(1, total_connections + 1)
        ]

        graph = MagicMock()
        graph.nodes = [source] + targets
        graph.edges = edges
        mock_graph.return_value = graph

        mock_bio.return_value = {"biography": "A biography.", "personal_stories": []}

        # -- act --
        generate_and_cache_profile(db, "author", author.id, user.id)

        # -- assert: connections kwarg capped at 15 --
        bio_call_kwargs = mock_bio.call_args
        prompt_connections = bio_call_kwargs.kwargs["connections"]
        assert len(prompt_connections) == _MAX_PROMPT_CONNECTIONS

        # -- assert: connections are in descending strength order (strongest first) --
        # Edges are sorted by strength descending, so publisher:20 (strength 20) comes first
        expected_names = [
            f"Publisher {i}" for i in range(total_connections, total_connections - 15, -1)
        ]
        actual_names = [c["name"] for c in prompt_connections]
        assert actual_names == expected_names

        # -- assert: valid_entity_ids includes ALL connections (not just 15) --
        # strip_invalid_markers is called at least once (for the biography text)
        assert mock_strip.call_count >= 1
        # Grab the valid_entity_ids arg from the first call
        valid_ids = mock_strip.call_args_list[0].args[1]
        assert len(valid_ids) == total_connections
        for i in range(1, total_connections + 1):
            assert f"publisher:{i}" in valid_ids
