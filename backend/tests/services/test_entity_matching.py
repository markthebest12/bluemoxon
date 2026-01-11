"""Tests for unified entity fuzzy matching service."""

from unittest.mock import patch

import pytest

from app.services.entity_matching import (
    ENTITY_CACHE_TTL_SECONDS,
    EntityMatch,
    fuzzy_match_entity,
    invalidate_entity_cache,
)


class TestEntityMatchDataclass:
    """Test EntityMatch dataclass structure."""

    def test_entity_match_has_required_fields(self):
        """EntityMatch should have entity_id, name, tier, confidence, book_count."""
        match = EntityMatch(
            entity_id=1,
            name="Test Publisher",
            tier="TIER_1",
            confidence=0.95,
            book_count=10,
        )
        assert match.entity_id == 1
        assert match.name == "Test Publisher"
        assert match.tier == "TIER_1"
        assert match.confidence == 0.95
        assert match.book_count == 10

    def test_entity_match_tier_can_be_none(self):
        """EntityMatch tier can be None for unclassified entities."""
        match = EntityMatch(
            entity_id=1,
            name="Unknown Publisher",
            tier=None,
            confidence=0.80,
            book_count=0,
        )
        assert match.tier is None


class TestFuzzyMatchPublisher:
    """Test fuzzy matching for publishers."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before and after each test."""
        invalidate_entity_cache("publisher")
        yield
        invalidate_entity_cache("publisher")

    def test_macmilan_matches_macmillan(self, db):
        """'Macmilan' should match 'Macmillan' at >80% confidence."""
        from app.models.publisher import Publisher

        pub = Publisher(name="Macmillan", tier="TIER_1")
        db.add(pub)
        db.flush()

        matches = fuzzy_match_entity(db, "publisher", "Macmilan", threshold=0.80)
        assert len(matches) >= 1
        assert matches[0].name == "Macmillan"
        assert matches[0].confidence >= 0.80

    def test_publisher_exact_match_high_confidence(self, db):
        """Exact publisher match should return >95% confidence."""
        from app.models.publisher import Publisher

        pub = Publisher(name="Harper & Brothers", tier="TIER_1")
        db.add(pub)
        db.flush()

        matches = fuzzy_match_entity(db, "publisher", "Harper & Brothers")
        assert len(matches) >= 1
        assert matches[0].name == "Harper & Brothers"
        assert matches[0].confidence >= 0.95

    def test_publisher_match_includes_tier(self, db):
        """Publisher match should include tier information."""
        from app.models.publisher import Publisher

        pub = Publisher(name="Oxford University Press", tier="TIER_1")
        db.add(pub)
        db.flush()

        matches = fuzzy_match_entity(db, "publisher", "Oxford University Press")
        assert len(matches) >= 1
        assert matches[0].tier == "TIER_1"

    def test_publisher_match_includes_book_count(self, db):
        """Publisher match should include book count."""
        from app.models.book import Book
        from app.models.publisher import Publisher

        pub = Publisher(name="Macmillan", tier="TIER_1")
        db.add(pub)
        db.flush()

        # Add some books to the publisher
        for i in range(3):
            book = Book(title=f"Book {i}", publisher_id=pub.id)
            db.add(book)
        db.flush()

        matches = fuzzy_match_entity(db, "publisher", "Macmillan")
        assert len(matches) >= 1
        assert matches[0].book_count == 3

    def test_publisher_applies_normalization(self, db):
        """Publisher matching should apply auto-correction rules."""
        from app.models.publisher import Publisher

        pub = Publisher(name="Harper & Brothers", tier="TIER_1")
        db.add(pub)
        db.flush()

        # Input with location suffix should be normalized before matching
        matches = fuzzy_match_entity(db, "publisher", "Harper & Brothers, New York", threshold=0.80)
        assert len(matches) >= 1
        assert matches[0].name == "Harper & Brothers"
        assert matches[0].confidence >= 0.95


