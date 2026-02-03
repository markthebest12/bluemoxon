"""Tests for entity portrait schema and admin upload endpoint (#1632)."""

import io
from unittest.mock import MagicMock, patch

from PIL import Image

from app.models.author import Author
from app.models.binder import Binder
from app.models.publisher import Publisher
from app.schemas.entity_profile import EntityType, ProfileEntity
from app.services.entity_profile import _build_profile_entity


def _create_test_image(width=800, height=800, fmt="JPEG") -> bytes:
    """Create a minimal test image in memory."""
    img = Image.new("RGB", (width, height), color=(128, 64, 32))
    buf = io.BytesIO()
    img.save(buf, fmt)
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestProfileEntitySchema:
    """ProfileEntity correctly serializes image_url field."""

    def test_image_url_null_by_default(self):
        entity = ProfileEntity(id=1, type=EntityType.author, name="Dickens")
        assert entity.image_url is None

    def test_image_url_round_trips(self):
        url = "https://cdn.example.com/entities/author/1/portrait.jpg"
        entity = ProfileEntity(id=1, type=EntityType.author, name="Dickens", image_url=url)
        assert entity.image_url == url

    def test_image_url_in_model_dump(self):
        url = "https://cdn.example.com/entities/author/1/portrait.jpg"
        entity = ProfileEntity(id=1, type=EntityType.author, name="Dickens", image_url=url)
        data = entity.model_dump()
        assert "image_url" in data
        assert data["image_url"] == url

    def test_image_url_null_in_model_dump(self):
        entity = ProfileEntity(id=1, type=EntityType.author, name="Dickens")
        data = entity.model_dump()
        assert "image_url" in data
        assert data["image_url"] is None


# ---------------------------------------------------------------------------
# Service layer: _build_profile_entity includes image_url
# ---------------------------------------------------------------------------


class TestBuildProfileEntity:
    """_build_profile_entity maps image_url from entity model."""

    def test_author_with_image_url(self, db):
        author = Author(id=1, name="Dickens", image_url="https://cdn/portrait.jpg")
        db.add(author)
        db.flush()

        result = _build_profile_entity(author, "author")
        assert result.image_url == "https://cdn/portrait.jpg"

    def test_author_without_image_url(self, db):
        author = Author(id=2, name="Hardy")
        db.add(author)
        db.flush()

        result = _build_profile_entity(author, "author")
        assert result.image_url is None

    def test_publisher_with_image_url(self, db):
        pub = Publisher(id=1, name="Macmillan", image_url="https://cdn/pub.jpg")
        db.add(pub)
        db.flush()

        result = _build_profile_entity(pub, "publisher")
        assert result.image_url == "https://cdn/pub.jpg"

    def test_binder_with_image_url(self, db):
        binder = Binder(id=1, name="Zaehnsdorf", image_url="https://cdn/binder.jpg")
        db.add(binder)
        db.flush()

        result = _build_profile_entity(binder, "binder")
        assert result.image_url == "https://cdn/binder.jpg"


# ---------------------------------------------------------------------------
# Admin portrait upload endpoint
# ---------------------------------------------------------------------------


