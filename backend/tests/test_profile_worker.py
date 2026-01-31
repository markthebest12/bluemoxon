"""Tests for profile generation worker handler."""

from unittest.mock import MagicMock, patch

from app.services.profile_worker import handle_profile_generation_message


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

        mock_update.assert_called_once_with(db, "test-job-1", success=False)

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
