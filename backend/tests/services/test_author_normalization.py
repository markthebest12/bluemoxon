"""Tests for author normalization service."""

from app.services.author_normalization import (
    extract_author_name_parts,
    normalize_author_name,
)


class TestNormalizeAuthorName:
    """Test normalization rules for author names."""

    # Name order normalization: "Dickens, Charles" -> "Charles Dickens"
    def test_last_first_to_first_last(self):
        result = normalize_author_name("Dickens, Charles")
        assert result == "Charles Dickens"

    def test_already_normalized_first_last(self):
        result = normalize_author_name("Charles Dickens")
        assert result == "Charles Dickens"

    def test_last_first_middle_to_first_middle_last(self):
        result = normalize_author_name("Bronte, Charlotte Emily")
        assert result == "Charlotte Emily Bronte"

    # Honorific handling: "Sir Walter Scott" -> "Walter Scott"
    def test_removes_sir_honorific(self):
        result = normalize_author_name("Sir Walter Scott")
        assert result == "Walter Scott"

    def test_removes_dame_honorific(self):
        result = normalize_author_name("Dame Agatha Christie")
        assert result == "Agatha Christie"

    def test_removes_dr_honorific(self):
        result = normalize_author_name("Dr. Samuel Johnson")
        assert result == "Samuel Johnson"

    def test_removes_rev_honorific(self):
        result = normalize_author_name("Rev. Charles Dodgson")
        assert result == "Charles Dodgson"

    def test_removes_reverend_honorific(self):
        result = normalize_author_name("Reverend Charles Dodgson")
        assert result == "Charles Dodgson"

    def test_removes_mr_honorific(self):
        result = normalize_author_name("Mr. Charles Dickens")
        assert result == "Charles Dickens"

    def test_removes_mrs_honorific(self):
        result = normalize_author_name("Mrs. Elizabeth Gaskell")
        assert result == "Elizabeth Gaskell"

    def test_removes_miss_honorific(self):
        result = normalize_author_name("Miss Jane Austen")
        assert result == "Jane Austen"

    def test_removes_prof_honorific(self):
        result = normalize_author_name("Prof. J.R.R. Tolkien")
        assert result == "J.R.R. Tolkien"

    def test_removes_professor_honorific(self):
        result = normalize_author_name("Professor J.R.R. Tolkien")
        assert result == "J.R.R. Tolkien"

    def test_removes_lord_honorific(self):
        result = normalize_author_name("Lord Byron")
        assert result == "Byron"

    def test_removes_lady_honorific(self):
        result = normalize_author_name("Lady Gregory")
        assert result == "Gregory"

    # Accent normalization: "Bronte" == "Bronte"
    def test_accent_normalization_bronte(self):
        result = normalize_author_name("Bronte")
        assert result == "Bronte"

    def test_accent_normalization_bronte_with_diaeresis(self):
        result = normalize_author_name("Bront\u00eb")  # e with diaeresis
        assert result == "Bronte"

    def test_accent_normalization_charlotte_bronte(self):
        result = normalize_author_name("Charlotte Bront\u00eb")
        assert result == "Charlotte Bronte"

    def test_accent_normalization_full_name_with_accent(self):
        result = normalize_author_name("Emily Bront\u00eb")
        assert result == "Emily Bronte"

    def test_accent_normalization_other_diacritics(self):
        # Test various diacritical marks
        result = normalize_author_name("Jos\u00e9 Garc\u00eda")  # Jose Garcia
        assert result == "Jose Garcia"

    def test_accent_normalization_cedilla(self):
        result = normalize_author_name("Fran\u00e7ois")  # Francois
        assert result == "Francois"

    # Whitespace normalization
    def test_strips_leading_whitespace(self):
        result = normalize_author_name("   Charles Dickens")
        assert result == "Charles Dickens"

    def test_strips_trailing_whitespace(self):
        result = normalize_author_name("Charles Dickens   ")
        assert result == "Charles Dickens"

    def test_strips_both_whitespace(self):
        result = normalize_author_name("   Charles   Dickens  ")
        assert result == "Charles Dickens"

    def test_collapses_multiple_spaces(self):
        result = normalize_author_name("Charles    Dickens")
        assert result == "Charles Dickens"

    # Case handling
    def test_preserves_case(self):
        # normalize_author_name should preserve case for display
        result = normalize_author_name("Charles Dickens")
        assert result == "Charles Dickens"

    def test_uppercase_input_preserved(self):
        # We preserve case - matching is case-insensitive elsewhere
        result = normalize_author_name("CHARLES DICKENS")
        assert result == "CHARLES DICKENS"

    def test_mixed_case_preserved(self):
        result = normalize_author_name("ChArLeS dIcKeNs")
        assert result == "ChArLeS dIcKeNs"

    def test_uppercase_comma_format(self):
        # From task description: "DICKENS, CHARLES" -> case handling
        result = normalize_author_name("DICKENS, CHARLES")
        assert result == "CHARLES DICKENS"

    # Edge cases
    def test_empty_string_returns_empty(self):
        result = normalize_author_name("")
        assert result == ""

    def test_none_returns_empty(self):
        result = normalize_author_name(None)
        assert result == ""

    def test_single_name_preserved(self):
        result = normalize_author_name("Voltaire")
        assert result == "Voltaire"

    def test_initials_preserved(self):
        result = normalize_author_name("J.R.R. Tolkien")
        assert result == "J.R.R. Tolkien"

    def test_hyphenated_name_preserved(self):
        result = normalize_author_name("Mary Wollstonecraft-Shelley")
        assert result == "Mary Wollstonecraft-Shelley"

    def test_apostrophe_name_preserved(self):
        result = normalize_author_name("O'Brien, Flann")
        assert result == "Flann O'Brien"

    # Combined transformations
    def test_combined_last_first_with_honorific(self):
        result = normalize_author_name("Scott, Sir Walter")
        assert result == "Walter Scott"

    def test_combined_accent_and_whitespace(self):
        result = normalize_author_name("  Bront\u00eb, Charlotte  ")
        assert result == "Charlotte Bronte"

    def test_combined_all_transformations(self):
        result = normalize_author_name("  Bront\u00eb,   Sir  Walter  ")
        assert result == "Walter Bronte"


