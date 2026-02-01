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


class TestBedrockHealthCheck:
    """Tests for Bedrock health check function (issue #1168)."""

    def test_check_bedrock_healthy(self, monkeypatch):
        """Test check_bedrock returns healthy when Bedrock API is accessible."""
        from unittest.mock import MagicMock

        from app.api.v1.health import _check_bedrock_sync

        mock_client = MagicMock()
        mock_client.list_foundation_models.return_value = {
            "modelSummaries": [{"modelId": "amazon.titan-text-lite-v1"}]
        }

        monkeypatch.setattr("app.api.v1.health._get_bedrock_client", lambda: mock_client)
        result = _check_bedrock_sync()

        assert result["status"] == "healthy"
        assert "latency_ms" in result
        assert isinstance(result["latency_ms"], int | float)
        assert result["latency_ms"] >= 0

    def test_check_bedrock_unhealthy_on_error(self, monkeypatch):
        """Test check_bedrock returns unhealthy on API error."""
        from unittest.mock import MagicMock

        from botocore.exceptions import ClientError

        from app.api.v1.health import _check_bedrock_sync

        mock_client = MagicMock()
        mock_client.list_foundation_models.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailable", "Message": "Service unavailable"}},
            "ListFoundationModels",
        )

        monkeypatch.setattr("app.api.v1.health._get_bedrock_client", lambda: mock_client)
        result = _check_bedrock_sync()

        assert result["status"] == "unhealthy"
        assert "error" in result
        assert result["error"] == "ServiceUnavailable"
        assert "latency_ms" in result

    def test_check_bedrock_skipped_on_access_denied_non_production(self, monkeypatch):
        """Test check_bedrock returns skipped when IAM permissions missing (non-prod)."""
        from unittest.mock import MagicMock, patch

        from botocore.exceptions import ClientError

        import app.api.v1.health as health_module
        from app.api.v1.health import _check_bedrock_sync

        mock_client = MagicMock()
        mock_client.list_foundation_models.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Access denied"}},
            "ListFoundationModels",
        )

        monkeypatch.setattr("app.api.v1.health._get_bedrock_client", lambda: mock_client)
        with patch.object(health_module.settings, "environment", "staging"):
            result = _check_bedrock_sync()

        assert result["status"] == "skipped"
        assert "reason" in result
        assert "IAM" in result["reason"] or "permission" in result["reason"].lower()
        assert "latency_ms" in result

    def test_check_bedrock_unhealthy_on_access_denied_production(self, monkeypatch):
        """Test check_bedrock returns unhealthy for AccessDenied in production."""
        from unittest.mock import MagicMock, patch

        from botocore.exceptions import ClientError

        import app.api.v1.health as health_module
        from app.api.v1.health import _check_bedrock_sync

        mock_client = MagicMock()
        mock_client.list_foundation_models.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Access denied"}},
            "ListFoundationModels",
        )

        monkeypatch.setattr("app.api.v1.health._get_bedrock_client", lambda: mock_client)
        with patch.object(health_module.settings, "environment", "production"):
            result = _check_bedrock_sync()

        assert result["status"] == "unhealthy"
        assert "error" in result
        assert "IAM" in result["error"] or "permission" in result["error"].lower()
        assert "latency_ms" in result

    def test_check_bedrock_timeout_handling(self, monkeypatch):
        """Test check_bedrock handles connection timeouts gracefully."""
        from unittest.mock import MagicMock

        from botocore.exceptions import ConnectTimeoutError

        from app.api.v1.health import _check_bedrock_sync

        mock_client = MagicMock()
        mock_client.list_foundation_models.side_effect = ConnectTimeoutError(
            endpoint_url="https://bedrock.us-east-1.amazonaws.com"
        )

        monkeypatch.setattr("app.api.v1.health._get_bedrock_client", lambda: mock_client)
        result = _check_bedrock_sync()

        assert result["status"] == "unhealthy"
        assert "error" in result
        assert "timeout" in result["error"].lower()
        assert "latency_ms" in result

    def test_check_bedrock_read_timeout_handling(self, monkeypatch):
        """Test check_bedrock handles read timeouts gracefully."""
        from unittest.mock import MagicMock

        from botocore.exceptions import ReadTimeoutError

        from app.api.v1.health import _check_bedrock_sync

        mock_client = MagicMock()
        mock_client.list_foundation_models.side_effect = ReadTimeoutError(
            endpoint_url="https://bedrock.us-east-1.amazonaws.com"
        )

        monkeypatch.setattr("app.api.v1.health._get_bedrock_client", lambda: mock_client)
        result = _check_bedrock_sync()

        assert result["status"] == "unhealthy"
        assert "error" in result
        assert "timeout" in result["error"].lower()
        assert "latency_ms" in result

    def test_check_bedrock_latency_is_measured(self, monkeypatch):
        """Test that latency measurement is accurate (not zero for real call)."""
        import time
        from unittest.mock import MagicMock

        from app.api.v1.health import _check_bedrock_sync

        mock_client = MagicMock()

        def slow_call(*args, **kwargs):
            time.sleep(0.05)  # 50ms delay
            return {"modelSummaries": []}

        mock_client.list_foundation_models.side_effect = slow_call

        monkeypatch.setattr("app.api.v1.health._get_bedrock_client", lambda: mock_client)
        result = _check_bedrock_sync()

        assert result["status"] == "healthy"
        assert result["latency_ms"] >= 50  # Should be at least 50ms

    def test_deep_health_includes_bedrock(self, client):
        """Test deep health check includes Bedrock status."""
        response = client.get("/api/v1/health/deep")
        assert response.status_code == 200
        data = response.json()

        assert "bedrock" in data["checks"], "Deep health must include Bedrock check"
        bedrock_check = data["checks"]["bedrock"]
        assert "status" in bedrock_check
        assert bedrock_check["status"] in ("healthy", "unhealthy", "skipped")

    @pytest.mark.asyncio
    async def test_check_bedrock_async_wrapper(self, monkeypatch):
        """Test that check_bedrock async wrapper properly calls sync function."""
        from unittest.mock import MagicMock

        from app.api.v1.health import check_bedrock

        mock_client = MagicMock()
        mock_client.list_foundation_models.return_value = {
            "modelSummaries": [{"modelId": "amazon.titan-text-lite-v1"}]
        }

        monkeypatch.setattr("app.api.v1.health._get_bedrock_client", lambda: mock_client)
        result = await check_bedrock()

        assert result["status"] == "healthy"
        assert "latency_ms" in result


