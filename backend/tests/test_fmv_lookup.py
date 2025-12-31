"""Tests for FMV lookup service."""

import json
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

    @patch("app.services.fmv_lookup.get_bedrock_client")
    @patch("app.services.fmv_lookup.get_model_id")
    def test_fallback_when_all_low_relevance(self, mock_model_id, mock_client):
        """When Claude rates all listings as 'low', return top 5 as fallback."""
        from app.services.fmv_lookup import _filter_listings_with_claude

        # Mock Claude response - all listings rated "low"
        low_listings = [
            {"title": "Book 1", "price": 500, "relevance": "low"},
            {"title": "Book 2", "price": 450, "relevance": "low"},
            {"title": "Book 3", "price": 400, "relevance": "low"},
            {"title": "Book 4", "price": 350, "relevance": "low"},
            {"title": "Book 5", "price": 300, "relevance": "low"},
            {"title": "Book 6", "price": 250, "relevance": "low"},
        ]
        mock_response = MagicMock()
        mock_response.__getitem__ = lambda self, key: {
            "body": MagicMock(
                read=lambda: json.dumps({"content": [{"text": json.dumps(low_listings)}]}).encode()
            )
        }[key]
        mock_client.return_value.invoke_model.return_value = mock_response
        mock_model_id.return_value = "anthropic.claude-3-sonnet"

        listings = [
            {"title": "Book 1", "price": 500},
            {"title": "Book 2", "price": 450},
            {"title": "Book 3", "price": 400},
            {"title": "Book 4", "price": 350},
            {"title": "Book 5", "price": 300},
            {"title": "Book 6", "price": 250},
        ]
        book_metadata = {
            "title": "Origin of Species",
            "author": "Darwin",
            "publication_year": 1859,
        }

        result = _filter_listings_with_claude(listings, book_metadata)

        # Should return top 5 low-relevance listings as fallback
        assert len(result) == 5
        # All should be marked as "low" relevance with fallback indicator
        for item in result:
            assert item["relevance"] in ("low", "fallback")

    @patch("app.services.fmv_lookup.get_bedrock_client")
    @patch("app.services.fmv_lookup.get_model_id")
    def test_prompt_focuses_on_binding_not_era(self, mock_model_id, mock_client):
        """Claude prompt should focus on binding type match, not strict era matching."""
        from app.services.fmv_lookup import _filter_listings_with_claude

        mock_response = MagicMock()
        mock_response.__getitem__ = lambda self, key: {
            "body": MagicMock(read=lambda: json.dumps({"content": [{"text": "[]"}]}).encode())
        }[key]
        mock_client.return_value.invoke_model.return_value = mock_response
        mock_model_id.return_value = "anthropic.claude-3-sonnet"

        listings = [{"title": "Test", "price": 100}]
        book_metadata = {
            "title": "Origin of Species",
            "author": "Darwin",
            "publication_year": 1859,
            "binding_type": "Full morocco",
        }

        _filter_listings_with_claude(listings, book_metadata)

        # Check the prompt sent to Claude
        call_args = mock_client.return_value.invoke_model.call_args
        body = json.loads(call_args.kwargs["body"])
        prompt = body["messages"][0]["content"]

        # Prompt should NOT contain strict era rejection language
        assert "within ~50 years" not in prompt.lower()
        assert "post-1950 are low" not in prompt.lower()

        # Prompt SHOULD mention binding type matching
        assert "binding" in prompt.lower()


class TestCalculateWeightedFmv:
    """Tests for _calculate_weighted_fmv function."""

    def test_high_relevance_only(self):
        """Uses only high relevance listings when sufficient."""
        from app.services.fmv_lookup import _calculate_weighted_fmv

        listings = [
            {"price": 1000, "relevance": "high"},
            {"price": 1200, "relevance": "high"},
            {"price": 1400, "relevance": "high"},
            {"price": 100, "relevance": "medium"},
            {"price": 50, "relevance": "low"},
        ]

        result = _calculate_weighted_fmv(listings)

        # Should use only high relevance (1000, 1200, 1400)
        assert result["fmv_low"] == 1000
        assert result["fmv_high"] == 1400
        assert result["fmv_confidence"] == "high"

    def test_falls_back_to_medium(self):
        """Falls back to medium when insufficient high."""
        from app.services.fmv_lookup import _calculate_weighted_fmv

        listings = [
            {"price": 1000, "relevance": "high"},
            {"price": 300, "relevance": "medium"},
            {"price": 400, "relevance": "medium"},
            {"price": 500, "relevance": "medium"},
        ]

        result = _calculate_weighted_fmv(listings)

        # Should include medium (only 1 high)
        assert result["fmv_confidence"] == "medium"

    def test_insufficient_data(self):
        """Returns low confidence when insufficient data."""
        from app.services.fmv_lookup import _calculate_weighted_fmv

        listings = [
            {"price": 1000, "relevance": "high"},
        ]

        result = _calculate_weighted_fmv(listings)

        assert result["fmv_confidence"] == "low"
        assert "Insufficient" in result["fmv_notes"]

    def test_empty_listings(self):
        """Handles empty listings gracefully."""
        from app.services.fmv_lookup import _calculate_weighted_fmv

        result = _calculate_weighted_fmv([])

        assert result["fmv_low"] is None
        assert result["fmv_high"] is None
        assert result["fmv_confidence"] == "low"

    def test_handles_fallback_relevance(self):
        """Treats 'fallback' relevance as low confidence but usable."""
        from app.services.fmv_lookup import _calculate_weighted_fmv

        listings = [
            {"price": 500, "relevance": "fallback"},
            {"price": 400, "relevance": "fallback"},
            {"price": 300, "relevance": "fallback"},
        ]

        result = _calculate_weighted_fmv(listings)

        # Should use fallback listings with low confidence
        assert result["fmv_low"] == 300
        assert result["fmv_high"] == 500
        assert result["fmv_confidence"] == "low"
        assert (
            "fallback" in result["fmv_notes"].lower()
            or "insufficient" in result["fmv_notes"].lower()
        )


