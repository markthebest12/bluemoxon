"""Scoring engine tests."""

from decimal import Decimal

from app.models.author import Author
from app.models.book import Book
from app.services.scoring import (
    ScoreBreakdown,
    calculate_all_scores,
    calculate_all_scores_with_breakdown,
    calculate_collection_impact,
    calculate_collection_impact_breakdown,
    calculate_investment_grade,
    calculate_investment_grade_breakdown,
    calculate_strategic_fit,
    calculate_strategic_fit_breakdown,
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

    def test_negative_discount_returns_zero(self):
        """Overpaying (negative discount) should score 0."""
        score = calculate_investment_grade(
            purchase_price=Decimal("1200"),
            value_mid=Decimal("1000"),  # -20% "discount" (overpaying)
        )
        assert score == 0

    def test_severely_overpriced_returns_zero(self):
        """Severely overpriced (-88% discount) should score 0, not 5."""
        score = calculate_investment_grade(
            purchase_price=Decimal("528"),
            value_mid=Decimal("281"),  # -88% "discount" - paying nearly double
        )
        assert score == 0


class TestStrategicFit:
    """Tests for strategic fit calculation."""

    def test_tier_1_publisher_adds_35(self):
        """Tier 1 publisher should add 35 points."""
        score = calculate_strategic_fit(
            publisher_tier="TIER_1",
            binder_tier=None,
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
            binder_tier=None,
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
        )
        assert score == 15

    def test_tier_1_binder_adds_40(self):
        """Tier 1 binder should add 40 points."""
        score = calculate_strategic_fit(
            publisher_tier=None,
            binder_tier="TIER_1",
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
        )
        assert score == 40

    def test_tier_2_binder_adds_20(self):
        """Tier 2 binder should add 20 points."""
        score = calculate_strategic_fit(
            publisher_tier=None,
            binder_tier="TIER_2",
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
        )
        assert score == 20

    def test_double_tier_1_bonus_adds_15(self):
        """DOUBLE TIER 1 bonus when both publisher AND binder are Tier 1."""
        score = calculate_strategic_fit(
            publisher_tier="TIER_1",  # +35
            binder_tier="TIER_1",  # +40
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
        )
        # 35 (publisher) + 40 (binder) + 15 (DOUBLE TIER 1) = 90
        assert score == 90

    def test_no_double_tier_1_bonus_with_tier_2(self):
        """No DOUBLE TIER 1 bonus when one is Tier 2."""
        score = calculate_strategic_fit(
            publisher_tier="TIER_1",  # +35
            binder_tier="TIER_2",  # +20
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
        )
        # 35 (publisher) + 20 (binder) = 55, no bonus
        assert score == 55

    def test_victorian_era_adds_20(self):
        """Victorian era (1837-1901) should add 20 points."""
        score = calculate_strategic_fit(
            publisher_tier=None,
            binder_tier=None,
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
            binder_tier=None,
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
            binder_tier=None,
            year_start=None,
            is_complete=True,
            condition_grade=None,
            author_priority_score=0,
        )
        assert score == 15

    def test_good_condition_adds_15(self):
        """Good or better condition should add 15 points."""
        for grade in ["Fine", "VG+", "VG", "Very Good", "VG-", "Good+", "Good"]:
            score = calculate_strategic_fit(
                publisher_tier=None,
                binder_tier=None,
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
            binder_tier=None,
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=50,
        )
        assert score == 50

    def test_four_volume_no_penalty(self):
        """4-volume set should NOT subtract points (Issue #587)."""
        score = calculate_strategic_fit(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
            volume_count=4,
        )
        assert score == 0

    def test_five_plus_volume_no_penalty(self):
        """5+ volume set should NOT subtract points (Issue #587)."""
        score = calculate_strategic_fit(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
            volume_count=6,
        )
        assert score == 0

    def test_combined_factors(self):
        """All factors should combine additively."""
        score = calculate_strategic_fit(
            publisher_tier="TIER_1",  # +35
            binder_tier="TIER_1",  # +40 + 15 (DOUBLE TIER 1)
            year_start=1867,  # +20 (Victorian)
            is_complete=True,  # +15
            condition_grade="Very Good",  # +15
            author_priority_score=50,  # +50
            volume_count=4,  # 0 (noted but no penalty per Issue #587)
        )
        # 35 + 40 + 15 + 20 + 15 + 15 + 50 + 0 = 190
        assert score == 190


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

    def test_volume_count_no_longer_affects_collection_impact(self):
        """Volume penalty moved to strategic_fit - should not affect collection_impact."""
        score = calculate_collection_impact(
            author_book_count=0,
            is_duplicate=False,
            completes_set=False,
            volume_count=6,
        )
        # Volume penalty is now in strategic_fit, not here
        assert score == 30  # 30 (new author) only, no volume penalty


class TestCalculateAllScores:
    """Tests for full score calculation."""

    def test_returns_all_score_components(self):
        """Should return dict with all score components."""
        result = calculate_all_scores(
            purchase_price=Decimal("300"),
            value_mid=Decimal("1000"),
            publisher_tier="TIER_1",
            binder_tier=None,
            year_start=1867,
            is_complete=True,
            condition_grade="Very Good",
            author_priority_score=50,
            author_book_count=0,
            is_duplicate=False,
            completes_set=False,
            volume_count=3,
        )

        assert "investment_grade" in result
        assert "strategic_fit" in result
        assert "collection_impact" in result
        assert "overall_score" in result

    def test_overall_is_sum_of_components(self):
        """Overall score should be sum of components."""
        result = calculate_all_scores(
            purchase_price=Decimal("300"),
            value_mid=Decimal("1000"),  # 70% discount -> 100
            publisher_tier="TIER_1",  # +35
            binder_tier=None,
            year_start=1867,  # +20
            is_complete=True,  # +15
            condition_grade="Very Good",  # +15
            author_priority_score=0,  # +0
            author_book_count=0,  # +30
            is_duplicate=False,  # +0
            completes_set=False,  # +0
            volume_count=3,  # +0
        )

        expected_investment = 100  # 70% discount
        expected_strategic = 35 + 20 + 15 + 15  # 85
        expected_collection = 30  # new author
        expected_overall = expected_investment + expected_strategic + expected_collection

        assert result["investment_grade"] == expected_investment
        assert result["strategic_fit"] == expected_strategic
        assert result["collection_impact"] == expected_collection
        assert result["overall_score"] == expected_overall

    def test_binder_tier_affects_strategic_fit(self):
        """Binder tier should contribute to strategic fit score."""
        result = calculate_all_scores(
            purchase_price=Decimal("500"),
            value_mid=Decimal("1000"),  # 50% discount -> 70
            publisher_tier="TIER_1",  # +35
            binder_tier="TIER_1",  # +40 + 15 (DOUBLE TIER 1)
            year_start=1867,  # +20
            is_complete=True,  # +15
            condition_grade="VG",  # +15
            author_priority_score=0,
            author_book_count=0,  # +30
            is_duplicate=False,
            completes_set=False,
            volume_count=4,  # 0 (noted but no penalty per Issue #587)
        )

        # strategic_fit = 35 + 40 + 15 + 20 + 15 + 15 + 0 = 140
        assert result["strategic_fit"] == 140
        # collection_impact = 30 (new author)
        assert result["collection_impact"] == 30
        # overall = 70 + 140 + 30 = 240
        assert result["overall_score"] == 240


class TestScoreBreakdown:
    """Tests for ScoreBreakdown dataclass."""

    def test_score_breakdown_add_factor(self):
        """ScoreBreakdown should accumulate factors."""
        breakdown = ScoreBreakdown(score=50)
        breakdown.add("test_factor", 25, "Test reason")
        breakdown.add("another_factor", 25, "Another reason")

        assert len(breakdown.factors) == 2
        assert breakdown.factors[0].name == "test_factor"
        assert breakdown.factors[0].points == 25
        assert breakdown.factors[0].reason == "Test reason"

    def test_score_breakdown_to_dict(self):
        """ScoreBreakdown.to_dict() should return serializable dict."""
        breakdown = ScoreBreakdown(score=85)
        breakdown.add("publisher_tier", 35, "Tier 1 publisher (Smith Elder)")
        breakdown.add("era", 20, "Victorian era (1867)")

        result = breakdown.to_dict()

        assert result["score"] == 85
        assert len(result["factors"]) == 2
        assert result["factors"][0]["name"] == "publisher_tier"
        assert result["factors"][0]["points"] == 35
        assert result["factors"][0]["reason"] == "Tier 1 publisher (Smith Elder)"


class TestInvestmentGradeBreakdown:
    """Tests for investment grade breakdown function."""

    def test_investment_grade_breakdown_with_discount(self):
        """Should include discount percentage in reason."""
        breakdown = calculate_investment_grade_breakdown(
            purchase_price=Decimal("100"),
            value_mid=Decimal("200"),
        )

        assert breakdown.score == 70  # 50% discount = 70 points
        assert len(breakdown.factors) == 1
        assert breakdown.factors[0].name == "discount"
        assert "50.0% discount" in breakdown.factors[0].reason
        assert "$100" in breakdown.factors[0].reason
        assert "$200" in breakdown.factors[0].reason

    def test_investment_grade_breakdown_missing_data(self):
        """Should explain missing data."""
        breakdown = calculate_investment_grade_breakdown(
            purchase_price=None,
            value_mid=Decimal("200"),
        )

        assert breakdown.score == 0
        assert breakdown.factors[0].name == "missing_data"
        assert "Missing" in breakdown.factors[0].reason


class TestStrategicFitBreakdown:
    """Tests for strategic fit breakdown function."""

    def test_strategic_fit_breakdown_all_factors(self):
        """Should include all scoring factors with names."""
        breakdown = calculate_strategic_fit_breakdown(
            publisher_tier="TIER_1",
            binder_tier="TIER_1",
            year_start=1867,
            is_complete=True,
            condition_grade="Very Good",
            author_priority_score=50,
            volume_count=4,
            author_name="George Eliot",
            publisher_name="Smith Elder",
            binder_name="Zaehnsdorf",
        )

        # Check total score: 35 + 40 + 15 (DOUBLE) + 20 + 15 + 15 + 50 + 0 = 190 (Issue #587: no volume penalty)
        assert breakdown.score == 190

        # Check factors include entity names
        factors_dict = {f.name: f for f in breakdown.factors}

        assert "publisher_tier" in factors_dict
        assert "Smith Elder" in factors_dict["publisher_tier"].reason

        assert "binder_tier" in factors_dict
        assert "Zaehnsdorf" in factors_dict["binder_tier"].reason

        assert "double_tier_1" in factors_dict
        assert factors_dict["double_tier_1"].points == 15

        assert "era" in factors_dict
        assert "Victorian" in factors_dict["era"].reason
        assert "1867" in factors_dict["era"].reason

        # Issue #587: volume_count with 0 points instead of volume_penalty with -10
        assert "volume_count" in factors_dict
        assert factors_dict["volume_count"].points == 0

        assert "author_priority" in factors_dict
        assert "George Eliot" in factors_dict["author_priority"].reason

    def test_strategic_fit_breakdown_non_priority_author(self):
        """Should explain non-priority author."""
        breakdown = calculate_strategic_fit_breakdown(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
            author_name="Unknown Author",
        )

        factors_dict = {f.name: f for f in breakdown.factors}
        assert "author_priority" in factors_dict
        assert factors_dict["author_priority"].points == 0
        assert "not a priority author" in factors_dict["author_priority"].reason

    def test_strategic_fit_breakdown_binder_tier(self):
        """Should include binder tier in breakdown."""
        breakdown = calculate_strategic_fit_breakdown(
            publisher_tier=None,
            binder_tier="TIER_1",
            year_start=None,
            is_complete=False,
            condition_grade=None,
            author_priority_score=0,
            binder_name="Rivière",
        )

        factors_dict = {f.name: f for f in breakdown.factors}
        assert "binder_tier" in factors_dict
        assert factors_dict["binder_tier"].points == 40
        assert "Rivière" in factors_dict["binder_tier"].reason


class TestCollectionImpactBreakdown:
    """Tests for collection impact breakdown function."""

    def test_collection_impact_breakdown_new_author(self):
        """Should explain new author bonus."""
        breakdown = calculate_collection_impact_breakdown(
            author_book_count=0,
            is_duplicate=False,
            completes_set=False,
            volume_count=1,
            author_name="Charles Darwin",
        )

        assert breakdown.score == 30
        factors_dict = {f.name: f for f in breakdown.factors}
        assert "author_presence" in factors_dict
        assert factors_dict["author_presence"].points == 30
        assert "New author" in factors_dict["author_presence"].reason
        assert "Charles Darwin" in factors_dict["author_presence"].reason

    def test_collection_impact_breakdown_duplicate_penalty(self):
        """Should explain duplicate penalty with title."""
        breakdown = calculate_collection_impact_breakdown(
            author_book_count=5,
            is_duplicate=True,
            completes_set=False,
            volume_count=1,
            author_name="Charles Dickens",
            duplicate_title="A Tale of Two Cities",
        )

        factors_dict = {f.name: f for f in breakdown.factors}
        assert "duplicate" in factors_dict
        assert factors_dict["duplicate"].points == -40
        assert "A Tale of Two Cities" in factors_dict["duplicate"].reason

    def test_collection_impact_breakdown_no_volume_penalty(self):
        """Volume penalty moved to strategic_fit - should not appear in collection_impact."""
        breakdown = calculate_collection_impact_breakdown(
            author_book_count=0,
            is_duplicate=False,
            completes_set=False,
            volume_count=8,
        )

        # Volume penalty is now in strategic_fit_breakdown, not here
        factors_dict = {f.name: f for f in breakdown.factors}
        assert "volume_penalty" not in factors_dict
        # Score should be 30 (new author) only
        assert breakdown.score == 30


class TestCalculateAllScoresWithBreakdown:
    """Tests for combined breakdown function."""

    def test_full_breakdown_structure(self):
        """Should return scores and nested breakdown dict."""
        result = calculate_all_scores_with_breakdown(
            purchase_price=Decimal("100"),
            value_mid=Decimal("500"),
            publisher_tier="TIER_1",
            binder_tier=None,
            year_start=1850,
            is_complete=True,
            condition_grade="Very Good",
            author_priority_score=30,
            author_book_count=0,
            is_duplicate=False,
            completes_set=False,
            volume_count=1,
            author_name="Thomas Hardy",
            publisher_name="Macmillan",
        )

        # Check top-level scores
        assert "investment_grade" in result
        assert "strategic_fit" in result
        assert "collection_impact" in result
        assert "overall_score" in result

        # Check breakdown nested structure
        assert "breakdown" in result
        assert "investment_grade" in result["breakdown"]
        assert "strategic_fit" in result["breakdown"]
        assert "collection_impact" in result["breakdown"]

        # Check each breakdown has score and factors
        for component in ["investment_grade", "strategic_fit", "collection_impact"]:
            assert "score" in result["breakdown"][component]
            assert "factors" in result["breakdown"][component]
            assert isinstance(result["breakdown"][component]["factors"], list)

    def test_breakdown_factors_match_scores(self):
        """Breakdown scores should match top-level scores."""
        result = calculate_all_scores_with_breakdown(
            purchase_price=Decimal("150"),
            value_mid=Decimal("300"),
            publisher_tier="TIER_2",
            binder_tier=None,
            year_start=1820,
            is_complete=False,
            condition_grade="Good",
            author_priority_score=0,
            author_book_count=2,
            is_duplicate=False,
            completes_set=True,
            volume_count=3,
        )

        assert result["investment_grade"] == result["breakdown"]["investment_grade"]["score"]
        assert result["strategic_fit"] == result["breakdown"]["strategic_fit"]["score"]
        assert result["collection_impact"] == result["breakdown"]["collection_impact"]["score"]
