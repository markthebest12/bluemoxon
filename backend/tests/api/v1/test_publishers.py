"""Tests for Publishers API."""

from app.models import Publisher


def test_create_publisher_with_preferred(client, db):
    """Editors can create publishers with preferred=True."""
    response = client.post(
        "/api/v1/publishers",
        json={"name": "Preferred Publisher", "preferred": True},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["preferred"] is True


def test_update_publisher_preferred(client, db):
    """Editors can update publisher preferred status."""
    publisher = Publisher(name="Test Publisher")
    db.add(publisher)
    db.commit()
    db.refresh(publisher)

    response = client.put(
        f"/api/v1/publishers/{publisher.id}",
        json={"preferred": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["preferred"] is True


def test_get_publisher_includes_preferred(client, db):
    """Publisher response includes preferred field."""
    publisher = Publisher(name="Test Publisher 2", preferred=False)
    db.add(publisher)
    db.commit()
    db.refresh(publisher)

    response = client.get(f"/api/v1/publishers/{publisher.id}")
    assert response.status_code == 200
    data = response.json()
    assert "preferred" in data
    assert data["preferred"] is False
