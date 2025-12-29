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


def test_reassign_author_moves_books_to_target(client, db):
    """Reassign endpoint moves all books from source to target author."""
    from app.models import Author, Book

    # Create source and target authors
    source = Author(name="Source Author")
    target = Author(name="Target Author")
    db.add_all([source, target])
    db.commit()
    db.refresh(source)
    db.refresh(target)

    # Create books for source author
    book1 = Book(title="Book 1", author_id=source.id)
    book2 = Book(title="Book 2", author_id=source.id)
    db.add_all([book1, book2])
    db.commit()

    # Reassign books from source to target
    response = client.post(
        f"/api/v1/authors/{source.id}/reassign",
        json={"target_id": target.id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["reassigned_count"] == 2
    assert data["deleted_entity"] == "Source Author"
    assert data["target_entity"] == "Target Author"

    # Verify source is deleted
    assert db.query(Author).filter(Author.id == source.id).first() is None

    # Verify books now belong to target
    db.refresh(book1)
    db.refresh(book2)
    assert book1.author_id == target.id
    assert book2.author_id == target.id


def test_reassign_author_404_when_source_not_found(client, db):
    """Reassign returns 404 when source author doesn't exist."""
    from app.models import Author

    target = Author(name="Target Author")
    db.add(target)
    db.commit()
    db.refresh(target)

    response = client.post(
        "/api/v1/authors/99999/reassign",
        json={"target_id": target.id},
    )

    assert response.status_code == 404


def test_reassign_author_400_when_target_not_found(client, db):
    """Reassign returns 400 when target author doesn't exist."""
    from app.models import Author

    source = Author(name="Source Author")
    db.add(source)
    db.commit()
    db.refresh(source)

    response = client.post(
        f"/api/v1/authors/{source.id}/reassign",
        json={"target_id": 99999},
    )

    assert response.status_code == 400


def test_reassign_author_400_when_same_entity(client, db):
    """Reassign returns 400 when source and target are the same."""
    from app.models import Author

    author = Author(name="Same Author")
    db.add(author)
    db.commit()
    db.refresh(author)

    response = client.post(
        f"/api/v1/authors/{author.id}/reassign",
        json={"target_id": author.id},
    )

    assert response.status_code == 400