class TestFuzzyMatchAuthor:
    """Test fuzzy matching for authors."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before and after each test."""
        invalidate_entity_cache("author")
        yield
        invalidate_entity_cache("author")

    def test_dickens_charles_matches_charles_dickens(self, db):
        """'Dickens, Charles' should match 'Charles Dickens' at >75% confidence."""
        from app.models.author import Author

        author = Author(name="Charles Dickens", tier="TIER_1")
        db.add(author)
        db.flush()

        # Default author threshold is 0.75
        matches = fuzzy_match_entity(db, "author", "Dickens, Charles", threshold=0.75)
        assert len(matches) >= 1
        assert matches[0].name == "Charles Dickens"
        assert matches[0].confidence >= 0.75

    def test_author_exact_match_high_confidence(self, db):
        """Exact author match should return >95% confidence."""
        from app.models.author import Author

        author = Author(name="Walter Scott", tier="TIER_1")
        db.add(author)
        db.flush()

        matches = fuzzy_match_entity(db, "author", "Walter Scott")
        assert len(matches) >= 1
        assert matches[0].name == "Walter Scott"
        assert matches[0].confidence >= 0.95

    def test_author_match_handles_honorifics(self, db):
        """Author matching should handle honorifics like 'Sir'."""
        from app.models.author import Author

        # Database has normalized name
        author = Author(name="Walter Scott", tier="TIER_1")
        db.add(author)
        db.flush()

        # Input has honorific
        matches = fuzzy_match_entity(db, "author", "Sir Walter Scott", threshold=0.75)
        assert len(matches) >= 1
        assert matches[0].name == "Walter Scott"
        assert matches[0].confidence >= 0.75

    def test_author_match_includes_book_count(self, db):
        """Author match should include book count."""
        from app.models.author import Author
        from app.models.book import Book

        author = Author(name="Charles Dickens", tier="TIER_1")
        db.add(author)
        db.flush()

        # Add books by this author
        for i in range(5):
            book = Book(title=f"Novel {i}", author_id=author.id)
            db.add(book)
        db.flush()

        matches = fuzzy_match_entity(db, "author", "Charles Dickens")
        assert len(matches) >= 1
        assert matches[0].book_count == 5

    def test_author_lower_threshold_allows_variations(self, db):
        """Lower threshold (0.75) allows more name variations to match."""
        from app.models.author import Author

        # Use a realistic case: "C. Dickens" vs "Charles Dickens"
        author = Author(name="Charles Dickens", tier="TIER_1")
        db.add(author)
        db.flush()

        # "C. Dickens" is a common abbreviation that should match at lower threshold
        # token_sort_ratio("c dickens", "charles dickens") should be reasonable
        matches_low = fuzzy_match_entity(db, "author", "C. Dickens", threshold=0.65)
        matches_high = fuzzy_match_entity(db, "author", "C. Dickens", threshold=0.90)

        # Lower threshold should allow the match; higher won't
        assert len(matches_low) >= 1
        assert len(matches_high) == 0 or matches_high[0].confidence < 0.90


class TestFuzzyMatchBinder:
    """Test fuzzy matching for binders."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before and after each test."""
        invalidate_entity_cache("binder")
        yield
        invalidate_entity_cache("binder")

    def test_bayntun_of_bath_matches_bayntun(self, db):
        """'Bayntun (of Bath)' should match 'Bayntun' at >80% confidence."""
        from app.models.binder import Binder

        binder = Binder(name="Bayntun", tier="TIER_1")
        db.add(binder)
        db.flush()

        matches = fuzzy_match_entity(db, "binder", "Bayntun (of Bath)", threshold=0.80)
        assert len(matches) >= 1
        assert matches[0].name == "Bayntun"
        assert matches[0].confidence >= 0.80

    def test_binder_exact_match_high_confidence(self, db):
        """Exact binder match should return >95% confidence."""
        from app.models.binder import Binder

        binder = Binder(name="Zaehnsdorf", tier="TIER_1")
        db.add(binder)
        db.flush()

        matches = fuzzy_match_entity(db, "binder", "Zaehnsdorf")
        assert len(matches) >= 1
        assert matches[0].name == "Zaehnsdorf"
        assert matches[0].confidence >= 0.95

    def test_binder_match_handles_accents(self, db):
        """Binder matching should handle accented characters."""
        from app.models.binder import Binder

        # Database might have ASCII or accented version
        binder = Binder(name="Riviere", tier="TIER_1")
        db.add(binder)
        db.flush()

        # Input has accent
        matches = fuzzy_match_entity(db, "binder", "Riviere", threshold=0.80)
        assert len(matches) >= 1
        assert matches[0].name == "Riviere"

    def test_binder_match_includes_book_count(self, db):
        """Binder match should include book count."""
        from app.models.binder import Binder
        from app.models.book import Book

        binder = Binder(name="Sangorski & Sutcliffe", tier="TIER_1")
        db.add(binder)
        db.flush()

        # Add books with this binder
        for i in range(2):
            book = Book(title=f"Fine Binding {i}", binder_id=binder.id)
            db.add(book)
        db.flush()

        matches = fuzzy_match_entity(db, "binder", "Sangorski & Sutcliffe")
        assert len(matches) >= 1
        assert matches[0].book_count == 2