class TestUploadEntityPortrait:
    """PUT /api/v1/entity/{entity_type}/{entity_id}/portrait endpoint."""

    @patch("app.api.v1.entity_profile.get_s3_client")
    @patch(
        "app.api.v1.entity_profile.get_cloudfront_cdn_url", return_value="https://cdn.example.com"
    )
    def test_upload_portrait_success(self, mock_cdn, mock_s3, client, db):
        """Admin can upload a portrait image for an author."""
        # Create an author in the DB
        author = Author(id=1, name="Dickens")
        db.add(author)
        db.commit()

        mock_s3_client = MagicMock()
        mock_s3.return_value = mock_s3_client

        img_bytes = _create_test_image()

        response = client.put(
            "/api/v1/entity/author/1/portrait",
            files={"file": ("portrait.jpg", img_bytes, "image/jpeg")},
        )

        assert response.status_code == 200
        data = response.json()
        assert "image_url" in data
        assert "entities/author/1/portrait.jpg" in data["image_url"]

        # Verify S3 was called with the correct key (positional: Fileobj, Bucket, Key)
        mock_s3_client.upload_fileobj.assert_called_once()
        call_args = mock_s3_client.upload_fileobj.call_args
        s3_key_arg = call_args[0][2]  # Third positional arg is the S3 key
        assert s3_key_arg == "entities/author/1/portrait.jpg"

    @patch("app.api.v1.entity_profile.get_s3_client")
    @patch(
        "app.api.v1.entity_profile.get_cloudfront_cdn_url", return_value="https://cdn.example.com"
    )
    def test_upload_portrait_updates_entity(self, mock_cdn, mock_s3, client, db):
        """Upload updates the entity's image_url in the database."""
        author = Author(id=1, name="Dickens")
        db.add(author)
        db.commit()

        mock_s3.return_value = MagicMock()
        img_bytes = _create_test_image()

        response = client.put(
            "/api/v1/entity/author/1/portrait",
            files={"file": ("portrait.jpg", img_bytes, "image/jpeg")},
        )
        assert response.status_code == 200

        # Verify DB was updated
        db.refresh(author)
        assert author.image_url is not None
        assert "entities/author/1/portrait.jpg" in author.image_url

    def test_upload_portrait_invalid_entity_type(self, client, db):
        """Invalid entity type returns 400."""
        img_bytes = _create_test_image()
        response = client.put(
            "/api/v1/entity/invalid_type/1/portrait",
            files={"file": ("portrait.jpg", img_bytes, "image/jpeg")},
        )
        assert response.status_code == 400

    @patch("app.api.v1.entity_profile.get_s3_client")
    @patch(
        "app.api.v1.entity_profile.get_cloudfront_cdn_url", return_value="https://cdn.example.com"
    )
    def test_upload_portrait_entity_not_found(self, mock_cdn, mock_s3, client, db):
        """Non-existent entity returns 404."""
        img_bytes = _create_test_image()
        response = client.put(
            "/api/v1/entity/author/999/portrait",
            files={"file": ("portrait.jpg", img_bytes, "image/jpeg")},
        )
        assert response.status_code == 404

    def test_upload_portrait_non_admin_forbidden(self, viewer_client, db):
        """Non-admin user gets 403."""
        author = Author(id=1, name="Dickens")
        db.add(author)
        db.commit()

        img_bytes = _create_test_image()
        response = viewer_client.put(
            "/api/v1/entity/author/1/portrait",
            files={"file": ("portrait.jpg", img_bytes, "image/jpeg")},
        )
        assert response.status_code == 403

    @patch("app.api.v1.entity_profile.get_s3_client")
    @patch(
        "app.api.v1.entity_profile.get_cloudfront_cdn_url", return_value="https://cdn.example.com"
    )
    def test_upload_portrait_publisher(self, mock_cdn, mock_s3, client, db):
        """Upload works for publisher entity type."""
        pub = Publisher(id=1, name="Macmillan")
        db.add(pub)
        db.commit()

        mock_s3.return_value = MagicMock()
        img_bytes = _create_test_image()

        response = client.put(
            "/api/v1/entity/publisher/1/portrait",
            files={"file": ("portrait.jpg", img_bytes, "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "entities/publisher/1/portrait.jpg" in data["image_url"]

    @patch("app.api.v1.entity_profile.get_s3_client")
    @patch(
        "app.api.v1.entity_profile.get_cloudfront_cdn_url", return_value="https://cdn.example.com"
    )
    def test_upload_portrait_binder(self, mock_cdn, mock_s3, client, db):
        """Upload works for binder entity type."""
        binder = Binder(id=1, name="Zaehnsdorf")
        db.add(binder)
        db.commit()

        mock_s3.return_value = MagicMock()
        img_bytes = _create_test_image()

        response = client.put(
            "/api/v1/entity/binder/1/portrait",
            files={"file": ("portrait.jpg", img_bytes, "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "entities/binder/1/portrait.jpg" in data["image_url"]
