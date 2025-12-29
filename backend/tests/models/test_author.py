"""Tests for Author model."""

from app.models.author import Author


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
