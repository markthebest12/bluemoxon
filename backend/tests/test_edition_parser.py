"""Tests for edition parsing utility.

Tests for is_first_edition_text() which auto-infers whether edition text
indicates a first edition.
"""

from app.utils.edition_parser import is_first_edition_text


class TestIsFirstEditionText:
    """Tests for is_first_edition_text function."""

    # === Positive cases: should return True ===

    def test_first_edition_exact(self):
        """Basic 'First Edition' match."""
        assert is_first_edition_text("First Edition") is True

    def test_first_edition_lowercase(self):
        """Case insensitivity test."""
        assert is_first_edition_text("first edition") is True

    def test_first_edition_uppercase(self):
        """All caps variation."""
        assert is_first_edition_text("FIRST EDITION") is True

    def test_first_edition_mixed_case(self):
        """Mixed case variation."""
        assert is_first_edition_text("First EDITION") is True

    def test_1st_edition(self):
        """Numeric ordinal with 'Edition'."""
        assert is_first_edition_text("1st Edition") is True

    def test_1st_ed_period(self):
        """Abbreviated with period."""
        assert is_first_edition_text("1st ed.") is True

    def test_first_ed_period(self):
        """Word form abbreviated."""
        assert is_first_edition_text("First ed.") is True

    def test_first_ed_no_period(self):
        """Abbreviated without period."""
        assert is_first_edition_text("First ed") is True

    def test_first_american_edition(self):
        """First American Edition should count as first edition."""
        assert is_first_edition_text("First American Edition") is True

    def test_first_uk_edition(self):
        """First UK Edition should count as first edition."""
        assert is_first_edition_text("First UK Edition") is True

    def test_first_english_edition(self):
        """First English Edition should count as first edition."""
        assert is_first_edition_text("First English Edition") is True

    def test_first_british_edition(self):
        """First British Edition should count as first edition."""
        assert is_first_edition_text("First British Edition") is True

    def test_first_trade_edition(self):
        """First Trade Edition should count as first edition."""
        assert is_first_edition_text("First Trade Edition") is True

    def test_first_collected_edition(self):
        """First Collected Edition should count as first edition."""
        assert is_first_edition_text("First Collected Edition") is True

    def test_first_edition_with_extra_whitespace(self):
        """Extra whitespace should be handled."""
        assert is_first_edition_text("  First Edition  ") is True
        assert is_first_edition_text("First   Edition") is True

    def test_first_only(self):
        """Just 'First' should count as first edition."""
        assert is_first_edition_text("First") is True

    def test_1st_only(self):
        """Just '1st' should count as first edition."""
        assert is_first_edition_text("1st") is True

    def test_first_printing(self):
        """First Printing should count as first edition."""
        assert is_first_edition_text("First Printing") is True

    def test_first_impression(self):
        """First Impression should count as first edition."""
        assert is_first_edition_text("First Impression") is True

    def test_first_edition_first_printing(self):
        """Common format: First Edition, First Printing."""
        assert is_first_edition_text("First Edition, First Printing") is True

    def test_first_edition_thus(self):
        """First Edition Thus - first edition of a new format."""
        assert is_first_edition_text("First Edition Thus") is True

    # === Negative cases: should return False ===

    def test_second_edition(self):
        """Second Edition should NOT match."""
        assert is_first_edition_text("Second Edition") is False

    def test_2nd_edition(self):
        """2nd Edition should NOT match."""
        assert is_first_edition_text("2nd Edition") is False

    def test_third_edition(self):
        """Third Edition should NOT match."""
        assert is_first_edition_text("Third Edition") is False

    def test_3rd_edition(self):
        """3rd Edition should NOT match."""
        assert is_first_edition_text("3rd Edition") is False

    def test_fourth_edition(self):
        """Fourth Edition should NOT match."""
        assert is_first_edition_text("Fourth Edition") is False

    def test_fifth_edition(self):
        """Fifth Edition should NOT match."""
        assert is_first_edition_text("Fifth Edition") is False

    def test_new_edition(self):
        """New Edition should NOT match (implies not first)."""
        assert is_first_edition_text("New Edition") is False

    def test_revised_edition(self):
        """Revised Edition should NOT match."""
        assert is_first_edition_text("Revised Edition") is False

    def test_enlarged_edition(self):
        """Enlarged Edition should NOT match."""
        assert is_first_edition_text("Enlarged Edition") is False

    def test_later_printing(self):
        """Later Printing should NOT match."""
        assert is_first_edition_text("Later Printing") is False

    def test_reprint(self):
        """Reprint should NOT match."""
        assert is_first_edition_text("Reprint") is False

    def test_empty_string(self):
        """Empty string should return None (unknown)."""
        assert is_first_edition_text("") is None

    def test_none_input(self):
        """None input should return None (unknown)."""
        assert is_first_edition_text(None) is None

    def test_whitespace_only(self):
        """Whitespace-only should return None."""
        assert is_first_edition_text("   ") is None

    def test_no_edition_info(self):
        """Text without edition info should return None."""
        assert is_first_edition_text("Bound in morocco") is None

    def test_just_edition(self):
        """Just 'Edition' without ordinal should return None."""
        assert is_first_edition_text("Edition") is None

    def test_numeric_edition_number(self):
        """Just a number like '2' or '3' should not match."""
        assert is_first_edition_text("2") is None
        assert is_first_edition_text("3") is None

    def test_number_1_only(self):
        """Just '1' should be treated as unknown (too ambiguous)."""
        assert is_first_edition_text("1") is None

    # === Edge cases ===

    def test_first_edition_state(self):
        """First Edition, Second State should still count as first edition."""
        assert is_first_edition_text("First Edition, Second State") is True

    def test_first_edition_second_printing(self):
        """First Edition, Second Printing - still first edition."""
        assert is_first_edition_text("First Edition, Second Printing") is True

    def test_first_separate_edition(self):
        """First Separate Edition - first standalone publication."""
        assert is_first_edition_text("First Separate Edition") is True

    def test_true_first(self):
        """True First / True First Edition patterns."""
        assert is_first_edition_text("True First") is True
        assert is_first_edition_text("True First Edition") is True
