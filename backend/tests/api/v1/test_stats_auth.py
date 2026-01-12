"""Tests for stats endpoint authentication."""

import pytest
from fastapi.testclient import TestClient

from app.auth import require_viewer
from app.db import get_db
from app.main import app
from app.models.base import Base
from tests.conftest import TestingSessionLocal, engine, get_mock_editor

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
    "/api/v1/stats/dashboard",
]


class TestStatsAuth:
    """Tests for stats endpoint authentication requirements."""

    @pytest.fixture
    def db(self):
        """Create a fresh database for each test."""
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            Base.metadata.drop_all(bind=engine)

    @pytest.fixture
    def unauthenticated_client(self, db):
        """Client without auth overrides."""

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    @pytest.fixture
    def authenticated_client(self, db):
        """Client with auth overrides for require_viewer."""

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[require_viewer] = get_mock_editor
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    @pytest.mark.parametrize("endpoint", STATS_ENDPOINTS)
    def test_stats_endpoint_requires_auth(self, unauthenticated_client, endpoint):
        """Test that stats endpoints return 401 without authentication."""
        response = unauthenticated_client.get(endpoint)
        assert response.status_code == 401, f"{endpoint} should require auth"

    @pytest.mark.parametrize("endpoint", STATS_ENDPOINTS)
    def test_stats_endpoint_works_with_auth(self, authenticated_client, endpoint):
        """Test that stats endpoints work with authentication."""
        response = authenticated_client.get(endpoint)
        assert response.status_code == 200, f"{endpoint} should work with auth"
