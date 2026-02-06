"""Tests for Wikidata candidate scoring module."""

import pytest

from app.utils.wikidata_scoring import (
    name_similarity,
    occupation_match,
    score_candidate,
    works_overlap,
    year_overlap,
)

# --- Name similarity tests ---


class TestNameSimilarity:
    """Test name_similarity function."""

    def test_full_name_vs_extended_name(self):
        """Charles Dickens vs Charles John Huffam Dickens -> high similarity."""
        score = name_similarity("Charles Dickens", "Charles John Huffam Dickens")
        assert score >= 0.8, f"Expected >= 0.8, got {score}"

    def test_identical_names(self):
        """Identical names should return 1.0."""
        assert name_similarity("Charles Dickens", "Charles Dickens") == 1.0

    def test_completely_different_names(self):
        """Unrelated names should return low similarity."""
        score = name_similarity("Charles Dickens", "John Smith")
        assert score <= 0.1, f"Expected <= 0.1, got {score}"

    def test_empty_strings(self):
        """Empty strings should return 0.0."""
        assert name_similarity("", "Charles Dickens") == 0.0
        assert name_similarity("Charles Dickens", "") == 0.0
        assert name_similarity("", "") == 0.0

    def test_single_name_match(self):
        """Single matching token should give partial score."""
        score = name_similarity("Dickens", "Charles Dickens")
        assert score == 1.0  # 1/min(1,2) = 1.0

    def test_case_insensitive(self):
        """Name matching should be case-insensitive."""
        assert name_similarity("charles dickens", "CHARLES DICKENS") == 1.0


# --- Year overlap tests ---


class TestYearOverlap:
    """Test year_overlap function."""

    def test_exact_birth_and_death(self):
        """Exact match on both birth and death years -> 1.0."""
        score = year_overlap(1812, 1870, 1812, 1870)
        assert score == 1.0

    def test_one_exact_match(self):
        """One exact match -> 0.5."""
        score = year_overlap(1812, 1870, 1812, None)
        assert score == 0.5

    def test_close_years(self):
        """Within +/-5 years -> 0.3 per year."""
        # Birth off by 3, death off by 2 -> both close -> 0.3 + 0.3 = 0.6
        score = year_overlap(1812, 1870, 1815, 1868)
        assert score == pytest.approx(0.6)

    def test_no_match(self):
        """No matching years -> 0.0."""
        score = year_overlap(1812, 1870, 1950, 2020)
        assert score == 0.0

    def test_all_none(self):
        """All None years -> 0.0."""
        score = year_overlap(None, None, None, None)
        assert score == 0.0

    def test_entity_has_years_candidate_none(self):
        """Entity has years but candidate doesn't -> 0.0."""
        score = year_overlap(1812, 1870, None, None)
        assert score == 0.0

    def test_exact_birth_close_death(self):
        """Exact birth + close death -> 0.5 + 0.3 = 0.8."""
        score = year_overlap(1812, 1870, 1812, 1873)
        assert score == pytest.approx(0.8)

    def test_close_birth_exact_death(self):
        """Close birth + exact death -> 0.3 + 0.5 = 0.8."""
        score = year_overlap(1812, 1870, 1815, 1870)
        assert score == pytest.approx(0.8)

    def test_score_capped_at_one(self):
        """Score should never exceed 1.0."""
        # Exact birth + exact death = 1.0 (not via individual path)
        score = year_overlap(1812, 1870, 1812, 1870)
        assert score <= 1.0


# --- Works overlap tests ---


class TestWorksOverlap:
    """Test works_overlap function."""

    def test_matching_titles(self):
        """Shared titles should produce positive score."""
        entity = ["Oliver Twist", "A Tale of Two Cities", "David Copperfield"]
        candidate = ["Oliver Twist", "David Copperfield", "Great Expectations"]
        score = works_overlap(entity, candidate)
        # 2 shared out of 4 unique -> 0.5
        assert score == pytest.approx(0.5)

    def test_no_overlap(self):
        """No shared titles -> 0.0."""
        score = works_overlap(["Oliver Twist"], ["Great Expectations"])
        assert score == 0.0

    def test_empty_lists(self):
        """Empty lists -> 0.0."""
        assert works_overlap([], []) == 0.0
        assert works_overlap(["Book A"], []) == 0.0
        assert works_overlap([], ["Book A"]) == 0.0

    def test_case_insensitive(self):
        """Title matching should be case-insensitive."""
        score = works_overlap(["oliver twist"], ["Oliver Twist"])
        assert score == 1.0


# --- Occupation match tests ---


