"""Tests for FMV lookup service."""

import urllib.parse
from unittest.mock import MagicMock, patch

from app.services.fmv_lookup import _build_context_aware_query


class TestBuildContextAwareQuery:
    """Tests for _build_context_aware_query function."""

    def test_basic_title_and_author(self):
        """Basic query with just title and author."""
        result = _build_context_aware_query(
            title="Vanity Fair",
            author="Thackeray",
        )
        decoded = urllib.parse.unquote_plus(result).lower()
        assert "vanity fair" in decoded
        assert "thackeray" in decoded

    def test_multi_volume_set(self):
        """Query includes volume count for multi-volume sets."""
        result = _build_context_aware_query(
            title="Life of Scott",
            author="Lockhart",
            volumes=7,
        )
        decoded = urllib.parse.unquote_plus(result).lower()
        assert "7 volumes" in decoded or "7 vol" in decoded

    def test_binding_type_morocco(self):
        """Query includes morocco for morocco bindings."""
        result = _build_context_aware_query(
            title="Essays of Elia",
            author="Lamb",
            binding_type="Full morocco",
        )
        decoded = urllib.parse.unquote_plus(result).lower()
        assert "morocco" in decoded

    def test_binding_type_calf(self):
        """Query includes calf for calf bindings."""
        result = _build_context_aware_query(
            title="Essays of Elia",
            author="Lamb",
            binding_type="Full polished calf",
        )
        decoded = urllib.parse.unquote_plus(result).lower()
        assert "calf" in decoded

    def test_first_edition(self):
        """Query includes first edition when specified."""
        result = _build_context_aware_query(
            title="Origin of Species",
            author="Darwin",
            edition="First Edition",
        )
        decoded = urllib.parse.unquote_plus(result).lower()
        assert "first edition" in decoded

    def test_binder_attribution(self):
        """Query includes binder name when specified."""
        result = _build_context_aware_query(
            title="Essays of Elia",
            author="Lamb",
            binder="Riviere",
        )
        decoded = urllib.parse.unquote_plus(result).lower()
        assert "riviere" in decoded

    def test_full_metadata(self):
        """Query with all metadata fields."""
        result = _build_context_aware_query(
            title="Memoirs of the Life of Sir Walter Scott",
            author="John Gibson Lockhart",
            volumes=7,
            binding_type="Full polished calf",
            binder="J. Leighton",
            edition="First Edition",
        )
        decoded = urllib.parse.unquote_plus(result).lower()
        # Should contain key terms
        assert "scott" in decoded
        assert "lockhart" in decoded
        assert "7 volumes" in decoded or "7 vol" in decoded
        assert "calf" in decoded
        assert "first edition" in decoded


class TestFilterListingsWithClaude:
    """Tests for _filter_listings_with_claude function."""

    @patch("app.services.fmv_lookup.get_bedrock_client")
    @patch("app.services.fmv_lookup.get_model_id")
    def test_filters_by_relevance(self, mock_model_id, mock_client):
        """Claude filters listings and adds relevance scores."""
        from app.services.fmv_lookup import _filter_listings_with_claude

        # Mock Claude response - returns only high/medium relevance
        mock_response = MagicMock()
        mock_response.__getitem__ = lambda self, key: {
            "body": MagicMock(
                read=lambda: b'{"content": [{"text": "[{\\"title\\": \\"7 vol set\\", \\"price\\": 1000, \\"relevance\\": \\"high\\"}]"}]}'
            )
        }[key]
        mock_client.return_value.invoke_model.return_value = mock_response
        mock_model_id.return_value = "anthropic.claude-3-sonnet"

        listings = [
            {"title": "7 vol set", "price": 1000},
            {"title": "single vol", "price": 50},
        ]
        book_metadata = {
            "title": "Life of Scott",
            "author": "Lockhart",
            "volumes": 7,
        }

        result = _filter_listings_with_claude(listings, book_metadata)

        # Should only return high/medium relevance
        assert len(result) == 1
        assert result[0]["relevance"] == "high"

    def test_handles_empty_listings(self):
        """Returns empty list for empty input."""
        from app.services.fmv_lookup import _filter_listings_with_claude

        result = _filter_listings_with_claude([], {"title": "Test"})
        assert result == []

    @patch("app.services.fmv_lookup.get_bedrock_client")
    @patch("app.services.fmv_lookup.get_model_id")
    def test_fallback_on_error(self, mock_model_id, mock_client):
        """Falls back to medium relevance on Claude error."""
        from app.services.fmv_lookup import _filter_listings_with_claude

        mock_client.return_value.invoke_model.side_effect = Exception("API error")
        mock_model_id.return_value = "anthropic.claude-3-sonnet"

        listings = [
            {"title": "Test book", "price": 100},
        ]
        book_metadata = {"title": "Test book"}

        result = _filter_listings_with_claude(listings, book_metadata)

        # Should return listings with medium relevance as fallback
        assert len(result) == 1
        assert result[0]["relevance"] == "medium"
