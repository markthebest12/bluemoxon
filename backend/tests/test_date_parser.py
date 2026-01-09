"""Tests for date_parser utility module.

These tests verify the parse_publication_date function handles various
historical publication date formats commonly found in antiquarian book records.
"""

from app.enums import Era
from app.utils.date_parser import compute_era, parse_publication_date


class TestParsePublicationDate:
    """Tests for parse_publication_date function."""

    def test_single_year(self):
        """Single year should return same year for start and end."""
        assert parse_publication_date("1851") == (1851, 1851)
        assert parse_publication_date("1900") == (1900, 1900)
        assert parse_publication_date("2000") == (2000, 2000)

    def test_year_range(self):
        """Year range should return start and end years."""
        assert parse_publication_date("1867-1880") == (1867, 1880)
        assert parse_publication_date("1800-1850") == (1800, 1850)
        assert parse_publication_date("1890-1895") == (1890, 1895)

    def test_year_range_with_spaces(self):
        """Year range with spaces should be handled."""
        assert parse_publication_date("1867 - 1880") == (1867, 1880)
        assert parse_publication_date("1867- 1880") == (1867, 1880)
        assert parse_publication_date("1867 -1880") == (1867, 1880)

    def test_decade_format(self):
        """Decade format (1880s) should return decade start and end."""
        assert parse_publication_date("1880s") == (1880, 1889)
        assert parse_publication_date("1890s") == (1890, 1899)
        assert parse_publication_date("1800s") == (1800, 1809)
        assert parse_publication_date("1850s") == (1850, 1859)

    def test_circa_single_year(self):
        """Circa prefix with single year."""
        assert parse_publication_date("c.1890") == (1890, 1890)
        assert parse_publication_date("c. 1890") == (1890, 1890)
        assert parse_publication_date("circa 1890") == (1890, 1890)
        assert parse_publication_date("Circa 1890") == (1890, 1890)
        assert parse_publication_date("ca. 1890") == (1890, 1890)
        assert parse_publication_date("ca 1890") == (1890, 1890)

    def test_circa_with_range(self):
        """Circa prefix with year range."""
        assert parse_publication_date("c.1880-1890") == (1880, 1890)
        assert parse_publication_date("circa 1880-1890") == (1880, 1890)
        assert parse_publication_date("c. 1880-1890") == (1880, 1890)

    def test_circa_with_decade(self):
        """Circa prefix with decade format."""
        assert parse_publication_date("c.1880s") == (1880, 1889)
        assert parse_publication_date("circa 1880s") == (1880, 1889)

    def test_square_brackets(self):
        """Years in square brackets (uncertain dates)."""
        assert parse_publication_date("[1851]") == (1851, 1851)
        assert parse_publication_date("[1867-1880]") == (1867, 1880)
        assert parse_publication_date("[c.1890]") == (1890, 1890)
        assert parse_publication_date("[1880s]") == (1880, 1889)

    def test_question_mark_uncertain(self):
        """Years with question mark (uncertain)."""
        assert parse_publication_date("1851?") == (1851, 1851)
        assert parse_publication_date("1880?") == (1880, 1880)

    def test_nd_no_date(self):
        """'n.d.' or 'no date' should return None for both."""
        assert parse_publication_date("n.d.") == (None, None)
        assert parse_publication_date("N.D.") == (None, None)
        assert parse_publication_date("no date") == (None, None)
        assert parse_publication_date("No Date") == (None, None)
        assert parse_publication_date("[n.d.]") == (None, None)

    def test_empty_and_none(self):
        """Empty string or None should return None for both."""
        assert parse_publication_date("") == (None, None)
        assert parse_publication_date(None) == (None, None)
        assert parse_publication_date("   ") == (None, None)

    def test_invalid_formats(self):
        """Invalid formats should return None for both."""
        assert parse_publication_date("abc") == (None, None)
        assert parse_publication_date("nineteenth century") == (None, None)
        assert parse_publication_date("Victorian era") == (None, None)

    def test_whitespace_handling(self):
        """Leading/trailing whitespace should be stripped."""
        assert parse_publication_date("  1851  ") == (1851, 1851)
        assert parse_publication_date("\t1867-1880\n") == (1867, 1880)
        assert parse_publication_date("  c.1890  ") == (1890, 1890)

    def test_complex_formats(self):
        """Complex or edge case formats."""
        # Two-digit short form for end year (less common but seen)
        assert parse_publication_date("1867-80") == (1867, 1880)
        assert parse_publication_date("1890-95") == (1890, 1895)

        # Full 4-digit short form still works
        assert parse_publication_date("1867-1880") == (1867, 1880)

    def test_early_nineteenth_century(self):
        """Early years (before 1800) should still work."""
        assert parse_publication_date("1750") == (1750, 1750)
        assert parse_publication_date("1799") == (1799, 1799)
        assert parse_publication_date("1750-1760") == (1750, 1760)

    def test_twentieth_century(self):
        """20th century dates should work."""
        assert parse_publication_date("1920") == (1920, 1920)
        assert parse_publication_date("1920s") == (1920, 1929)
        assert parse_publication_date("1901-1910") == (1901, 1910)

    def test_preserves_original_when_only_year_start_explicit(self):
        """When only year_start is provided explicitly, year_end defaults same."""
        # This tests the function's behavior, not the schema
        # The function should always return both values
        year_start, year_end = parse_publication_date("1851")
        assert year_start == 1851
        assert year_end == 1851


