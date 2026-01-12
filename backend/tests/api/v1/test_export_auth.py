"""Tests for export endpoint authentication.

Uses shared fixtures from conftest.py:
- unauthenticated_client: Client without auth (expects 401)
- client: Client with full auth (expects 200)
"""


class TestExportAuth:
    """Tests for export endpoint authentication requirements."""

    def test_export_csv_requires_auth(self, unauthenticated_client):
        """Test that /export/csv returns 401 without authentication."""
        response = unauthenticated_client.get("/api/v1/export/csv")
        assert response.status_code == 401

    def test_export_json_requires_auth(self, unauthenticated_client):
        """Test that /export/json returns 401 without authentication."""
        response = unauthenticated_client.get("/api/v1/export/json")
        assert response.status_code == 401

    def test_export_csv_works_with_auth(self, client):
        """Test that /export/csv works with authentication."""
        response = client.get("/api/v1/export/csv")
        assert response.status_code == 200

    def test_export_json_works_with_auth(self, client):
        """Test that /export/json works with authentication."""
        response = client.get("/api/v1/export/json")
        assert response.status_code == 200
