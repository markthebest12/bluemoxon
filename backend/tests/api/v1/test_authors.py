"""Tests for Authors API."""

from app.models import Author


def test_create_author_with_preferred(client, db):
    """Editors can create authors with preferred=True."""
    response = client.post(
        "/api/v1/authors",
        json={"name": "Preferred Author", "preferred": True},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["preferred"] is True


def test_update_author_preferred(client, db):
    """Editors can update author preferred status."""
    # Create an author first
    author = Author(name="Test Author")
    db.add(author)
    db.commit()
    db.refresh(author)

    response = client.put(
        f"/api/v1/authors/{author.id}",
        json={"preferred": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["preferred"] is True


def test_get_author_includes_preferred(client, db):
    """Author response includes preferred field."""
    # Create an author first
    author = Author(name="Test Author 2", preferred=False)
    db.add(author)
    db.commit()
    db.refresh(author)

    response = client.get(f"/api/v1/authors/{author.id}")
    assert response.status_code == 200
    data = response.json()
    assert "preferred" in data
    assert data["preferred"] is False
