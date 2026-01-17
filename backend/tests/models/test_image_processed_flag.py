"""Tests for is_background_processed flag on BookImage."""

from app.models import Book, BookImage


def test_default_is_false(db):
    """New images should have is_background_processed=False by default."""
    book = Book(title="Test Book")
    db.add(book)
    db.commit()

    image = BookImage(
        book_id=book.id,
        s3_key="test_123.jpg",
        display_order=0,
        is_primary=True,
    )
    db.add(image)
    db.commit()

    assert image.is_background_processed is False


def test_can_set_to_true(db):
    """Should be able to set is_background_processed=True."""
    book = Book(title="Test Book")
    db.add(book)
    db.commit()

    image = BookImage(
        book_id=book.id,
        s3_key="test_123.jpg",
        display_order=0,
        is_primary=True,
        is_background_processed=True,
    )
    db.add(image)
    db.commit()

    db.refresh(image)
    assert image.is_background_processed is True
