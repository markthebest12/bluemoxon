"""Tests for entity profile endpoint."""

import time
from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth import CurrentUser, require_admin, require_editor, require_viewer
from app.db import get_db
from app.main import app
from app.models import Author, Binder, Book, BookImage, Publisher
from app.models.entity_profile import EntityProfile
from app.models.profile_generation_job import JobStatus, ProfileGenerationJob
from app.models.user import User
from app.schemas.entity_profile import ProfileBook
from app.services.ai_profile_generator import (
    GeneratorConfig,
    _validate_ai_connections,
    generate_ai_connections,
)
from app.services.entity_profile import (
    _build_connections,
    _build_profile_books,
    _build_stats,
    _check_staleness,
    _get_entity_books,
    generate_and_cache_profile,
    is_profile_stale,
)

# NOTE: profile_client, editor_client, and viewer_regen_client share boilerplate
# (User creation, CurrentUser mock, get_db override). A factory extraction was
# considered but deferred — SQLAlchemy session scoping requires the User and
# db override to live in the fixture scope to avoid DetachedInstanceError.


class TestProfileBookImageUrl:
    """Tests for primary_image_url in ProfileBook (#1634)."""

    def test_schema_accepts_primary_image_url(self):
        """ProfileBook schema accepts and serializes primary_image_url."""
        book = ProfileBook(
            id=1,
            title="Test Book",
            year=1850,
            primary_image_url="/api/v1/books/1/images/10/file",
        )
        assert book.primary_image_url == "/api/v1/books/1/images/10/file"

    def test_schema_defaults_primary_image_url_to_none(self):
        """ProfileBook schema defaults primary_image_url to None."""
        book = ProfileBook(id=1, title="Test Book")
        assert book.primary_image_url is None

    @patch("app.services.entity_profile.get_settings")
    def test_build_profile_books_with_primary_image(self, mock_settings, db):
        """_build_profile_books returns primary_image_url for books with images."""
        mock_settings.return_value = MagicMock(is_aws_lambda=False)

        author = Author(name="Image Test Author")
        db.add(author)
        db.flush()

        book = Book(
            title="Book With Image",
            author_id=author.id,
            status="ON_HAND",
            year_start=1860,
        )
        db.add(book)
        db.flush()

        image = BookImage(
            book_id=book.id,
            s3_key="test_image.jpg",
            display_order=0,
            is_primary=True,
        )
        db.add(image)
        db.commit()

        result = _build_profile_books(db, [book])
        assert len(result) == 1
        assert result[0].primary_image_url == f"/api/v1/books/{book.id}/images/{image.id}/file"

    @patch("app.services.entity_profile.get_settings")
    def test_build_profile_books_without_images(self, mock_settings, db):
        """_build_profile_books returns None for primary_image_url when no images."""
        mock_settings.return_value = MagicMock(is_aws_lambda=False)

        author = Author(name="No Image Author")
        db.add(author)
        db.flush()

        book = Book(
            title="Book Without Image",
            author_id=author.id,
            status="ON_HAND",
        )
        db.add(book)
        db.commit()

        result = _build_profile_books(db, [book])
        assert len(result) == 1
        assert result[0].primary_image_url is None

    @patch("app.services.entity_profile.get_settings")
    def test_build_profile_books_prefers_primary_image(self, mock_settings, db):
        """_build_profile_books uses is_primary=True image over display_order."""
        mock_settings.return_value = MagicMock(is_aws_lambda=False)

        book = Book(title="Multi Image Book", status="ON_HAND")
        db.add(book)
        db.flush()

        # Non-primary image with lower display_order
        img1 = BookImage(
            book_id=book.id,
            s3_key="first.jpg",
            display_order=0,
            is_primary=False,
        )
        # Primary image with higher display_order
        img2 = BookImage(
            book_id=book.id,
            s3_key="primary.jpg",
            display_order=1,
            is_primary=True,
        )
        db.add_all([img1, img2])
        db.commit()

        result = _build_profile_books(db, [book])
        assert result[0].primary_image_url == f"/api/v1/books/{book.id}/images/{img2.id}/file"

    @patch("app.services.entity_profile.get_settings")
    def test_build_profile_books_falls_back_to_first_by_display_order(self, mock_settings, db):
        """Without is_primary, uses first image by display_order."""
        mock_settings.return_value = MagicMock(is_aws_lambda=False)

        book = Book(title="Fallback Image Book", status="ON_HAND")
        db.add(book)
        db.flush()

        img1 = BookImage(
            book_id=book.id,
            s3_key="second.jpg",
            display_order=1,
            is_primary=False,
        )
        img2 = BookImage(
            book_id=book.id,
            s3_key="first.jpg",
            display_order=0,
            is_primary=False,
        )
        db.add_all([img1, img2])
        db.commit()

        result = _build_profile_books(db, [book])
        # Should pick img2 (display_order=0)
        assert result[0].primary_image_url == f"/api/v1/books/{book.id}/images/{img2.id}/file"

    @patch("app.services.entity_profile.get_cloudfront_url")
    @patch("app.services.entity_profile.get_settings")
    def test_build_profile_books_uses_cloudfront_in_lambda(self, mock_settings, mock_cf_url, db):
        """_build_profile_books uses CloudFront URL when running in Lambda."""
        mock_settings.return_value = MagicMock(is_aws_lambda=True)
        mock_cf_url.return_value = "https://cdn.example.com/books/test_image.jpg"

        book = Book(title="Lambda Book", status="ON_HAND")
        db.add(book)
        db.flush()

        image = BookImage(
            book_id=book.id,
            s3_key="test_image.jpg",
            display_order=0,
            is_primary=True,
        )
        db.add(image)
        db.commit()

        result = _build_profile_books(db, [book])
        assert result[0].primary_image_url == "https://cdn.example.com/books/test_image.jpg"
        mock_cf_url.assert_called_once_with("test_image.jpg")

    @patch("app.services.entity_profile.get_settings")
    def test_build_profile_books_empty_list(self, mock_settings, db):
        """_build_profile_books handles empty list."""
        mock_settings.return_value = MagicMock(is_aws_lambda=False)
        result = _build_profile_books(db, [])
        assert result == []


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


@pytest.fixture(scope="function")
def editor_client(db):
    """Test client with editor auth and a real User record for regenerate endpoint."""
    user = User(cognito_sub="test-editor-ep", email="ep-editor@example.com", role="editor")
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
    app.dependency_overrides[require_editor] = lambda: mock_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def viewer_regen_client(db):
    """Client with viewer auth that raises 403 on require_editor."""
    user = User(cognito_sub="test-viewer-regen", email="viewer-regen@example.com", role="viewer")
    db.add(user)
    db.flush()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_require_editor():
        raise HTTPException(status_code=403, detail="Editor role required")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_editor] = override_require_editor
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

    def test_cached_profile_visible_to_any_user(self, profile_client, db):
        """Cached profile is visible to any authenticated user (#1715).

        Profiles are per-entity, not per-user. A cached bio_summary is
        returned regardless of which user requests it.
        """
        author = Author(name="Cross-Owner Author", birth_year=1800, death_year=1870)
        db.add(author)
        db.flush()

        cached_profile = EntityProfile(
            entity_type="author",
            entity_id=author.id,
            bio_summary="A distinguished Victorian author.",
            personal_stories=[
                {
                    "title": "Early life",
                    "text": "Born in 1800.",
                    "significance": "context",
                    "tone": "intellectual",
                }
            ],
        )
        db.add(cached_profile)
        db.commit()

        response = profile_client.get(f"/api/v1/entity/author/{author.id}/profile")
        assert response.status_code == 200

        data = response.json()
        assert data["profile"]["bio_summary"] == "A distinguished Victorian author."
        assert len(data["profile"]["personal_stories"]) == 1

    def test_requires_authentication(self, unauthenticated_client, db):
        """Endpoint requires authentication."""
        response = unauthenticated_client.get("/api/v1/entity/author/1/profile")
        assert response.status_code == 401


