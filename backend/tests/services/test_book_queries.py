"""Tests for book query helpers."""

from app.enums import OWNED_STATUSES, BookStatus
from app.models import Author, Book
from app.services.book_queries import get_other_books_by_author


class TestGetOtherBooksByAuthor:
    """Tests for get_other_books_by_author helper."""

    def test_returns_empty_when_no_author(self, db):
        """Books without author_id should return empty list."""
        book = Book(title="Orphan Book", status=BookStatus.ON_HAND)
        db.add(book)
        db.commit()

        result = get_other_books_by_author(book, db)
        assert result == []

    def test_returns_owned_books_by_same_author(self, db):
        """Should return ON_HAND and IN_TRANSIT books by same author."""
        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        book1 = Book(title="Book 1", author_id=author.id, status=BookStatus.ON_HAND)
        book2 = Book(title="Book 2", author_id=author.id, status=BookStatus.IN_TRANSIT)
        book3 = Book(title="Book 3", author_id=author.id, status=BookStatus.EVALUATING)
        db.add_all([book1, book2, book3])
        db.commit()

        result = get_other_books_by_author(book1, db, owned_only=True)

        assert len(result) == 1
        assert book2 in result
        assert book3 not in result

    def test_excludes_self(self, db):
        """Should not include the book itself in results."""
        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        book = Book(title="Only Book", author_id=author.id, status=BookStatus.ON_HAND)
        db.add(book)
        db.commit()

        result = get_other_books_by_author(book, db)

        assert book not in result
        assert result == []

    def test_owned_only_false_returns_all_statuses(self, db):
        """With owned_only=False, should return books of any status."""
        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        book1 = Book(title="Book 1", author_id=author.id, status=BookStatus.ON_HAND)
        book2 = Book(title="Book 2", author_id=author.id, status=BookStatus.EVALUATING)
        book3 = Book(title="Book 3", author_id=author.id, status=BookStatus.REMOVED)
        db.add_all([book1, book2, book3])
        db.commit()

        result = get_other_books_by_author(book1, db, owned_only=False)

        assert len(result) == 2
        assert book2 in result
        assert book3 in result

    def test_excludes_books_by_different_author(self, db):
        """Should not return books by different authors."""
        author1 = Author(name="Author 1")
        author2 = Author(name="Author 2")
        db.add_all([author1, author2])
        db.flush()

        book1 = Book(title="Book 1", author_id=author1.id, status=BookStatus.ON_HAND)
        book2 = Book(title="Book 2", author_id=author2.id, status=BookStatus.ON_HAND)
        db.add_all([book1, book2])
        db.commit()

        result = get_other_books_by_author(book1, db)

        assert book2 not in result


class TestOwnedStatusesSqlAlchemyIntegration:
    """Integration tests verifying OWNED_STATUSES works with SQLAlchemy."""

    def test_owned_statuses_works_in_sqlalchemy_in_query(self, db):
        """Verify OWNED_STATUSES enum values work correctly in .in_() queries."""
        book_on_hand = Book(title="On Hand", status=BookStatus.ON_HAND)
        book_in_transit = Book(title="In Transit", status=BookStatus.IN_TRANSIT)
        book_evaluating = Book(title="Evaluating", status=BookStatus.EVALUATING)
        book_removed = Book(title="Removed", status=BookStatus.REMOVED)
        db.add_all([book_on_hand, book_in_transit, book_evaluating, book_removed])
        db.commit()

        result = db.query(Book).filter(Book.status.in_(OWNED_STATUSES)).all()

        assert len(result) == 2
        assert book_on_hand in result
        assert book_in_transit in result
        assert book_evaluating not in result
        assert book_removed not in result

    def test_owned_statuses_matches_string_storage(self, db):
        """Verify StrEnum values match what's stored in the database."""
        book = Book(title="Test", status=BookStatus.ON_HAND)
        db.add(book)
        db.commit()

        # Query using raw string to verify DB stores string value
        result = db.query(Book).filter(Book.status == "ON_HAND").first()
        assert result is not None
        assert result.id == book.id

        # Query using enum to verify enum comparison works
        result = db.query(Book).filter(Book.status == BookStatus.ON_HAND).first()
        assert result is not None
        assert result.id == book.id

    def test_owned_statuses_is_immutable_tuple(self):
        """Verify OWNED_STATUSES is a tuple (immutable) not a list."""
        assert isinstance(OWNED_STATUSES, tuple)
        assert len(OWNED_STATUSES) == 2
        assert BookStatus.IN_TRANSIT in OWNED_STATUSES
        assert BookStatus.ON_HAND in OWNED_STATUSES
