"""Tests for publisher validation service."""

import pytest

from app.services.publisher_validation import (
    PUBLISHER_CACHE_TTL_SECONDS,
    auto_correct_publisher_name,
    fuzzy_match_publisher,
    get_or_create_publisher,
    invalidate_publisher_cache,
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
    """Test publisher name normalization and tier assignment (DB-backed)."""

    @pytest.fixture(autouse=True)
    def seed_aliases(self, db):
        """Seed publisher aliases for tests."""
        from app.models.publisher import Publisher
        from app.models.publisher_alias import PublisherAlias

        # Create publishers with tiers and their aliases
        publishers_data = [
            ("Macmillan and Co.", "TIER_1", ["Macmillan"]),
            ("Chapman & Hall", "TIER_1", ["Chapman and Hall"]),
            ("Smith, Elder & Co.", "TIER_1", ["Smith Elder"]),
            ("John Murray", "TIER_1", ["Murray"]),
            ("Oxford University Press", "TIER_1", ["OUP"]),
            ("Longmans, Green & Co.", "TIER_1", ["Longmans", "Longman"]),
            ("Harper & Brothers", "TIER_1", ["Harper"]),
            ("D. Appleton and Company", "TIER_1", ["Appleton"]),
            ("Chatto and Windus", "TIER_2", ["Chatto & Windus"]),
            ("George Allen", "TIER_2", []),
        ]

        for name, tier, aliases in publishers_data:
            pub = Publisher(name=name, tier=tier)
            db.add(pub)
            db.flush()
            # Add canonical name as alias
            db.add(PublisherAlias(alias_name=name, publisher_id=pub.id))
            for alias in aliases:
                db.add(PublisherAlias(alias_name=alias, publisher_id=pub.id))
        db.flush()

    def test_tier_1_macmillan(self, db):
        name, tier = normalize_publisher_name(db, "Macmillan and Co.")
        assert name == "Macmillan and Co."
        assert tier == "TIER_1"

    def test_tier_1_chapman_hall(self, db):
        name, tier = normalize_publisher_name(db, "Chapman & Hall")
        assert name == "Chapman & Hall"
        assert tier == "TIER_1"

    def test_tier_1_smith_elder(self, db):
        name, tier = normalize_publisher_name(db, "Smith, Elder & Co.")
        assert name == "Smith, Elder & Co."
        assert tier == "TIER_1"

    def test_tier_1_john_murray(self, db):
        name, tier = normalize_publisher_name(db, "John Murray")
        assert name == "John Murray"
        assert tier == "TIER_1"

    def test_tier_1_oxford_university_press(self, db):
        name, tier = normalize_publisher_name(db, "Oxford University Press")
        assert name == "Oxford University Press"
        assert tier == "TIER_1"

    def test_tier_1_longmans(self, db):
        name, tier = normalize_publisher_name(db, "Longmans, Green & Co.")
        assert name == "Longmans, Green & Co."
        assert tier == "TIER_1"

    def test_tier_1_harper_brothers(self, db):
        name, tier = normalize_publisher_name(db, "Harper & Brothers")
        assert name == "Harper & Brothers"
        assert tier == "TIER_1"

    def test_tier_2_chatto_windus(self, db):
        name, tier = normalize_publisher_name(db, "Chatto and Windus")
        assert name == "Chatto and Windus"
        assert tier == "TIER_2"

    def test_tier_2_george_allen(self, db):
        name, tier = normalize_publisher_name(db, "George Allen")
        assert name == "George Allen"
        assert tier == "TIER_2"

    def test_unknown_publisher_no_tier(self, db):
        name, tier = normalize_publisher_name(db, "Unknown Publisher")
        assert name == "Unknown Publisher"
        assert tier is None

    def test_applies_auto_correct_first(self, db):
        # Should remove location suffix, then match tier
        name, tier = normalize_publisher_name(db, "Harper & Brothers, New York")
        assert name == "Harper & Brothers"
        assert tier == "TIER_1"

    def test_case_insensitive_matching(self, db):
        name, tier = normalize_publisher_name(db, "MACMILLAN AND CO.")
        assert name == "Macmillan and Co."
        assert tier == "TIER_1"

    def test_no_substring_matching_murray(self, db):
        # "Murray Printing Company" should NOT match "John Murray"
        name, tier = normalize_publisher_name(db, "Murray Printing Company")
        assert name == "Murray Printing Company"
        assert tier is None  # NOT TIER_1

    def test_no_substring_matching_harper(self, db):
        # "Harper's Magazine Press" should NOT match "Harper & Brothers"
        name, tier = normalize_publisher_name(db, "Harper's Magazine Press")
        assert name == "Harper's Magazine Press"
        assert tier is None  # NOT TIER_1

    def test_no_substring_matching_appleton(self, db):
        # "Appleton Wisconsin Books" should NOT match "D. Appleton and Company"
        name, tier = normalize_publisher_name(db, "Appleton Wisconsin Books")
        assert name == "Appleton Wisconsin Books"
        assert tier is None  # NOT TIER_1

    def test_alias_lookup_variant(self, db):
        # "Macmillan" alias should resolve to "Macmillan and Co."
        name, tier = normalize_publisher_name(db, "Macmillan")
        assert name == "Macmillan and Co."
        assert tier == "TIER_1"

    def test_alias_lookup_variant_chapman(self, db):
        # "Chapman and Hall" alias should resolve to "Chapman & Hall"
        name, tier = normalize_publisher_name(db, "Chapman and Hall")
        assert name == "Chapman & Hall"
        assert tier == "TIER_1"


class TestFuzzyMatchPublisher:
    """Test fuzzy matching against existing publishers."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before and after each test."""
        invalidate_publisher_cache()
        yield
        invalidate_publisher_cache()

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

    @pytest.fixture(autouse=True)
    def seed_aliases(self, db):
        """Seed publisher aliases for tier lookup."""
        from app.models.publisher import Publisher
        from app.models.publisher_alias import PublisherAlias

        # Create publishers with tiers and their aliases
        publishers_data = [
            ("Macmillan and Co.", "TIER_1", ["Macmillan"]),
            ("Harper & Brothers", "TIER_1", ["Harper"]),
        ]

        for name, tier, aliases in publishers_data:
            pub = Publisher(name=name, tier=tier)
            db.add(pub)
            db.flush()
            db.add(PublisherAlias(alias_name=name, publisher_id=pub.id))
            for alias in aliases:
                db.add(PublisherAlias(alias_name=alias, publisher_id=pub.id))
        db.flush()

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

    def test_returns_tier_from_db(self, db):
        """Tier now comes from database, not hardcoded lookup."""
        # The seeded "Macmillan and Co." has TIER_1 in the database
        result = get_or_create_publisher(db, "Macmillan and Co.")
        assert result is not None
        assert result.name == "Macmillan and Co."
        assert result.tier == "TIER_1"  # Comes from DB, not hardcoded

    def test_unknown_publisher_has_no_tier(self, db):
        """Publishers not in aliases table get no tier."""
        result = get_or_create_publisher(db, "Some Random Publisher")
        assert result is not None
        assert result.tier is None

    def test_flags_new_publisher_for_enrichment(self, db):
        result = get_or_create_publisher(db, "New Unknown Publisher")
        assert result is not None
        assert result.description is None  # Not enriched yet
        # New publishers should exist but without enrichment


class TestPublisherCaching:
    """Test publisher caching for fuzzy matching performance."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before each test."""
        invalidate_publisher_cache()
        yield
        invalidate_publisher_cache()

    def test_cache_avoids_repeated_db_queries(self, db):
        """Verify that multiple fuzzy_match_publisher calls use cache, not DB."""
        import app.services.publisher_validation as pv
        from app.models.publisher import Publisher

        # Create some publishers
        db.add(Publisher(name="Harper & Brothers", tier="TIER_1"))
        db.add(Publisher(name="Macmillan", tier="TIER_1"))
        db.flush()

        # Clear cache to start fresh
        invalidate_publisher_cache()

        # Verify cache is empty
        assert pv._publisher_cache is None

        # First call should populate cache
        fuzzy_match_publisher(db, "Harper")

        # Verify cache is now populated
        assert pv._publisher_cache is not None
        cache_after_first_call = pv._publisher_cache
        cache_time_after_first = pv._publisher_cache_time

        # Second call should use same cache (not re-query)
        fuzzy_match_publisher(db, "Macmillan")

        # Cache should be the exact same object (not re-queried)
        assert pv._publisher_cache is cache_after_first_call
        assert pv._publisher_cache_time == cache_time_after_first

    def test_cache_invalidation_forces_db_query(self, db):
        """Verify that invalidate_publisher_cache forces a fresh DB query."""
        from app.models.publisher import Publisher

        db.add(Publisher(name="Original Publisher", tier="TIER_1"))
        db.flush()

        # First call populates cache
        matches1 = fuzzy_match_publisher(db, "Original Publisher")
        assert len(matches1) >= 1

        # Add new publisher
        db.add(Publisher(name="New Publisher", tier="TIER_2"))
        db.flush()

        # Without invalidation, cache would miss the new publisher
        # Invalidate cache
        invalidate_publisher_cache()

        # Now should see the new publisher
        matches2 = fuzzy_match_publisher(db, "New Publisher")
        assert len(matches2) >= 1
        assert any(m.name == "New Publisher" for m in matches2)

    def test_get_or_create_publisher_invalidates_cache_on_create(self, db):
        """Verify that creating a new publisher invalidates the cache."""
        from app.models.publisher import Publisher
        from app.models.publisher_alias import PublisherAlias

        # Seed an alias so normalize_publisher_name works
        pub = Publisher(name="Existing Publisher", tier="TIER_1")
        db.add(pub)
        db.flush()
        db.add(PublisherAlias(alias_name="Existing Publisher", publisher_id=pub.id))
        db.flush()

        # Populate cache
        fuzzy_match_publisher(db, "Existing Publisher")

        # Create a new publisher via get_or_create_publisher
        new_pub = get_or_create_publisher(db, "Brand New Publisher")
        assert new_pub is not None
        assert new_pub.name == "Brand New Publisher"

        # The new publisher should be findable via fuzzy match
        # (cache should have been invalidated)
        matches = fuzzy_match_publisher(db, "Brand New Publisher")
        assert len(matches) >= 1
        assert any(m.name == "Brand New Publisher" for m in matches)

    def test_cache_ttl_constant_is_set(self):
        """Verify cache TTL is configured."""
        assert PUBLISHER_CACHE_TTL_SECONDS == 300  # 5 minutes
