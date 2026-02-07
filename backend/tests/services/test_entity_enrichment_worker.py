"""Tests for portrait sync integration in the entity enrichment worker.

Verifies that portrait sync is triggered after successful enrichment,
that portrait sync failures never cause enrichment to appear failed,
and that the correct portrait sync function is called for each entity type.
"""

from unittest.mock import patch

from app.services.entity_enrichment_worker import (
    _trigger_portrait_sync,
    handle_entity_enrichment_message,
)
from app.services.wikidata_client import WikidataThrottledError


class TestPortraitSyncTriggeredAfterEnrichment:
    """Verify portrait sync is called after successful enrichment."""

    @patch("app.services.entity_enrichment_worker._trigger_portrait_sync")
    @patch("app.services.entity_enrichment_worker._apply_enrichment")
    @patch("app.services.entity_enrichment_worker._parse_enrichment_response")
    @patch("app.services.entity_enrichment_worker._call_bedrock_for_enrichment")
    def test_successful_enrichment_triggers_portrait_sync(
        self, mock_bedrock, mock_parse, mock_apply, mock_portrait, db
    ):
        """After enrichment succeeds, portrait sync is called with correct args."""
        mock_bedrock.return_value = '{"birth_year": 1812}'
        mock_parse.return_value = {"birth_year": 1812}
        mock_apply.return_value = ["birth_year"]

        message = {
            "entity_type": "author",
            "entity_id": 42,
            "entity_name": "Charles Dickens",
        }

        handle_entity_enrichment_message(message, db)

        mock_portrait.assert_called_once_with(db, "author", 42)

    @patch("app.services.entity_enrichment_worker._trigger_portrait_sync")
    @patch("app.services.entity_enrichment_worker._apply_enrichment")
    @patch("app.services.entity_enrichment_worker._parse_enrichment_response")
    @patch("app.services.entity_enrichment_worker._call_bedrock_for_enrichment")
    def test_publisher_enrichment_triggers_portrait_sync(
        self, mock_bedrock, mock_parse, mock_apply, mock_portrait, db
    ):
        """Publisher enrichment also triggers portrait sync."""
        mock_bedrock.return_value = '{"founded_year": 1843}'
        mock_parse.return_value = {"founded_year": 1843}
        mock_apply.return_value = ["founded_year"]

        message = {
            "entity_type": "publisher",
            "entity_id": 10,
            "entity_name": "Macmillan",
        }

        handle_entity_enrichment_message(message, db)

        mock_portrait.assert_called_once_with(db, "publisher", 10)

    @patch("app.services.entity_enrichment_worker._trigger_portrait_sync")
    @patch("app.services.entity_enrichment_worker._apply_enrichment")
    @patch("app.services.entity_enrichment_worker._parse_enrichment_response")
    @patch("app.services.entity_enrichment_worker._call_bedrock_for_enrichment")
    def test_binder_enrichment_triggers_portrait_sync(
        self, mock_bedrock, mock_parse, mock_apply, mock_portrait, db
    ):
        """Binder enrichment also triggers portrait sync."""
        mock_bedrock.return_value = '{"founded_year": 1842}'
        mock_parse.return_value = {"founded_year": 1842}
        mock_apply.return_value = ["founded_year"]

        message = {
            "entity_type": "binder",
            "entity_id": 5,
            "entity_name": "Zaehnsdorf",
        }

        handle_entity_enrichment_message(message, db)

        mock_portrait.assert_called_once_with(db, "binder", 5)


