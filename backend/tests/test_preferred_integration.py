"""Integration tests for preferred entity scoring bonus.

These tests verify that the preferred bonus flows through the entire
scoring chain - from model attributes to the final quality score.
"""

from app.models import Author, Binder, Book, Publisher
from app.services.tiered_scoring import calculate_quality_score


class TestPreferredEntityIntegration:
    """Test that preferred entities add +10 to quality score through full call chain."""

    def test_preferred_author_from_model_adds_bonus(self, db):
        """Preferred author attribute flows to quality score calculation."""
        # Create preferred author
        author = Author(name="Jane Austen", preferred=True)
        db.add(author)
        db.commit()

        # Create book with preferred author
        book = Book(title="Pride and Prejudice", author_id=author.id)
        db.add(book)
        db.commit()
        db.refresh(book)

        # Calculate score passing preferred value from model
        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
            author_preferred=book.author.preferred if book.author else False,
            publisher_preferred=False,
            binder_preferred=False,
        )

        # Base score with only preferred author = 10
        assert score == 10

    def test_preferred_publisher_from_model_adds_bonus(self, db):
        """Preferred publisher attribute flows to quality score calculation."""
        publisher = Publisher(name="Bentley", preferred=True)
        db.add(publisher)
        db.commit()

        book = Book(title="Test Book", publisher_id=publisher.id)
        db.add(book)
        db.commit()
        db.refresh(book)

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
            author_preferred=False,
            publisher_preferred=book.publisher.preferred if book.publisher else False,
            binder_preferred=False,
        )

        assert score == 10

    def test_preferred_binder_from_model_adds_bonus(self, db):
        """Preferred binder attribute flows to quality score calculation."""
        binder = Binder(name="Riviere", preferred=True)
        db.add(binder)
        db.commit()

        book = Book(title="Test Book", binder_id=binder.id)
        db.add(book)
        db.commit()
        db.refresh(book)

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
            author_preferred=False,
            publisher_preferred=False,
            binder_preferred=book.binder.preferred if book.binder else False,
        )

        assert score == 10

    def test_all_three_preferred_from_models_add_30(self, db):
        """All three preferred entities from models add +30 total."""
        author = Author(name="Jane Austen", preferred=True)
        publisher = Publisher(name="Bentley", preferred=True)
        binder = Binder(name="Riviere", preferred=True)
        db.add_all([author, publisher, binder])
        db.commit()

        book = Book(
            title="Pride and Prejudice",
            author_id=author.id,
            publisher_id=publisher.id,
            binder_id=binder.id,
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
            author_preferred=book.author.preferred if book.author else False,
            publisher_preferred=book.publisher.preferred if book.publisher else False,
            binder_preferred=book.binder.preferred if book.binder else False,
        )

        assert score == 30

    def test_model_preferred_default_is_false(self, db):
        """Model preferred field defaults to False."""
        author = Author(name="Unknown Author")
        publisher = Publisher(name="Unknown Press")
        binder = Binder(name="Unknown Binder")
        db.add_all([author, publisher, binder])
        db.commit()

        # Verify defaults are False
        assert author.preferred is False
        assert publisher.preferred is False
        assert binder.preferred is False

        book = Book(
            title="Test Book",
            author_id=author.id,
            publisher_id=publisher.id,
            binder_id=binder.id,
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        score = calculate_quality_score(
            publisher_tier=None,
            binder_tier=None,
            year_start=None,
            condition_grade=None,
            is_complete=False,
            author_priority_score=0,
            volume_count=1,
            is_duplicate=False,
            author_preferred=book.author.preferred if book.author else False,
            publisher_preferred=book.publisher.preferred if book.publisher else False,
            binder_preferred=book.binder.preferred if book.binder else False,
        )

        # No bonus from non-preferred entities
        assert score == 0
