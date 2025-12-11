"""Scoring engine tests."""

from app.models.author import Author
from app.models.book import Book


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
