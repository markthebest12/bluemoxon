"""Health check endpoint tests."""

import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app


class TestBasicHealth:
    """Tests for basic health endpoint."""

    def test_health_check(self, client):
        """Test root health endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestLivenessProbe:
    """Tests for liveness probe endpoint."""

    def test_liveness_returns_ok(self, client):
        """Test liveness probe returns ok."""
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestReadinessProbe:
    """Tests for readiness probe endpoint."""

    def test_readiness_with_database(self, client):
        """Test readiness probe checks database."""
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ready", "not_ready")
        assert "checks" in data
        assert "database" in data["checks"]


class TestDeepHealthCheck:
    """Tests for deep health check endpoint."""

    def test_deep_health_returns_all_checks(self, client):
        """Test deep health check returns all component statuses."""
        response = client.get("/api/v1/health/deep")
        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data
        assert "total_latency_ms" in data
        assert "checks" in data

        # Check all components are present
        checks = data["checks"]
        assert "database" in checks
        assert "s3" in checks
        assert "cognito" in checks
        assert "config" in checks

        # Each check should have a status
        for check_name, check_data in checks.items():
            assert "status" in check_data, f"{check_name} missing status"

    def test_deep_health_database_check_has_latency(self, client):
        """Test database check includes latency measurement."""
        response = client.get("/api/v1/health/deep")
        data = response.json()

        db_check = data["checks"]["database"]
        if db_check["status"] == "healthy":
            assert "latency_ms" in db_check
            assert isinstance(db_check["latency_ms"], int | float)

    def test_deep_health_database_validates_schema(self, client, db):
        """Test database check validates schema by fetching actual row data.

        This catches missing columns that COUNT(*) wouldn't detect.
        A schema mismatch (e.g., model has column X but DB doesn't) would
        cause health to return unhealthy, not falsely report healthy.
        """
        from app.models import Book

        # Create a book to ensure there's data to fetch
        book = Book(title="Schema Test Book")
        db.add(book)
        db.commit()

        response = client.get("/api/v1/health/deep")
        data = response.json()

        db_check = data["checks"]["database"]
        # Health check should validate schema, not just count
        # This field proves we actually fetched row data
        assert db_check["status"] == "healthy"
        assert "schema_validated" in db_check, (
            "Health check must validate schema by fetching actual row data. "
            "COUNT(*) alone doesn't catch missing columns."
        )
        assert db_check["schema_validated"] is True

    def test_deep_health_overall_status_logic(self, client):
        """Test overall status reflects component statuses."""
        response = client.get("/api/v1/health/deep")
        data = response.json()

        # Overall status should be one of these
        assert data["status"] in ("healthy", "degraded", "unhealthy")


class TestServiceInfo:
    """Tests for service info endpoint."""

    def test_service_info_returns_metadata(self, client):
        """Test service info returns expected metadata."""
        response = client.get("/api/v1/health/info")
        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "bluemoxon-api"
        assert "version" in data
        assert "environment" in data
        assert "region" in data
        assert "features" in data
        assert "endpoints" in data

    def test_service_info_features_are_booleans(self, client):
        """Test feature flags are boolean values."""
        response = client.get("/api/v1/health/info")
        data = response.json()

        for feature, value in data["features"].items():
            assert isinstance(value, bool), f"Feature {feature} should be boolean"


class TestHealthAdminEndpointsSecurity:
    """Tests for admin-only health endpoints (issue #808).

    These POST endpoints modify data and MUST require admin authentication:
    - /health/cleanup-orphans - deletes orphaned records
    - /health/recalculate-discounts - modifies book discount values
    - /health/merge-binders - merges/deletes binder records
    - /health/migrate - runs database migrations
    """

    @pytest.fixture
    def unauthenticated_client(self, db):
        """Create a test client WITHOUT auth overrides."""

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        # Don't override require_admin - will require real auth
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()

    def test_cleanup_orphans_requires_admin_auth(self, unauthenticated_client):
        """POST /health/cleanup-orphans requires admin authentication."""
        response = unauthenticated_client.post("/api/v1/health/cleanup-orphans")
        assert response.status_code == 401, (
            f"Expected 401 Unauthorized, got {response.status_code}. "
            "Endpoint must require authentication (issue #808)"
        )

    def test_recalculate_discounts_requires_admin_auth(self, unauthenticated_client):
        """POST /health/recalculate-discounts requires admin authentication."""
        response = unauthenticated_client.post("/api/v1/health/recalculate-discounts")
        assert response.status_code == 401, (
            f"Expected 401 Unauthorized, got {response.status_code}. "
            "Endpoint must require authentication (issue #808)"
        )

    def test_merge_binders_requires_admin_auth(self, unauthenticated_client):
        """POST /health/merge-binders requires admin authentication."""
        response = unauthenticated_client.post("/api/v1/health/merge-binders")
        assert response.status_code == 401, (
            f"Expected 401 Unauthorized, got {response.status_code}. "
            "Endpoint must require authentication (issue #808)"
        )

    def test_migrate_requires_admin_auth(self, unauthenticated_client):
        """POST /health/migrate requires admin authentication."""
        response = unauthenticated_client.post("/api/v1/health/migrate")
        assert response.status_code == 401, (
            f"Expected 401 Unauthorized, got {response.status_code}. "
            "Endpoint must require authentication (issue #808)"
        )

    def test_cleanup_orphans_succeeds_with_admin(self, client):
        """POST /health/cleanup-orphans succeeds with admin auth."""
        response = client.post("/api/v1/health/cleanup-orphans")
        assert response.status_code == 200

    def test_recalculate_discounts_succeeds_with_admin(self, client):
        """POST /health/recalculate-discounts succeeds with admin auth."""
        response = client.post("/api/v1/health/recalculate-discounts")
        assert response.status_code == 200

    def test_merge_binders_succeeds_with_admin(self, client):
        """POST /health/merge-binders succeeds with admin auth."""
        response = client.post("/api/v1/health/merge-binders")
        assert response.status_code == 200

    def test_migrate_succeeds_with_admin(self, client):
        """POST /health/migrate succeeds with admin auth."""
        response = client.post("/api/v1/health/migrate")
        assert response.status_code == 200


class TestMigrationSqlModule:
    """Tests for migration SQL module usage."""

    def test_health_uses_migration_sql_module(self):
        """health.py should import from migration_sql, not define SQL inline."""
        from app.api.v1 import health
        from app.db import migration_sql

        # Verify health.py's migrations list comes from migration_sql
        assert health.migrations == migration_sql.MIGRATIONS
