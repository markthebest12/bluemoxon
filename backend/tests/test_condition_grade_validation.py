"""Tests for condition grade validation and normalization.

Ensures AI-generated condition grades are validated against the ConditionGrade enum
before being saved to the database.
"""

from app.services.analysis_summary import normalize_condition_grade


class TestNormalizeConditionGrade:
    """Tests for normalizing AI condition grades to enum values."""

    def test_valid_enum_values_pass_through(self):
        """Exact enum values should pass through unchanged."""
        assert normalize_condition_grade("FINE") == "FINE"
        assert normalize_condition_grade("NEAR_FINE") == "NEAR_FINE"
        assert normalize_condition_grade("VERY_GOOD") == "VERY_GOOD"
        assert normalize_condition_grade("GOOD") == "GOOD"
        assert normalize_condition_grade("FAIR") == "FAIR"
        assert normalize_condition_grade("POOR") == "POOR"

    def test_case_insensitive_matching(self):
        """Enum values should match regardless of case."""
        assert normalize_condition_grade("fine") == "FINE"
        assert normalize_condition_grade("Fine") == "FINE"
        assert normalize_condition_grade("very_good") == "VERY_GOOD"
        assert normalize_condition_grade("Very_Good") == "VERY_GOOD"

    def test_common_aliases_normalized(self):
        """Common AI aliases should normalize to enum values."""
        # VG variants -> VERY_GOOD
        assert normalize_condition_grade("VG") == "VERY_GOOD"
        assert normalize_condition_grade("vg") == "VERY_GOOD"
        assert normalize_condition_grade("Very Good") == "VERY_GOOD"

        # VG+ -> NEAR_FINE (better than VG)
        assert normalize_condition_grade("VG+") == "NEAR_FINE"

        # NF variants -> NEAR_FINE
        assert normalize_condition_grade("NF") == "NEAR_FINE"
        assert normalize_condition_grade("Near Fine") == "NEAR_FINE"

        # G variants -> GOOD
        assert normalize_condition_grade("G") == "GOOD"
        assert normalize_condition_grade("Good") == "GOOD"

        # F variants -> FINE
        assert normalize_condition_grade("F") == "FINE"

    def test_invalid_values_return_none(self):
        """Invalid/unknown values should return None."""
        assert normalize_condition_grade("Excellent") is None
        assert normalize_condition_grade("Bad") is None
        assert normalize_condition_grade("Unknown") is None
        assert normalize_condition_grade("") is None
        assert normalize_condition_grade(None) is None

    def test_whitespace_handling(self):
        """Whitespace should be trimmed."""
        assert normalize_condition_grade("  FINE  ") == "FINE"
        assert normalize_condition_grade(" VG ") == "VERY_GOOD"

    def test_hyphenated_inputs(self):
        """Hyphenated inputs should normalize to underscore format."""
        assert normalize_condition_grade("NEAR-FINE") == "NEAR_FINE"
        assert normalize_condition_grade("VERY-GOOD") == "VERY_GOOD"

    def test_whitespace_variations(self):
        """Various whitespace patterns should be handled correctly."""
        assert normalize_condition_grade("VG  +") == "NEAR_FINE"
        assert normalize_condition_grade("VERY   GOOD") == "VERY_GOOD"
        assert normalize_condition_grade("good +") == "GOOD"
        assert normalize_condition_grade("vg -") == "GOOD"

    def test_tabs_and_newlines(self):
        """Tabs and newlines should be stripped."""
        assert normalize_condition_grade("FINE\t") == "FINE"
        assert normalize_condition_grade("\nVG") == "VERY_GOOD"
        assert normalize_condition_grade(" VG \n") == "VERY_GOOD"

    def test_migration_aliases_all_normalized(self):
        """Test ALL aliases from migration dd7f743834bc."""
        assert normalize_condition_grade("as new") == "FINE"
        assert normalize_condition_grade("mint") == "FINE"
        assert normalize_condition_grade("near-fine") == "NEAR_FINE"
        assert normalize_condition_grade("vg +") == "NEAR_FINE"
        assert normalize_condition_grade("very-good") == "VERY_GOOD"
        assert normalize_condition_grade("vg-") == "GOOD"
        assert normalize_condition_grade("vg -") == "GOOD"
        assert normalize_condition_grade("good+") == "GOOD"
        assert normalize_condition_grade("good +") == "GOOD"
        assert normalize_condition_grade("vg/g") == "GOOD"
        assert normalize_condition_grade("reading copy") == "FAIR"
        assert normalize_condition_grade("ex-library") == "POOR"
        assert normalize_condition_grade("ex-lib") == "POOR"
        assert normalize_condition_grade("ex library") == "POOR"

    def test_vg_minus_maps_to_good_not_very_good(self):
        """VG- is definitionally worse than VG. Must map to GOOD."""
        assert normalize_condition_grade("VG-") == "GOOD"
        assert normalize_condition_grade("vg-") == "GOOD"
        assert normalize_condition_grade("VG -") == "GOOD"


class TestConditionGradeFromAlias:
    """Tests for ConditionGrade.from_alias() enum method."""

    def test_returns_enum_not_string(self):
        from app.enums import ConditionGrade

        result = ConditionGrade.from_alias("VG")
        assert result == ConditionGrade.VERY_GOOD
        assert isinstance(result, ConditionGrade)

    def test_none_input_returns_none(self):
        from app.enums import ConditionGrade

        assert ConditionGrade.from_alias(None) is None

    def test_non_string_returns_none(self):
        from app.enums import ConditionGrade

        assert ConditionGrade.from_alias(123) is None
        assert ConditionGrade.from_alias([]) is None


class TestExtractBookUpdatesValidation:
    """Tests that extract_book_updates_from_yaml validates condition_grade."""

    def test_valid_condition_grade_included(self):
        """Valid condition grades should be included in updates."""
        from app.services.analysis_summary import extract_book_updates_from_yaml

        yaml_data = {"condition_grade": "VERY_GOOD"}
        updates = extract_book_updates_from_yaml(yaml_data)
        assert updates["condition_grade"] == "VERY_GOOD"

    def test_alias_condition_grade_normalized(self):
        """Alias condition grades should be normalized in updates."""
        from app.services.analysis_summary import extract_book_updates_from_yaml

        yaml_data = {"condition_grade": "VG"}
        updates = extract_book_updates_from_yaml(yaml_data)
        assert updates["condition_grade"] == "VERY_GOOD"

    def test_invalid_condition_grade_excluded(self):
        """Invalid condition grades should NOT be included in updates."""
        from app.services.analysis_summary import extract_book_updates_from_yaml

        yaml_data = {"condition_grade": "Excellent", "binding_type": "Full Morocco"}
        updates = extract_book_updates_from_yaml(yaml_data)

        # condition_grade should be excluded, but other fields kept
        assert "condition_grade" not in updates
        assert updates["binding_type"] == "Full Morocco"
