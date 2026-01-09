"""Tests for entity validation service."""

from unittest.mock import MagicMock, patch

from app.services.entity_matching import EntityMatch


class TestValidateEntityCreation:
    """Test validate_entity_creation function."""

    def test_returns_none_when_no_matches(self):
        """No matches means validation passes."""
        from app.services.entity_validation import validate_entity_creation

        db = MagicMock()
        with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[]):
            result = validate_entity_creation(db, "publisher", "Totally New Press")
        assert result is None

    def test_returns_error_when_similar_exists(self):
        """Similar match returns EntityValidationError."""
        from app.services.entity_validation import validate_entity_creation

        db = MagicMock()
        match = EntityMatch(
            entity_id=5,
            name="Macmillan and Co.",
            tier="TIER_1",
            confidence=0.94,
            book_count=12,
        )
        with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[match]):
            with patch("app.services.entity_validation.get_settings") as mock_settings:
                mock_settings.return_value.entity_validation_mode = "enforce"
                result = validate_entity_creation(db, "publisher", "Macmilan")

        assert result is not None
        assert result.error == "similar_entity_exists"
        assert result.entity_type == "publisher"
        assert result.input == "Macmilan"
        assert len(result.suggestions) == 1
        assert result.suggestions[0].id == 5
        assert result.suggestions[0].match == 0.94

    def test_exact_match_returns_error(self):
        """Exact match (1.0 confidence) should still return error."""
        from app.services.entity_validation import validate_entity_creation

        db = MagicMock()
        match = EntityMatch(
            entity_id=5,
            name="Macmillan and Co.",
            tier="TIER_1",
            confidence=1.0,
            book_count=12,
        )
        with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[match]):
            with patch("app.services.entity_validation.get_settings") as mock_settings:
                mock_settings.return_value.entity_validation_mode = "enforce"
                result = validate_entity_creation(db, "publisher", "Macmillan and Co.")

        # Even exact match should return error - entity already exists
        assert result is not None
        assert result.error == "similar_entity_exists"

    def test_multiple_suggestions_returned(self):
        """Multiple matches are returned as suggestions."""
        from app.services.entity_validation import validate_entity_creation

        db = MagicMock()
        matches = [
            EntityMatch(
                entity_id=5, name="Macmillan and Co.", tier="TIER_1", confidence=0.94, book_count=12
            ),
            EntityMatch(
                entity_id=6, name="Macmillan Ltd", tier="TIER_2", confidence=0.88, book_count=3
            ),
        ]
        with patch("app.services.entity_validation.fuzzy_match_entity", return_value=matches):
            with patch("app.services.entity_validation.get_settings") as mock_settings:
                mock_settings.return_value.entity_validation_mode = "enforce"
                result = validate_entity_creation(db, "publisher", "Macmilan")

        assert result is not None
        assert len(result.suggestions) == 2
        assert result.suggestions[0].id == 5
        assert result.suggestions[1].id == 6


class TestValidationMode:
    """Test log-only vs enforce validation modes."""

    def test_log_mode_returns_none_but_logs(self, caplog):
        """In log mode, validation passes but logs warning."""
        import logging

        from app.services.entity_validation import validate_entity_creation

        db = MagicMock()
        match = EntityMatch(
            entity_id=5,
            name="Macmillan and Co.",
            tier="TIER_1",
            confidence=0.94,
            book_count=12,
        )

        with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[match]):
            with patch("app.services.entity_validation.get_settings") as mock_settings:
                mock_settings.return_value.entity_validation_mode = "log"
                with caplog.at_level(logging.WARNING):
                    result = validate_entity_creation(db, "publisher", "Macmilan")

        assert result is None  # Log mode returns None (allows creation)
        assert "would reject" in caplog.text
        assert "Macmilan" in caplog.text

    def test_enforce_mode_returns_error(self):
        """In enforce mode, validation returns error."""
        from app.services.entity_validation import validate_entity_creation

        db = MagicMock()
        match = EntityMatch(
            entity_id=5,
            name="Macmillan and Co.",
            tier="TIER_1",
            confidence=0.94,
            book_count=12,
        )

        with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[match]):
            with patch("app.services.entity_validation.get_settings") as mock_settings:
                mock_settings.return_value.entity_validation_mode = "enforce"
                result = validate_entity_creation(db, "publisher", "Macmilan")

        assert result is not None
        assert result.error == "similar_entity_exists"