class TestCheckRedis:
    """Tests for Redis health check function.

    Tests target _check_redis_sync directly since that contains the logic.
    The async check_redis wrapper just runs it in an executor.
    """

    def test_check_redis_skipped_when_not_configured(self, monkeypatch):
        """Test _check_redis_sync returns skipped status when redis_url is empty."""
        from app.api.v1 import health

        monkeypatch.setattr(health.settings, "redis_url", "")

        result = health._check_redis_sync()

        assert result["status"] == "skipped"
        assert result["reason"] == "Redis not configured"
        assert "latency_ms" not in result

    def test_check_redis_healthy_on_successful_ping(self, monkeypatch):
        """Test _check_redis_sync returns healthy status when PING succeeds."""
        from unittest.mock import MagicMock

        from app.api.v1 import health

        monkeypatch.setattr(health.settings, "redis_url", "redis://localhost:6379")

        mock_client = MagicMock()
        mock_client.ping.return_value = True

        def mock_from_url(url, socket_timeout=None):
            return mock_client

        monkeypatch.setattr(health.redis, "from_url", mock_from_url)

        result = health._check_redis_sync()

        assert result["status"] == "healthy"
        assert "latency_ms" in result
        assert isinstance(result["latency_ms"], float)
        assert "error" not in result

    def test_check_redis_closes_connection_on_success(self, monkeypatch):
        """Test _check_redis_sync closes connection in finally block."""
        from unittest.mock import MagicMock

        from app.api.v1 import health

        monkeypatch.setattr(health.settings, "redis_url", "redis://localhost:6379")

        mock_client = MagicMock()
        mock_client.ping.return_value = True

        def mock_from_url(url, socket_timeout=None):
            return mock_client

        monkeypatch.setattr(health.redis, "from_url", mock_from_url)

        health._check_redis_sync()

        mock_client.close.assert_called_once()

    def test_check_redis_closes_connection_on_error(self, monkeypatch):
        """Test _check_redis_sync closes connection even when ping fails."""
        from unittest.mock import MagicMock

        from app.api.v1 import health
        from app.api.v1.health import RedisConnectionError

        monkeypatch.setattr(health.settings, "redis_url", "redis://localhost:6379")

        mock_client = MagicMock()
        mock_client.ping.side_effect = RedisConnectionError("Connection refused")

        def mock_from_url(url, socket_timeout=None):
            return mock_client

        monkeypatch.setattr(health.redis, "from_url", mock_from_url)

        health._check_redis_sync()

        mock_client.close.assert_called_once()

    def test_check_redis_unhealthy_on_connection_error(self, monkeypatch):
        """Test _check_redis_sync returns unhealthy with sanitized error on ConnectionError."""
        from unittest.mock import MagicMock

        from app.api.v1 import health
        from app.api.v1.health import RedisConnectionError

        monkeypatch.setattr(health.settings, "redis_url", "redis://localhost:6379")

        mock_client = MagicMock()
        mock_client.ping.side_effect = RedisConnectionError("Connection refused to /secret/path")

        def mock_from_url(url, socket_timeout=None):
            return mock_client

        monkeypatch.setattr(health.redis, "from_url", mock_from_url)

        result = health._check_redis_sync()

        assert result["status"] == "unhealthy"
        assert result["error"] == "Redis connection failed"
        assert "/secret/path" not in result["error"]
        assert "latency_ms" in result

    def test_check_redis_unhealthy_on_timeout_error(self, monkeypatch):
        """Test _check_redis_sync returns unhealthy with sanitized error on TimeoutError."""
        from unittest.mock import MagicMock

        from app.api.v1 import health
        from app.api.v1.health import RedisTimeoutError

        monkeypatch.setattr(health.settings, "redis_url", "redis://localhost:6379")

        mock_client = MagicMock()
        mock_client.ping.side_effect = RedisTimeoutError(
            "Timeout connecting to redis://secret:6379"
        )

        def mock_from_url(url, socket_timeout=None):
            return mock_client

        monkeypatch.setattr(health.redis, "from_url", mock_from_url)

        result = health._check_redis_sync()

        assert result["status"] == "unhealthy"
        assert result["error"] == "Redis connection timed out"
        assert "secret" not in result["error"]
        assert "latency_ms" in result

    def test_check_redis_unhealthy_on_redis_error(self, monkeypatch):
        """Test _check_redis_sync returns unhealthy with sanitized error on other RedisError."""
        from unittest.mock import MagicMock

        from app.api.v1 import health
        from app.api.v1.health import RedisError

        monkeypatch.setattr(health.settings, "redis_url", "redis://localhost:6379")

        mock_client = MagicMock()
        mock_client.ping.side_effect = RedisError("NOAUTH password required at /etc/redis.conf")

        def mock_from_url(url, socket_timeout=None):
            return mock_client

        monkeypatch.setattr(health.redis, "from_url", mock_from_url)

        result = health._check_redis_sync()

        assert result["status"] == "unhealthy"
        assert result["error"] == "Redis error occurred"
        assert "/etc/redis.conf" not in result["error"]
        assert "latency_ms" in result

    def test_check_redis_latency_measurement(self, monkeypatch):
        """Test _check_redis_sync measures latency accurately."""
        import time
        from unittest.mock import MagicMock

        from app.api.v1 import health

        monkeypatch.setattr(health.settings, "redis_url", "redis://localhost:6379")

        mock_client = MagicMock()

        def slow_ping():
            time.sleep(0.05)  # 50ms delay
            return True

        mock_client.ping = slow_ping

        def mock_from_url(url, socket_timeout=None):
            return mock_client

        monkeypatch.setattr(health.redis, "from_url", mock_from_url)

        result = health._check_redis_sync()

        assert result["status"] == "healthy"
        assert "latency_ms" in result
        assert result["latency_ms"] >= 50.0

    @pytest.mark.asyncio
    async def test_check_redis_async_wrapper(self, monkeypatch):
        """Test async check_redis wrapper calls sync version via executor."""
        from unittest.mock import MagicMock

        from app.api.v1 import health

        monkeypatch.setattr(health.settings, "redis_url", "redis://localhost:6379")

        mock_client = MagicMock()
        mock_client.ping.return_value = True

        def mock_from_url(url, socket_timeout=None):
            return mock_client

        monkeypatch.setattr(health.redis, "from_url", mock_from_url)

        result = await health.check_redis()

        assert result["status"] == "healthy"
        assert "latency_ms" in result


