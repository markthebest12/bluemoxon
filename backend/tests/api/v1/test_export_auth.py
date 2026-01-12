"""Tests for export endpoint authentication."""

import pytest
from fastapi.testclient import TestClient

from app.auth import require_viewer
from app.db import get_db
from app.main import app
from app.models.base import Base
from tests.conftest import TestingSessionLocal, engine, get_mock_editor


class TestExportAuth:
    """Tests for export endpoint authentication requirements."""

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
        """Client with auth overrides for viewer role."""

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

    def test_export_csv_requires_auth(self, unauthenticated_client):
        """Test that /export/csv returns 401 without authentication."""
        response = unauthenticated_client.get("/api/v1/export/csv")
        assert response.status_code == 401

    def test_export_json_requires_auth(self, unauthenticated_client):
        """Test that /export/json returns 401 without authentication."""
        response = unauthenticated_client.get("/api/v1/export/json")
        assert response.status_code == 401

    def test_export_csv_works_with_auth(self, authenticated_client):
        """Test that /export/csv works with authentication."""
        response = authenticated_client.get("/api/v1/export/csv")
        assert response.status_code == 200

    def test_export_json_works_with_auth(self, authenticated_client):
        """Test that /export/json works with authentication."""
        response = authenticated_client.get("/api/v1/export/json")
        assert response.status_code == 200
