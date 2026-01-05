"""Health check endpoint tests."""


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


class TestMigrateEndpoint:
    """Tests for database migration endpoint using Alembic programmatically.

    These tests mock the Alembic command module to verify the endpoint
    correctly invokes migrations without actually running them in tests.

    The endpoint is expected to:
    1. Call alembic.command.upgrade(config, "head")
    2. Return previous_version and new_version in the response
    3. Handle errors gracefully with proper error responses
    """

    def test_migrate_calls_alembic_upgrade(self, client, db):
        """Verify endpoint calls alembic.command.upgrade(config, 'head')."""
        from unittest.mock import MagicMock, patch

        mock_config = MagicMock()

        with patch("app.api.v1.health.command") as mock_command:
            with patch("app.api.v1.health.Config", return_value=mock_config):
                response = client.post("/api/v1/health/migrate")

                assert response.status_code == 200
                mock_command.upgrade.assert_called_once()
                # Verify called with config and "head"
                call_args = mock_command.upgrade.call_args
                assert call_args[0][0] == mock_config
                assert call_args[0][1] == "head"

    def test_migrate_returns_version_info(self, client, db):
        """Verify response includes previous_version and new_version."""
        from unittest.mock import MagicMock, patch

        mock_config = MagicMock()

        with patch("app.api.v1.health.command"):
            with patch("app.api.v1.health.Config", return_value=mock_config):
                response = client.post("/api/v1/health/migrate")

                assert response.status_code == 200
                data = response.json()
                assert "previous_version" in data
                assert "new_version" in data

    def test_migrate_handles_alembic_error(self, client, db):
        """Verify proper error handling when Alembic fails."""
        from unittest.mock import MagicMock, patch

        from alembic.util.exc import CommandError

        mock_config = MagicMock()

        with patch("app.api.v1.health.command") as mock_command:
            with patch("app.api.v1.health.Config", return_value=mock_config):
                mock_command.upgrade.side_effect = CommandError("Migration failed")

                response = client.post("/api/v1/health/migrate")

                # Should return 200 with error status, not 500
                assert response.status_code == 200
                data = response.json()
                assert data.get("status") in ("failed", "error")
                assert "error" in data or "errors" in data

    def test_migrate_returns_success_status(self, client, db):
        """Verify successful response structure."""
        from unittest.mock import MagicMock, patch

        mock_config = MagicMock()

        with patch("app.api.v1.health.command"):
            with patch("app.api.v1.health.Config", return_value=mock_config):
                response = client.post("/api/v1/health/migrate")

                assert response.status_code == 200
                data = response.json()

                # Verify success response structure
                assert "status" in data
                assert data["status"] == "success"
                assert "previous_version" in data
                assert "new_version" in data
