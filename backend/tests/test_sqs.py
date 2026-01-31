"""Tests for SQS service profile generation functions."""

from unittest.mock import MagicMock, patch

import pytest


class TestProfileGenerationQueue:
    """Tests for profile generation SQS dispatch (#1550)."""

    @patch("app.services.sqs.settings")
    @patch("app.services.sqs._get_queue_url")
    def test_get_queue_url(self, mock_get_url, mock_settings):
        """Returns queue URL from settings."""
        from app.services.sqs import get_profile_generation_queue_url

        mock_settings.profile_generation_queue_name = "test-queue"
        mock_get_url.return_value = "https://sqs.us-east-1.amazonaws.com/123/test-queue"

        url = get_profile_generation_queue_url()
        assert url == "https://sqs.us-east-1.amazonaws.com/123/test-queue"

    @patch("app.services.sqs.settings")
    def test_get_queue_url_raises_when_not_configured(self, mock_settings):
        """Raises ValueError when queue name not set."""
        from app.services.sqs import get_profile_generation_queue_url

        mock_settings.profile_generation_queue_name = None
        with pytest.raises(ValueError, match="PROFILE_GENERATION_QUEUE_NAME"):
            get_profile_generation_queue_url()

    @patch("app.services.sqs.get_profile_generation_queue_url")
    @patch("app.services.sqs.get_sqs_client")
    def test_send_jobs_batches_messages(self, mock_client_fn, mock_url):
        """Messages are sent in batches of 10 via send_message_batch."""
        from app.services.sqs import send_profile_generation_jobs

        client = MagicMock()
        client.send_message_batch.return_value = {"Successful": [], "Failed": []}
        mock_client_fn.return_value = client
        mock_url.return_value = "https://sqs/queue"

        messages = [
            {"job_id": "j1", "entity_type": "author", "entity_id": i, "owner_id": 1}
            for i in range(25)
        ]
        send_profile_generation_jobs(messages)

        assert client.send_message_batch.call_count == 3
