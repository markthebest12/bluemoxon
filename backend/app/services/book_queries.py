"""Book query helpers for common data access patterns."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.enums import OWNED_STATUSES

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Book


def get_other_books_by_author(book: Book, db: Session, owned_only: bool = True) -> list[Book]:
    """Get books by same author, excluding the given book.

    Args:
        book: The book to find siblings for
        db: Database session
        owned_only: If True, only return books with OWNED_STATUSES (IN_TRANSIT, ON_HAND).
                   If False, return all books by the author.

    Returns:
        List of books by the same author, excluding the given book.
    """
    from app.models import Book as BookModel

    if not book.author_id:
        return []

    query = db.query(BookModel).filter(
        BookModel.author_id == book.author_id,
        BookModel.id != book.id,
    )
    if owned_only:
        query = query.filter(BookModel.status.in_(OWNED_STATUSES))
    return query.all()