class TestPortraitSyncFailureDoesNotFailEnrichment:
    """Portrait sync failures must never cause enrichment to appear failed."""

    @patch("app.services.entity_enrichment_worker._trigger_portrait_sync")
    @patch("app.services.entity_enrichment_worker._apply_enrichment")
    @patch("app.services.entity_enrichment_worker._parse_enrichment_response")
    @patch("app.services.entity_enrichment_worker._call_bedrock_for_enrichment")
    def test_portrait_sync_exception_does_not_propagate(
        self, mock_bedrock, mock_parse, mock_apply, mock_portrait, db
    ):
        """Even if portrait sync raises, enrichment message handling succeeds."""
        mock_bedrock.return_value = '{"birth_year": 1812}'
        mock_parse.return_value = {"birth_year": 1812}
        mock_apply.return_value = ["birth_year"]
        mock_portrait.side_effect = RuntimeError("Wikidata down")

        message = {
            "entity_type": "author",
            "entity_id": 1,
            "entity_name": "Charles Dickens",
        }

        # Should NOT raise — portrait sync failure is swallowed
        # Note: _trigger_portrait_sync internally catches exceptions,
        # but even if it somehow leaked, the enrichment should succeed.
        # Here we test at the _trigger_portrait_sync boundary since the
        # mock replaces the entire function.
        # The real function catches exceptions internally, tested below.
        handle_entity_enrichment_message(message, db)

        mock_apply.assert_called_once()

    @patch("app.services.entity_enrichment_worker.process_person_entity")
    def test_trigger_portrait_sync_catches_generic_exception(self, mock_person, db):
        """_trigger_portrait_sync catches generic exceptions and logs warning."""
        from app.models.author import Author

        author = Author(name="Test Author")
        db.add(author)
        db.commit()
        db.refresh(author)

        mock_person.side_effect = RuntimeError("Network timeout")

        # Should NOT raise
        _trigger_portrait_sync(db, "author", author.id)

        mock_person.assert_called_once()

    @patch("app.services.entity_enrichment_worker.process_person_entity")
    def test_trigger_portrait_sync_catches_wikidata_throttled_error(self, mock_person, db):
        """_trigger_portrait_sync specifically catches WikidataThrottledError."""
        from app.models.author import Author

        author = Author(name="Test Author")
        db.add(author)
        db.commit()
        db.refresh(author)

        mock_person.side_effect = WikidataThrottledError("429 Too Many Requests")

        # Should NOT raise
        _trigger_portrait_sync(db, "author", author.id)

        mock_person.assert_called_once()


class TestFailedEnrichmentDoesNotTriggerPortraitSync:
    """When enrichment fails, portrait sync must NOT be called."""

    @patch("app.services.entity_enrichment_worker._trigger_portrait_sync")
    @patch("app.services.entity_enrichment_worker._call_bedrock_for_enrichment")
    def test_bedrock_error_skips_portrait_sync(self, mock_bedrock, mock_portrait, db):
        """Bedrock ClientError prevents portrait sync from running."""
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

        handle_entity_enrichment_message(message, db)

        mock_portrait.assert_not_called()

    @patch("app.services.entity_enrichment_worker._trigger_portrait_sync")
    @patch("app.services.entity_enrichment_worker._call_bedrock_for_enrichment")
    def test_json_parse_error_skips_portrait_sync(self, mock_bedrock, mock_portrait, db):
        """Invalid JSON from Bedrock prevents portrait sync from running."""
        mock_bedrock.return_value = "I don't know this author"

        message = {
            "entity_type": "publisher",
            "entity_id": 1,
            "entity_name": "Unknown Press",
        }

        handle_entity_enrichment_message(message, db)

        mock_portrait.assert_not_called()

    @patch("app.services.entity_enrichment_worker._trigger_portrait_sync")
    @patch("app.services.entity_enrichment_worker._call_bedrock_for_enrichment")
    def test_unexpected_error_skips_portrait_sync(self, mock_bedrock, mock_portrait, db):
        """Unexpected exception during enrichment prevents portrait sync."""
        mock_bedrock.side_effect = RuntimeError("Unexpected failure")

        message = {
            "entity_type": "binder",
            "entity_id": 1,
            "entity_name": "Test Binder",
        }

        handle_entity_enrichment_message(message, db)

        mock_portrait.assert_not_called()


