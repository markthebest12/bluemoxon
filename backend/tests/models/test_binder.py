"""Tests for Binder model."""

from app.models.binder import Binder


def test_binder_preferred_defaults_to_false(db):
    """New binders should have preferred=False by default."""
    binder = Binder(name="Test Binder")
    db.add(binder)
    db.commit()
    db.refresh(binder)

    assert binder.preferred is False


def test_binder_preferred_can_be_set_true(db):
    """Binders can be marked as preferred."""
    binder = Binder(name="Preferred Binder", preferred=True)
    db.add(binder)
    db.commit()
    db.refresh(binder)

    assert binder.preferred is True
