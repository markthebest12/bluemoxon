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
