"""Tests for publisher validation service."""

from app.services.publisher_validation import (
    auto_correct_publisher_name,
    fuzzy_match_publisher,
    get_or_create_publisher,
    normalize_publisher_name,
)


class TestAutoCorrectPublisherName:
    """Test auto-correction rules for publisher names."""

    def test_removes_new_york_suffix(self):
        result = auto_correct_publisher_name("Harper & Brothers, New York")
        assert result == "Harper & Brothers"

    def test_removes_london_suffix(self):
        result = auto_correct_publisher_name("Macmillan and Co., London")
        assert result == "Macmillan and Co."

    def test_removes_philadelphia_suffix(self):
        result = auto_correct_publisher_name("J.B. Lippincott Company, Philadelphia")
        assert result == "J.B. Lippincott Company"

    def test_removes_boston_suffix(self):
        result = auto_correct_publisher_name("D.C. Heath & Co., Boston")
        assert result == "D.C. Heath & Co."

    def test_removes_parenthetical_edition_info(self):
        result = auto_correct_publisher_name("D.C. Heath & Co. (Arden Shakespeare)")
        assert result == "D.C. Heath & Co."

    def test_removes_parenthetical_series_info(self):
        result = auto_correct_publisher_name("Oxford University Press (World's Classics)")
        assert result == "Oxford University Press"

    def test_handles_dual_publisher_keeps_first(self):
        result = auto_correct_publisher_name("Doubleday, Page & Company / Review of Reviews")
        assert result == "Doubleday, Page & Company"

    def test_handles_dual_publisher_with_ampersand(self):
        result = auto_correct_publisher_name("Henry Frowde / Oxford University Press")
        assert result == "Oxford University Press"

    def test_expands_d_to_david_for_bogue(self):
        result = auto_correct_publisher_name("D. Bogue")
        assert result == "David Bogue"

    def test_normalizes_ampersand_co_punctuation(self):
        result = auto_correct_publisher_name("Harper & Co")
        assert result == "Harper & Co."

    def test_preserves_clean_name(self):
        result = auto_correct_publisher_name("Oxford University Press")
        assert result == "Oxford University Press"

    def test_handles_multiple_issues(self):
        result = auto_correct_publisher_name("D. Bogue, Fleet-Street (First Edition)")
        assert result == "David Bogue"

    def test_strips_whitespace(self):
        result = auto_correct_publisher_name("  Harper & Brothers  ")
        assert result == "Harper & Brothers"


class TestNormalizePublisherName:
    """Test publisher name normalization and tier assignment."""

    def test_tier_1_macmillan(self):
        name, tier = normalize_publisher_name("Macmillan and Co.")
        assert name == "Macmillan and Co."
        assert tier == "TIER_1"

    def test_tier_1_chapman_hall(self):
        name, tier = normalize_publisher_name("Chapman & Hall")
        assert name == "Chapman & Hall"
        assert tier == "TIER_1"

    def test_tier_1_smith_elder(self):
        name, tier = normalize_publisher_name("Smith, Elder & Co.")
        assert name == "Smith, Elder & Co."
        assert tier == "TIER_1"

    def test_tier_1_john_murray(self):
        name, tier = normalize_publisher_name("John Murray")
        assert name == "John Murray"
        assert tier == "TIER_1"

    def test_tier_1_oxford_university_press(self):
        name, tier = normalize_publisher_name("Oxford University Press")
        assert name == "Oxford University Press"
        assert tier == "TIER_1"

    def test_tier_1_longmans(self):
        name, tier = normalize_publisher_name("Longmans, Green & Co.")
        assert name == "Longmans, Green & Co."
        assert tier == "TIER_1"

    def test_tier_1_harper_brothers(self):
        name, tier = normalize_publisher_name("Harper & Brothers")
        assert name == "Harper & Brothers"
        assert tier == "TIER_1"

    def test_tier_2_chatto_windus(self):
        name, tier = normalize_publisher_name("Chatto and Windus")
        assert name == "Chatto and Windus"
        assert tier == "TIER_2"

    def test_tier_2_george_allen(self):
        name, tier = normalize_publisher_name("George Allen")
        assert name == "George Allen"
        assert tier == "TIER_2"

    def test_unknown_publisher_no_tier(self):
        name, tier = normalize_publisher_name("Unknown Publisher")
        assert name == "Unknown Publisher"
        assert tier is None

    def test_applies_auto_correct_first(self):
        # Should remove location suffix, then match tier
        name, tier = normalize_publisher_name("Harper & Brothers, New York")
        assert name == "Harper & Brothers"
        assert tier == "TIER_1"

    def test_case_insensitive_matching(self):
        name, tier = normalize_publisher_name("MACMILLAN AND CO.")
        assert name == "Macmillan and Co."
        assert tier == "TIER_1"

    def test_no_substring_matching_murray(self):
        # "Murray Printing Company" should NOT match "John Murray"
        name, tier = normalize_publisher_name("Murray Printing Company")
        assert name == "Murray Printing Company"
        assert tier is None  # NOT TIER_1

    def test_no_substring_matching_harper(self):
        # "Harper's Magazine Press" should NOT match "Harper & Brothers"
        name, tier = normalize_publisher_name("Harper's Magazine Press")
        assert name == "Harper's Magazine Press"
        assert tier is None  # NOT TIER_1

    def test_no_substring_matching_appleton(self):
        # "Appleton Wisconsin Books" should NOT match "D. Appleton and Company"
        name, tier = normalize_publisher_name("Appleton Wisconsin Books")
        assert name == "Appleton Wisconsin Books"
        assert tier is None  # NOT TIER_1