class TestDeepHealthCheckWithRedis:
    """Tests for Redis integration in deep health check endpoint."""

    def test_deep_health_includes_redis_check(self, client):
        """Test deep health check includes redis in checks."""
        response = client.get("/api/v1/health/deep")
        assert response.status_code == 200
        data = response.json()

        assert "checks" in data
        assert "redis" in data["checks"]

    def test_deep_health_redis_skipped_when_not_configured(self, client, monkeypatch):
        """Test deep health shows redis as skipped when not configured."""
        from app.api.v1 import health

        monkeypatch.setattr(health.settings, "redis_url", "")

        response = client.get("/api/v1/health/deep")
        data = response.json()

        redis_check = data["checks"]["redis"]
        assert redis_check["status"] == "skipped"
        assert redis_check["reason"] == "Redis not configured"


class TestNormalizeConditionGrades:
    """Tests for /health/normalize-condition-grades endpoint."""

    def test_normalizes_vg_to_very_good(self, client, db):
        """Test normalization works: VG -> VERY_GOOD."""
        from app.models import Book

        book = Book(title="Test Book", condition_grade="VG")
        db.add(book)
        db.commit()
        book_id = book.id

        response = client.post("/api/v1/health/normalize-condition-grades")
        assert response.status_code == 200
        data = response.json()

        assert data["normalized"] == 1
        assert data["skipped"] == 0
        assert len(data["details"]) == 1
        assert data["details"][0]["book_id"] == book_id
        assert data["details"][0]["old"] == "VG"
        assert data["details"][0]["new"] == "VERY_GOOD"

        db.refresh(book)
        assert book.condition_grade == "VERY_GOOD"

    def test_null_condition_grades_untouched(self, client, db):
        """Test NULL condition grades are not modified."""
        from app.models import Book

        book = Book(title="Test Book", condition_grade=None)
        db.add(book)
        db.commit()

        response = client.post("/api/v1/health/normalize-condition-grades")
        assert response.status_code == 200
        data = response.json()

        assert data["normalized"] == 0
        assert data["skipped"] == 0

        db.refresh(book)
        assert book.condition_grade is None

    def test_idempotent_second_call_returns_zero(self, client, db):
        """Test idempotency: second call returns normalized: 0."""
        from app.models import Book

        book = Book(title="Test Book", condition_grade="VG")
        db.add(book)
        db.commit()

        response1 = client.post("/api/v1/health/normalize-condition-grades")
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["normalized"] == 1

        response2 = client.post("/api/v1/health/normalize-condition-grades")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["normalized"] == 0
        assert data2["skipped"] == 0

    def test_already_normalized_values_skipped(self, client, db):
        """Test already normalized values are not changed."""
        from app.models import Book

        book = Book(title="Test Book", condition_grade="VERY_GOOD")
        db.add(book)
        db.commit()

        response = client.post("/api/v1/health/normalize-condition-grades")
        assert response.status_code == 200
        data = response.json()

        assert data["normalized"] == 0
        assert data["skipped"] == 0

        db.refresh(book)
        assert book.condition_grade == "VERY_GOOD"

    def test_unrecognized_values_are_skipped(self, client, db):
        """Test unrecognized condition grades are skipped, not normalized."""
        from app.models import Book

        book = Book(title="Test Book", condition_grade="UNKNOWN_VALUE")
        db.add(book)
        db.commit()
        book_id = book.id

        response = client.post("/api/v1/health/normalize-condition-grades")
        assert response.status_code == 200
        data = response.json()

        assert data["normalized"] == 0
        assert data["skipped"] == 1
        assert len(data["details"]) == 1
        assert data["details"][0]["book_id"] == book_id
        assert data["details"][0]["old"] == "UNKNOWN_VALUE"
        assert data["details"][0]["reason"] == "unrecognized"

        db.refresh(book)
        assert book.condition_grade == "UNKNOWN_VALUE"

    def test_multiple_books_normalized(self, client, db):
        """Test multiple books are normalized in one call."""
        from app.models import Book

        book1 = Book(title="Book 1", condition_grade="VG")
        book2 = Book(title="Book 2", condition_grade="NF")
        book3 = Book(title="Book 3", condition_grade="G")
        db.add_all([book1, book2, book3])
        db.commit()

        response = client.post("/api/v1/health/normalize-condition-grades")
        assert response.status_code == 200
        data = response.json()

        assert data["normalized"] == 3
        assert data["skipped"] == 0
        assert len(data["details"]) == 3

        db.refresh(book1)
        db.refresh(book2)
        db.refresh(book3)
        assert book1.condition_grade == "VERY_GOOD"
        assert book2.condition_grade == "NEAR_FINE"
        assert book3.condition_grade == "GOOD"

    def test_requires_admin_auth(self, unauthenticated_client):
        """Test endpoint requires admin authentication."""
        response = unauthenticated_client.post("/api/v1/health/normalize-condition-grades")
        assert response.status_code == 401