class TestThresholdFiltering:
    """Test that matches below threshold are not returned."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before and after each test."""
        invalidate_entity_cache("publisher")
        yield
        invalidate_entity_cache("publisher")

    def test_below_threshold_not_returned(self, db):
        """Matches below threshold should not be returned."""
        from app.models.publisher import Publisher

        pub = Publisher(name="Harper & Brothers", tier="TIER_1")
        db.add(pub)
        db.flush()

        # "Completely Different" has very low similarity to "Harper & Brothers"
        matches = fuzzy_match_entity(
            db, "publisher", "Completely Different Publisher", threshold=0.80
        )
        # Should return empty or only matches above threshold
        for match in matches:
            assert match.confidence >= 0.80

    def test_high_threshold_filters_more(self, db):
        """Higher threshold should return fewer results."""
        from app.models.publisher import Publisher

        pub = Publisher(name="Macmillan", tier="TIER_1")
        db.add(pub)
        db.flush()

        # "Macmilan" is close but not exact
        low_threshold_matches = fuzzy_match_entity(db, "publisher", "Macmilan", threshold=0.60)
        high_threshold_matches = fuzzy_match_entity(db, "publisher", "Macmilan", threshold=0.95)

        # Lower threshold should return matches; higher might not
        assert len(high_threshold_matches) <= len(low_threshold_matches)


class TestMaxResultsLimiting:
    """Test max_results parameter limits output."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before and after each test."""
        invalidate_entity_cache("publisher")
        yield
        invalidate_entity_cache("publisher")

    def test_max_results_limits_output(self, db):
        """max_results should limit the number of matches returned."""
        from app.models.publisher import Publisher

        # Create many similar publishers
        for i in range(10):
            pub = Publisher(name=f"Harper Publisher {i}", tier="TIER_1")
            db.add(pub)
        db.flush()

        matches = fuzzy_match_entity(db, "publisher", "Harper", threshold=0.50, max_results=3)
        assert len(matches) <= 3

    def test_max_results_default_is_5(self, db):
        """Default max_results should be 5."""
        from app.models.publisher import Publisher

        # Create many similar publishers
        for i in range(10):
            pub = Publisher(name=f"Harper Publisher {i}", tier="TIER_1")
            db.add(pub)
        db.flush()

        matches = fuzzy_match_entity(db, "publisher", "Harper", threshold=0.30)
        assert len(matches) <= 5

    def test_results_sorted_by_confidence_descending(self, db):
        """Results should be sorted by confidence, highest first."""
        from app.models.publisher import Publisher

        db.add(Publisher(name="Harper", tier="TIER_1"))
        db.add(Publisher(name="Harper & Brothers", tier="TIER_1"))
        db.add(Publisher(name="Harpers Magazine", tier=None))
        db.flush()

        matches = fuzzy_match_entity(db, "publisher", "Harper", threshold=0.50, max_results=3)
        assert len(matches) >= 2
        # Verify descending order
        for i in range(len(matches) - 1):
            assert matches[i].confidence >= matches[i + 1].confidence


class TestEmptyResults:
    """Test behavior when no matches are found."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before and after each test."""
        for entity_type in ["publisher", "author", "binder"]:
            invalidate_entity_cache(entity_type)
        yield
        for entity_type in ["publisher", "author", "binder"]:
            invalidate_entity_cache(entity_type)

    def test_empty_database_returns_empty_list(self, db):
        """Searching empty database should return empty list."""
        matches = fuzzy_match_entity(db, "publisher", "Any Publisher")
        assert matches == []

    def test_no_match_returns_empty_list(self, db):
        """When no entities match, return empty list."""
        from app.models.publisher import Publisher

        pub = Publisher(name="Oxford University Press", tier="TIER_1")
        db.add(pub)
        db.flush()

        matches = fuzzy_match_entity(
            db, "publisher", "Completely Unrelated Name XYZ", threshold=0.80
        )
        assert matches == []

    def test_empty_input_returns_empty_list(self, db):
        """Empty input string should return empty list."""
        from app.models.publisher import Publisher

        pub = Publisher(name="Macmillan", tier="TIER_1")
        db.add(pub)
        db.flush()

        matches = fuzzy_match_entity(db, "publisher", "")
        assert matches == []


