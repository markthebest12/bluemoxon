"""Tests for entity validation service."""

from unittest.mock import MagicMock, patch

from app.schemas.entity_validation import EntityValidationError
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


class TestValidateEntityForBook:
    """Test validate_entity_for_book function for book endpoint validation.

    Note: validate_entity_for_book now returns ValidationResult instead of
    int | EntityValidationError | None. Tests updated accordingly.
    """

    def test_exact_match_returns_entity_id(self):
        """Exact match by normalized name in DB returns ValidationResult with entity_id."""
        from app.services.entity_validation import ValidationResult, validate_entity_for_book

        db = MagicMock()
        # Exact match via _get_entity_by_normalized_name returns (id, name)
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=(5, "Macmillan and Co."),
        ):
            result = validate_entity_for_book(db, "publisher", "Macmillan and Co.")

        # Exact match returns ValidationResult with entity_id set
        assert isinstance(result, ValidationResult)
        assert result.entity_id == 5
        assert result.success is True

    def test_fuzzy_match_returns_409_error(self):
        """Fuzzy match (80%+) returns ValidationResult with error set."""
        from app.services.entity_validation import ValidationResult, validate_entity_for_book

        db = MagicMock()
        # No exact match, but fuzzy match found
        match = EntityMatch(
            entity_id=5,
            name="Macmillan and Co.",
            tier="TIER_1",
            confidence=0.94,
            book_count=12,
        )
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name", return_value=None
        ):
            with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[match]):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "enforce"
                    mock_settings.return_value.entity_match_threshold_publisher = 0.80
                    result = validate_entity_for_book(db, "publisher", "Macmilan")

        # Fuzzy match returns ValidationResult with error
        assert isinstance(result, ValidationResult)
        assert result.error is not None
        assert isinstance(result.error, EntityValidationError)
        assert result.error.error == "similar_entity_exists"
        assert result.error.entity_type == "publisher"
        assert result.error.input == "Macmilan"
        assert len(result.error.suggestions) == 1
        assert result.error.suggestions[0].id == 5

    def test_no_match_returns_400_error(self):
        """No match at all returns ValidationResult with unknown_entity error."""
        from app.services.entity_validation import ValidationResult, validate_entity_for_book

        db = MagicMock()
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name", return_value=None
        ):
            with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[]):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "enforce"
                    mock_settings.return_value.entity_match_threshold_publisher = 0.80
                    result = validate_entity_for_book(db, "publisher", "Unknown Press")

        # No match returns ValidationResult with error
        assert isinstance(result, ValidationResult)
        assert result.error is not None
        assert isinstance(result.error, EntityValidationError)
        assert result.error.error == "unknown_entity"
        assert result.error.entity_type == "publisher"
        assert result.error.input == "Unknown Press"
        assert result.error.suggestions is None

    def test_empty_name_returns_empty_result(self):
        """Empty or None name returns empty ValidationResult (skip validation)."""
        from app.services.entity_validation import ValidationResult, validate_entity_for_book

        db = MagicMock()

        # Test None
        result = validate_entity_for_book(db, "publisher", None)
        assert isinstance(result, ValidationResult)
        assert result.success is False
        assert result.error is None

        # Test empty string
        result = validate_entity_for_book(db, "publisher", "")
        assert isinstance(result, ValidationResult)
        assert result.success is False

        # Test whitespace only
        result = validate_entity_for_book(db, "publisher", "   ")
        assert isinstance(result, ValidationResult)
        assert result.success is False

    def test_log_mode_returns_skipped_on_fuzzy_match(self, caplog):
        """In log mode, fuzzy match logs warning and returns skipped_match.

        Unlike before (which returned None), now returns ValidationResult with
        skipped_match set so callers have visibility into why association was
        skipped (#1013 fix).
        """
        import logging

        from app.services.entity_validation import ValidationResult, validate_entity_for_book

        db = MagicMock()
        match = EntityMatch(
            entity_id=5,
            name="Macmillan and Co.",
            tier="TIER_1",
            confidence=0.94,
            book_count=12,
        )

        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name", return_value=None
        ):
            with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[match]):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "log"
                    mock_settings.return_value.entity_match_threshold_publisher = 0.80
                    with caplog.at_level(logging.WARNING):
                        result = validate_entity_for_book(db, "publisher", "Macmilan")

        # Log mode returns ValidationResult with skipped_match for visibility
        assert isinstance(result, ValidationResult)
        assert result.was_skipped is True
        assert result.skipped_match is not None
        assert result.skipped_match.name == "Macmillan and Co."
        assert "would reject" in caplog.text
        assert "skipping association" in caplog.text

    def test_log_mode_returns_empty_on_no_match(self, caplog):
        """In log mode, no match logs warning and returns empty ValidationResult."""
        import logging

        from app.services.entity_validation import ValidationResult, validate_entity_for_book

        db = MagicMock()

        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name", return_value=None
        ):
            with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[]):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "log"
                    mock_settings.return_value.entity_match_threshold_publisher = 0.80
                    with caplog.at_level(logging.WARNING):
                        result = validate_entity_for_book(db, "publisher", "Unknown Press")

        # Log mode returns empty ValidationResult (no entity to associate)
        assert isinstance(result, ValidationResult)
        assert result.success is False
        assert result.was_skipped is False
        assert result.error is None
        assert "unknown" in caplog.text.lower() or "not found" in caplog.text.lower()

    def test_binder_exact_match(self):
        """Binder exact match by normalized name returns ValidationResult with entity_id."""
        from app.services.entity_validation import ValidationResult, validate_entity_for_book

        db = MagicMock()
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=(10, "Riviere & Son"),
        ):
            result = validate_entity_for_book(db, "binder", "Riviere & Son")

        # Exact match for binder returns ValidationResult with entity_id
        assert isinstance(result, ValidationResult)
        assert result.entity_id == 10
        assert result.success is True

    def test_author_exact_match(self):
        """Author exact match by normalized name returns ValidationResult with entity_id."""
        from app.services.entity_validation import ValidationResult, validate_entity_for_book

        db = MagicMock()
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=(20, "Charles Dickens"),
        ):
            result = validate_entity_for_book(db, "author", "Charles Dickens")

        # Exact match for author returns ValidationResult with entity_id
        assert isinstance(result, ValidationResult)
        assert result.entity_id == 20
        assert result.success is True


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
