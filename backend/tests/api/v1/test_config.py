"""Tests for public config endpoints."""

from fastapi.testclient import TestClient

from app.services.bedrock import MODEL_DISPLAY_NAMES


class TestModelLabelsEndpoint:
    """Tests for GET /api/v1/config/model-labels."""

    def test_returns_labels(self, client: TestClient):
        """Should return all active model display names."""
        response = client.get("/api/v1/config/model-labels")
        assert response.status_code == 200

        data = response.json()
        assert "labels" in data
        labels = data["labels"]

        # Should contain all active models
        assert "sonnet" in labels
        assert "opus" in labels
        assert "haiku" in labels

        # Values should match the registry
        for key, display_name in MODEL_DISPLAY_NAMES.items():
            assert labels[key] == display_name

    def test_no_auth_required(self, unauthenticated_client: TestClient):
        """Public endpoint should work without authentication."""
        response = unauthenticated_client.get("/api/v1/config/model-labels")
        assert response.status_code == 200

        data = response.json()
        assert "labels" in data
        assert len(data["labels"]) > 0

    def test_viewer_can_access(self, viewer_client: TestClient):
        """Viewers should be able to access model labels."""
        response = viewer_client.get("/api/v1/config/model-labels")
        assert response.status_code == 200

    def test_labels_match_display_names(self, client: TestClient):
        """Labels in response should exactly match MODEL_DISPLAY_NAMES from registry."""
        response = client.get("/api/v1/config/model-labels")
        data = response.json()

        assert data["labels"] == MODEL_DISPLAY_NAMES