class TestFuzzyMatchPublisher:
    """Test fuzzy matching against existing publishers."""

    def test_exact_match_returns_high_confidence(self, db):
        from app.models.publisher import Publisher

        # Create existing publisher
        pub = Publisher(name="Harper & Brothers", tier="TIER_1")
        db.add(pub)
        db.flush()

        matches = fuzzy_match_publisher(db, "Harper & Brothers")
        assert len(matches) >= 1
        assert matches[0].name == "Harper & Brothers"
        assert matches[0].confidence >= 0.95
        assert matches[0].publisher_id == pub.id

    def test_close_match_returns_medium_confidence(self, db):
        from app.models.publisher import Publisher

        pub = Publisher(name="Harper & Brothers", tier="TIER_1")
        db.add(pub)
        db.flush()

        # More significant variation for medium confidence
        matches = fuzzy_match_publisher(db, "Harper Bros")
        assert len(matches) >= 1
        assert matches[0].name == "Harper & Brothers"
        assert 0.6 <= matches[0].confidence < 0.95

    def test_no_match_returns_empty(self, db):
        from app.models.publisher import Publisher

        pub = Publisher(name="Harper & Brothers", tier="TIER_1")
        db.add(pub)
        db.flush()

        matches = fuzzy_match_publisher(db, "Completely Different Publisher")
        assert len(matches) == 0 or matches[0].confidence < 0.6

    def test_returns_top_3_matches(self, db):
        from app.models.publisher import Publisher

        # Create several publishers
        db.add(Publisher(name="Harper & Brothers", tier="TIER_1"))
        db.add(Publisher(name="Harper & Row", tier="TIER_2"))
        db.add(Publisher(name="Harpers Magazine", tier=None))
        db.add(Publisher(name="Macmillan", tier="TIER_1"))
        db.flush()

        matches = fuzzy_match_publisher(db, "Harper")
        assert len(matches) <= 3
        # All returned should have Harper in name
        for match in matches:
            assert "Harper" in match.name or match.confidence > 0.5

    def test_match_includes_tier(self, db):
        from app.models.publisher import Publisher

        pub = Publisher(name="Macmillan and Co.", tier="TIER_1")
        db.add(pub)
        db.flush()

        matches = fuzzy_match_publisher(db, "Macmillan")
        assert len(matches) >= 1
        assert matches[0].tier == "TIER_1"


class TestGetOrCreatePublisher:
    """Test publisher lookup/creation from parsed data."""

    def test_returns_none_for_none_input(self, db):
        result = get_or_create_publisher(db, None)
        assert result is None

    def test_returns_none_for_empty_string(self, db):
        result = get_or_create_publisher(db, "")
        assert result is None

    def test_creates_tier_1_publisher(self, db):
        result = get_or_create_publisher(db, "Macmillan and Co.")
        assert result is not None
        assert result.name == "Macmillan and Co."
        assert result.tier == "TIER_1"
        assert result.id is not None

    def test_creates_unknown_publisher_no_tier(self, db):
        result = get_or_create_publisher(db, "Unknown Local Press")
        assert result is not None
        assert result.name == "Unknown Local Press"
        assert result.tier is None

    def test_returns_existing_publisher_exact_match(self, db):
        # Create first
        first = get_or_create_publisher(db, "Harper & Brothers")
        db.flush()

        # Look up again
        second = get_or_create_publisher(db, "Harper & Brothers")
        assert second.id == first.id

    def test_returns_existing_publisher_fuzzy_match(self, db):
        # Create first
        first = get_or_create_publisher(db, "Harper & Brothers")
        db.flush()

        # Look up with typo - should still match
        second = get_or_create_publisher(db, "Harpr & Brothers")
        assert second.id == first.id

    def test_applies_auto_correction(self, db):
        result = get_or_create_publisher(db, "Harper & Brothers, New York")
        assert result.name == "Harper & Brothers"
        assert result.tier == "TIER_1"

    def test_updates_tier_if_missing(self, db):
        from app.models.publisher import Publisher

        # Create publisher without tier manually
        pub = Publisher(name="Macmillan and Co.", tier=None)
        db.add(pub)
        db.flush()

        # Get via service - should update tier
        result = get_or_create_publisher(db, "Macmillan and Co.")
        assert result.id == pub.id
        assert result.tier == "TIER_1"

    def test_flags_new_publisher_for_enrichment(self, db):
        result = get_or_create_publisher(db, "New Unknown Publisher")
        assert result is not None
        assert result.description is None  # Not enriched yet
        # New publishers should exist but without enrichment
