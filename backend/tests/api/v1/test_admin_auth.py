"""Tests for admin GET endpoint authentication.

Uses shared fixtures from conftest.py:
- unauthenticated_client: Client without auth (expects 401)
- viewer_client: Client with viewer auth (expects 403 on admin endpoints)
- client: Client with admin auth (expects 200)
"""

from unittest.mock import patch


class TestAdminGetAuth:
    """Tests for admin GET endpoint authentication requirements."""

    # Unauthenticated access tests (401)
    def test_admin_config_requires_auth(self, unauthenticated_client):
        """Test that GET /admin/config returns 401 without authentication."""
        response = unauthenticated_client.get("/api/v1/admin/config")
        assert response.status_code == 401

    def test_admin_system_info_requires_auth(self, unauthenticated_client):
        """Test that GET /admin/system-info returns 401 without authentication."""
        response = unauthenticated_client.get("/api/v1/admin/system-info")
        assert response.status_code == 401

    def test_admin_costs_requires_auth(self, unauthenticated_client):
        """Test that GET /admin/costs returns 401 without authentication."""
        response = unauthenticated_client.get("/api/v1/admin/costs")
        assert response.status_code == 401

    # Role escalation tests - viewer should NOT access admin endpoints (403)
    def test_admin_config_forbidden_for_viewer(self, viewer_client):
        """Test that GET /admin/config returns 403 for viewer role."""
        response = viewer_client.get("/api/v1/admin/config")
        assert response.status_code == 403, "Viewer should not access admin config"

    def test_admin_system_info_forbidden_for_viewer(self, viewer_client):
        """Test that GET /admin/system-info returns 403 for viewer role."""
        response = viewer_client.get("/api/v1/admin/system-info")
        assert response.status_code == 403, "Viewer should not access system info"

    def test_admin_costs_forbidden_for_viewer(self, viewer_client):
        """Test that GET /admin/costs returns 403 for viewer role."""
        response = viewer_client.get("/api/v1/admin/costs")
        assert response.status_code == 403, "Viewer should not access costs"

    # Admin access tests (200)
    def test_admin_config_works_with_admin(self, client):
        """Test that GET /admin/config works with admin authentication."""
        response = client.get("/api/v1/admin/config")
        assert response.status_code == 200

    def test_admin_system_info_works_with_admin(self, client):
        """Test that GET /admin/system-info works with admin authentication."""
        response = client.get("/api/v1/admin/system-info")
        assert response.status_code == 200

    def test_admin_costs_works_with_admin(self, client):
        """Test that GET /admin/costs works with admin authentication."""
        mock_costs = {
            "period_start": "2026-01-01",
            "period_end": "2026-01-12",
            "bedrock_models": [],
            "daily_trend": [],
            "other_services": [],
            "total_mtd": 0.0,
            "bedrock_total": 0.0,
            "other_costs": {},
            "total_aws_cost": 0.0,
            "cached_at": "2026-01-12T00:00:00Z",
        }
        with patch("app.api.v1.admin.fetch_costs", return_value=mock_costs):
            response = client.get("/api/v1/admin/costs")
            assert response.status_code == 200
