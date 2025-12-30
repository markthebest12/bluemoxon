"""Tests for admin cleanup endpoint."""

import json
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


class TestAdminCleanupEndpoint:
    """Tests for POST /admin/cleanup endpoint."""

    def test_cleanup_all_invokes_lambda(self, client: TestClient):
        """Test that cleanup with action='all' invokes Lambda correctly."""
        with patch("app.api.v1.admin.boto3") as mock_boto3:
            mock_lambda = MagicMock()
            mock_boto3.client.return_value = mock_lambda
            mock_lambda.invoke.return_value = {
                "StatusCode": 200,
                "Payload": MagicMock(
                    read=lambda: json.dumps(
                        {
                            "stale_evaluations_archived": 5,
                            "sources_checked": 100,
                            "sources_expired": 10,
                            "orphans_found": 3,
                            "orphans_deleted": 0,
                            "archives_retried": 2,
                            "archives_succeeded": 1,
                            "archives_failed": 1,
                        }
                    ).encode()
                ),
            }

            response = client.post(
                "/api/v1/admin/cleanup", json={"action": "all"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["stale_archived"] == 5
            assert data["sources_checked"] == 100
            assert data["sources_expired"] == 10
            assert data["orphans_found"] == 3
            assert data["orphans_deleted"] == 0

    def test_cleanup_stale_only(self, client: TestClient):
        """Test cleanup with action='stale' only runs stale cleanup."""
        with patch("app.api.v1.admin.boto3") as mock_boto3:
            mock_lambda = MagicMock()
            mock_boto3.client.return_value = mock_lambda
            mock_lambda.invoke.return_value = {
                "StatusCode": 200,
                "Payload": MagicMock(
                    read=lambda: json.dumps(
                        {"stale_evaluations_archived": 3}
                    ).encode()
                ),
            }

            response = client.post(
                "/api/v1/admin/cleanup", json={"action": "stale"}
            )

            assert response.status_code == 200
            # Verify Lambda was called with correct action
            call_args = mock_lambda.invoke.call_args
            payload = json.loads(call_args.kwargs["Payload"])
            assert payload["action"] == "stale"

    def test_cleanup_orphans_with_delete(self, client: TestClient):
        """Test cleanup orphans with delete_orphans=True."""
        with patch("app.api.v1.admin.boto3") as mock_boto3:
            mock_lambda = MagicMock()
            mock_boto3.client.return_value = mock_lambda
            mock_lambda.invoke.return_value = {
                "StatusCode": 200,
                "Payload": MagicMock(
                    read=lambda: json.dumps(
                        {"orphans_found": 5, "orphans_deleted": 5}
                    ).encode()
                ),
            }

            response = client.post(
                "/api/v1/admin/cleanup",
                json={"action": "orphans", "delete_orphans": True},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["orphans_deleted"] == 5

            # Verify Lambda was called with delete_orphans=True
            call_args = mock_lambda.invoke.call_args
            payload = json.loads(call_args.kwargs["Payload"])
            assert payload["delete_orphans"] is True

    def test_cleanup_invalid_action(self, client: TestClient):
        """Test cleanup with invalid action returns validation error."""
        response = client.post(
            "/api/v1/admin/cleanup", json={"action": "invalid"}
        )
        assert response.status_code == 422

    def test_cleanup_lambda_error(self, client: TestClient):
        """Test cleanup handles Lambda invocation errors."""
        with patch("app.api.v1.admin.boto3") as mock_boto3:
            mock_lambda = MagicMock()
            mock_boto3.client.return_value = mock_lambda
            mock_lambda.invoke.return_value = {
                "StatusCode": 200,
                "Payload": MagicMock(
                    read=lambda: json.dumps(
                        {"error": "bucket is required for orphans action"}
                    ).encode()
                ),
            }

            response = client.post(
                "/api/v1/admin/cleanup", json={"action": "all"}
            )

            assert response.status_code == 500
            data = response.json()
            assert "error" in data["detail"].lower()

    def test_cleanup_default_action_is_all(self, client: TestClient):
        """Test that default action is 'all'."""
        with patch("app.api.v1.admin.boto3") as mock_boto3:
            mock_lambda = MagicMock()
            mock_boto3.client.return_value = mock_lambda
            mock_lambda.invoke.return_value = {
                "StatusCode": 200,
                "Payload": MagicMock(
                    read=lambda: json.dumps(
                        {"stale_evaluations_archived": 0}
                    ).encode()
                ),
            }

            response = client.post("/api/v1/admin/cleanup", json={})

            assert response.status_code == 200
            call_args = mock_lambda.invoke.call_args
            payload = json.loads(call_args.kwargs["Payload"])
            assert payload["action"] == "all"