class TestExtractAuthorNameParts:
    """Test extraction of name parts from various formats."""

    # "Last, First" format
    def test_last_comma_first(self):
        first, middle, last = extract_author_name_parts("Dickens, Charles")
        assert first == "Charles"
        assert middle is None
        assert last == "Dickens"

    def test_last_comma_first_middle(self):
        first, middle, last = extract_author_name_parts("Bronte, Charlotte Emily")
        assert first == "Charlotte"
        assert middle == "Emily"
        assert last == "Bronte"

    def test_last_comma_first_multiple_middle(self):
        first, middle, last = extract_author_name_parts("Tolkien, John Ronald Reuel")
        assert first == "John"
        assert middle == "Ronald Reuel"
        assert last == "Tolkien"

    # "First Last" format
    def test_first_last(self):
        first, middle, last = extract_author_name_parts("Charles Dickens")
        assert first == "Charles"
        assert middle is None
        assert last == "Dickens"

    def test_first_middle_last(self):
        first, middle, last = extract_author_name_parts("Charlotte Emily Bronte")
        assert first == "Charlotte"
        assert middle == "Emily"
        assert last == "Bronte"

    def test_first_multiple_middle_last(self):
        first, middle, last = extract_author_name_parts("John Ronald Reuel Tolkien")
        assert first == "John"
        assert middle == "Ronald Reuel"
        assert last == "Tolkien"

    # Edge cases
    def test_single_name(self):
        first, middle, last = extract_author_name_parts("Voltaire")
        assert first is None
        assert middle is None
        assert last == "Voltaire"

    def test_empty_string(self):
        first, middle, last = extract_author_name_parts("")
        assert first is None
        assert middle is None
        assert last is None

    def test_none_input(self):
        first, middle, last = extract_author_name_parts(None)
        assert first is None
        assert middle is None
        assert last is None

    def test_whitespace_only(self):
        first, middle, last = extract_author_name_parts("   ")
        assert first is None
        assert middle is None
        assert last is None

    # Complex names
    def test_hyphenated_last_name(self):
        first, middle, last = extract_author_name_parts("Mary Wollstonecraft-Shelley")
        assert first == "Mary"
        assert middle is None
        assert last == "Wollstonecraft-Shelley"

    def test_apostrophe_last_name(self):
        first, middle, last = extract_author_name_parts("O'Brien, Flann")
        assert first == "Flann"
        assert middle is None
        assert last == "O'Brien"

    def test_initials_first_name(self):
        first, middle, last = extract_author_name_parts("J.R.R. Tolkien")
        assert first == "J.R.R."
        assert middle is None
        assert last == "Tolkien"

    def test_initials_with_middle(self):
        first, middle, last = extract_author_name_parts("T. S. Eliot")
        assert first == "T."
        assert middle == "S."
        assert last == "Eliot"

    # Tricky comma cases
    def test_last_comma_first_with_extra_whitespace(self):
        first, middle, last = extract_author_name_parts("Dickens,  Charles")
        assert first == "Charles"
        assert middle is None
        assert last == "Dickens"

    def test_last_comma_first_leading_trailing_whitespace(self):
        first, middle, last = extract_author_name_parts("  Dickens, Charles  ")
        assert first == "Charles"
        assert middle is None
        assert last == "Dickens"

    # Jr., Sr., III suffix handling (these stay with last name)
    def test_jr_suffix(self):
        first, middle, last = extract_author_name_parts("Henry James Jr.")
        assert first == "Henry"
        assert middle == "James"
        assert last == "Jr."

    def test_comma_format_with_jr(self):
        first, middle, last = extract_author_name_parts("James Jr., Henry")
        assert first == "Henry"
        assert middle is None
        assert last == "James Jr."
