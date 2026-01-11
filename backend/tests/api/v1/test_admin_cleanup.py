"""Tests for admin cleanup endpoints."""

import json
import uuid
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.cleanup_job import CleanupJob


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

            response = client.post("/api/v1/admin/cleanup", json={"action": "all"})

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
                    read=lambda: json.dumps({"stale_evaluations_archived": 3}).encode()
                ),
            }

            response = client.post("/api/v1/admin/cleanup", json={"action": "stale"})

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
                    read=lambda: json.dumps({"orphans_found": 5, "orphans_deleted": 5}).encode()
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
        response = client.post("/api/v1/admin/cleanup", json={"action": "invalid"})
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

            response = client.post("/api/v1/admin/cleanup", json={"action": "all"})

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
                    read=lambda: json.dumps({"stale_evaluations_archived": 0}).encode()
                ),
            }

            response = client.post("/api/v1/admin/cleanup", json={})

            assert response.status_code == 200
            call_args = mock_lambda.invoke.call_args
            payload = json.loads(call_args.kwargs["Payload"])
            assert payload["action"] == "all"


class TestOrphanScanEndpoint:
    """Tests for GET /admin/cleanup/orphans/scan endpoint."""

    def test_scan_returns_full_orphan_data(self, client: TestClient):
        """Test that scan returns detailed orphan information."""
        with patch("app.api.v1.admin.boto3") as mock_boto3:
            mock_lambda = MagicMock()
            mock_boto3.client.return_value = mock_lambda
            mock_lambda.invoke.return_value = {
                "StatusCode": 200,
                "Payload": MagicMock(
                    read=lambda: json.dumps(
                        {
                            "orphans_found": 5,
                            "total_bytes": 1024000,
                            "orphans_by_book": [
                                {
                                    "folder_id": 123,
                                    "book_id": 456,
                                    "book_title": "Test Book",
                                    "count": 3,
                                    "bytes": 512000,
                                    "keys": ["123/img1.jpg", "123/img2.jpg", "123/img3.jpg"],
                                },
                                {
                                    "folder_id": 789,
                                    "book_id": None,
                                    "book_title": None,
                                    "count": 2,
                                    "bytes": 512000,
                                    "keys": ["789/img1.jpg", "789/img2.jpg"],
                                },
                            ],
                        }
                    ).encode()
                ),
            }

            response = client.get("/api/v1/admin/cleanup/orphans/scan")

            assert response.status_code == 200
            data = response.json()
            assert data["total_count"] == 5
            assert data["total_bytes"] == 1024000
            assert len(data["orphans_by_book"]) == 2

            # Verify first orphan group (existing book)
            group1 = data["orphans_by_book"][0]
            assert group1["folder_id"] == 123
            assert group1["book_id"] == 456
            assert group1["book_title"] == "Test Book"
            assert group1["count"] == 3
            assert group1["bytes"] == 512000
            assert len(group1["keys"]) == 3

            # Verify second orphan group (deleted book)
            group2 = data["orphans_by_book"][1]
            assert group2["folder_id"] == 789
            assert group2["book_id"] is None
            assert group2["book_title"] is None
            assert group2["count"] == 2

    def test_scan_invokes_lambda_with_return_details(self, client: TestClient):
        """Test that scan requests detailed orphan info from Lambda."""
        with patch("app.api.v1.admin.boto3") as mock_boto3:
            mock_lambda = MagicMock()
            mock_boto3.client.return_value = mock_lambda
            mock_lambda.invoke.return_value = {
                "StatusCode": 200,
                "Payload": MagicMock(
                    read=lambda: json.dumps(
                        {"orphans_found": 0, "total_bytes": 0, "orphans_by_book": []}
                    ).encode()
                ),
            }

            client.get("/api/v1/admin/cleanup/orphans/scan")

            # Verify Lambda was called with return_details=True
            call_args = mock_lambda.invoke.call_args
            payload = json.loads(call_args.kwargs["Payload"])
            assert payload["action"] == "orphans"
            assert payload["delete_orphans"] is False
            assert payload["return_details"] is True

    def test_scan_handles_lambda_error(self, client: TestClient):
        """Test that scan handles Lambda errors gracefully."""
        with patch("app.api.v1.admin.boto3") as mock_boto3:
            mock_lambda = MagicMock()
            mock_boto3.client.return_value = mock_lambda
            mock_lambda.invoke.return_value = {
                "StatusCode": 200,
                "Payload": MagicMock(
                    read=lambda: json.dumps({"error": "S3 access denied"}).encode()
                ),
            }

            response = client.get("/api/v1/admin/cleanup/orphans/scan")

            assert response.status_code == 500
            data = response.json()
            assert "error" in data["detail"].lower()