class TestCheckLambdas:
    """Tests for Lambda availability check function."""

    @pytest.mark.asyncio
    async def test_check_lambdas_all_healthy(self, monkeypatch):
        """Test check_lambdas returns healthy when all Lambda functions are Active."""
        from unittest.mock import MagicMock

        from app.api.v1.health import check_lambdas

        # Mock get_lambda_environment to return test environment
        monkeypatch.setattr("app.api.v1.health.get_lambda_environment", lambda service: "staging")

        # Mock the _get_lambda_client helper for cleaner mocking
        mock_lambda_client = MagicMock()
        mock_lambda_client.get_function.return_value = {
            "Configuration": {
                "FunctionName": "bluemoxon-staging-scraper",
                "State": "Active",
            }
        }
        monkeypatch.setattr("app.api.v1.health._get_lambda_client", lambda: mock_lambda_client)

        result = await check_lambdas()

        assert result["status"] == "healthy"
        assert "lambdas" in result
        assert "latency_ms" in result

        # Verify all four Lambdas were checked
        assert "scraper" in result["lambdas"]
        assert "cleanup" in result["lambdas"]
        assert "image_processor" in result["lambdas"]
        assert "retry_queue_failed" in result["lambdas"]

        # Verify each Lambda shows Active status
        for _name, status in result["lambdas"].items():
            assert status["status"] == "healthy"
            assert status["state"] == "Active"

    @pytest.mark.asyncio
    async def test_check_lambdas_one_failed(self, monkeypatch):
        """Test check_lambdas returns unhealthy when one Lambda is Failed."""
        from unittest.mock import MagicMock

        from app.api.v1.health import check_lambdas

        monkeypatch.setattr("app.api.v1.health.get_lambda_environment", lambda service: "staging")

        # Mock the _get_lambda_client helper for cleaner mocking
        mock_lambda_client = MagicMock()

        def mock_get_function(FunctionName):
            if "scraper" in FunctionName:
                return {
                    "Configuration": {
                        "FunctionName": FunctionName,
                        "State": "Active",
                    }
                }
            elif "cleanup" in FunctionName:
                return {
                    "Configuration": {
                        "FunctionName": FunctionName,
                        "State": "Failed",
                    }
                }
            else:
                return {
                    "Configuration": {
                        "FunctionName": FunctionName,
                        "State": "Active",
                    }
                }

        mock_lambda_client.get_function.side_effect = mock_get_function
        monkeypatch.setattr("app.api.v1.health._get_lambda_client", lambda: mock_lambda_client)

        result = await check_lambdas()

        assert result["status"] == "unhealthy"
        assert result["lambdas"]["scraper"]["status"] == "healthy"
        assert result["lambdas"]["cleanup"]["status"] == "unhealthy"
        assert result["lambdas"]["cleanup"]["state"] == "Failed"

    @pytest.mark.asyncio
    async def test_check_lambdas_missing_function(self, monkeypatch):
        """Test check_lambdas handles ResourceNotFoundException for missing Lambda.

        Missing functions (not_found) should result in overall unhealthy status
        since a missing Lambda indicates something is broken.
        """
        from unittest.mock import MagicMock

        from botocore.exceptions import ClientError

        from app.api.v1.health import check_lambdas

        monkeypatch.setattr("app.api.v1.health.get_lambda_environment", lambda service: "staging")

        # Mock the _get_lambda_client helper for cleaner mocking
        mock_lambda_client = MagicMock()

        def mock_get_function(FunctionName):
            if "scraper" in FunctionName:
                raise ClientError(
                    {
                        "Error": {
                            "Code": "ResourceNotFoundException",
                            "Message": "Function not found",
                        }
                    },
                    "GetFunction",
                )
            return {
                "Configuration": {
                    "FunctionName": FunctionName,
                    "State": "Active",
                }
            }

        mock_lambda_client.get_function.side_effect = mock_get_function
        monkeypatch.setattr("app.api.v1.health._get_lambda_client", lambda: mock_lambda_client)

        result = await check_lambdas()

        # Missing function should be marked as not_found, overall unhealthy
        # (not_found indicates something is broken)
        assert result["status"] == "unhealthy"
        assert result["lambdas"]["scraper"]["status"] == "not_found"
        assert result["lambdas"]["cleanup"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_check_lambdas_pending_state(self, monkeypatch):
        """Test check_lambdas returns degraded when a Lambda is Pending."""
        from unittest.mock import MagicMock

        from app.api.v1.health import check_lambdas

        monkeypatch.setattr("app.api.v1.health.get_lambda_environment", lambda service: "staging")

        mock_lambda_client = MagicMock()

        def mock_get_function(FunctionName):
            if "scraper" in FunctionName:
                return {
                    "Configuration": {
                        "FunctionName": FunctionName,
                        "State": "Pending",
                    }
                }
            return {
                "Configuration": {
                    "FunctionName": FunctionName,
                    "State": "Active",
                }
            }

        mock_lambda_client.get_function.side_effect = mock_get_function
        monkeypatch.setattr("app.api.v1.health._get_lambda_client", lambda: mock_lambda_client)

        result = await check_lambdas()

        # Pending state is degraded (not unhealthy, not healthy)
        assert result["status"] == "degraded"
        assert result["lambdas"]["scraper"]["status"] == "degraded"
        assert result["lambdas"]["scraper"]["state"] == "Pending"

    @pytest.mark.asyncio
    async def test_check_lambdas_error_status_is_unhealthy(self, monkeypatch):
        """Test check_lambdas returns unhealthy when a Lambda returns error status.

        Error status (from unexpected ClientError like throttling) should result
        in overall unhealthy status since it indicates something is broken.
        """
        from unittest.mock import MagicMock

        from botocore.exceptions import ClientError

        from app.api.v1.health import check_lambdas

        monkeypatch.setattr("app.api.v1.health.get_lambda_environment", lambda service: "staging")

        mock_lambda_client = MagicMock()

        def mock_get_function(FunctionName):
            if "scraper" in FunctionName:
                raise ClientError(
                    {
                        "Error": {
                            "Code": "ThrottlingException",
                            "Message": "Rate exceeded",
                        }
                    },
                    "GetFunction",
                )
            return {
                "Configuration": {
                    "FunctionName": FunctionName,
                    "State": "Active",
                }
            }

        mock_lambda_client.get_function.side_effect = mock_get_function
        monkeypatch.setattr("app.api.v1.health._get_lambda_client", lambda: mock_lambda_client)

        result = await check_lambdas()

        # Error status should result in overall unhealthy
        assert result["status"] == "unhealthy"
        assert result["lambdas"]["scraper"]["status"] == "error"
        assert result["lambdas"]["scraper"]["error"] == "ThrottlingException"

    @pytest.mark.asyncio
    async def test_check_lambdas_connect_timeout(self, monkeypatch):
        """Test check_lambdas handles ConnectTimeoutError."""
        from unittest.mock import MagicMock

        from botocore.exceptions import ConnectTimeoutError

        from app.api.v1.health import check_lambdas

        monkeypatch.setattr("app.api.v1.health.get_lambda_environment", lambda service: "staging")

        mock_lambda_client = MagicMock()

        def mock_get_function(FunctionName):
            if "scraper" in FunctionName:
                raise ConnectTimeoutError(endpoint_url="https://lambda.us-east-1.amazonaws.com")
            return {
                "Configuration": {
                    "FunctionName": FunctionName,
                    "State": "Active",
                }
            }

        mock_lambda_client.get_function.side_effect = mock_get_function
        monkeypatch.setattr("app.api.v1.health._get_lambda_client", lambda: mock_lambda_client)

        result = await check_lambdas()

        # Timeout should result in error status and overall unhealthy
        assert result["status"] == "unhealthy"
        assert result["lambdas"]["scraper"]["status"] == "error"
        assert "Timeout" in result["lambdas"]["scraper"]["error"]

    @pytest.mark.asyncio
    async def test_check_lambdas_read_timeout(self, monkeypatch):
        """Test check_lambdas handles ReadTimeoutError."""
        from unittest.mock import MagicMock

        from botocore.exceptions import ReadTimeoutError

        from app.api.v1.health import check_lambdas

        monkeypatch.setattr("app.api.v1.health.get_lambda_environment", lambda service: "staging")

        mock_lambda_client = MagicMock()

        def mock_get_function(FunctionName):
            if "scraper" in FunctionName:
                raise ReadTimeoutError(endpoint_url="https://lambda.us-east-1.amazonaws.com")
            return {
                "Configuration": {
                    "FunctionName": FunctionName,
                    "State": "Active",
                }
            }

        mock_lambda_client.get_function.side_effect = mock_get_function
        monkeypatch.setattr("app.api.v1.health._get_lambda_client", lambda: mock_lambda_client)

        result = await check_lambdas()

        # Timeout should result in error status and overall unhealthy
        assert result["status"] == "unhealthy"
        assert result["lambdas"]["scraper"]["status"] == "error"
        assert "Timeout" in result["lambdas"]["scraper"]["error"]

    @pytest.mark.asyncio
    async def test_check_lambdas_parallel_execution(self, monkeypatch):
        """Test check_lambdas executes Lambda checks in parallel.

        Verifies that all Lambda function names are checked (indicating
        parallel execution was attempted). The ThreadPoolExecutor should
        check all 4 functions concurrently.
        """
        from unittest.mock import MagicMock

        from app.api.v1.health import check_lambdas

        monkeypatch.setattr("app.api.v1.health.get_lambda_environment", lambda service: "staging")

        mock_lambda_client = MagicMock()
        checked_functions = []

        def mock_get_function(FunctionName):
            checked_functions.append(FunctionName)
            return {
                "Configuration": {
                    "FunctionName": FunctionName,
                    "State": "Active",
                }
            }

        mock_lambda_client.get_function.side_effect = mock_get_function
        monkeypatch.setattr("app.api.v1.health._get_lambda_client", lambda: mock_lambda_client)

        result = await check_lambdas()

        # Verify all 4 functions were checked (scraper, cleanup, image-processor, retry-queue-failed)
        assert len(checked_functions) == 4
        assert any("scraper" in f for f in checked_functions)
        assert any("cleanup" in f for f in checked_functions)
        assert any("image-processor" in f for f in checked_functions)
        assert any("retry-queue-failed" in f for f in checked_functions)
        assert result["status"] == "healthy"

    def test_deep_health_includes_lambdas_check(self, client, monkeypatch):
        """Test deep health endpoint includes Lambda availability check."""
        from unittest.mock import MagicMock

        monkeypatch.setattr("app.api.v1.health.get_lambda_environment", lambda service: "staging")

        mock_lambda_client = MagicMock()
        mock_lambda_client.get_function.return_value = {
            "Configuration": {
                "FunctionName": "bluemoxon-staging-scraper",
                "State": "Active",
            }
        }
        monkeypatch.setattr("app.api.v1.health._get_lambda_client", lambda: mock_lambda_client)

        response = client.get("/api/v1/health/deep")
        assert response.status_code == 200
        data = response.json()

        assert "lambdas" in data["checks"]
        assert data["checks"]["lambdas"]["status"] in (
            "healthy",
            "degraded",
            "unhealthy",
            "skipped",
        )

    @pytest.mark.asyncio
    async def test_check_lambdas_access_denied_non_production(self, monkeypatch):
        """Test check_lambdas returns skipped when AccessDeniedException in non-production.

        In staging/dev environments, IAM permissions for Lambda:GetFunction may not
        be configured. This should result in 'skipped' status, not 'error' or 'unhealthy'.
        """
        from unittest.mock import MagicMock, patch

        from botocore.exceptions import ClientError

        from app.api.v1.health import check_lambdas

        monkeypatch.setattr("app.api.v1.health.get_lambda_environment", lambda service: "staging")

        mock_lambda_client = MagicMock()
        mock_lambda_client.get_function.side_effect = ClientError(
            {
                "Error": {
                    "Code": "AccessDeniedException",
                    "Message": "User is not authorized to perform: lambda:GetFunction",
                }
            },
            "GetFunction",
        )
        monkeypatch.setattr("app.api.v1.health._get_lambda_client", lambda: mock_lambda_client)

        # Patch settings.environment to staging
        import app.api.v1.health as health_module

        with patch.object(health_module.settings, "environment", "staging"):
            result = await check_lambdas()

        # All Lambdas should be skipped, overall status should be healthy
        assert result["status"] == "healthy"
        for lambda_name, lambda_status in result["lambdas"].items():
            assert lambda_status["status"] == "skipped", (
                f"Lambda {lambda_name} should be skipped on AccessDeniedException in non-prod"
            )
            assert "reason" in lambda_status
            assert "IAM" in lambda_status["reason"]

    @pytest.mark.asyncio
    async def test_check_lambdas_access_denied_production(self, monkeypatch):
        """Test check_lambdas returns unhealthy when AccessDeniedException in production.

        In production, IAM permissions should be properly configured. AccessDeniedException
        indicates a broken configuration and should result in 'unhealthy' status.
        """
        from unittest.mock import MagicMock, patch

        from botocore.exceptions import ClientError

        from app.api.v1.health import check_lambdas

        monkeypatch.setattr("app.api.v1.health.get_lambda_environment", lambda service: "prod")

        mock_lambda_client = MagicMock()
        mock_lambda_client.get_function.side_effect = ClientError(
            {
                "Error": {
                    "Code": "AccessDeniedException",
                    "Message": "User is not authorized to perform: lambda:GetFunction",
                }
            },
            "GetFunction",
        )
        monkeypatch.setattr("app.api.v1.health._get_lambda_client", lambda: mock_lambda_client)

        # Patch settings.environment to production
        import app.api.v1.health as health_module

        with patch.object(health_module.settings, "environment", "production"):
            result = await check_lambdas()

        # All Lambdas should be unhealthy, overall status should be unhealthy
        assert result["status"] == "unhealthy"
        for lambda_name, lambda_status in result["lambdas"].items():
            assert lambda_status["status"] == "unhealthy", (
                f"Lambda {lambda_name} should be unhealthy on AccessDeniedException in production"
            )
            assert "error" in lambda_status
            assert "IAM" in lambda_status["error"]

    @pytest.mark.asyncio
    async def test_check_lambdas_overall_healthy_when_all_skipped(self, monkeypatch):
        """Test overall status is healthy when all Lambdas are skipped.

        When all Lambda checks return 'skipped' (e.g., due to missing IAM permissions
        in non-production), the overall status should be 'healthy', not 'unhealthy'.
        """
        from unittest.mock import MagicMock, patch

        from botocore.exceptions import ClientError

        from app.api.v1.health import check_lambdas

        monkeypatch.setattr("app.api.v1.health.get_lambda_environment", lambda service: "staging")

        mock_lambda_client = MagicMock()
        mock_lambda_client.get_function.side_effect = ClientError(
            {
                "Error": {
                    "Code": "AccessDeniedException",
                    "Message": "Access denied",
                }
            },
            "GetFunction",
        )
        monkeypatch.setattr("app.api.v1.health._get_lambda_client", lambda: mock_lambda_client)

        import app.api.v1.health as health_module

        with patch.object(health_module.settings, "environment", "staging"):
            result = await check_lambdas()

        # Overall status should be healthy, not unhealthy
        assert result["status"] == "healthy", (
            "Overall status should be 'healthy' when all Lambdas are 'skipped'"
        )


class TestCheckSqsProfileGeneration:
    """Tests for profile generation queue in SQS health check."""

    def test_check_sqs_includes_profile_generation_queue(self, monkeypatch):
        """check_sqs should include profile_generation when configured."""
        from app.api.v1 import health
        from app.api.v1.health import check_sqs

        monkeypatch.setattr(
            health.settings, "profile_generation_queue_name", "test-profile-gen-queue"
        )
        monkeypatch.setattr(health.settings, "analysis_queue_name", None)
        monkeypatch.setattr(health.settings, "eval_runbook_queue_name", None)
        monkeypatch.setattr(health.settings, "image_processing_queue_name", None)

        # Mock boto3 SQS client
        import unittest.mock as mock

        mock_sqs = mock.MagicMock()
        mock_sqs.get_queue_url.return_value = {
            "QueueUrl": "https://sqs.us-east-1.amazonaws.com/123/test-profile-gen-queue"
        }
        mock_sqs.get_queue_attributes.return_value = {
            "Attributes": {"ApproximateNumberOfMessages": "5"}
        }
        monkeypatch.setattr("app.api.v1.health.boto3.client", lambda *a, **kw: mock_sqs)

        result = check_sqs()

        assert result["status"] == "healthy"
        assert "profile_generation" in result["queues"]
        assert result["queues"]["profile_generation"]["status"] == "healthy"
        assert result["queues"]["profile_generation"]["messages"] == 5

    def test_check_sqs_excludes_unconfigured_profile_generation(self, monkeypatch):
        """check_sqs should exclude profile_generation when not configured."""
        from app.api.v1 import health
        from app.api.v1.health import check_sqs

        monkeypatch.setattr(health.settings, "profile_generation_queue_name", None)
        monkeypatch.setattr(health.settings, "analysis_queue_name", "test-analysis-queue")
        monkeypatch.setattr(health.settings, "eval_runbook_queue_name", None)
        monkeypatch.setattr(health.settings, "image_processing_queue_name", None)

        import unittest.mock as mock

        mock_sqs = mock.MagicMock()
        mock_sqs.get_queue_url.return_value = {
            "QueueUrl": "https://sqs.us-east-1.amazonaws.com/123/test-analysis-queue"
        }
        mock_sqs.get_queue_attributes.return_value = {
            "Attributes": {"ApproximateNumberOfMessages": "0"}
        }
        monkeypatch.setattr("app.api.v1.health.boto3.client", lambda *a, **kw: mock_sqs)

        result = check_sqs()

        assert result["status"] == "healthy"
        assert "profile_generation" not in result["queues"]
        assert "analysis" in result["queues"]
