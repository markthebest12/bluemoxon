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


def test_reassign_publisher_moves_books_to_target(client, db):
    """Reassign endpoint moves all books from source to target publisher."""
    from app.models import Book, Publisher

    # Create source and target publishers
    source = Publisher(name="Source Publisher")
    target = Publisher(name="Target Publisher")
    db.add_all([source, target])
    db.commit()
    db.refresh(source)
    db.refresh(target)

    # Create books for source publisher
    book1 = Book(title="Book 1", publisher_id=source.id)
    book2 = Book(title="Book 2", publisher_id=source.id)
    db.add_all([book1, book2])
    db.commit()

    # Reassign books from source to target
    response = client.post(
        f"/api/v1/publishers/{source.id}/reassign",
        json={"target_id": target.id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["reassigned_count"] == 2
    assert data["deleted_entity"] == "Source Publisher"
    assert data["target_entity"] == "Target Publisher"

    # Verify source is deleted
    assert db.query(Publisher).filter(Publisher.id == source.id).first() is None

    # Verify books now belong to target
    db.refresh(book1)
    db.refresh(book2)
    assert book1.publisher_id == target.id
    assert book2.publisher_id == target.id


def test_reassign_publisher_404_when_source_not_found(client, db):
    """Reassign returns 404 when source publisher doesn't exist."""
    from app.models import Publisher

    target = Publisher(name="Target Publisher")
    db.add(target)
    db.commit()
    db.refresh(target)

    response = client.post(
        "/api/v1/publishers/99999/reassign",
        json={"target_id": target.id},
    )

    assert response.status_code == 404


def test_reassign_publisher_400_when_target_not_found(client, db):
    """Reassign returns 400 when target publisher doesn't exist."""
    from app.models import Publisher

    source = Publisher(name="Source Publisher")
    db.add(source)
    db.commit()
    db.refresh(source)

    response = client.post(
        f"/api/v1/publishers/{source.id}/reassign",
        json={"target_id": 99999},
    )

    assert response.status_code == 400


def test_reassign_publisher_400_when_same_entity(client, db):
    """Reassign returns 400 when source and target are the same."""
    from app.models import Publisher

    publisher = Publisher(name="Same Publisher")
    db.add(publisher)
    db.commit()
    db.refresh(publisher)

    response = client.post(
        f"/api/v1/publishers/{publisher.id}/reassign",
        json={"target_id": publisher.id},
    )

    assert response.status_code == 400
