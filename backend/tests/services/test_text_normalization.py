"""Tests for shared text normalization utilities."""

from app.services.text_normalization import normalize_whitespace, remove_diacritics


class TestRemoveDiacritics:
    """Test diacritic removal (accent folding)."""

    def test_removes_acute_accent(self):
        assert remove_diacritics("café") == "cafe"

    def test_removes_grave_accent(self):
        assert remove_diacritics("è") == "e"

    def test_removes_diaeresis(self):
        assert remove_diacritics("Brontë") == "Bronte"

    def test_removes_circumflex(self):
        assert remove_diacritics("hôtel") == "hotel"

    def test_removes_tilde(self):
        assert remove_diacritics("señor") == "senor"

    def test_removes_cedilla(self):
        assert remove_diacritics("façade") == "facade"

    def test_removes_multiple_diacritics(self):
        assert remove_diacritics("naïve résumé") == "naive resume"

    def test_preserves_plain_ascii(self):
        assert remove_diacritics("Hello World") == "Hello World"

    def test_preserves_case(self):
        assert remove_diacritics("CAFÉ") == "CAFE"

    def test_empty_string(self):
        assert remove_diacritics("") == ""

    def test_riviere_accent(self):
        """Specific test for Rivière binder name."""
        assert remove_diacritics("Rivière") == "Riviere"


class TestNormalizeWhitespace:
    """Test whitespace normalization."""

    def test_strips_leading_whitespace(self):
        assert normalize_whitespace("  hello") == "hello"

    def test_strips_trailing_whitespace(self):
        assert normalize_whitespace("hello  ") == "hello"

    def test_strips_both_ends(self):
        assert normalize_whitespace("  hello  ") == "hello"

    def test_collapses_multiple_spaces(self):
        assert normalize_whitespace("hello    world") == "hello world"

    def test_handles_tabs(self):
        assert normalize_whitespace("hello\tworld") == "hello world"

    def test_handles_newlines(self):
        assert normalize_whitespace("hello\nworld") == "hello world"

    def test_handles_mixed_whitespace(self):
        assert normalize_whitespace("  hello  \t\n  world  ") == "hello world"

    def test_preserves_single_space(self):
        assert normalize_whitespace("hello world") == "hello world"

    def test_empty_string(self):
        assert normalize_whitespace("") == ""

    def test_whitespace_only(self):
        assert normalize_whitespace("   \t\n   ") == ""

    def test_single_word(self):
        assert normalize_whitespace("hello") == "hello"