class TestOrphanDeleteJobEndpoint:
    """Tests for POST /admin/cleanup/orphans/delete endpoint."""

    def test_delete_creates_job_and_returns_id(self, client: TestClient, db: Session):
        """Test that delete creates a job and returns job ID."""
        with patch("app.api.v1.admin.boto3") as mock_boto3:
            mock_lambda = MagicMock()
            mock_boto3.client.return_value = mock_lambda

            response = client.post(
                "/api/v1/admin/cleanup/orphans/delete",
                json={"total_count": 10, "total_bytes": 2048000},
            )

            assert response.status_code == 202
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "pending"

            # Verify job was created in DB
            job_id = uuid.UUID(data["job_id"])
            job = db.get(CleanupJob, job_id)
            assert job is not None
            assert job.total_count == 10
            assert job.total_bytes == 2048000
            assert job.status == "pending"
            assert job.deleted_count == 0
            assert job.deleted_bytes == 0

    def test_delete_invokes_lambda_async(self, client: TestClient, db: Session):
        """Test that delete invokes Lambda asynchronously with job_id."""
        with patch("app.api.v1.admin.boto3") as mock_boto3:
            mock_lambda = MagicMock()
            mock_boto3.client.return_value = mock_lambda

            response = client.post(
                "/api/v1/admin/cleanup/orphans/delete",
                json={"total_count": 10, "total_bytes": 2048000},
            )

            assert response.status_code == 202
            data = response.json()

            # Verify Lambda was invoked asynchronously
            call_args = mock_lambda.invoke.call_args
            assert call_args.kwargs["InvocationType"] == "Event"
            payload = json.loads(call_args.kwargs["Payload"])
            assert payload["job_id"] == data["job_id"]
            assert "bucket" in payload

    def test_delete_requires_total_count_and_bytes(self, client: TestClient):
        """Test that delete requires total_count and total_bytes."""
        response = client.post(
            "/api/v1/admin/cleanup/orphans/delete",
            json={},
        )

        assert response.status_code == 422


class TestCleanupJobStatusEndpoint:
    """Tests for GET /admin/cleanup/jobs/{job_id} endpoint."""

    def test_get_job_status(self, client: TestClient, db: Session):
        """Test getting status of an existing job."""
        # Create a job in the DB
        job = CleanupJob(
            total_count=100,
            total_bytes=10240000,
            deleted_count=50,
            deleted_bytes=5120000,
            status="running",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        response = client.get(f"/api/v1/admin/cleanup/jobs/{job.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == str(job.id)
        assert data["status"] == "running"
        assert data["progress_pct"] == 50.0
        assert data["total_count"] == 100
        assert data["total_bytes"] == 10240000
        assert data["deleted_count"] == 50
        assert data["deleted_bytes"] == 5120000
        assert data["error_message"] is None
        assert "created_at" in data
        assert data["completed_at"] is None

    def test_get_job_status_completed(self, client: TestClient, db: Session):
        """Test getting status of a completed job."""
        from datetime import UTC, datetime

        # Create a completed job in the DB
        job = CleanupJob(
            total_count=100,
            total_bytes=10240000,
            deleted_count=100,
            deleted_bytes=10240000,
            status="completed",
            completed_at=datetime.now(UTC),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        response = client.get(f"/api/v1/admin/cleanup/jobs/{job.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["progress_pct"] == 100.0
        assert data["completed_at"] is not None

    def test_get_job_status_failed(self, client: TestClient, db: Session):
        """Test getting status of a failed job."""
        # Create a failed job in the DB
        job = CleanupJob(
            total_count=100,
            total_bytes=10240000,
            deleted_count=30,
            deleted_bytes=3072000,
            status="failed",
            error_message="S3 rate limit exceeded",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        response = client.get(f"/api/v1/admin/cleanup/jobs/{job.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_message"] == "S3 rate limit exceeded"
        assert data["progress_pct"] == 30.0

    def test_get_nonexistent_job_returns_404(self, client: TestClient):
        """Test that requesting a nonexistent job returns 404."""
        fake_uuid = str(uuid.uuid4())
        response = client.get(f"/api/v1/admin/cleanup/jobs/{fake_uuid}")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_job_invalid_uuid_returns_422(self, client: TestClient):
        """Test that an invalid UUID returns 422."""
        response = client.get("/api/v1/admin/cleanup/jobs/not-a-uuid")

        assert response.status_code == 422