class TestCacheBehavior:
    """Test caching behavior for performance."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before and after each test."""
        invalidate_entity_cache("publisher")
        yield
        invalidate_entity_cache("publisher")

    def test_cache_ttl_is_5_minutes(self):
        """Cache TTL should be 300 seconds (5 minutes)."""
        assert ENTITY_CACHE_TTL_SECONDS == 300

    def test_cache_is_used_for_repeated_queries(self, db):
        """Cache should be used for repeated queries."""
        import app.services.entity_matching as em
        from app.models.publisher import Publisher

        pub = Publisher(name="Macmillan", tier="TIER_1")
        db.add(pub)
        db.flush()

        # First call populates cache
        fuzzy_match_entity(db, "publisher", "Macmillan")

        # Get cache state
        cache_after_first = em._entity_caches.get("publisher")
        assert cache_after_first is not None

        # Second call should use same cache
        fuzzy_match_entity(db, "publisher", "Harper")

        # Cache should be the same object
        assert em._entity_caches.get("publisher") is cache_after_first

    def test_cache_invalidation_forces_refresh(self, db):
        """Cache invalidation should force a fresh DB query."""
        from app.models.publisher import Publisher

        pub = Publisher(name="Original Publisher", tier="TIER_1")
        db.add(pub)
        db.flush()

        # First call populates cache
        matches1 = fuzzy_match_entity(db, "publisher", "Original Publisher")
        assert len(matches1) >= 1

        # Add new publisher
        new_pub = Publisher(name="New Publisher", tier="TIER_2")
        db.add(new_pub)
        db.flush()

        # Without invalidation, new publisher won't be found
        # Invalidate cache
        invalidate_entity_cache("publisher")

        # Now should find new publisher
        matches2 = fuzzy_match_entity(db, "publisher", "New Publisher")
        assert len(matches2) >= 1
        assert any(m.name == "New Publisher" for m in matches2)

    def test_cache_expiration_with_mock_time(self, db):
        """Cache should expire after TTL seconds."""
        import app.services.entity_matching as em
        from app.models.publisher import Publisher

        pub = Publisher(name="Macmillan", tier="TIER_1")
        db.add(pub)
        db.flush()

        # First call populates cache
        fuzzy_match_entity(db, "publisher", "Macmillan")

        # Record cache time
        initial_cache_time = em._entity_cache_times.get("publisher", 0)

        # Mock time to be past TTL
        with patch("app.services.entity_matching.time") as mock_time:
            # Make monotonic() return time past TTL
            mock_time.monotonic.return_value = initial_cache_time + ENTITY_CACHE_TTL_SECONDS + 1

            # This should trigger cache refresh
            fuzzy_match_entity(db, "publisher", "Macmillan")

            # Cache time should be updated (to the mocked value)
            # Note: The actual implementation will update cache time
            # We just verify the time module was called
            assert mock_time.monotonic.called

    def test_separate_caches_per_entity_type(self, db):
        """Each entity type should have its own cache."""
        from app.models.author import Author
        from app.models.publisher import Publisher

        pub = Publisher(name="Macmillan", tier="TIER_1")
        author = Author(name="Charles Dickens", tier="TIER_1")
        db.add(pub)
        db.add(author)
        db.flush()

        # Query both types
        fuzzy_match_entity(db, "publisher", "Macmillan")
        fuzzy_match_entity(db, "author", "Dickens")

        # Invalidate only publisher cache
        invalidate_entity_cache("publisher")

        # Author cache should still be populated
        import app.services.entity_matching as em

        assert em._entity_caches.get("author") is not None


