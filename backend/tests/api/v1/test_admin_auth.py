"""Tests for admin GET endpoint authentication."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.models.base import Base
from tests.conftest import TestingSessionLocal, engine


class TestAdminGetAuth:
    """Tests for admin GET endpoint authentication requirements."""

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
    def db(self):
        """Create a fresh database for each test."""
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            Base.metadata.drop_all(bind=engine)

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