class TestExtractComparablesPrompt:
    """Tests for _extract_comparables_with_claude prompt variations."""

    @patch("app.services.fmv_lookup.get_bedrock_client")
    @patch("app.services.fmv_lookup.get_model_id")
    def test_ebay_prompt_says_sold_listings(self, mock_model_id, mock_client):
        """eBay extraction prompt asks for sold listings."""
        from app.services.fmv_lookup import _extract_comparables_with_claude

        mock_response = MagicMock()
        mock_response.__getitem__ = lambda self, key: {
            "body": MagicMock(read=lambda: b'{"content": [{"text": "[]"}]}')
        }[key]
        mock_client.return_value.invoke_model.return_value = mock_response
        mock_model_id.return_value = "anthropic.claude-3-sonnet"

        _extract_comparables_with_claude("<html></html>", "ebay", "Test Book")

        # Check the prompt sent to Claude
        call_args = mock_client.return_value.invoke_model.call_args
        body = json.loads(call_args.kwargs["body"])
        prompt = body["messages"][0]["content"]
        assert "sold book listings" in prompt.lower()

    @patch("app.services.fmv_lookup.get_bedrock_client")
    @patch("app.services.fmv_lookup.get_model_id")
    def test_abebooks_prompt_says_active_listings(self, mock_model_id, mock_client):
        """AbeBooks extraction prompt asks for active/for-sale listings."""
        from app.services.fmv_lookup import _extract_comparables_with_claude

        mock_response = MagicMock()
        mock_response.__getitem__ = lambda self, key: {
            "body": MagicMock(read=lambda: b'{"content": [{"text": "[]"}]}')
        }[key]
        mock_client.return_value.invoke_model.return_value = mock_response
        mock_model_id.return_value = "anthropic.claude-3-sonnet"

        _extract_comparables_with_claude("<html></html>", "abebooks", "Test Book")

        # Check the prompt sent to Claude
        call_args = mock_client.return_value.invoke_model.call_args
        body = json.loads(call_args.kwargs["body"])
        prompt = body["messages"][0]["content"]
        assert "for sale" in prompt.lower() or "currently available" in prompt.lower()
        assert "sold" not in prompt.lower()


class TestLookupFmvIntegration:
    """Integration tests for full FMV lookup flow."""

    @patch("app.services.fmv_lookup._fetch_listings_via_scraper_lambda")
    @patch("app.services.fmv_lookup._fetch_search_page")
    @patch("app.services.fmv_lookup._filter_listings_with_claude")
    @patch("app.services.fmv_lookup._extract_comparables_with_claude")
    def test_abebooks_receives_context_aware_params(
        self, mock_extract, mock_filter, mock_fetch_page, mock_fetch_lambda
    ):
        """AbeBooks lookup receives volume and binding parameters."""
        from app.services.fmv_lookup import lookup_fmv

        # Mock eBay (scraper Lambda)
        mock_fetch_lambda.return_value = []
        mock_filter.return_value = []

        # Mock AbeBooks (direct HTTP)
        mock_fetch_page.return_value = "<html>test</html>"
        mock_extract.return_value = []

        lookup_fmv(
            title="Life of Scott",
            author="Lockhart",
            volumes=7,
            binding_type="Full calf",
        )

        # Verify AbeBooks fetch was called
        assert mock_fetch_page.called
        # Check the URL contains context-aware terms
        call_url = mock_fetch_page.call_args[0][0]
        assert "7" in call_url and "volume" in call_url.lower()