class TestEntityTypeMapping:
    """Verify correct portrait sync function is called for each entity type."""

    @patch("app.services.entity_enrichment_worker.process_person_entity")
    def test_author_uses_process_person_entity(self, mock_person, db):
        """Authors use process_person_entity for portrait sync."""
        from app.models.author import Author

        author = Author(name="Charles Dickens")
        db.add(author)
        db.commit()
        db.refresh(author)

        mock_person.return_value = {"status": "uploaded"}

        _trigger_portrait_sync(db, "author", author.id)

        mock_person.assert_called_once()
        call_args = mock_person.call_args
        assert call_args[0][1].name == "Charles Dickens"
        assert call_args[0][2] == "author"
        assert call_args[1]["threshold"] == 0.7
        assert call_args[1]["dry_run"] is False

    @patch("app.services.entity_enrichment_worker.process_org_entity")
    def test_publisher_uses_process_org_entity(self, mock_org, db):
        """Publishers use process_org_entity for portrait sync."""
        from app.models.publisher import Publisher

        publisher = Publisher(name="Macmillan")
        db.add(publisher)
        db.commit()
        db.refresh(publisher)

        mock_org.return_value = {"status": "uploaded"}

        _trigger_portrait_sync(db, "publisher", publisher.id)

        mock_org.assert_called_once()
        call_args = mock_org.call_args
        assert call_args[0][1].name == "Macmillan"
        assert call_args[0][2] == "publisher"
        assert call_args[1]["threshold"] == 0.7
        assert call_args[1]["dry_run"] is False

    @patch("app.services.entity_enrichment_worker.process_org_entity")
    def test_binder_uses_process_org_entity(self, mock_org, db):
        """Binders use process_org_entity for portrait sync."""
        from app.models.binder import Binder

        binder = Binder(name="Zaehnsdorf")
        db.add(binder)
        db.commit()
        db.refresh(binder)

        mock_org.return_value = {"status": "no_results"}

        _trigger_portrait_sync(db, "binder", binder.id)

        mock_org.assert_called_once()
        call_args = mock_org.call_args
        assert call_args[0][1].name == "Zaehnsdorf"
        assert call_args[0][2] == "binder"

    @patch("app.services.entity_enrichment_worker.process_person_entity")
    @patch("app.services.entity_enrichment_worker.process_org_entity")
    def test_author_does_not_call_org_entity(self, mock_org, mock_person, db):
        """Author portrait sync never calls process_org_entity."""
        from app.models.author import Author

        author = Author(name="Test Author")
        db.add(author)
        db.commit()
        db.refresh(author)

        mock_person.return_value = {"status": "no_results"}

        _trigger_portrait_sync(db, "author", author.id)

        mock_person.assert_called_once()
        mock_org.assert_not_called()

    @patch("app.services.entity_enrichment_worker.process_org_entity")
    @patch("app.services.entity_enrichment_worker.process_person_entity")
    def test_publisher_does_not_call_person_entity(self, mock_person, mock_org, db):
        """Publisher portrait sync never calls process_person_entity."""
        from app.models.publisher import Publisher

        publisher = Publisher(name="Test Publisher")
        db.add(publisher)
        db.commit()
        db.refresh(publisher)

        mock_org.return_value = {"status": "no_results"}

        _trigger_portrait_sync(db, "publisher", publisher.id)

        mock_org.assert_called_once()
        mock_person.assert_not_called()


class TestTriggerPortraitSyncEdgeCases:
    """Edge cases for _trigger_portrait_sync."""

    @patch("app.services.entity_enrichment_worker.process_person_entity")
    def test_entity_not_found_logs_warning(self, mock_person, db):
        """If entity is not in DB, portrait sync is skipped gracefully."""
        _trigger_portrait_sync(db, "author", 99999)

        mock_person.assert_not_called()