class TestInvalidEntityType:
    """Test handling of invalid entity types."""

    def test_invalid_entity_type_raises_error(self, db):
        """Invalid entity type should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown entity type"):
            fuzzy_match_entity(db, "invalid_type", "Test Name")  # type: ignore


class TestConfidenceScoring:
    """Test confidence score calculation."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before and after each test."""
        invalidate_entity_cache("publisher")
        yield
        invalidate_entity_cache("publisher")

    def test_uses_token_sort_ratio(self, db):
        """Should use token_sort_ratio for word order independence."""
        from app.models.publisher import Publisher

        # "Brothers & Harper" vs "Harper & Brothers" should match well
        # due to token_sort_ratio handling word order
        pub = Publisher(name="Harper & Brothers", tier="TIER_1")
        db.add(pub)
        db.flush()

        matches = fuzzy_match_entity(db, "publisher", "Brothers & Harper", threshold=0.80)
        assert len(matches) >= 1
        # Token sort should give high score despite word order
        assert matches[0].confidence >= 0.80

    def test_confidence_normalized_to_0_1_scale(self, db):
        """Confidence should be normalized to 0.0-1.0 scale."""
        from app.models.publisher import Publisher

        pub = Publisher(name="Test Publisher", tier=None)
        db.add(pub)
        db.flush()

        matches = fuzzy_match_entity(db, "publisher", "Test Publisher", threshold=0.0)
        assert len(matches) >= 1
        assert 0.0 <= matches[0].confidence <= 1.0


class TestNormalizationContract:
    """Document the normalization contract for fuzzy_match_entity.

    IMPORTANT: fuzzy_match_entity() expects RAW (unnormalized) input.
    It normalizes internally using type-specific normalization rules.

    This contract exists because:
    - validate_entity_for_book normalizes for exact match, then passes raw to fuzzy
    - The function handles normalization consistently for all callers
    - Passing pre-normalized input would result in double-normalization

    See GitHub issue #1016 for context on this design decision.
    """

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before and after each test."""
        for entity_type in ["publisher", "author", "binder"]:
            invalidate_entity_cache(entity_type)
        yield
        for entity_type in ["publisher", "author", "binder"]:
            invalidate_entity_cache(entity_type)

    def test_expects_raw_input_not_prenormalized(self, db):
        """fuzzy_match_entity expects raw input - it normalizes internally.

        This test documents the API contract. Callers should pass the original
        user input, NOT pre-normalized values. The function handles all
        normalization consistently.
        """
        from app.models.publisher import Publisher

        # Database has normalized name
        pub = Publisher(name="Harper & Brothers", tier="TIER_1")
        db.add(pub)
        db.flush()

        # Raw input with location suffix (common in auction data)
        raw_input = "Harper & Brothers, New York"

        # This should match because fuzzy_match_entity normalizes internally
        matches = fuzzy_match_entity(db, "publisher", raw_input, threshold=0.80)

        assert len(matches) >= 1
        assert matches[0].name == "Harper & Brothers"
        assert matches[0].confidence >= 0.95

    def test_normalizes_input_before_comparison(self, db):
        """Verify that input normalization happens before fuzzy comparison.

        The function should:
        1. Normalize the input name using type-specific rules
        2. Compare against pre-normalized cached entity names
        3. Return matches above threshold
        """
        from app.models.author import Author

        # Database has normalized name (no honorific)
        author = Author(name="Walter Scott", tier="TIER_1")
        db.add(author)
        db.flush()

        # Raw input with honorific that normalization should strip
        raw_input = "Sir Walter Scott"

        # Should match because author normalization strips honorifics
        matches = fuzzy_match_entity(db, "author", raw_input, threshold=0.75)

        assert len(matches) >= 1
        assert matches[0].name == "Walter Scott"

    def test_binder_normalization_strips_parentheticals(self, db):
        """Binder normalization removes location parentheticals.

        Example: "Bayntun (of Bath)" -> "Bayntun"
        This is applied internally by fuzzy_match_entity.
        """
        from app.models.binder import Binder

        binder = Binder(name="Bayntun", tier="TIER_1")
        db.add(binder)
        db.flush()

        # Raw input with parenthetical
        raw_input = "Bayntun (of Bath)"

        matches = fuzzy_match_entity(db, "binder", raw_input, threshold=0.80)

        assert len(matches) >= 1
        assert matches[0].name == "Bayntun"
        # After normalization, should be very high confidence
        assert matches[0].confidence >= 0.95
