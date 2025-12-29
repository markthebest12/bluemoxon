"""Tests for Publisher model."""

from app.models.publisher import Publisher


def test_publisher_preferred_defaults_to_false(db):
    """New publishers should have preferred=False by default."""
    publisher = Publisher(name="Test Publisher")
    db.add(publisher)
    db.commit()
    db.refresh(publisher)

    assert publisher.preferred is False


def test_publisher_preferred_can_be_set_true(db):
    """Publishers can be marked as preferred."""
    publisher = Publisher(name="Preferred Publisher", preferred=True)
    db.add(publisher)
    db.commit()
    db.refresh(publisher)

    assert publisher.preferred is True
