"""Tests for entity profile endpoint."""

import pytest
from fastapi.testclient import TestClient

from app.auth import CurrentUser, require_viewer
from app.db import get_db
from app.main import app
from app.models import Author, Binder, Book, Publisher
from app.models.user import User


@pytest.fixture(scope="function")
def profile_client(db):
    """Test client with a real User record for entity profile endpoints."""
    user = User(cognito_sub="test-viewer-ep", email="ep@example.com", role="viewer")
    db.add(user)
    db.flush()

    mock_user = CurrentUser(
        cognito_sub=user.cognito_sub,
        email=user.email,
        role=user.role,
        db_user=user,
    )

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_viewer] = lambda: mock_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestEntityProfileEndpoint:
    """Tests for GET /api/v1/entity/:type/:id/profile."""

    def test_author_profile_returns_200(self, profile_client, db):
        """Author profile returns entity data."""
        author = Author(
            name="Elizabeth Barrett Browning",
            birth_year=1806,
            death_year=1861,
            tier="TIER_1",
        )
        db.add(author)
        db.flush()

        book = Book(
            title="Aurora Leigh",
            author_id=author.id,
            status="ON_HAND",
            year_start=1877,
            edition="American reprint",
        )
        db.add(book)
        db.commit()

        response = profile_client.get(f"/api/v1/entity/author/{author.id}/profile")
        assert response.status_code == 200

        data = response.json()
        assert data["entity"]["name"] == "Elizabeth Barrett Browning"
        assert data["entity"]["type"] == "author"
        assert data["entity"]["birth_year"] == 1806
        assert data["stats"]["total_books"] == 1

    def test_publisher_profile_returns_200(self, profile_client, db):
        """Publisher profile returns entity data."""
        publisher = Publisher(name="Smith, Elder & Co.", tier="TIER_1")
        db.add(publisher)
        db.commit()

        response = profile_client.get(f"/api/v1/entity/publisher/{publisher.id}/profile")
        assert response.status_code == 200

        data = response.json()
        assert data["entity"]["name"] == "Smith, Elder & Co."
        assert data["entity"]["type"] == "publisher"

    def test_binder_profile_returns_200(self, profile_client, db):
        """Binder profile returns entity data."""
        binder = Binder(name="Riviere & Son", tier="TIER_1")
        db.add(binder)
        db.commit()

        response = profile_client.get(f"/api/v1/entity/binder/{binder.id}/profile")
        assert response.status_code == 200

        data = response.json()
        assert data["entity"]["name"] == "Riviere & Son"

    def test_nonexistent_entity_returns_404(self, profile_client, db):
        """Requesting missing entity returns 404."""
        response = profile_client.get("/api/v1/entity/author/99999/profile")
        assert response.status_code == 404

    def test_invalid_entity_type_returns_422(self, profile_client, db):
        """Invalid entity type returns validation error."""
        response = profile_client.get("/api/v1/entity/invalid/1/profile")
        assert response.status_code == 422

    def test_profile_includes_books(self, profile_client, db):
        """Profile includes the entity's books."""
        author = Author(name="Robert Browning", birth_year=1812, death_year=1889)
        db.add(author)
        db.flush()

        book1 = Book(
            title="Ring and the Book",
            author_id=author.id,
            status="ON_HAND",
            year_start=1868,
            edition="First Edition",
        )
        book2 = Book(
            title="Poetical Works",
            author_id=author.id,
            status="ON_HAND",
            year_start=1898,
        )
        db.add_all([book1, book2])
        db.commit()

        response = profile_client.get(f"/api/v1/entity/author/{author.id}/profile")
        data = response.json()

        assert data["stats"]["total_books"] == 2
        assert len(data["books"]) == 2
        titles = [b["title"] for b in data["books"]]
        assert "Ring and the Book" in titles
        assert "Poetical Works" in titles

    def test_profile_excludes_removed_books(self, profile_client, db):
        """Profile only includes ON_HAND and IN_TRANSIT books."""
        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        book_owned = Book(title="Owned Book", author_id=author.id, status="ON_HAND")
        book_sold = Book(title="Sold Book", author_id=author.id, status="SOLD")
        db.add_all([book_owned, book_sold])
        db.commit()

        response = profile_client.get(f"/api/v1/entity/author/{author.id}/profile")
        data = response.json()

        assert data["stats"]["total_books"] == 1
        assert data["books"][0]["title"] == "Owned Book"

    def test_profile_without_ai_content(self, profile_client, db):
        """Profile works without cached AI content."""
        author = Author(name="Obscure Author")
        db.add(author)
        db.commit()

        response = profile_client.get(f"/api/v1/entity/author/{author.id}/profile")
        data = response.json()

        assert data["profile"]["bio_summary"] is None
        assert data["profile"]["personal_stories"] == []
        assert data["profile"]["is_stale"] is False

    def test_stats_calculation(self, profile_client, db):
        """Stats are correctly calculated from books."""
        author = Author(name="Stats Author")
        db.add(author)
        db.flush()

        book1 = Book(
            title="Book 1",
            author_id=author.id,
            status="ON_HAND",
            year_start=1850,
            is_first_edition=True,
        )
        book2 = Book(
            title="Book 2",
            author_id=author.id,
            status="ON_HAND",
            year_start=1870,
        )
        db.add_all([book1, book2])
        db.commit()

        response = profile_client.get(f"/api/v1/entity/author/{author.id}/profile")
        data = response.json()

        assert data["stats"]["total_books"] == 2
        assert data["stats"]["first_editions"] == 1
        assert data["stats"]["date_range"] == [1850, 1870]

    def test_requires_authentication(self, unauthenticated_client, db):
        """Endpoint requires authentication."""
        response = unauthenticated_client.get("/api/v1/entity/author/1/profile")
        assert response.status_code == 401
