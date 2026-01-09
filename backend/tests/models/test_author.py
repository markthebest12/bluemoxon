"""Tests for Author model."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.author import Author


def test_author_name_unique_constraint(db):
    """Author names must be unique.

    This test verifies that the database enforces uniqueness on author names,
    preventing duplicate authors from being created (e.g., via race conditions).
    """
    author1 = Author(name="Charles Dickens")
    db.add(author1)
    db.commit()

    author2 = Author(name="Charles Dickens")
    db.add(author2)
    with pytest.raises(IntegrityError):
        db.commit()


def test_author_preferred_defaults_to_false(db):
    """New authors should have preferred=False by default."""
    author = Author(name="Test Author")
    db.add(author)
    db.commit()
    db.refresh(author)

    assert author.preferred is False


def test_author_preferred_can_be_set_true(db):
    """Authors can be marked as preferred."""
    author = Author(name="Preferred Author", preferred=True)
    db.add(author)
    db.commit()
    db.refresh(author)

    assert author.preferred is True
