"""Tests for POST /admin/maintenance/portrait-sync endpoint."""

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.author import Author
from app.models.publisher import Publisher


class TestPortraitSyncEndpoint:
    """Tests for the portrait sync admin endpoint."""

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_default_dry_run_true(self, mock_query, mock_sleep, client: TestClient, db: Session):
        author = Author(name="Charles Dickens", birth_year=1812, death_year=1870)
        db.add(author)
        db.flush()

        mock_query.return_value = [
            {
                "item": {"value": "http://wd/Q5686"},
                "itemLabel": {"value": "Charles Dickens"},
                "birth": {"value": "1812-02-07T00:00:00Z"},
                "death": {"value": "1870-06-09T00:00:00Z"},
                "image": {"value": "http://commons.wikimedia.org/wiki/Special:FilePath/D.jpg"},
                "occupationLabel": {"value": "novelist"},
            }
        ]

        response = client.post(
            "/api/v1/admin/maintenance/portrait-sync",
            params={"entity_type": "author", "entity_ids": [author.id]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["dry_run"] is True
        assert data["threshold"] == 0.7
        assert "summary" in data
        assert "results" in data

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_response_shape(self, mock_query, mock_sleep, client: TestClient, db: Session):
        author = Author(name="Nobody Special")
        db.add(author)
        db.flush()

        mock_query.return_value = []

        response = client.post(
            "/api/v1/admin/maintenance/portrait-sync",
            params={"entity_type": "author", "entity_ids": [author.id]},
        )

        assert response.status_code == 200
        data = response.json()

        assert "dry_run" in data
        assert "threshold" in data
        assert "summary" in data
        assert "results" in data

        summary = data["summary"]
        for key in [
            "total_processed",
            "skipped_existing",
            "matched",
            "uploaded",
            "no_results",
            "below_threshold",
            "no_portrait",
            "download_failed",
            "upload_failed",
            "processing_failed",
            "duration_seconds",
            "fallback_commons_sdc",
            "fallback_google_kg",
            "fallback_nls_map",
        ]:
            assert key in summary, f"Missing summary field: {key}"

        assert len(data["results"]) == 1
        result = data["results"][0]
        for key in [
            "entity_type",
            "entity_id",
            "entity_name",
            "status",
            "score",
            "image_source",
        ]:
            assert key in result, f"Missing result field: {key}"

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_entity_type_filter(self, mock_query, mock_sleep, client: TestClient, db: Session):
        author = Author(name="Test Author")
        publisher = Publisher(name="Test Publisher")
        db.add_all([author, publisher])
        db.flush()

        mock_query.return_value = []

        response = client.post(
            "/api/v1/admin/maintenance/portrait-sync",
            params={"entity_type": "publisher"},
        )

        assert response.status_code == 200
        data = response.json()
        for r in data["results"]:
            assert r["entity_type"] == "publisher"

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_entity_ids_filter(self, mock_query, mock_sleep, client: TestClient, db: Session):
        a1 = Author(name="Author One")
        a2 = Author(name="Author Two")
        db.add_all([a1, a2])
        db.flush()

        mock_query.return_value = []

        response = client.post(
            "/api/v1/admin/maintenance/portrait-sync",
            params={"entity_type": "author", "entity_ids": [a1.id]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total_processed"] == 1
        assert data["results"][0]["entity_id"] == a1.id

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_threshold_parameter(self, mock_query, mock_sleep, client: TestClient, db: Session):
        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        mock_query.return_value = []

        response = client.post(
            "/api/v1/admin/maintenance/portrait-sync",
            params={"threshold": 0.9, "entity_type": "author"},
        )

        assert response.status_code == 200
        assert response.json()["threshold"] == 0.9

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_skip_existing_default(self, mock_query, mock_sleep, client: TestClient, db: Session):
        author = Author(name="Has Portrait", image_url="https://cdn.example.com/portrait.jpg")
        db.add(author)
        db.flush()

        response = client.post(
            "/api/v1/admin/maintenance/portrait-sync",
            params={"entity_type": "author", "entity_ids": [author.id]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["skipped_existing"] == 1
        mock_query.assert_not_called()

    def test_non_admin_returns_403(self, viewer_client: TestClient):
        response = viewer_client.post("/api/v1/admin/maintenance/portrait-sync")
        assert response.status_code == 403

    def test_entity_ids_without_type_returns_400(self, client: TestClient):
        response = client.post(
            "/api/v1/admin/maintenance/portrait-sync",
            params={"entity_ids": [1, 2]},
        )
        assert response.status_code == 400
        assert "entity_type is required" in response.json()["detail"]

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_too_many_entities_returns_400(
        self, mock_query, mock_sleep, client: TestClient, db: Session
    ):
        for i in range(11):
            db.add(Author(name=f"Author {i}"))
        db.flush()

        response = client.post(
            "/api/v1/admin/maintenance/portrait-sync",
            params={"entity_type": "author"},
        )
        assert response.status_code == 400
        assert "Too many entities" in response.json()["detail"]

    @patch("app.services.portrait_sync.time.sleep")
    @patch("app.services.portrait_sync._search_commons_sdc")
    @patch("app.services.portrait_sync.query_wikidata")
    def test_enable_fallbacks_param(
        self, mock_query, mock_commons, mock_sleep, client: TestClient, db: Session
    ):
        """enable_fallbacks=true should trigger fallback providers."""
        author = Author(name="Test Author")
        db.add(author)
        db.flush()

        mock_query.return_value = []
        mock_commons.return_value = "https://upload.wikimedia.org/thumb/test.jpg"

        response = client.post(
            "/api/v1/admin/maintenance/portrait-sync",
            params={
                "entity_type": "author",
                "entity_ids": [author.id],
                "enable_fallbacks": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["results"][0]["image_source"] == "commons_sdc"
        assert data["summary"]["fallback_commons_sdc"] == 1