class TestParsePublicationDateEdgeCases:
    """Edge case tests for parse_publication_date."""

    def test_minimum_valid_year(self):
        """Very early years should still be parsed."""
        assert parse_publication_date("1000") == (1000, 1000)
        assert parse_publication_date("1500") == (1500, 1500)

    def test_future_years_allowed(self):
        """Future years should still be parsed (no validation here)."""
        assert parse_publication_date("2030") == (2030, 2030)
        assert parse_publication_date("2100") == (2100, 2100)

    def test_reverse_range_normalized(self):
        """Reversed ranges should swap to be chronological."""
        # If someone enters 1880-1867, we should normalize it
        assert parse_publication_date("1880-1867") == (1867, 1880)

    def test_same_year_range(self):
        """Range where start equals end."""
        assert parse_publication_date("1850-1850") == (1850, 1850)

    def test_three_digit_year(self):
        """Three digit years should not be parsed (ambiguous)."""
        assert parse_publication_date("851") == (None, None)
        assert parse_publication_date("99") == (None, None)

    def test_five_digit_year(self):
        """Five digit numbers should not be parsed as years."""
        assert parse_publication_date("18510") == (None, None)
        assert parse_publication_date("12345") == (None, None)

    def test_partial_range(self):
        """Incomplete ranges should return None."""
        assert parse_publication_date("1850-") == (None, None)
        assert parse_publication_date("-1850") == (None, None)

    def test_century_rollover_in_short_form(self):
        """Two-digit end year crossing century boundary."""
        assert parse_publication_date("1898-02") == (1898, 1902)
        assert parse_publication_date("1899-05") == (1899, 1905)


class TestComputeEra:
    """Tests for compute_era function."""

    def test_pre_romantic(self):
        """Years before 1800 should be Pre-Romantic."""
        assert compute_era(1750, 1750) == Era.PRE_ROMANTIC
        assert compute_era(1799, 1799) == Era.PRE_ROMANTIC
        assert compute_era(1500, None) == Era.PRE_ROMANTIC

    def test_romantic(self):
        """Years 1800-1836 should be Romantic."""
        assert compute_era(1800, 1800) == Era.ROMANTIC
        assert compute_era(1820, 1820) == Era.ROMANTIC
        assert compute_era(1836, 1836) == Era.ROMANTIC

    def test_victorian(self):
        """Years 1837-1901 should be Victorian."""
        assert compute_era(1837, 1837) == Era.VICTORIAN
        assert compute_era(1850, 1850) == Era.VICTORIAN
        assert compute_era(1867, 1880) == Era.VICTORIAN
        assert compute_era(1901, 1901) == Era.VICTORIAN

    def test_edwardian(self):
        """Years 1902-1910 should be Edwardian."""
        assert compute_era(1902, 1902) == Era.EDWARDIAN
        assert compute_era(1905, 1905) == Era.EDWARDIAN
        assert compute_era(1910, 1910) == Era.EDWARDIAN

    def test_post_1910(self):
        """Years after 1910 should be Post-1910."""
        assert compute_era(1911, 1911) == Era.POST_1910
        assert compute_era(1920, 1920) == Era.POST_1910
        assert compute_era(2000, 2000) == Era.POST_1910

    def test_unknown(self):
        """None values should return Unknown."""
        assert compute_era(None, None) == Era.UNKNOWN

    def test_year_start_preferred(self):
        """year_start should be used over year_end when both available."""
        # A multi-year publication spanning eras should use year_start
        assert compute_era(1836, 1840) == Era.ROMANTIC  # Uses 1836
        assert compute_era(1901, 1905) == Era.VICTORIAN  # Uses 1901

    def test_year_end_fallback(self):
        """year_end should be used when year_start is None."""
        assert compute_era(None, 1850) == Era.VICTORIAN
        assert compute_era(None, 1800) == Era.ROMANTIC
        assert compute_era(None, 1910) == Era.EDWARDIAN

    def test_era_boundaries(self):
        """Test exact era boundary years."""
        # Pre-Romantic/Romantic boundary
        assert compute_era(1799, None) == Era.PRE_ROMANTIC
        assert compute_era(1800, None) == Era.ROMANTIC

        # Romantic/Victorian boundary
        assert compute_era(1836, None) == Era.ROMANTIC
        assert compute_era(1837, None) == Era.VICTORIAN

        # Victorian/Edwardian boundary
        assert compute_era(1901, None) == Era.VICTORIAN
        assert compute_era(1902, None) == Era.EDWARDIAN

        # Edwardian/Post-1910 boundary
        assert compute_era(1910, None) == Era.EDWARDIAN
        assert compute_era(1911, None) == Era.POST_1910
