"""Tests for entity enrichment worker."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.models.author import Author
from app.models.binder import Binder
from app.models.publisher import Publisher
from app.services.entity_enrichment_worker import (
    _apply_enrichment,
    _build_enrichment_prompt,
    _classify_era,
    _parse_enrichment_response,
    handle_entity_enrichment_message,
    handler,
)


class TestClassifyEra:
    """Tests for era classification from birth/death years."""

    def test_victorian_author(self):
        assert _classify_era(1819, 1900) == "Victorian"

    def test_romantic_author(self):
        assert _classify_era(1788, 1824) == "Romantic"

    def test_georgian_author(self):
        assert _classify_era(1709, 1784) == "Georgian"

    def test_modern_author(self):
        assert _classify_era(1920, 1990) == "Modern"

    def test_edwardian_author(self):
        # midpoint = (1880+1930)/2 = 1905 -> Edwardian (1901-1914)
        assert _classify_era(1880, 1930) == "Edwardian"

    def test_death_year_only(self):
        """Falls back to death_year - 30 as midpoint."""
        # death_year=1900, midpoint=1870 -> Victorian (1837-1901)
        assert _classify_era(None, 1900) == "Victorian"

    def test_birth_year_only(self):
        """Falls back to birth_year + 40 as midpoint."""
        # birth_year=1820, midpoint=1860 -> Victorian (1837-1901)
        assert _classify_era(1820, None) == "Victorian"

    def test_no_years(self):
        assert _classify_era(None, None) is None


class TestBuildEnrichmentPrompt:
    """Tests for prompt construction."""

    def test_author_prompt_contains_name(self):
        prompt = _build_enrichment_prompt("author", "Charles Dickens")
        assert "Charles Dickens" in prompt
        assert "birth_year" in prompt
        assert "death_year" in prompt
        assert "era" in prompt

    def test_publisher_prompt_contains_name(self):
        prompt = _build_enrichment_prompt("publisher", "Macmillan")
        assert "Macmillan" in prompt
        assert "founded_year" in prompt
        assert "description" in prompt

    def test_binder_prompt_contains_name(self):
        prompt = _build_enrichment_prompt("binder", "Zaehnsdorf")
        assert "Zaehnsdorf" in prompt
        assert "founded_year" in prompt
        assert "closed_year" in prompt
        assert "full_name" in prompt


class TestParseEnrichmentResponse:
    """Tests for Bedrock response parsing."""

    def test_plain_json(self):
        response = '{"birth_year": 1812, "death_year": 1870, "era": "Victorian"}'
        result = _parse_enrichment_response(response)
        assert result["birth_year"] == 1812
        assert result["death_year"] == 1870

    def test_json_in_code_block(self):
        response = '```json\n{"birth_year": 1812, "death_year": 1870}\n```'
        result = _parse_enrichment_response(response)
        assert result["birth_year"] == 1812

    def test_json_in_generic_code_block(self):
        response = '```\n{"founded_year": 1843}\n```'
        result = _parse_enrichment_response(response)
        assert result["founded_year"] == 1843

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_enrichment_response("not json at all")


class TestApplyEnrichment:
    """Tests for applying enrichment data to entities."""

    def test_updates_null_author_fields(self, db):
        author = Author(name="Charles Dickens")
        db.add(author)
        db.commit()
        db.refresh(author)

        updated = _apply_enrichment(
            db,
            "author",
            author.id,
            {"birth_year": 1812, "death_year": 1870, "era": "Victorian"},
        )

        db.refresh(author)
        assert author.birth_year == 1812
        assert author.death_year == 1870
        assert author.era == "Victorian"
        assert "birth_year" in updated
        assert "death_year" in updated

    def test_does_not_overwrite_existing_values(self, db):
        author = Author(name="Jane Austen", birth_year=1775)
        db.add(author)
        db.commit()
        db.refresh(author)

        updated = _apply_enrichment(
            db,
            "author",
            author.id,
            {"birth_year": 9999, "death_year": 1817},
        )

        db.refresh(author)
        assert author.birth_year == 1775  # NOT overwritten
        assert author.death_year == 1817  # Was NULL, now enriched
        assert "birth_year" not in updated
        assert "death_year" in updated

    def test_derives_era_from_years(self, db):
        """Era is derived from birth/death years if not returned by Bedrock."""
        author = Author(name="Robert Browning")
        db.add(author)
        db.commit()
        db.refresh(author)

        updated = _apply_enrichment(
            db,
            "author",
            author.id,
            {"birth_year": 1812, "death_year": 1889, "era": None},
        )

        db.refresh(author)
        assert author.era == "Victorian"
        assert "era" in updated

    def test_updates_publisher_fields(self, db):
        publisher = Publisher(name="Macmillan")
        db.add(publisher)
        db.commit()
        db.refresh(publisher)

        updated = _apply_enrichment(
            db,
            "publisher",
            publisher.id,
            {"founded_year": 1843, "description": "Major Victorian publisher"},
        )

        db.refresh(publisher)
        assert publisher.founded_year == 1843
        assert publisher.description == "Major Victorian publisher"
        assert "founded_year" in updated

    def test_updates_binder_fields(self, db):
        binder = Binder(name="Zaehnsdorf")
        db.add(binder)
        db.commit()
        db.refresh(binder)

        updated = _apply_enrichment(
            db,
            "binder",
            binder.id,
            {
                "founded_year": 1842,
                "closed_year": 1947,
                "full_name": "Joseph Zaehnsdorf Ltd",
            },
        )

        db.refresh(binder)
        assert binder.founded_year == 1842
        assert binder.closed_year == 1947
        assert binder.full_name == "Joseph Zaehnsdorf Ltd"
        assert len(updated) == 3

    def test_rejects_unreasonable_years(self, db):
        author = Author(name="Nobody Known")
        db.add(author)
        db.commit()
        db.refresh(author)

        updated = _apply_enrichment(
            db,
            "author",
            author.id,
            {"birth_year": 500, "death_year": 3000},
        )

        db.refresh(author)
        assert author.birth_year is None
        assert author.death_year is None
        assert len(updated) == 0

    def test_handles_string_year_values(self, db):
        """Bedrock sometimes returns years as strings."""
        publisher = Publisher(name="Smith Elder")
        db.add(publisher)
        db.commit()
        db.refresh(publisher)

        updated = _apply_enrichment(
            db,
            "publisher",
            publisher.id,
            {"founded_year": "1816", "description": None},
        )

        db.refresh(publisher)
        assert publisher.founded_year == 1816
        assert "founded_year" in updated

    def test_missing_entity_returns_empty(self, db):
        updated = _apply_enrichment(db, "author", 99999, {"birth_year": 1800})
        assert updated == []

    def test_null_enrichment_values_skipped(self, db):
        author = Author(name="Unknown Author")
        db.add(author)
        db.commit()
        db.refresh(author)

        updated = _apply_enrichment(
            db,
            "author",
            author.id,
            {"birth_year": None, "death_year": None, "era": None},
        )

        db.refresh(author)
        assert author.birth_year is None
        assert author.death_year is None
        assert author.era is None
        assert len(updated) == 0

    def test_ignores_unknown_fields(self, db):
        """Extra fields from Bedrock that aren't in the schema are ignored."""
        author = Author(name="Test Author")
        db.add(author)
        db.commit()
        db.refresh(author)

        updated = _apply_enrichment(
            db,
            "author",
            author.id,
            {"birth_year": 1800, "nationality": "British", "favorite_color": "blue"},
        )

        assert "birth_year" in updated
        assert "nationality" not in updated


