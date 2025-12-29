"""Tests for Binders API."""

from app.models import Binder


def test_create_binder_with_preferred(client, db):
    """Editors can create binders with preferred=True."""
    response = client.post(
        "/api/v1/binders",
        json={"name": "Preferred Binder", "preferred": True},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["preferred"] is True


def test_update_binder_preferred(client, db):
    """Editors can update binder preferred status."""
    binder = Binder(name="Test Binder")
    db.add(binder)
    db.commit()
    db.refresh(binder)

    response = client.put(
        f"/api/v1/binders/{binder.id}",
        json={"preferred": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["preferred"] is True


def test_get_binder_includes_preferred(client, db):
    """Binder response includes preferred field."""
    binder = Binder(name="Test Binder 2", preferred=False)
    db.add(binder)
    db.commit()
    db.refresh(binder)

    response = client.get(f"/api/v1/binders/{binder.id}")
    assert response.status_code == 200
    data = response.json()
    assert "preferred" in data
    assert data["preferred"] is False
