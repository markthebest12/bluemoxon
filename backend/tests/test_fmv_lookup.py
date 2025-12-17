"""Tests for FMV lookup service."""

import urllib.parse

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
