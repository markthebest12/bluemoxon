"""Tests for entity profile endpoint."""

import time
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.auth import CurrentUser, require_viewer
from app.db import get_db
from app.main import app
from app.models import Author, Binder, Book, Publisher
from app.models.entity_profile import EntityProfile
from app.models.user import User
from app.services.entity_profile import _check_staleness, _get_entity_books


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


class TestEntityProfileTimestamps:
    """Tests for #1554: EntityProfile has TimestampMixin."""

    def test_entity_profile_has_created_at(self, db):
        """EntityProfile model has created_at as timezone-aware datetime."""
        user = User(cognito_sub="test-ts", email="ts@example.com", role="viewer")
        db.add(user)
        db.flush()

        profile = EntityProfile(
            entity_type="author",
            entity_id=1,
            owner_id=user.id,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

        assert isinstance(profile.created_at, datetime)

    def test_entity_profile_has_updated_at(self, db):
        """EntityProfile model has updated_at from TimestampMixin."""
        user = User(cognito_sub="test-ts2", email="ts2@example.com", role="viewer")
        db.add(user)
        db.flush()

        profile = EntityProfile(
            entity_type="author",
            entity_id=2,
            owner_id=user.id,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

        assert isinstance(profile.updated_at, datetime)

    def test_updated_at_changes_on_modification(self, db):
        """updated_at advances when the profile is modified."""
        user = User(cognito_sub="test-ts3", email="ts3@example.com", role="viewer")
        db.add(user)
        db.flush()

        profile = EntityProfile(
            entity_type="author",
            entity_id=3,
            owner_id=user.id,
            bio_summary="Original bio",
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

        original_updated = profile.updated_at

        time.sleep(0.01)
        profile.bio_summary = "Updated bio"
        db.commit()
        db.refresh(profile)

        assert profile.updated_at >= original_updated
        assert profile.bio_summary == "Updated bio"


class TestEntityFKMap:
    """Tests for _get_entity_books and _check_staleness behaviour."""

    def test_get_entity_books_unknown_type_returns_empty(self, db):
        """_get_entity_books returns [] for unknown entity type."""
        result = _get_entity_books(db, "unknown", 1)
        assert result == []

    @pytest.mark.parametrize(
        ("entity_type", "model_cls", "fk_field", "book_title"),
        [
            ("author", Author, "author_id", "FK Author Book"),
            ("publisher", Publisher, "publisher_id", "FK Publisher Book"),
            ("binder", Binder, "binder_id", "FK Binder Book"),
        ],
    )
    def test_get_entity_books_by_type(self, db, entity_type, model_cls, fk_field, book_title):
        """_get_entity_books returns books for each entity type."""
        entity = model_cls(name=f"Test FK {entity_type.title()}")
        db.add(entity)
        db.flush()

        book = Book(title=book_title, status="ON_HAND", **{fk_field: entity.id})
        db.add(book)
        db.commit()

        result = _get_entity_books(db, entity_type, entity.id)
        assert len(result) == 1
        assert result[0].title == book_title

    def test_get_entity_books_excludes_non_owned_statuses(self, db):
        """_get_entity_books excludes books with non-owned statuses like SOLD."""
        author = Author(name="Status Filter Author")
        db.add(author)
        db.flush()

        book_owned = Book(title="Owned Book", author_id=author.id, status="ON_HAND")
        book_sold = Book(title="Sold Book", author_id=author.id, status="SOLD")
        db.add_all([book_owned, book_sold])
        db.commit()

        result = _get_entity_books(db, "author", author.id)
        assert len(result) == 1
        assert result[0].title == "Owned Book"

    def test_check_staleness_unknown_type_returns_false(self, db):
        """_check_staleness returns False for unknown entity type."""
        user = User(cognito_sub="test-fk-stale", email="fk-stale@example.com", role="viewer")
        db.add(user)
        db.flush()

        profile = EntityProfile(
            entity_type="unknown",
            entity_id=1,
            owner_id=user.id,
            generated_at=datetime(2020, 1, 1, tzinfo=UTC),
        )
        db.add(profile)
        db.commit()

        result = _check_staleness(db, profile, "unknown", 1)
        assert result is False

    def test_check_staleness_returns_true_when_book_updated_after_profile(self, db):
        """_check_staleness returns True when a book was updated after generated_at."""
        user = User(cognito_sub="test-stale-true", email="stale-true@example.com", role="viewer")
        db.add(user)
        db.flush()

        author = Author(name="Stale Author")
        db.add(author)
        db.flush()

        old_time = datetime.now(UTC) - timedelta(hours=2)
        book = Book(title="Stale Book", author_id=author.id, status="ON_HAND")
        db.add(book)
        db.commit()

        profile = EntityProfile(
            entity_type="author",
            entity_id=author.id,
            owner_id=user.id,
            generated_at=old_time,
        )
        db.add(profile)
        db.commit()

        db.query(Book).filter(Book.id == book.id).update({"updated_at": datetime.now(UTC)})
        db.commit()
        db.refresh(profile)

        result = _check_staleness(db, profile, "author", author.id)
        assert result is True

    def test_check_staleness_returns_false_when_profile_is_fresh(self, db):
        """_check_staleness returns False when generated_at is after book updates."""
        user = User(cognito_sub="test-stale-false", email="stale-false@example.com", role="viewer")
        db.add(user)
        db.flush()

        author = Author(name="Fresh Author")
        db.add(author)
        db.flush()

        book = Book(title="Fresh Book", author_id=author.id, status="ON_HAND")
        db.add(book)
        db.commit()

        future_time = datetime.now(UTC) + timedelta(hours=1)
        profile = EntityProfile(
            entity_type="author",
            entity_id=author.id,
            owner_id=user.id,
            generated_at=future_time,
        )
        db.add(profile)
        db.commit()

        result = _check_staleness(db, profile, "author", author.id)
        assert result is False
