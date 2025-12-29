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


def test_reassign_binder_moves_books_to_target(client, db):
    """Reassign endpoint moves all books from source to target binder."""
    from app.models import Binder, Book

    # Create source and target binders
    source = Binder(name="Source Binder")
    target = Binder(name="Target Binder")
    db.add_all([source, target])
    db.commit()
    db.refresh(source)
    db.refresh(target)

    # Create books for source binder
    book1 = Book(title="Book 1", binder_id=source.id)
    book2 = Book(title="Book 2", binder_id=source.id)
    db.add_all([book1, book2])
    db.commit()

    # Reassign books from source to target
    response = client.post(
        f"/api/v1/binders/{source.id}/reassign",
        json={"target_id": target.id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["reassigned_count"] == 2
    assert data["deleted_entity"] == "Source Binder"
    assert data["target_entity"] == "Target Binder"

    # Verify source is deleted
    assert db.query(Binder).filter(Binder.id == source.id).first() is None

    # Verify books now belong to target
    db.refresh(book1)
    db.refresh(book2)
    assert book1.binder_id == target.id
    assert book2.binder_id == target.id


def test_reassign_binder_404_when_source_not_found(client, db):
    """Reassign returns 404 when source binder doesn't exist."""
    from app.models import Binder

    target = Binder(name="Target Binder")
    db.add(target)
    db.commit()
    db.refresh(target)

    response = client.post(
        "/api/v1/binders/99999/reassign",
        json={"target_id": target.id},
    )

    assert response.status_code == 404


def test_reassign_binder_400_when_target_not_found(client, db):
    """Reassign returns 400 when target binder doesn't exist."""
    from app.models import Binder

    source = Binder(name="Source Binder")
    db.add(source)
    db.commit()
    db.refresh(source)

    response = client.post(
        f"/api/v1/binders/{source.id}/reassign",
        json={"target_id": 99999},
    )

    assert response.status_code == 400


def test_reassign_binder_400_when_same_entity(client, db):
    """Reassign returns 400 when source and target are the same."""
    from app.models import Binder

    binder = Binder(name="Same Binder")
    db.add(binder)
    db.commit()
    db.refresh(binder)

    response = client.post(
        f"/api/v1/binders/{binder.id}/reassign",
        json={"target_id": binder.id},
    )

    assert response.status_code == 400
