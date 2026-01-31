"""Tests for profile generation worker handler."""

import json
from unittest.mock import MagicMock, patch

from app.services.profile_worker import handle_profile_generation_message, handler


class TestProfileWorker:
    """Tests for profile generation worker handler."""

    @patch("app.services.profile_worker.get_or_build_graph")
    @patch("app.services.profile_worker.generate_and_cache_profile")
    @patch("app.services.profile_worker._update_job_progress")
    def test_success_increments_succeeded(self, mock_update, mock_gen, mock_graph, db):
        """Successful generation increments succeeded count."""
        mock_graph.return_value = MagicMock()
        mock_gen.return_value = MagicMock()

        message = {
            "job_id": "test-job-1",
            "entity_type": "author",
            "entity_id": 1,
            "owner_id": 1,
        }

        handle_profile_generation_message(message, db)

        mock_gen.assert_called_once()
        mock_update.assert_called_once_with(db, "test-job-1", success=True)

    @patch("app.services.profile_worker.get_or_build_graph")
    @patch("app.services.profile_worker.generate_and_cache_profile")
    @patch("app.services.profile_worker._update_job_progress")
    def test_failure_increments_failed(self, mock_update, mock_gen, mock_graph, db):
        """Failed generation increments failed count."""
        mock_graph.return_value = MagicMock()
        mock_gen.side_effect = Exception("Bedrock error")

        message = {
            "job_id": "test-job-1",
            "entity_type": "author",
            "entity_id": 1,
            "owner_id": 1,
        }

        handle_profile_generation_message(message, db)

        mock_update.assert_called_once_with(
            db, "test-job-1", success=False, error="author:1: Bedrock error"
        )

    @patch("app.services.profile_worker.get_or_build_graph")
    @patch("app.services.profile_worker._check_staleness")
    @patch("app.services.profile_worker.generate_and_cache_profile")
    @patch("app.services.profile_worker._update_job_progress")
    def test_skips_non_stale_entity(self, mock_update, mock_gen, mock_stale, mock_graph, db):
        """Non-stale entity is skipped (idempotency)."""
        mock_graph.return_value = MagicMock()
        mock_stale.return_value = False  # Not stale = already generated

        message = {
            "job_id": "test-job-1",
            "entity_type": "author",
            "entity_id": 1,
            "owner_id": 1,
        }

        handle_profile_generation_message(message, db)

        mock_gen.assert_not_called()
        mock_update.assert_called_once_with(db, "test-job-1", success=True)


class TestProfileWorkerHandler:
    """Tests for Lambda handler entry point."""

    @patch("app.services.profile_worker.SessionLocal")
    @patch("app.services.profile_worker.handle_profile_generation_message")
    def test_handler_processes_sqs_records(self, mock_handle, mock_session):
        """Handler iterates SQS records and calls handle per message."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        event = {
            "Records": [
                {
                    "messageId": "msg-1",
                    "body": json.dumps(
                        {
                            "job_id": "j1",
                            "entity_type": "author",
                            "entity_id": 1,
                            "owner_id": 1,
                        }
                    ),
                },
            ]
        }

        result = handler(event, None)

        assert result == {"batchItemFailures": []}
        mock_handle.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("app.services.profile_worker.SessionLocal")
    @patch("app.services.profile_worker.handle_profile_generation_message")
    def test_handler_reports_failures(self, mock_handle, mock_session):
        """Handler reports failed messages in batchItemFailures."""
        mock_session.return_value = MagicMock()
        mock_handle.side_effect = Exception("DB error")

        event = {
            "Records": [
                {
                    "messageId": "msg-1",
                    "body": json.dumps(
                        {"job_id": "j1", "entity_type": "author", "entity_id": 1, "owner_id": 1}
                    ),
                },
            ]
        }

        result = handler(event, None)

        assert result == {"batchItemFailures": [{"itemIdentifier": "msg-1"}]}

    def test_handler_version_check(self):
        """Version check payload returns version info."""
        result = handler({"version": True}, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["worker"] == "profile-generation"