class TestEntityProfileTimestamps:
    """Tests for #1554: EntityProfile has TimestampMixin."""

    def test_entity_profile_has_created_at(self, db):
        """EntityProfile model has created_at as timezone-aware datetime."""
        profile = EntityProfile(
            entity_type="author",
            entity_id=1,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

        assert isinstance(profile.created_at, datetime)

    def test_entity_profile_has_updated_at(self, db):
        """EntityProfile model has updated_at from TimestampMixin."""
        profile = EntityProfile(
            entity_type="author",
            entity_id=2,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

        assert isinstance(profile.updated_at, datetime)

    def test_updated_at_changes_on_modification(self, db):
        """updated_at advances when the profile is modified."""
        profile = EntityProfile(
            entity_type="author",
            entity_id=3,
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


class TestRegenerateEndpoint:
    """Tests for POST /api/v1/entity/{entity_type}/{entity_id}/profile/regenerate (#1718).

    The endpoint is async: it deletes cached profile, enqueues an SQS message,
    and returns 202 Accepted immediately.
    """

    @patch("app.api.v1.entity_profile.send_profile_generation_jobs")
    def test_regenerate_returns_202_and_enqueues_sqs(self, mock_send, editor_client, db):
        """Regenerate returns 202 and sends SQS message."""
        author = Author(name="Test Author")
        db.add(author)
        db.commit()

        response = editor_client.post(f"/api/v1/entity/author/{author.id}/profile/regenerate")
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "queued"
        assert "queued" in data["message"].lower()
        mock_send.assert_called_once()

        # Verify the SQS message contents
        messages = mock_send.call_args.args[0]
        assert len(messages) == 1
        msg = messages[0]
        assert msg["entity_type"] == "author"
        assert msg["entity_id"] == author.id
        assert msg["job_id"] is None

    @patch("app.api.v1.entity_profile.send_profile_generation_jobs")
    def test_regenerate_deletes_existing_profile(self, mock_send, editor_client, db):
        """Existing cached profile is deleted before enqueueing."""
        author = Author(name="Cached Author")
        db.add(author)
        db.flush()

        profile = EntityProfile(
            entity_type="author",
            entity_id=author.id,
            bio_summary="Old bio",
        )
        db.add(profile)
        db.commit()

        # Verify profile exists
        assert (
            db.query(EntityProfile)
            .filter(
                EntityProfile.entity_type == "author",
                EntityProfile.entity_id == author.id,
            )
            .count()
            == 1
        )

        response = editor_client.post(f"/api/v1/entity/author/{author.id}/profile/regenerate")
        assert response.status_code == 202

        # Profile should be deleted
        assert (
            db.query(EntityProfile)
            .filter(
                EntityProfile.entity_type == "author",
                EntityProfile.entity_id == author.id,
            )
            .count()
            == 0
        )

    def test_regenerate_nonexistent_entity_returns_404(self, editor_client, db):
        """Regenerating profile for nonexistent entity returns 404."""
        response = editor_client.post("/api/v1/entity/author/99999/profile/regenerate")
        assert response.status_code == 404

    def test_regenerate_requires_editor_auth(self, viewer_regen_client, db):
        """Viewer auth gets 403 on regenerate (require_editor)."""
        author = Author(name="Auth Test Author")
        db.add(author)
        db.commit()

        response = viewer_regen_client.post(f"/api/v1/entity/author/{author.id}/profile/regenerate")
        assert response.status_code == 403

    def test_regenerate_invalid_entity_type_returns_422(self, editor_client):
        """Invalid entity_type returns validation error."""
        response = editor_client.post("/api/v1/entity/invalid/1/profile/regenerate")
        assert response.status_code == 422

    @patch("app.api.v1.entity_profile.send_profile_generation_jobs")
    def test_regenerate_sqs_failure_returns_500(self, mock_send, db):
        """SQS send failure returns 500.

        Uses a dedicated client with raise_server_exceptions=False so the
        HTTP 500 surfaces as a response instead of propagating through TestClient.
        """
        user = User(cognito_sub="test-editor-500", email="ep-500@example.com", role="editor")
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
        app.dependency_overrides[require_editor] = lambda: mock_user

        author = Author(name="Error Author")
        db.add(author)
        db.commit()

        mock_send.side_effect = RuntimeError("SQS connection failed")

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(f"/api/v1/entity/author/{author.id}/profile/regenerate")
        app.dependency_overrides.clear()

        assert response.status_code == 500

    def test_regenerate_zero_entity_id_returns_422(self, editor_client):
        """entity_id=0 is rejected by FastAPI ge=1 validation."""
        response = editor_client.post("/api/v1/entity/author/0/profile/regenerate")
        assert response.status_code == 422


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
        profile = EntityProfile(
            entity_type="unknown",
            entity_id=1,
            generated_at=datetime(2020, 1, 1, tzinfo=UTC),
        )
        db.add(profile)
        db.commit()

        result = _check_staleness(db, profile, "unknown", 1)
        assert result is False

    def test_check_staleness_returns_true_when_book_updated_after_profile(self, db):
        """_check_staleness returns True when a book was updated after generated_at."""
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
            generated_at=future_time,
        )
        db.add(profile)
        db.commit()

        result = _check_staleness(db, profile, "author", author.id)
        assert result is False


class TestIsProfileStale:
    """Tests for the public is_profile_stale() API (#1770)."""

    def test_returns_true_when_no_profile_exists(self, db):
        """is_profile_stale returns True when entity has no profile at all."""
        author = Author(name="No Profile Author")
        db.add(author)
        db.flush()

        assert is_profile_stale(db, "author", author.id) is True

    def test_returns_true_when_books_updated_after_profile(self, db):
        """is_profile_stale returns True when books were updated after profile generation."""
        author = Author(name="Stale Profile Author")
        db.add(author)
        db.flush()

        book = Book(title="Updated Book", author_id=author.id, status="ON_HAND")
        db.add(book)
        db.commit()

        old_time = datetime.now(UTC) - timedelta(hours=2)
        profile = EntityProfile(
            entity_type="author",
            entity_id=author.id,
            generated_at=old_time,
        )
        db.add(profile)
        db.commit()

        db.query(Book).filter(Book.id == book.id).update({"updated_at": datetime.now(UTC)})
        db.commit()

        assert is_profile_stale(db, "author", author.id) is True

    def test_returns_false_when_profile_is_fresh(self, db):
        """is_profile_stale returns False when profile was generated after latest book update."""
        author = Author(name="Fresh Profile Author")
        db.add(author)
        db.flush()

        book = Book(title="Fresh Book", author_id=author.id, status="ON_HAND")
        db.add(book)
        db.commit()

        future_time = datetime.now(UTC) + timedelta(hours=1)
        profile = EntityProfile(
            entity_type="author",
            entity_id=author.id,
            generated_at=future_time,
        )
        db.add(profile)
        db.commit()

        assert is_profile_stale(db, "author", author.id) is False


def _make_graph_node(
    node_id,
    entity_id,
    name,
    node_type="author",
    era=None,
    birth_year=None,
    death_year=None,
    founded_year=None,
    closed_year=None,
    tier=None,
    book_count=0,
    book_ids=None,
):
    """Create a mock SocialCircleNode."""
    node = MagicMock()
    node.id = node_id
    node.entity_id = entity_id
    node.name = name
    node.type = MagicMock()
    node.type.value = node_type
    node.era = MagicMock() if era else None
    if era:
        node.era.value = era
    node.birth_year = birth_year
    node.death_year = death_year
    node.founded_year = founded_year
    node.closed_year = closed_year
    node.tier = tier
    node.book_count = book_count
    node.book_ids = book_ids or []
    return node


def _make_graph_edge(
    source, target, edge_type="author_publisher", strength=5, shared_book_ids=None
):
    """Create a mock SocialCircleEdge."""
    edge = MagicMock()
    edge.id = f"e:{source}:{target}"
    edge.source = source
    edge.target = target
    edge.type = MagicMock()
    edge.type.value = edge_type
    edge.strength = strength
    edge.shared_book_ids = shared_book_ids
    return edge


class TestBuildConnectionsClassifier:
    """Tests for _build_connections narrative_trigger population (#1553)."""

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.classify_connection")
    def test_populates_narrative_trigger(self, mock_classify, mock_graph, db):
        """Each connection gets a narrative_trigger from classify_connection."""
        source = _make_graph_node(
            "author:1", 1, "Darwin", era="victorian", birth_year=1809, death_year=1882
        )
        target = _make_graph_node(
            "publisher:2", 2, "Murray", node_type="publisher", era="romantic", founded_year=1768
        )
        edge = _make_graph_edge("author:1", "publisher:2")

        graph = MagicMock()
        graph.nodes = [source, target]
        graph.edges = [edge]
        mock_graph.return_value = graph
        mock_classify.return_value = "cross_era_bridge"

        connections = _build_connections(db, "author", 1, None)

        assert len(connections) == 1
        assert connections[0].narrative_trigger == "cross_era_bridge"
        mock_classify.assert_called_once()
        call_kwargs = mock_classify.call_args
        assert call_kwargs.kwargs["source_era"] == "victorian"
        assert call_kwargs.kwargs["target_era"] == "romantic"

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.classify_connection")
    def test_no_trigger_when_classifier_returns_none(self, mock_classify, mock_graph, db):
        """narrative_trigger is None when classifier returns None."""
        source = _make_graph_node("author:1", 1, "Author A", era="victorian", birth_year=1850)
        target = _make_graph_node(
            "author:2", 2, "Author B", node_type="author", era="victorian", birth_year=1855
        )
        edge = _make_graph_edge("author:1", "author:2", edge_type="author_author")

        graph = MagicMock()
        graph.nodes = [source, target]
        graph.edges = [edge]
        mock_graph.return_value = graph
        mock_classify.return_value = None

        connections = _build_connections(db, "author", 1, None)

        assert len(connections) == 1
        assert connections[0].narrative_trigger is None

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.classify_connection")
    def test_source_connection_count_passed_to_classifier(self, mock_classify, mock_graph, db):
        """source_connection_count equals total edges for the source entity."""
        source = _make_graph_node("author:1", 1, "Hub Author")
        targets = [
            _make_graph_node(f"publisher:{i}", i, f"Pub {i}", node_type="publisher")
            for i in range(2, 8)
        ]
        edges = [_make_graph_edge("author:1", f"publisher:{i}") for i in range(2, 8)]

        graph = MagicMock()
        graph.nodes = [source] + targets
        graph.edges = edges
        mock_graph.return_value = graph
        mock_classify.return_value = "hub_figure"

        _build_connections(db, "author", 1, None)

        for call in mock_classify.call_args_list:
            assert call.kwargs["source_connection_count"] == 6

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.classify_connection")
    def test_cached_relationship_story_sets_has_relationship_story(
        self, mock_classify, mock_graph, db
    ):
        """has_relationship_story=True when cached profile has a story for this pair."""
        profile = EntityProfile(
            entity_type="author",
            entity_id=1,
            relationship_stories={"author:1:publisher:2": {"summary": "test"}},
        )
        db.add(profile)
        db.commit()

        source = _make_graph_node("author:1", 1, "Darwin")
        target = _make_graph_node("publisher:2", 2, "Murray", node_type="publisher")
        edge = _make_graph_edge("author:1", "publisher:2")

        graph = MagicMock()
        graph.nodes = [source, target]
        graph.edges = [edge]
        mock_graph.return_value = graph
        mock_classify.return_value = "social_circle"

        _build_connections(db, "author", 1, profile)

        assert mock_classify.call_args.kwargs["has_relationship_story"] is True


class TestBuildConnectionsSharedBooks:
    """Tests for _build_connections shared_books population (#1556)."""

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.classify_connection", return_value=None)
    def test_populates_shared_books(self, _mock_classify, mock_graph, db):
        """shared_books contains ProfileBook objects for shared_book_ids."""
        author = Author(name="Shared Books Author", birth_year=1812)
        db.add(author)
        db.flush()
        publisher = Publisher(name="Shared Books Publisher")
        db.add(publisher)
        db.flush()

        book = Book(
            title="Shared Work",
            author_id=author.id,
            publisher_id=publisher.id,
            status="ON_HAND",
            year_start=1868,
            edition="First",
            condition_grade="FINE",
        )
        db.add(book)
        db.commit()

        source = _make_graph_node("author:1", author.id, author.name)
        target = _make_graph_node(
            f"publisher:{publisher.id}", publisher.id, publisher.name, node_type="publisher"
        )
        edge = _make_graph_edge("author:1", f"publisher:{publisher.id}", shared_book_ids=[book.id])

        graph = MagicMock()
        graph.nodes = [source, target]
        graph.edges = [edge]
        mock_graph.return_value = graph

        connections = _build_connections(db, "author", author.id, None)

        assert len(connections) == 1
        assert len(connections[0].shared_books) == 1
        sb = connections[0].shared_books[0]
        assert sb.title == "Shared Work"
        assert sb.year == 1868
        assert sb.edition == "First"
        assert sb.condition == "FINE"

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.classify_connection", return_value=None)
    def test_shared_books_capped_at_5(self, _mock_classify, mock_graph, db):
        """shared_books is capped at 5 per connection."""
        author = Author(name="Many Books Author")
        db.add(author)
        db.flush()
        publisher = Publisher(name="Many Books Publisher")
        db.add(publisher)
        db.flush()

        book_ids = []
        for i in range(8):
            book = Book(
                title=f"Book {i}",
                author_id=author.id,
                publisher_id=publisher.id,
                status="ON_HAND",
                year_start=1860 + i,
            )
            db.add(book)
            db.flush()
            book_ids.append(book.id)
        db.commit()

        source = _make_graph_node("author:1", author.id, author.name)
        target = _make_graph_node(
            f"publisher:{publisher.id}", publisher.id, publisher.name, node_type="publisher"
        )
        edge = _make_graph_edge("author:1", f"publisher:{publisher.id}", shared_book_ids=book_ids)

        graph = MagicMock()
        graph.nodes = [source, target]
        graph.edges = [edge]
        mock_graph.return_value = graph

        connections = _build_connections(db, "author", author.id, None)

        assert len(connections[0].shared_books) == 5

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.classify_connection", return_value=None)
    def test_empty_shared_book_ids(self, _mock_classify, mock_graph, db):
        """shared_books is empty when edge has no shared_book_ids."""
        source = _make_graph_node("author:1", 1, "Author")
        target = _make_graph_node("publisher:2", 2, "Publisher", node_type="publisher")
        edge = _make_graph_edge("author:1", "publisher:2", shared_book_ids=None)

        graph = MagicMock()
        graph.nodes = [source, target]
        graph.edges = [edge]
        mock_graph.return_value = graph

        connections = _build_connections(db, "author", 1, None)

        assert connections[0].shared_books == []
        assert connections[0].shared_book_count == 0

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.classify_connection", return_value=None)
    def test_shared_books_bulk_query_efficiency(self, _mock_classify, mock_graph, db):
        """Shared books across multiple edges are fetched in a single query."""
        author = Author(name="Multi-Edge Author")
        db.add(author)
        db.flush()
        pub1 = Publisher(name="Pub One")
        pub2 = Publisher(name="Pub Two")
        db.add_all([pub1, pub2])
        db.flush()

        book1 = Book(title="Book A", author_id=author.id, publisher_id=pub1.id, status="ON_HAND")
        book2 = Book(title="Book B", author_id=author.id, publisher_id=pub2.id, status="ON_HAND")
        db.add_all([book1, book2])
        db.commit()

        source = _make_graph_node("author:1", author.id, author.name)
        t1 = _make_graph_node(f"publisher:{pub1.id}", pub1.id, pub1.name, node_type="publisher")
        t2 = _make_graph_node(f"publisher:{pub2.id}", pub2.id, pub2.name, node_type="publisher")
        e1 = _make_graph_edge("author:1", f"publisher:{pub1.id}", shared_book_ids=[book1.id])
        e2 = _make_graph_edge("author:1", f"publisher:{pub2.id}", shared_book_ids=[book2.id])

        graph = MagicMock()
        graph.nodes = [source, t1, t2]
        graph.edges = [e1, e2]
        mock_graph.return_value = graph

        connections = _build_connections(db, "author", author.id, None)

        assert len(connections) == 2
        titles = {connections[0].shared_books[0].title, connections[1].shared_books[0].title}
        assert titles == {"Book A", "Book B"}


class TestBuildConnectionsRelationshipStory:
    """Tests for _build_connections relationship_story from cached profile (#1553)."""

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.classify_connection", return_value="cross_era_bridge")
    def test_cached_relationship_story_populated(self, _mock_classify, mock_graph, db):
        """relationship_story is populated from cached profile data."""
        story_data = {
            "summary": "Darwin and Murray had a productive partnership",
            "details": [
                {
                    "text": "They published Origin together",
                    "significance": "revelation",
                    "tone": "intellectual",
                }
            ],
            "narrative_style": "prose-paragraph",
        }
        profile = EntityProfile(
            entity_type="author",
            entity_id=1,
            relationship_stories={"author:1:publisher:2": story_data},
        )
        db.add(profile)
        db.commit()

        source = _make_graph_node("author:1", 1, "Darwin")
        target = _make_graph_node("publisher:2", 2, "Murray", node_type="publisher")
        edge = _make_graph_edge("author:1", "publisher:2")

        graph = MagicMock()
        graph.nodes = [source, target]
        graph.edges = [edge]
        mock_graph.return_value = graph

        connections = _build_connections(db, "author", 1, profile)

        assert connections[0].relationship_story is not None
        assert (
            connections[0].relationship_story.summary
            == "Darwin and Murray had a productive partnership"
        )
        assert connections[0].relationship_story.narrative_style == "prose-paragraph"

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.classify_connection", return_value=None)
    def test_no_relationship_story_when_not_cached(self, _mock_classify, mock_graph, db):
        """relationship_story is None when no cached story exists."""
        source = _make_graph_node("author:1", 1, "Author")
        target = _make_graph_node("publisher:2", 2, "Publisher", node_type="publisher")
        edge = _make_graph_edge("author:1", "publisher:2")

        graph = MagicMock()
        graph.nodes = [source, target]
        graph.edges = [edge]
        mock_graph.return_value = graph

        connections = _build_connections(db, "author", 1, None)

        assert connections[0].relationship_story is None


class TestGenerateAndCacheProfileTriggers:
    """Tests for generate_and_cache_profile trigger-based narrative selection (#1553)."""

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.generate_bio_and_stories")
    @patch("app.services.entity_profile.classify_connection")
    @patch("app.services.entity_profile.generate_relationship_story")
    @patch("app.services.entity_profile.generate_connection_narrative")
    @patch(
        "app.services.entity_profile.GeneratorConfig.resolve",
        return_value=GeneratorConfig(model_id="claude-3-haiku"),
    )
    def test_high_impact_trigger_generates_relationship_story(
        self, _mock_model, mock_narrative, mock_story, mock_classify, mock_bio, mock_graph, db
    ):
        """cross_era_bridge trigger calls generate_relationship_story."""
        author = Author(name="Darwin", birth_year=1809, death_year=1882)
        db.add(author)
        db.flush()
        db.commit()

        mock_bio.return_value = {"biography": "A bio", "personal_stories": []}
        mock_classify.return_value = "cross_era_bridge"
        mock_story.return_value = {
            "summary": "Cross-era partnership",
            "details": [],
            "narrative_style": "prose-paragraph",
        }

        source = _make_graph_node("author:1", author.id, "Darwin", era="victorian", birth_year=1809)
        target = _make_graph_node(
            "publisher:2", 2, "Murray", node_type="publisher", era="romantic", founded_year=1768
        )
        edge = _make_graph_edge("author:1", "publisher:2")
        graph = MagicMock()
        graph.nodes = [source, target]
        graph.edges = [edge]
        mock_graph.return_value = graph

        result = generate_and_cache_profile(db, "author", author.id)

        mock_story.assert_called_once()
        mock_narrative.assert_not_called()
        assert result.relationship_stories is not None
        assert f"author:{author.id}:publisher:2" in result.relationship_stories
        assert (
            result.connection_narratives[f"author:{author.id}:publisher:2"]
            == "Cross-era partnership"
        )

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.generate_bio_and_stories")
    @patch("app.services.entity_profile.classify_connection")
    @patch("app.services.entity_profile.generate_relationship_story")
    @patch("app.services.entity_profile.generate_connection_narrative")
    @patch(
        "app.services.entity_profile.GeneratorConfig.resolve",
        return_value=GeneratorConfig(model_id="claude-3-haiku"),
    )
    def test_low_impact_trigger_generates_simple_narrative(
        self, _mock_model, mock_narrative, mock_story, mock_classify, mock_bio, mock_graph, db
    ):
        """hub_figure trigger calls generate_connection_narrative, not generate_relationship_story."""
        author = Author(name="Hub Author")
        db.add(author)
        db.flush()
        db.commit()

        mock_bio.return_value = {"biography": "A bio", "personal_stories": []}
        mock_classify.return_value = "hub_figure"
        mock_narrative.return_value = "A simple narrative"

        source = _make_graph_node("author:1", author.id, "Hub Author")
        target = _make_graph_node("publisher:2", 2, "Pub", node_type="publisher")
        edge = _make_graph_edge("author:1", "publisher:2")
        graph = MagicMock()
        graph.nodes = [source, target]
        graph.edges = [edge]
        mock_graph.return_value = graph

        result = generate_and_cache_profile(db, "author", author.id)

        mock_narrative.assert_called_once()
        mock_story.assert_not_called()
        assert f"author:{author.id}:publisher:2" in result.connection_narratives

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.generate_bio_and_stories")
    @patch("app.services.entity_profile.classify_connection")
    @patch("app.services.entity_profile.generate_relationship_story")
    @patch("app.services.entity_profile.generate_connection_narrative")
    @patch(
        "app.services.entity_profile.GeneratorConfig.resolve",
        return_value=GeneratorConfig(model_id="claude-3-haiku"),
    )
    def test_no_trigger_skips_narrative_generation(
        self, _mock_model, mock_narrative, mock_story, mock_classify, mock_bio, mock_graph, db
    ):
        """No trigger means no AI generation for that connection."""
        author = Author(name="Skip Author")
        db.add(author)
        db.flush()
        db.commit()

        mock_bio.return_value = {"biography": "A bio", "personal_stories": []}
        mock_classify.return_value = None

        source = _make_graph_node("author:1", author.id, "Skip Author")
        target = _make_graph_node("publisher:2", 2, "Pub", node_type="publisher")
        edge = _make_graph_edge("author:1", "publisher:2")
        graph = MagicMock()
        graph.nodes = [source, target]
        graph.edges = [edge]
        mock_graph.return_value = graph

        result = generate_and_cache_profile(db, "author", author.id)

        mock_narrative.assert_not_called()
        mock_story.assert_not_called()
        assert result.connection_narratives == {}
        assert result.relationship_stories == {}

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.generate_bio_and_stories")
    @patch("app.services.entity_profile.classify_connection")
    @patch("app.services.entity_profile.generate_relationship_story")
    @patch("app.services.entity_profile.generate_connection_narrative")
    @patch(
        "app.services.entity_profile.GeneratorConfig.resolve",
        return_value=GeneratorConfig(model_id="claude-3-haiku"),
    )
    def test_max_narratives_respected(
        self, _mock_model, mock_narrative, mock_story, mock_classify, mock_bio, mock_graph, db
    ):
        """max_narratives limits total AI generations."""
        author = Author(name="Max Author")
        db.add(author)
        db.flush()
        db.commit()

        mock_bio.return_value = {"biography": "A bio", "personal_stories": []}
        mock_classify.return_value = "hub_figure"
        mock_narrative.return_value = "A narrative"

        source = _make_graph_node("author:1", author.id, "Max Author")
        targets = [
            _make_graph_node(f"publisher:{i}", i, f"Pub {i}", node_type="publisher")
            for i in range(2, 7)
        ]
        edges = [_make_graph_edge("author:1", f"publisher:{i}") for i in range(2, 7)]
        graph = MagicMock()
        graph.nodes = [source] + targets
        graph.edges = edges
        mock_graph.return_value = graph

        generate_and_cache_profile(db, "author", author.id, max_narratives=2)

        assert mock_narrative.call_count == 2

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.generate_bio_and_stories")
    @patch("app.services.entity_profile.classify_connection")
    @patch("app.services.entity_profile.generate_relationship_story")
    @patch("app.services.entity_profile.generate_connection_narrative")
    @patch(
        "app.services.entity_profile.GeneratorConfig.resolve",
        return_value=GeneratorConfig(model_id="claude-3-haiku"),
    )
    def test_regeneration_preserves_existing_relationship_stories(
        self, _mock_model, mock_narrative, mock_story, mock_classify, mock_bio, mock_graph, db
    ):
        """Regeneration merges new stories into existing ones instead of replacing."""
        author = Author(name="Merge Author")
        db.add(author)
        db.flush()

        # Pre-existing profile with an externally-populated story
        existing_profile = EntityProfile(
            entity_type="author",
            entity_id=author.id,
            bio_summary="Old bio",
            relationship_stories={
                "author:1:binder:99": {
                    "summary": "Existing story",
                    "details": [],
                    "narrative_style": "prose-paragraph",
                }
            },
        )
        db.add(existing_profile)
        db.commit()

        mock_bio.return_value = {"biography": "New bio", "personal_stories": []}
        mock_classify.return_value = "cross_era_bridge"
        mock_story.return_value = {
            "summary": "New cross-era story",
            "details": [],
            "narrative_style": "prose-paragraph",
        }

        source = _make_graph_node(
            "author:1", author.id, "Merge Author", era="victorian", birth_year=1809
        )
        target = _make_graph_node(
            "publisher:2", 2, "Pub", node_type="publisher", era="romantic", founded_year=1768
        )
        edge = _make_graph_edge("author:1", "publisher:2")
        graph = MagicMock()
        graph.nodes = [source, target]
        graph.edges = [edge]
        mock_graph.return_value = graph

        result = generate_and_cache_profile(db, "author", author.id)

        # New story is present
        assert f"author:{author.id}:publisher:2" in result.relationship_stories
        # Existing story is preserved (merged, not overwritten)
        assert "author:1:binder:99" in result.relationship_stories
        assert result.relationship_stories["author:1:binder:99"]["summary"] == "Existing story"

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.generate_bio_and_stories")
    @patch("app.services.entity_profile.classify_connection")
    @patch(
        "app.services.entity_profile.GeneratorConfig.resolve",
        return_value=GeneratorConfig(model_id="claude-3-haiku"),
    )
    def test_null_bio_from_ai_logs_warning_and_creates_profile(
        self, _mock_model, mock_classify, mock_bio, mock_graph, db, caplog
    ):
        """AI returning null biography logs a warning but still creates profile (#1717).

        generate_bio_and_stories can return {"biography": None}. The service
        should log a warning and still persist the profile (with bio_summary=None).
        """
        import logging

        author = Author(name="Null Bio Author")
        db.add(author)
        db.flush()
        db.commit()

        mock_bio.return_value = {"biography": None, "personal_stories": []}
        mock_classify.return_value = None

        source = _make_graph_node("author:1", author.id, "Null Bio Author")
        graph = MagicMock()
        graph.nodes = [source]
        graph.edges = []
        mock_graph.return_value = graph

        with caplog.at_level(logging.WARNING, logger="app.services.entity_profile"):
            result = generate_and_cache_profile(db, "author", author.id)

        # Profile is created successfully with None bio
        assert result is not None
        assert result.bio_summary is None
        assert result.personal_stories == []

        # Warning was logged
        assert any("empty biography" in record.message for record in caplog.records)


@pytest.fixture(scope="function")
def admin_client(db):
    """Test client with admin role and real db_user for generate-all endpoints."""
    user = User(cognito_sub="test-admin-ep", email="admin-ep@example.com", role="admin")
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
    app.dependency_overrides[require_admin] = lambda: mock_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestGenerateAllAsync:
    """Tests for async batch generation endpoint (#1550)."""

    @patch("app.api.v1.entity_profile.send_profile_generation_jobs")
    def test_generate_all_returns_job_id(self, mock_send, admin_client, db):
        """POST /generate-all returns job_id and enqueues messages."""
        author = Author(name="Batch Author")
        db.add(author)
        db.commit()

        response = admin_client.post("/api/v1/entity/profiles/generate-all")
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == JobStatus.IN_PROGRESS
        assert data["total_entities"] >= 1
        mock_send.assert_called_once()

    @patch("app.api.v1.entity_profile.send_profile_generation_jobs")
    def test_generate_all_empty_returns_no_job(self, mock_send, admin_client, db):
        """POST /generate-all with no entities returns empty status."""
        response = admin_client.post("/api/v1/entity/profiles/generate-all")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "empty"
        assert data["total_entities"] == 0
        assert data["job_id"] is None
        mock_send.assert_not_called()

    @patch("app.api.v1.entity_profile.send_profile_generation_jobs")
    def test_generate_all_returns_existing_job(self, mock_send, admin_client, db):
        """Returns existing job if one is already in progress."""
        user = db.query(User).filter(User.cognito_sub == "test-admin-ep").first()
        job = ProfileGenerationJob(owner_id=user.id, status=JobStatus.IN_PROGRESS, total_entities=5)
        db.add(job)
        db.commit()

        response = admin_client.post("/api/v1/entity/profiles/generate-all")
        data = response.json()
        assert data["job_id"] == job.id
        assert data["status"] == JobStatus.IN_PROGRESS
        mock_send.assert_not_called()


class TestGenerateAllStatus:
    """Tests for batch generation status endpoint (#1550)."""

    def test_status_returns_job_progress(self, admin_client, db):
        """GET status returns job progress."""
        user = db.query(User).filter(User.cognito_sub == "test-admin-ep").first()
        job = ProfileGenerationJob(
            owner_id=user.id, status=JobStatus.IN_PROGRESS, total_entities=10, succeeded=7, failed=1
        )
        db.add(job)
        db.commit()

        response = admin_client.get(f"/api/v1/entity/profiles/generate-all/status/{job.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total_entities"] == 10
        assert data["succeeded"] == 7
        assert data["failed"] == 1

    def test_status_404_for_unknown_job(self, admin_client):
        """GET status returns 404 for unknown job."""
        response = admin_client.get("/api/v1/entity/profiles/generate-all/status/nonexistent-id")
        assert response.status_code == 404


class TestCancelJob:
    """Tests for cancel profile generation job endpoint (#1611)."""

    def test_cancel_in_progress_job(self, admin_client, db):
        """POST cancel marks in-progress job as cancelled."""
        user = db.query(User).filter(User.cognito_sub == "test-admin-ep").first()
        job = ProfileGenerationJob(
            owner_id=user.id,
            status=JobStatus.IN_PROGRESS,
            total_entities=264,
            succeeded=10,
            failed=2,
        )
        db.add(job)
        db.commit()

        response = admin_client.post(f"/api/v1/entity/profiles/generate-all/{job.id}/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job.id
        assert data["status"] == JobStatus.CANCELLED
        assert data["completed_at"] is not None

        # Verify DB state
        db.refresh(job)
        assert job.status == JobStatus.CANCELLED
        assert job.completed_at is not None

    def test_cancel_pending_job(self, admin_client, db):
        """POST cancel marks pending job as cancelled."""
        user = db.query(User).filter(User.cognito_sub == "test-admin-ep").first()
        job = ProfileGenerationJob(owner_id=user.id, status=JobStatus.PENDING, total_entities=100)
        db.add(job)
        db.commit()

        response = admin_client.post(f"/api/v1/entity/profiles/generate-all/{job.id}/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == JobStatus.CANCELLED

    def test_cancel_completed_job_returns_409(self, admin_client, db):
        """POST cancel on completed job returns 409 Conflict."""
        user = db.query(User).filter(User.cognito_sub == "test-admin-ep").first()
        job = ProfileGenerationJob(
            owner_id=user.id,
            status=JobStatus.COMPLETED,
            total_entities=10,
            succeeded=10,
            completed_at=datetime.now(UTC),
        )
        db.add(job)
        db.commit()

        response = admin_client.post(f"/api/v1/entity/profiles/generate-all/{job.id}/cancel")
        assert response.status_code == 409

    def test_cancel_already_cancelled_job_returns_409(self, admin_client, db):
        """POST cancel on already-cancelled job returns 409 Conflict."""
        user = db.query(User).filter(User.cognito_sub == "test-admin-ep").first()
        job = ProfileGenerationJob(
            owner_id=user.id,
            status=JobStatus.CANCELLED,
            total_entities=10,
            completed_at=datetime.now(UTC),
        )
        db.add(job)
        db.commit()

        response = admin_client.post(f"/api/v1/entity/profiles/generate-all/{job.id}/cancel")
        assert response.status_code == 409

    def test_cancel_nonexistent_job_returns_404(self, admin_client):
        """POST cancel on non-existent job returns 404."""
        response = admin_client.post("/api/v1/entity/profiles/generate-all/nonexistent-id/cancel")
        assert response.status_code == 404

    @patch("app.api.v1.entity_profile.send_profile_generation_jobs")
    def test_cancelled_job_unblocks_new_generate_all(self, mock_send, admin_client, db):
        """After cancelling a job, generate-all creates a new one."""
        user = db.query(User).filter(User.cognito_sub == "test-admin-ep").first()
        job = ProfileGenerationJob(
            owner_id=user.id, status=JobStatus.IN_PROGRESS, total_entities=264
        )
        db.add(job)
        author = Author(name="Cancel Test Author")
        db.add(author)
        db.commit()

        # Cancel the stale job
        cancel_resp = admin_client.post(f"/api/v1/entity/profiles/generate-all/{job.id}/cancel")
        assert cancel_resp.status_code == 200

        # Now generate-all should create a new job
        gen_resp = admin_client.post("/api/v1/entity/profiles/generate-all")
        assert gen_resp.status_code == 200
        data = gen_resp.json()
        assert data["job_id"] != job.id
        assert data["status"] == JobStatus.IN_PROGRESS

    def test_cancel_failed_job_returns_409(self, admin_client, db):
        """POST cancel on failed job returns 409 Conflict."""
        user = db.query(User).filter(User.cognito_sub == "test-admin-ep").first()
        job = ProfileGenerationJob(
            owner_id=user.id,
            status=JobStatus.FAILED,
            total_entities=10,
            completed_at=datetime.now(UTC),
        )
        db.add(job)
        db.commit()

        response = admin_client.post(f"/api/v1/entity/profiles/generate-all/{job.id}/cancel")
        assert response.status_code == 409

    def test_cancel_requires_admin_auth(self, viewer_client, db):
        """Viewer auth gets 403 on cancel endpoint (require_admin)."""
        response = viewer_client.post("/api/v1/entity/profiles/generate-all/some-job-id/cancel")
        assert response.status_code == 403


class TestBuildStatsAggregation:
    """Tests for _build_stats condition_distribution and acquisition_by_year (#1633)."""

    def _make_book(self, **kwargs):
        """Create a Book with sensible defaults for stats testing."""
        defaults = {
            "title": "Test Book",
            "status": "ON_HAND",
            "year_start": None,
            "value_mid": None,
            "is_first_edition": False,
            "condition_grade": None,
            "purchase_date": None,
        }
        defaults.update(kwargs)
        return Book(**defaults)

    def test_mixed_conditions(self, db):
        """Books with varied condition grades produce correct counts per grade."""
        books = [
            self._make_book(title="Fine Book", condition_grade="FINE"),
            self._make_book(title="Near Fine Book", condition_grade="NEAR_FINE"),
            self._make_book(title="VG Book 1", condition_grade="VERY_GOOD"),
            self._make_book(title="VG Book 2", condition_grade="VERY_GOOD"),
            self._make_book(title="Good Book", condition_grade="GOOD"),
        ]

        stats = _build_stats(books)

        assert stats.condition_distribution == {
            "FINE": 1,
            "NEAR_FINE": 1,
            "VERY_GOOD": 2,
            "GOOD": 1,
        }

    def test_null_conditions_counted_as_ungraded(self, db):
        """Books with null condition_grade are counted as 'UNGRADED'."""
        books = [
            self._make_book(title="Graded", condition_grade="FINE"),
            self._make_book(title="Ungraded 1", condition_grade=None),
            self._make_book(title="Ungraded 2", condition_grade=None),
        ]

        stats = _build_stats(books)

        assert stats.condition_distribution == {
            "FINE": 1,
            "UNGRADED": 2,
        }

    def test_acquisition_by_year(self, db):
        """Books with varied purchase_date values produce correct year grouping."""
        books = [
            self._make_book(title="Book 2020", purchase_date=date(2020, 3, 15)),
            self._make_book(title="Book 2020b", purchase_date=date(2020, 11, 1)),
            self._make_book(title="Book 2021", purchase_date=date(2021, 6, 20)),
            self._make_book(title="Book 2023", purchase_date=date(2023, 1, 5)),
        ]

        stats = _build_stats(books)

        assert stats.acquisition_by_year == {
            2020: 2,
            2021: 1,
            2023: 1,
        }

    def test_empty_books_returns_empty_dicts(self, db):
        """Empty book list produces empty dicts for both new fields."""
        stats = _build_stats([])

        assert stats.condition_distribution == {}
        assert stats.acquisition_by_year == {}

    def test_no_acquisition_dates_returns_empty_dict(self, db):
        """Books all without purchase_date produce empty acquisition_by_year."""
        books = [
            self._make_book(title="No Date 1", condition_grade="FINE"),
            self._make_book(title="No Date 2", condition_grade="GOOD"),
        ]

        stats = _build_stats(books)

        assert stats.acquisition_by_year == {}
        # condition_distribution should still be populated
        assert stats.condition_distribution == {"FINE": 1, "GOOD": 1}


class TestValidateAIConnections:
    """Tests for _validate_ai_connections() (#1805)."""

    def test_valid_connections_pass_through(self):
        """Valid connections are returned unchanged."""
        raw = [
            {
                "target_type": "author",
                "target_id": 227,
                "relationship": "family",
                "sub_type": "MARRIAGE",
                "confidence": 0.95,
                "evidence": "Married in 1846",
            }
        ]
        all_ids = {"author:31", "author:227"}
        result = _validate_ai_connections(raw, "author", 31, all_ids)
        assert len(result) == 1
        assert result[0]["relationship"] == "family"
        assert result[0]["sub_type"] == "MARRIAGE"
        assert result[0]["confidence"] == 0.95

    def test_empty_connections_return_empty(self):
        """Empty input returns empty list."""
        result = _validate_ai_connections([], "author", 1, set())
        assert result == []

    def test_self_connection_filtered(self):
        """Connections from entity to itself are filtered out."""
        raw = [
            {
                "target_type": "author",
                "target_id": 31,
                "relationship": "family",
                "confidence": 0.9,
            }
        ]
        all_ids = {"author:31"}
        result = _validate_ai_connections(raw, "author", 31, all_ids)
        assert result == []

    def test_invalid_relationship_type_filtered(self):
        """Connections with invalid relationship types are filtered."""
        raw = [
            {
                "target_type": "author",
                "target_id": 227,
                "relationship": "enemy",  # Not a valid type
                "confidence": 0.8,
            }
        ]
        all_ids = {"author:31", "author:227"}
        result = _validate_ai_connections(raw, "author", 31, all_ids)
        assert result == []

    def test_non_collection_entity_filtered(self):
        """Connections to entities not in the collection are filtered."""
        raw = [
            {
                "target_type": "author",
                "target_id": 9999,
                "relationship": "friendship",
                "confidence": 0.7,
            }
        ]
        all_ids = {"author:31", "author:227"}
        result = _validate_ai_connections(raw, "author", 31, all_ids)
        assert result == []

    def test_duplicate_connections_deduped(self):
        """Duplicate connections (same pair + relationship) are deduplicated."""
        raw = [
            {
                "target_type": "author",
                "target_id": 227,
                "relationship": "family",
                "confidence": 0.95,
                "evidence": "First mention",
            },
            {
                "target_type": "author",
                "target_id": 227,
                "relationship": "family",
                "confidence": 0.90,
                "evidence": "Second mention",
            },
        ]
        all_ids = {"author:31", "author:227"}
        result = _validate_ai_connections(raw, "author", 31, all_ids)
        assert len(result) == 1

    def test_bad_json_entries_skipped(self):
        """Non-dict entries in the list are skipped."""
        raw = [
            "not a dict",
            42,
            None,
            {
                "target_type": "author",
                "target_id": 227,
                "relationship": "friendship",
                "confidence": 0.7,
            },
        ]
        all_ids = {"author:31", "author:227"}
        result = _validate_ai_connections(raw, "author", 31, all_ids)
        assert len(result) == 1

    def test_confidence_clamped(self):
        """Confidence values are clamped to 0.0-1.0 range."""
        raw = [
            {
                "target_type": "author",
                "target_id": 227,
                "relationship": "family",
                "confidence": 2.5,
            }
        ]
        all_ids = {"author:31", "author:227"}
        result = _validate_ai_connections(raw, "author", 31, all_ids)
        assert result[0]["confidence"] == 1.0

    def test_missing_confidence_defaults_to_half(self):
        """Missing confidence defaults to 0.5."""
        raw = [
            {
                "target_type": "author",
                "target_id": 227,
                "relationship": "family",
            }
        ]
        all_ids = {"author:31", "author:227"}
        result = _validate_ai_connections(raw, "author", 31, all_ids)
        assert result[0]["confidence"] == 0.5


class TestGenerateAIConnections:
    """Tests for generate_ai_connections() (#1805)."""

    @patch("app.services.ai_profile_generator._invoke")
    def test_valid_response_parsed(self, mock_invoke):
        """Valid AI response is parsed and validated."""
        mock_invoke.return_value = '{"connections": [{"target_type": "author", "target_id": 227, "relationship": "family", "sub_type": "MARRIAGE", "confidence": 0.95, "evidence": "Married in 1846"}]}'
        config = GeneratorConfig(model_id="test-model")
        all_entities = [
            {"entity_type": "author", "entity_id": 31, "name": "EBB"},
            {"entity_type": "author", "entity_id": 227, "name": "RB"},
        ]
        result = generate_ai_connections("EBB", "author", 31, all_entities, config=config)
        assert len(result) == 1
        assert result[0]["relationship"] == "family"

    @patch("app.services.ai_profile_generator._invoke")
    def test_empty_all_entities_returns_empty(self, mock_invoke):
        """Empty all_entities list returns empty without calling AI."""
        config = GeneratorConfig(model_id="test-model")
        result = generate_ai_connections("EBB", "author", 31, [], config=config)
        assert result == []
        mock_invoke.assert_not_called()

    @patch("app.services.ai_profile_generator._invoke")
    def test_ai_failure_returns_empty(self, mock_invoke):
        """AI invocation failure returns empty list."""
        mock_invoke.side_effect = RuntimeError("API error")
        config = GeneratorConfig(model_id="test-model")
        all_entities = [
            {"entity_type": "author", "entity_id": 31, "name": "EBB"},
        ]
        result = generate_ai_connections("EBB", "author", 31, all_entities, config=config)
        assert result == []

    @patch("app.services.ai_profile_generator._invoke")
    def test_malformed_json_returns_empty(self, mock_invoke):
        """Malformed JSON response returns empty list."""
        mock_invoke.return_value = "not valid json at all"
        config = GeneratorConfig(model_id="test-model")
        all_entities = [
            {"entity_type": "author", "entity_id": 31, "name": "EBB"},
        ]
        result = generate_ai_connections("EBB", "author", 31, all_entities, config=config)
        assert result == []


class TestBuildConnectionsAIMerge:
    """Tests for AI connection merge in _build_connections (#1803)."""

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.classify_connection", return_value=None)
    def test_ai_connections_appear_in_build_connections(self, _mock_classify, mock_graph, db):
        """AI connections from profile are included in _build_connections output."""
        author1 = Author(name="Elizabeth Barrett Browning", birth_year=1806, death_year=1861)
        author2 = Author(name="Robert Browning", birth_year=1812, death_year=1889)
        db.add_all([author1, author2])
        db.flush()

        profile = EntityProfile(
            entity_type="author",
            entity_id=author1.id,
            ai_connections=[
                {
                    "source_type": "author",
                    "source_id": author1.id,
                    "target_type": "author",
                    "target_id": author2.id,
                    "relationship": "family",
                    "sub_type": "MARRIAGE",
                    "confidence": 0.95,
                    "evidence": "Married in 1846",
                }
            ],
        )
        db.add(profile)
        db.commit()

        source = _make_graph_node(
            f"author:{author1.id}", author1.id, "EBB", era="victorian", birth_year=1806
        )
        target = _make_graph_node(
            f"author:{author2.id}", author2.id, "RB", era="victorian", birth_year=1812
        )

        graph = MagicMock()
        graph.nodes = [source, target]
        graph.edges = []
        mock_graph.return_value = graph

        connections = _build_connections(db, "author", author1.id, profile, graph=graph)

        ai_conns = [c for c in connections if c.is_ai_discovered]
        assert len(ai_conns) == 1
        assert ai_conns[0].connection_type == "family"
        assert ai_conns[0].sub_type == "MARRIAGE"
        assert ai_conns[0].confidence == 0.95
        assert ai_conns[0].narrative == "Married in 1846"

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.classify_connection", return_value=None)
    def test_ai_connections_get_key_priority(self, _mock_classify, mock_graph, db):
        """AI-discovered connections are prioritized for key slots."""
        author = Author(name="Darwin", birth_year=1809, death_year=1882)
        db.add(author)
        db.flush()

        # Create several graph targets
        targets = []
        edges = []
        for i in range(2, 8):
            t = _make_graph_node(f"publisher:{i}", i, f"Pub {i}", node_type="publisher")
            targets.append(t)
            e = _make_graph_edge(f"author:{author.id}", f"publisher:{i}", shared_book_ids=[100 + i])
            edges.append(e)

        # Also create a target for AI connection
        ai_target = _make_graph_node("author:99", 99, "AI Friend", era="victorian", birth_year=1820)
        targets.append(ai_target)

        profile = EntityProfile(
            entity_type="author",
            entity_id=author.id,
            ai_connections=[
                {
                    "source_type": "author",
                    "source_id": author.id,
                    "target_type": "author",
                    "target_id": 99,
                    "relationship": "friendship",
                    "sub_type": "CLOSE_FRIENDS",
                    "confidence": 0.8,
                    "evidence": "Were close friends",
                }
            ],
        )
        db.add(profile)
        db.commit()

        source = _make_graph_node(f"author:{author.id}", author.id, "Darwin")
        graph = MagicMock()
        graph.nodes = [source] + targets
        graph.edges = edges
        mock_graph.return_value = graph

        connections = _build_connections(db, "author", author.id, profile, graph=graph)

        # The AI connection should be marked as key
        ai_conn = next(c for c in connections if c.is_ai_discovered)
        assert ai_conn.is_key is True


class TestPipelineAIConnections:
    """Tests for AI connections in generate_and_cache_profile pipeline (#1806)."""

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.generate_bio_and_stories")
    @patch("app.services.entity_profile.generate_ai_connections")
    @patch("app.services.entity_profile.classify_connection")
    @patch(
        "app.services.entity_profile.GeneratorConfig.resolve",
        return_value=GeneratorConfig(model_id="claude-3-haiku"),
    )
    def test_ai_connections_stored_in_profile(
        self, _mock_model, mock_classify, mock_ai_conn, mock_bio, mock_graph, db
    ):
        """generate_and_cache_profile stores AI connections in the profile."""
        author = Author(name="Browning", birth_year=1812, death_year=1889)
        db.add(author)
        db.flush()
        db.commit()

        mock_bio.return_value = {"biography": "A bio", "personal_stories": []}
        mock_classify.return_value = None
        mock_ai_conn.return_value = [
            {
                "source_type": "author",
                "source_id": author.id,
                "target_type": "author",
                "target_id": 99,
                "relationship": "family",
                "sub_type": "MARRIAGE",
                "confidence": 0.95,
                "evidence": "Married EBB",
            }
        ]

        source = _make_graph_node(f"author:{author.id}", author.id, "Browning")
        graph = MagicMock()
        graph.nodes = [source]
        graph.edges = []
        mock_graph.return_value = graph

        result = generate_and_cache_profile(db, "author", author.id)

        assert result.ai_connections is not None
        assert len(result.ai_connections) == 1
        assert result.ai_connections[0]["relationship"] == "family"

    @patch("app.services.entity_profile.get_or_build_graph")
    @patch("app.services.entity_profile.generate_bio_and_stories")
    @patch("app.services.entity_profile.generate_ai_connections")
    @patch("app.services.entity_profile.classify_connection")
    @patch(
        "app.services.entity_profile.GeneratorConfig.resolve",
        return_value=GeneratorConfig(model_id="claude-3-haiku"),
    )
    def test_empty_ai_connections_stored(
        self, _mock_model, mock_classify, mock_ai_conn, mock_bio, mock_graph, db
    ):
        """Empty AI connections are stored as empty list."""
        author = Author(name="Obscure Author")
        db.add(author)
        db.flush()
        db.commit()

        mock_bio.return_value = {"biography": "A bio", "personal_stories": []}
        mock_classify.return_value = None
        mock_ai_conn.return_value = []

        source = _make_graph_node(f"author:{author.id}", author.id, "Obscure Author")
        graph = MagicMock()
        graph.nodes = [source]
        graph.edges = []
        mock_graph.return_value = graph

        result = generate_and_cache_profile(db, "author", author.id)

        assert result.ai_connections == []
