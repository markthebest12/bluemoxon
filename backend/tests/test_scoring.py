"""Scoring engine tests."""

from decimal import Decimal

from app.models.author import Author
from app.models.book import Book
from app.services.scoring import (
    calculate_collection_impact,
    calculate_investment_grade,
    calculate_strategic_fit,
    is_duplicate_title,
)


class TestBookScoreFields:
    """Tests for book score fields."""

    def test_book_has_score_fields(self, db):
        """Book model should have all score fields."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()
        db.refresh(book)

        assert hasattr(book, "investment_grade")
        assert hasattr(book, "strategic_fit")
        assert hasattr(book, "collection_impact")
        assert hasattr(book, "overall_score")
        assert hasattr(book, "scores_calculated_at")

    def test_book_score_fields_default_to_none(self, db):
        """Score fields should default to None."""
        book = Book(title="Test Book")
        db.add(book)
        db.commit()
        db.refresh(book)

        assert book.investment_grade is None
        assert book.strategic_fit is None
        assert book.collection_impact is None
        assert book.overall_score is None
        assert book.scores_calculated_at is None


class TestAuthorPriorityScore:
    """Tests for author priority_score field."""

    def test_author_has_priority_score_field(self, db):
        """Author model should have priority_score field defaulting to 0."""
        author = Author(name="Test Author")
        db.add(author)
        db.commit()
        db.refresh(author)

        assert hasattr(author, "priority_score")
        assert author.priority_score == 0

    def test_author_priority_score_can_be_set(self, db):
        """Author priority_score can be set to custom value."""
        author = Author(name="Thomas Hardy", priority_score=50)
        db.add(author)
        db.commit()
        db.refresh(author)

        assert author.priority_score == 50


class TestInvestmentGrade:
    """Tests for investment grade calculation."""

    def test_exceptional_discount_70_plus(self):
        """70%+ discount should score 100."""
        score = calculate_investment_grade(
            purchase_price=Decimal("100"),
            value_mid=Decimal("400"),  # 75% discount
        )
        assert score == 100

    def test_strong_discount_60_to_69(self):
        """60-69% discount should score 85."""
        score = calculate_investment_grade(
            purchase_price=Decimal("350"),
            value_mid=Decimal("1000"),  # 65% discount
        )
        assert score == 85

    def test_good_discount_50_to_59(self):
        """50-59% discount should score 70."""
        score = calculate_investment_grade(
            purchase_price=Decimal("450"),
            value_mid=Decimal("1000"),  # 55% discount
        )
        assert score == 70

    def test_meets_minimum_40_to_49(self):
        """40-49% discount should score 55."""
        score = calculate_investment_grade(
            purchase_price=Decimal("550"),
            value_mid=Decimal("1000"),  # 45% discount
        )
        assert score == 55

    def test_below_target_30_to_39(self):
        """30-39% discount should score 35."""
        score = calculate_investment_grade(
            purchase_price=Decimal("650"),
            value_mid=Decimal("1000"),  # 35% discount
        )
        assert score == 35

    def test_marginal_20_to_29(self):
        """20-29% discount should score 20."""
        score = calculate_investment_grade(
            purchase_price=Decimal("750"),
            value_mid=Decimal("1000"),  # 25% discount
        )
        assert score == 20

    def test_poor_under_20(self):
        """Under 20% discount should score 5."""
        score = calculate_investment_grade(
            purchase_price=Decimal("900"),
            value_mid=Decimal("1000"),  # 10% discount
        )
        assert score == 5

    def test_no_price_data_returns_zero(self):
        """Missing price data should score 0."""
        assert calculate_investment_grade(None, Decimal("1000")) == 0
        assert calculate_investment_grade(Decimal("100"), None) == 0
        assert calculate_investment_grade(None, None) == 0

    def test_negative_discount_returns_five(self):
        """Overpaying (negative discount) should score 5."""
        score = calculate_investment_grade(
            purchase_price=Decimal("1200"),
            value_mid=Decimal("1000"),  # -20% "discount"
        )
        assert score == 5


class TestStrategicFit:
    """Tests for strategic fit calculation."""

    def test_tier_1_publisher_adds_35(self):
        """Tier 1 publisher should add 35 points."""
        score = calculate_strategic_fit(
            publisher_tier="TIER_1",
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
        )
        assert score == 35

    def test_tier_2_publisher_adds_15(self):
        """Tier 2 publisher should add 15 points."""
        score = calculate_strategic_fit(
            publisher_tier="TIER_2",
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
        )
        assert score == 15

    def test_victorian_era_adds_20(self):
        """Victorian era (1837-1901) should add 20 points."""
        score = calculate_strategic_fit(
            publisher_tier=None,
            year_start=1867,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
        )
        assert score == 20

    def test_romantic_era_adds_20(self):
        """Romantic era (1800-1836) should add 20 points."""
        score = calculate_strategic_fit(
            publisher_tier=None,
            year_start=1820,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
        )
        assert score == 20

    def test_complete_set_adds_15(self):
        """Complete set should add 15 points."""
        score = calculate_strategic_fit(
            publisher_tier=None,
            year_start=None,
            is_complete=True,
            condition_grade=None,
            author_priority_score=0,
        )
        assert score == 15

    def test_good_condition_adds_15(self):
        """Good or better condition should add 15 points."""
        for grade in ["Fine", "Very Good", "Good"]:
            score = calculate_strategic_fit(
                publisher_tier=None,
                year_start=None,
                is_complete=False,
                condition_grade=grade,
                author_priority_score=0,
            )
            assert score == 15, f"Failed for grade: {grade}"

    def test_author_priority_added(self):
        """Author priority score should be added directly."""
        score = calculate_strategic_fit(
            publisher_tier=None,
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=50,
        )
        assert score == 50

    def test_combined_factors(self):
        """All factors should combine additively."""
        score = calculate_strategic_fit(
            publisher_tier="TIER_1",  # +35
            year_start=1867,  # +20 (Victorian)
            is_complete=True,  # +15
            condition_grade="Very Good",  # +15
            author_priority_score=50,  # +50
        )
        assert score == 135  # 35 + 20 + 15 + 15 + 50


class TestDuplicateDetection:
    """Tests for fuzzy title matching."""

    def test_exact_match_is_duplicate(self):
        """Exact title match should be detected as duplicate."""
        assert is_duplicate_title("Essays of Elia", "Essays of Elia") is True

    def test_case_insensitive_match(self):
        """Case differences should still match."""
        assert is_duplicate_title("Essays of Elia", "essays of elia") is True

    def test_article_differences_match(self):
        """Titles differing only by articles should match."""
        assert is_duplicate_title("The Water-Babies", "Water-Babies") is True

    def test_different_titles_not_duplicate(self):
        """Different titles should not match."""
        assert is_duplicate_title("Complete Works", "Poetical Works") is False

    def test_similar_but_different_not_duplicate(self):
        """Similar but distinct titles should not match."""
        assert is_duplicate_title("Essays of Elia", "Last Essays of Elia") is False


class TestCollectionImpact:
    """Tests for collection impact calculation."""

    def test_new_author_adds_30(self):
        """New author to collection should add 30 points."""
        score = calculate_collection_impact(
            author_book_count=0,
            is_duplicate=False,
            completes_set=False,
            volume_count=1,
        )
        assert score == 30

    def test_fills_author_gap_adds_15(self):
        """Second book by author should add 15 points."""
        score = calculate_collection_impact(
            author_book_count=1,
            is_duplicate=False,
            completes_set=False,
            volume_count=1,
        )
        assert score == 15

    def test_third_book_no_bonus(self):
        """Third+ book by author gets no bonus."""
        score = calculate_collection_impact(
            author_book_count=2,
            is_duplicate=False,
            completes_set=False,
            volume_count=1,
        )
        assert score == 0

    def test_duplicate_subtracts_40(self):
        """Duplicate title should subtract 40 points."""
        score = calculate_collection_impact(
            author_book_count=0,
            is_duplicate=True,
            completes_set=False,
            volume_count=1,
        )
        assert score == -10  # 30 (new author) - 40 (duplicate)

    def test_completes_set_adds_25(self):
        """Completing a set should add 25 points."""
        score = calculate_collection_impact(
            author_book_count=2,
            is_duplicate=False,
            completes_set=True,
            volume_count=1,
        )
        assert score == 25

    def test_large_set_subtracts_20(self):
        """5+ volume set should subtract 20 points."""
        score = calculate_collection_impact(
            author_book_count=0,
            is_duplicate=False,
            completes_set=False,
            volume_count=6,
        )
        assert score == 10  # 30 (new author) - 20 (large set)
