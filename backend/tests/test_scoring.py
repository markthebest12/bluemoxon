"""Scoring engine tests."""

from decimal import Decimal

from app.models.author import Author
from app.models.book import Book
from app.services.scoring import calculate_investment_grade


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
