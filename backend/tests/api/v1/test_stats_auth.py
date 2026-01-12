"""Tests for stats endpoint authentication.

Uses shared fixtures from conftest.py:
- db: Fresh database for each test
- unauthenticated_client: Client without auth (expects 401)
- client: Client with full auth (expects 200)
"""

import pytest

STATS_ENDPOINTS = [
    "/api/v1/stats/overview",
    "/api/v1/stats/metrics",
    "/api/v1/stats/by-category",
    "/api/v1/stats/by-condition",
    "/api/v1/stats/by-publisher",
    "/api/v1/stats/by-author",
    "/api/v1/stats/bindings",
    "/api/v1/stats/by-era",
    "/api/v1/stats/pending-deliveries",
    "/api/v1/stats/acquisitions-by-month",
    "/api/v1/stats/acquisitions-daily",
    "/api/v1/stats/value-by-category",
    "/api/v1/stats/dashboard",
]


class TestStatsAuth:
    """Tests for stats endpoint authentication requirements."""

    @pytest.mark.parametrize("endpoint", STATS_ENDPOINTS)
    def test_stats_endpoint_requires_auth(self, unauthenticated_client, endpoint):
        """Test that stats endpoints return 401 without authentication."""
        response = unauthenticated_client.get(endpoint)
        assert response.status_code == 401, f"{endpoint} should require auth"

    @pytest.mark.parametrize("endpoint", STATS_ENDPOINTS)
    def test_stats_endpoint_works_with_auth(self, client, endpoint):
        """Test that stats endpoints work with authentication."""
        response = client.get(endpoint)
        assert response.status_code == 200, f"{endpoint} should work with auth"