class TestHandleEntityEnrichmentMessage:
    """Tests for the message handler."""

    @patch("app.services.entity_enrichment_worker._apply_enrichment")
    @patch("app.services.entity_enrichment_worker._parse_enrichment_response")
    @patch("app.services.entity_enrichment_worker._call_bedrock_for_enrichment")
    def test_success_flow(self, mock_bedrock, mock_parse, mock_apply, db):
        """Successful enrichment calls Bedrock and applies data."""
        mock_bedrock.return_value = '{"birth_year": 1812}'
        mock_parse.return_value = {"birth_year": 1812}
        mock_apply.return_value = ["birth_year"]

        message = {
            "entity_type": "author",
            "entity_id": 1,
            "entity_name": "Charles Dickens",
        }

        handle_entity_enrichment_message(message, db)

        mock_bedrock.assert_called_once()
        mock_parse.assert_called_once_with('{"birth_year": 1812}')
        mock_apply.assert_called_once_with(db, "author", 1, {"birth_year": 1812})

    @patch("app.services.entity_enrichment_worker._call_bedrock_for_enrichment")
    def test_bedrock_error_does_not_raise(self, mock_bedrock, db):
        """Bedrock errors are caught and logged, not raised."""
        from botocore.exceptions import ClientError

        mock_bedrock.side_effect = ClientError(
            {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
            "InvokeModel",
        )

        message = {
            "entity_type": "author",
            "entity_id": 1,
            "entity_name": "Test Author",
        }

        # Should not raise
        handle_entity_enrichment_message(message, db)

    @patch("app.services.entity_enrichment_worker._call_bedrock_for_enrichment")
    def test_invalid_json_does_not_raise(self, mock_bedrock, db):
        """Invalid JSON from Bedrock is caught and logged."""
        mock_bedrock.return_value = "I don't know this author"

        message = {
            "entity_type": "publisher",
            "entity_id": 1,
            "entity_name": "Unknown Press",
        }

        # Should not raise
        handle_entity_enrichment_message(message, db)

    def test_unknown_entity_type_logged(self, db):
        """Unknown entity type is logged and skipped."""
        message = {
            "entity_type": "unknown",
            "entity_id": 1,
            "entity_name": "Test",
        }

        # Should not raise
        handle_entity_enrichment_message(message, db)


class TestEnrichmentWorkerHandler:
    """Tests for Lambda handler entry point."""

    @patch("app.services.entity_enrichment_worker.SessionLocal")
    @patch("app.services.entity_enrichment_worker.handle_entity_enrichment_message")
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
                            "entity_type": "author",
                            "entity_id": 1,
                            "entity_name": "Charles Dickens",
                        }
                    ),
                },
            ]
        }

        result = handler(event, None)

        assert result == {"batchItemFailures": []}
        mock_handle.assert_called_once()
        mock_db.close.assert_called_once()

    @patch("app.services.entity_enrichment_worker.SessionLocal")
    @patch("app.services.entity_enrichment_worker.handle_entity_enrichment_message")
    def test_handler_reports_failures(self, mock_handle, mock_session):
        """Handler reports failed messages in batchItemFailures."""
        mock_session.return_value = MagicMock()
        mock_handle.side_effect = Exception("DB error")

        event = {
            "Records": [
                {
                    "messageId": "msg-1",
                    "body": json.dumps(
                        {
                            "entity_type": "author",
                            "entity_id": 1,
                            "entity_name": "Test",
                        }
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
        assert body["worker"] == "entity-enrichment"

    @patch("app.services.entity_enrichment_worker.SessionLocal")
    @patch("app.services.entity_enrichment_worker.handle_entity_enrichment_message")
    def test_handler_multiple_records(self, mock_handle, mock_session):
        """Handler processes multiple SQS records in a batch."""
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        event = {
            "Records": [
                {
                    "messageId": "msg-1",
                    "body": json.dumps(
                        {"entity_type": "author", "entity_id": 1, "entity_name": "Author A"}
                    ),
                },
                {
                    "messageId": "msg-2",
                    "body": json.dumps(
                        {"entity_type": "publisher", "entity_id": 2, "entity_name": "Publisher B"}
                    ),
                },
            ]
        }

        result = handler(event, None)

        assert result == {"batchItemFailures": []}
        assert mock_handle.call_count == 2


class TestSendEntityEnrichmentJob:
    """Tests for the SQS send function (fire-and-forget)."""

    @patch("app.services.sqs.get_entity_enrichment_queue_url")
    @patch("app.services.sqs.get_sqs_client")
    def test_sends_message(self, mock_client_fn, mock_url):
        """Message is sent to SQS with correct payload."""
        from app.services.sqs import send_entity_enrichment_job

        client = MagicMock()
        client.send_message.return_value = {"MessageId": "test-id"}
        mock_client_fn.return_value = client
        mock_url.return_value = "https://sqs/queue"

        send_entity_enrichment_job("author", 42, "Charles Dickens")

        client.send_message.assert_called_once()
        call_kwargs = client.send_message.call_args[1]
        body = json.loads(call_kwargs["MessageBody"])
        assert body["entity_type"] == "author"
        assert body["entity_id"] == 42
        assert body["entity_name"] == "Charles Dickens"

    @patch("app.services.sqs.get_entity_enrichment_queue_url")
    def test_failure_does_not_raise(self, mock_url):
        """SQS failures are caught silently (fire-and-forget)."""
        from app.services.sqs import send_entity_enrichment_job

        mock_url.side_effect = ValueError("Queue not configured")

        # Should NOT raise
        send_entity_enrichment_job("author", 1, "Test")

    @patch("app.services.sqs.settings")
    @patch("app.services.sqs._get_queue_url")
    def test_get_queue_url(self, mock_get_url, mock_settings):
        """Returns queue URL from settings."""
        from app.services.sqs import get_entity_enrichment_queue_url

        mock_settings.entity_enrichment_queue_name = "test-enrichment-queue"
        mock_get_url.return_value = "https://sqs.us-east-1.amazonaws.com/123/test-enrichment-queue"

        url = get_entity_enrichment_queue_url()
        assert url == "https://sqs.us-east-1.amazonaws.com/123/test-enrichment-queue"

    @patch("app.services.sqs.settings")
    def test_get_queue_url_raises_when_not_configured(self, mock_settings):
        """Raises ValueError when queue name not set."""
        from app.services.sqs import get_entity_enrichment_queue_url

        mock_settings.entity_enrichment_queue_name = None
        with pytest.raises(ValueError, match="ENTITY_ENRICHMENT_QUEUE_NAME"):
            get_entity_enrichment_queue_url()
