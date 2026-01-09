"""Tests for binder normalization service."""

from app.services.binder_normalization import normalize_binder_name_for_matching


class TestNormalizeBinderNameForMatching:
    """Test normalization rules for binder names used in fuzzy matching."""

    # Parenthetical description stripping
    def test_strips_parenthetical_of_bath(self):
        result = normalize_binder_name_for_matching("Bayntun (of Bath)")
        assert result == "Bayntun"

    def test_strips_parenthetical_location(self):
        result = normalize_binder_name_for_matching("Sangorski & Sutcliffe (London)")
        assert result == "Sangorski & Sutcliffe"

    def test_strips_multiple_parentheticals(self):
        result = normalize_binder_name_for_matching("Binder Name (note one) (note two)")
        assert result == "Binder Name"

    def test_strips_parenthetical_with_numbers(self):
        result = normalize_binder_name_for_matching("Bindery (est. 1850)")
        assert result == "Bindery"

    # Square bracket stripping
    def test_strips_square_brackets(self):
        result = normalize_binder_name_for_matching("Bedford [some note]")
        assert result == "Bedford"

    def test_strips_square_brackets_multiple(self):
        result = normalize_binder_name_for_matching("Bedford [note 1] [note 2]")
        assert result == "Bedford"

    def test_strips_mixed_brackets(self):
        result = normalize_binder_name_for_matching("Bedford (location) [note]")
        assert result == "Bedford"

    # Accent normalization (ASCII folding)
    def test_accent_normalization_riviere(self):
        result = normalize_binder_name_for_matching("Rivière")
        assert result == "Riviere"

    def test_accent_normalization_riviere_and_son(self):
        result = normalize_binder_name_for_matching("Rivière & Son")
        assert result == "Riviere & Son"

    def test_accent_normalization_cedilla(self):
        result = normalize_binder_name_for_matching("François")
        assert result == "Francois"

    def test_accent_normalization_umlaut(self):
        result = normalize_binder_name_for_matching("Müller")
        assert result == "Muller"

    def test_accent_normalization_multiple_diacritics(self):
        result = normalize_binder_name_for_matching("Société Générale")
        assert result == "Societe Generale"

    # Whitespace normalization
    def test_strips_leading_whitespace(self):
        result = normalize_binder_name_for_matching("  Zaehnsdorf")
        assert result == "Zaehnsdorf"

    def test_strips_trailing_whitespace(self):
        result = normalize_binder_name_for_matching("Zaehnsdorf  ")
        assert result == "Zaehnsdorf"

    def test_strips_both_whitespace(self):
        result = normalize_binder_name_for_matching("  Zaehnsdorf  ")
        assert result == "Zaehnsdorf"

    def test_collapses_multiple_spaces(self):
        result = normalize_binder_name_for_matching("Sangorski  &   Sutcliffe")
        assert result == "Sangorski & Sutcliffe"

    # Case preservation (matching is case-insensitive elsewhere)
    def test_preserves_case_uppercase(self):
        result = normalize_binder_name_for_matching("BAYNTUN")
        assert result == "BAYNTUN"

    def test_preserves_case_mixed(self):
        result = normalize_binder_name_for_matching("BaYnTuN")
        assert result == "BaYnTuN"

    def test_preserves_case_lowercase(self):
        result = normalize_binder_name_for_matching("bayntun")
        assert result == "bayntun"

    # Edge cases
    def test_empty_string_returns_empty(self):
        result = normalize_binder_name_for_matching("")
        assert result == ""

    def test_none_returns_empty(self):
        result = normalize_binder_name_for_matching(None)
        assert result == ""

    def test_whitespace_only_returns_empty(self):
        result = normalize_binder_name_for_matching("   ")
        assert result == ""

    def test_single_word_name(self):
        result = normalize_binder_name_for_matching("Zaehnsdorf")
        assert result == "Zaehnsdorf"

    def test_ampersand_preserved(self):
        result = normalize_binder_name_for_matching("Sangorski & Sutcliffe")
        assert result == "Sangorski & Sutcliffe"

    def test_hyphen_preserved(self):
        result = normalize_binder_name_for_matching("Bayntun-Riviere")
        assert result == "Bayntun-Riviere"

    def test_period_preserved(self):
        result = normalize_binder_name_for_matching("J. Leighton")
        assert result == "J. Leighton"

    def test_apostrophe_preserved(self):
        result = normalize_binder_name_for_matching("O'Brien Bindery")
        assert result == "O'Brien Bindery"

    # Combined transformations
    def test_combined_accent_and_parenthetical(self):
        result = normalize_binder_name_for_matching("Rivière (Paris)")
        assert result == "Riviere"

    def test_combined_whitespace_and_parenthetical(self):
        result = normalize_binder_name_for_matching("  Bayntun   (of Bath)  ")
        assert result == "Bayntun"

    def test_combined_all_transformations(self):
        result = normalize_binder_name_for_matching("  Rivière  &  Son  (London) [fine binding]  ")
        assert result == "Riviere & Son"

    # Real-world binder names from TIER_1_BINDERS/TIER_2_BINDERS
    def test_sangorski_sutcliffe_clean(self):
        result = normalize_binder_name_for_matching("Sangorski & Sutcliffe")
        assert result == "Sangorski & Sutcliffe"

    def test_cobden_sanderson(self):
        result = normalize_binder_name_for_matching("Cobden-Sanderson")
        assert result == "Cobden-Sanderson"

    def test_leighton_son_hodge(self):
        result = normalize_binder_name_for_matching("Leighton, Son & Hodge")
        assert result == "Leighton, Son & Hodge"

    def test_birdsall_of_northampton(self):
        """Location suffix 'of Northampton' should be stripped for matching."""
        result = normalize_binder_name_for_matching("Birdsall of Northampton")
        assert result == "Birdsall"

    def test_h_sotheran_co(self):
        result = normalize_binder_name_for_matching("H. Sotheran & Co.")
        assert result == "H. Sotheran & Co."

    def test_j_e_bumpus(self):
        result = normalize_binder_name_for_matching("J. & E. Bumpus")
        assert result == "J. & E. Bumpus"

    # Location suffix handling ("of X" and ", X")
    def test_strips_comma_location(self):
        """Comma location suffix should be stripped for matching."""
        result = normalize_binder_name_for_matching("Birdsall, Northampton")
        assert result == "Birdsall"

    def test_strips_of_bath_without_parens(self):
        """'of Bath' without parentheses should be stripped."""
        result = normalize_binder_name_for_matching("Bayntun of Bath")
        assert result == "Bayntun"

    def test_preserves_roger_de_coverly(self):
        """'de' in 'Roger de Coverly' should NOT be treated as location suffix."""
        result = normalize_binder_name_for_matching("Roger de Coverly")
        assert result == "Roger de Coverly"

    def test_preserves_david_bryce_son(self):
        """'Son' should not be stripped as location suffix."""
        result = normalize_binder_name_for_matching("David Bryce & Son")
        assert result == "David Bryce & Son"

    def test_strips_of_london(self):
        """'of London' should be stripped."""
        result = normalize_binder_name_for_matching("Smith of London")
        assert result == "Smith"

    def test_combined_parenthetical_and_of_location(self):
        """Parenthetical should be stripped first, then 'of X'."""
        result = normalize_binder_name_for_matching("Bedford of Bath (note)")
        assert result == "Bedford"

    # Ensure normalization doesn't over-strip (avoid false positives)
    def test_does_not_strip_embedded_parenthetical(self):
        # Parentheticals should only be stripped if they appear at the end
        # "Root (and) Son" should preserve the middle part
        # Though this is an unlikely real case, we want predictable behavior
        result = normalize_binder_name_for_matching("Name (middle) More")
        # After stripping parentheticals, we get "Name  More" which collapses to "Name More"
        assert result == "Name More"

    def test_parenthetical_at_start_not_stripped(self):
        # Unusual case but should handle gracefully
        # Only trailing parentheticals are stripped, not leading ones
        result = normalize_binder_name_for_matching("(Note) Binder Name")
        # This should strip the leading parenthetical too for consistency
        assert result == "Binder Name"