class TestOccupationMatch:
    """Test occupation_match function."""

    def test_writer_occupation(self):
        """Writer occupation -> 1.0 (weight controls contribution)."""
        assert occupation_match(["writer"]) == 1.0

    def test_novelist_occupation(self):
        """Novelist occupation -> 1.0."""
        assert occupation_match(["novelist"]) == 1.0

    def test_publisher_occupation(self):
        """Publisher occupation -> 1.0."""
        assert occupation_match(["publisher"]) == 1.0

    def test_bookbinder_occupation(self):
        """Bookbinder occupation -> 1.0."""
        assert occupation_match(["bookbinder"]) == 1.0

    def test_irrelevant_occupation(self):
        """Irrelevant occupation -> 0.0."""
        assert occupation_match(["politician"]) == 0.0

    def test_empty_occupations(self):
        """No occupations -> 0.0."""
        assert occupation_match([]) == 0.0

    def test_mixed_occupations(self):
        """Mix of relevant and irrelevant -> 1.0."""
        assert occupation_match(["politician", "novelist"]) == 1.0


# --- Combined scoring tests ---


class TestScoreCandidate:
    """Test score_candidate combined scoring."""

    def test_charles_dickens_high_score(self):
        """Known Victorian author Charles Dickens with matching data -> score > 0.7."""
        score = score_candidate(
            entity_name="Charles Dickens",
            entity_birth=1812,
            entity_death=1870,
            entity_book_titles=["Oliver Twist", "A Tale of Two Cities", "David Copperfield"],
            candidate_label="Charles John Huffam Dickens",
            candidate_birth=1812,
            candidate_death=1870,
            candidate_works=["Oliver Twist", "David Copperfield", "Great Expectations"],
            candidate_occupations=["novelist", "writer"],
        )
        assert score > 0.7, f"Dickens score {score} should be > 0.7"

    def test_robert_browning_high_score(self):
        """Robert Browning with matching Wikidata candidate -> score > 0.7."""
        score = score_candidate(
            entity_name="Robert Browning",
            entity_birth=1812,
            entity_death=1889,
            entity_book_titles=["The Ring and the Book"],
            candidate_label="Robert Browning",
            candidate_birth=1812,
            candidate_death=1889,
            candidate_works=["The Ring and the Book", "Men and Women"],
            candidate_occupations=["poet", "playwright"],
        )
        assert score > 0.7, f"Browning score {score} should be > 0.7"

    def test_charles_darwin_high_score(self):
        """Charles Darwin with matching Wikidata candidate -> score > 0.7."""
        score = score_candidate(
            entity_name="Charles Darwin",
            entity_birth=1809,
            entity_death=1882,
            entity_book_titles=["On the Origin of Species"],
            candidate_label="Charles Robert Darwin",
            candidate_birth=1809,
            candidate_death=1882,
            candidate_works=["On the Origin of Species", "The Descent of Man"],
            candidate_occupations=["naturalist", "author"],
        )
        assert score > 0.7, f"Darwin score {score} should be > 0.7"

    def test_wrong_match_rejected(self):
        """Same name but wrong dates (born 1950) -> score < 0.7."""
        score = score_candidate(
            entity_name="Charles Dickens",
            entity_birth=1812,
            entity_death=1870,
            entity_book_titles=["Oliver Twist", "A Tale of Two Cities"],
            candidate_label="Charles Dickens",
            candidate_birth=1950,
            candidate_death=None,
            candidate_works=[],
            candidate_occupations=["journalist"],
        )
        assert score < 0.7, f"Wrong Dickens score {score} should be < 0.7"

    def test_partial_match_below_threshold(self):
        """Right name, no dates, no works overlap -> score < 0.7."""
        score = score_candidate(
            entity_name="Charles Dickens",
            entity_birth=1812,
            entity_death=1870,
            entity_book_titles=["Oliver Twist"],
            candidate_label="Charles Dickens",
            candidate_birth=None,
            candidate_death=None,
            candidate_works=[],
            candidate_occupations=[],
        )
        assert score < 0.7, f"Partial match score {score} should be < 0.7"

    def test_custom_weights(self):
        """Custom weights should be applied correctly."""
        # Weight only name at 1.0, everything else at 0.0
        score = score_candidate(
            entity_name="Charles Dickens",
            entity_birth=1812,
            entity_death=1870,
            entity_book_titles=[],
            candidate_label="Charles Dickens",
            candidate_birth=None,
            candidate_death=None,
            candidate_works=[],
            candidate_occupations=[],
            weights={"name": 1.0, "years": 0.0, "works": 0.0, "occupation": 0.0},
        )
        assert score == pytest.approx(1.0)

    def test_score_between_zero_and_one(self):
        """Score should always be between 0 and 1."""
        score = score_candidate(
            entity_name="Test Author",
            entity_birth=1800,
            entity_death=1850,
            entity_book_titles=["Book A"],
            candidate_label="Test Author",
            candidate_birth=1800,
            candidate_death=1850,
            candidate_works=["Book A"],
            candidate_occupations=["writer"],
        )
        assert 0.0 <= score <= 1.0
