"""Tests for ValidationResult and EntityAssociationResult dataclasses.

These tests cover the new dataclasses introduced to provide visibility into
entity validation outcomes, especially for log mode where associations
may be skipped without returning an error.
"""

from unittest.mock import MagicMock, patch

from app.schemas.entity_validation import EntityValidationError
from app.services.entity_matching import EntityMatch


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_success_when_entity_id_set(self):
        """ValidationResult.success is True when entity_id is set."""
        from app.services.entity_validation import ValidationResult

        result = ValidationResult(entity_id=42)
        assert result.success is True
        assert result.was_skipped is False
        assert result.error is None

    def test_not_success_when_entity_id_none(self):
        """ValidationResult.success is False when entity_id is None."""
        from app.services.entity_validation import ValidationResult

        result = ValidationResult()
        assert result.success is False

    def test_was_skipped_when_skipped_match_set(self):
        """ValidationResult.was_skipped is True when skipped_match is set."""
        from app.services.entity_validation import ValidationResult

        match = EntityMatch(
            entity_id=5,
            name="Riviere & Son",
            tier="TIER_1",
            confidence=0.94,
            book_count=12,
        )
        result = ValidationResult(skipped_match=match)
        assert result.was_skipped is True
        assert result.success is False
        assert result.skipped_match.name == "Riviere & Son"

    def test_error_stored(self):
        """ValidationResult stores error correctly."""
        from app.services.entity_validation import ValidationResult

        error = EntityValidationError(
            error="unknown_entity",
            entity_type="binder",
            input="Unknown Binder",
            suggestions=None,
            resolution="Create the binder first",
        )
        result = ValidationResult(error=error)
        assert result.error is not None
        assert result.error.error == "unknown_entity"
        assert result.success is False
        assert result.was_skipped is False

    def test_default_empty_result(self):
        """Empty ValidationResult has all properties False/None."""
        from app.services.entity_validation import ValidationResult

        result = ValidationResult()
        assert result.entity_id is None
        assert result.skipped_match is None
        assert result.error is None
        assert result.success is False
        assert result.was_skipped is False


class TestEntityAssociationResult:
    """Test EntityAssociationResult dataclass."""

    def test_has_errors_when_binder_error(self):
        """has_errors is True when binder has an error."""
        from app.services.entity_validation import (
            EntityAssociationResult,
            ValidationResult,
        )

        error = EntityValidationError(
            error="unknown_entity",
            entity_type="binder",
            input="Unknown Binder",
            suggestions=None,
            resolution="Create the binder first",
        )
        result = EntityAssociationResult(
            binder=ValidationResult(error=error),
            publisher=ValidationResult(entity_id=10),
        )
        assert result.has_errors is True

    def test_has_errors_when_publisher_error(self):
        """has_errors is True when publisher has an error."""
        from app.services.entity_validation import (
            EntityAssociationResult,
            ValidationResult,
        )

        error = EntityValidationError(
            error="similar_entity_exists",
            entity_type="publisher",
            input="Macmilan",
            suggestions=None,
            resolution="Use existing publisher",
        )
        result = EntityAssociationResult(
            binder=ValidationResult(entity_id=5),
            publisher=ValidationResult(error=error),
        )
        assert result.has_errors is True

    def test_no_errors_when_both_success(self):
        """has_errors is False when both have entity_ids."""
        from app.services.entity_validation import (
            EntityAssociationResult,
            ValidationResult,
        )

        result = EntityAssociationResult(
            binder=ValidationResult(entity_id=5),
            publisher=ValidationResult(entity_id=10),
        )
        assert result.has_errors is False

    def test_has_skipped_when_binder_skipped(self):
        """has_skipped is True when binder was skipped."""
        from app.services.entity_validation import (
            EntityAssociationResult,
            ValidationResult,
        )

        match = EntityMatch(
            entity_id=5,
            name="Riviere & Son",
            tier="TIER_1",
            confidence=0.94,
            book_count=12,
        )
        result = EntityAssociationResult(
            binder=ValidationResult(skipped_match=match),
            publisher=ValidationResult(entity_id=10),
        )
        assert result.has_skipped is True

    def test_has_skipped_when_publisher_skipped(self):
        """has_skipped is True when publisher was skipped."""
        from app.services.entity_validation import (
            EntityAssociationResult,
            ValidationResult,
        )

        match = EntityMatch(
            entity_id=10,
            name="Macmillan and Co.",
            tier="TIER_1",
            confidence=0.91,
            book_count=20,
        )
        result = EntityAssociationResult(
            binder=ValidationResult(entity_id=5),
            publisher=ValidationResult(skipped_match=match),
        )
        assert result.has_skipped is True

    def test_no_skipped_when_both_success(self):
        """has_skipped is False when both have entity_ids."""
        from app.services.entity_validation import (
            EntityAssociationResult,
            ValidationResult,
        )

        result = EntityAssociationResult(
            binder=ValidationResult(entity_id=5),
            publisher=ValidationResult(entity_id=10),
        )
        assert result.has_skipped is False

    def test_empty_results(self):
        """Empty results (no binder/publisher) have no errors/skips."""
        from app.services.entity_validation import (
            EntityAssociationResult,
            ValidationResult,
        )

        result = EntityAssociationResult(
            binder=ValidationResult(),
            publisher=ValidationResult(),
        )
        assert result.has_errors is False
        assert result.has_skipped is False


class TestValidateEntityForBookReturnsValidationResult:
    """Test validate_entity_for_book returns ValidationResult."""

    def test_exact_match_returns_validation_result_with_id(self):
        """Exact match returns ValidationResult with entity_id set."""
        from app.services.entity_validation import (
            ValidationResult,
            validate_entity_for_book,
        )

        db = MagicMock()
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=(5, "Macmillan and Co."),
        ):
            result = validate_entity_for_book(db, "publisher", "Macmillan and Co.")

        assert isinstance(result, ValidationResult)
        assert result.entity_id == 5
        assert result.success is True

    def test_fuzzy_match_enforce_returns_validation_result_with_error(self):
        """Fuzzy match in enforce mode returns ValidationResult with error."""
        from app.services.entity_validation import (
            ValidationResult,
            validate_entity_for_book,
        )

        db = MagicMock()
        match = EntityMatch(
            entity_id=5,
            name="Macmillan and Co.",
            tier="TIER_1",
            confidence=0.94,
            book_count=12,
        )
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=None,
        ):
            with patch(
                "app.services.entity_validation.fuzzy_match_entity",
                return_value=[match],
            ):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "enforce"
                    mock_settings.return_value.entity_match_threshold_publisher = 0.80
                    result = validate_entity_for_book(db, "publisher", "Macmilan")

        assert isinstance(result, ValidationResult)
        assert result.error is not None
        assert result.error.error == "similar_entity_exists"
        assert result.success is False

    def test_fuzzy_match_log_mode_returns_validation_result_with_skipped(self):
        """Fuzzy match in log mode returns ValidationResult with skipped_match.

        This is the key fix for #1013 - user can now see WHY the association
        was skipped and what entity matched.
        """
        from app.services.entity_validation import (
            ValidationResult,
            validate_entity_for_book,
        )

        db = MagicMock()
        match = EntityMatch(
            entity_id=5,
            name="Macmillan and Co.",
            tier="TIER_1",
            confidence=0.94,
            book_count=12,
        )
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=None,
        ):
            with patch(
                "app.services.entity_validation.fuzzy_match_entity",
                return_value=[match],
            ):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "log"
                    mock_settings.return_value.entity_match_threshold_publisher = 0.80
                    result = validate_entity_for_book(db, "publisher", "Macmilan")

        assert isinstance(result, ValidationResult)
        assert result.was_skipped is True
        assert result.skipped_match is not None
        assert result.skipped_match.name == "Macmillan and Co."
        assert result.skipped_match.confidence == 0.94
        assert result.success is False
        assert result.error is None

    def test_no_match_enforce_returns_validation_result_with_error(self):
        """No match in enforce mode returns ValidationResult with unknown_entity error."""
        from app.services.entity_validation import (
            ValidationResult,
            validate_entity_for_book,
        )

        db = MagicMock()
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=None,
        ):
            with patch(
                "app.services.entity_validation.fuzzy_match_entity",
                return_value=[],
            ):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "enforce"
                    mock_settings.return_value.entity_match_threshold_publisher = 0.80
                    result = validate_entity_for_book(db, "publisher", "Unknown Press")

        assert isinstance(result, ValidationResult)
        assert result.error is not None
        assert result.error.error == "unknown_entity"
        assert result.success is False

    def test_no_match_log_mode_returns_empty_validation_result(self):
        """No match in log mode returns empty ValidationResult (no association)."""
        from app.services.entity_validation import (
            ValidationResult,
            validate_entity_for_book,
        )

        db = MagicMock()
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=None,
        ):
            with patch(
                "app.services.entity_validation.fuzzy_match_entity",
                return_value=[],
            ):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "log"
                    mock_settings.return_value.entity_match_threshold_publisher = 0.80
                    result = validate_entity_for_book(db, "publisher", "Unknown Press")

        assert isinstance(result, ValidationResult)
        assert result.success is False
        assert result.was_skipped is False
        assert result.error is None

    def test_empty_name_returns_empty_validation_result(self):
        """Empty or None name returns empty ValidationResult."""
        from app.services.entity_validation import (
            ValidationResult,
            validate_entity_for_book,
        )

        db = MagicMock()

        result = validate_entity_for_book(db, "publisher", None)
        assert isinstance(result, ValidationResult)
        assert result.success is False
        assert result.was_skipped is False
        assert result.error is None

        result = validate_entity_for_book(db, "publisher", "")
        assert isinstance(result, ValidationResult)

        result = validate_entity_for_book(db, "publisher", "   ")
        assert isinstance(result, ValidationResult)


class TestValidateAndAssociateEntities:
    """Test validate_and_associate_entities function."""

    def test_associates_both_binder_and_publisher_on_success(self):
        """Successfully associates both binder and publisher when exact matches found."""
        from app.services.entity_validation import validate_and_associate_entities
        from app.utils.markdown_parser import ParsedAnalysis

        db = MagicMock()
        book = MagicMock()
        book.binder_id = None
        book.publisher_id = None

        parsed = ParsedAnalysis(
            binder_identification={"name": "Riviere & Son", "confidence": "HIGH"},
            publisher_identification={"name": "Macmillan and Co."},
        )

        # Mock exact matches for both
        def mock_get_normalized_name(db, entity_type, name):
            if entity_type == "binder":
                return (5, "Riviere & Son")
            elif entity_type == "publisher":
                return (10, "Macmillan and Co.")
            return None

        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            side_effect=mock_get_normalized_name,
        ):
            result = validate_and_associate_entities(db, book, parsed)

        assert result.binder.success is True
        assert result.binder.entity_id == 5
        assert result.publisher.success is True
        assert result.publisher.entity_id == 10
        assert book.binder_id == 5
        assert book.publisher_id == 10

    def test_does_not_associate_on_error(self):
        """Does not set book IDs when validation returns errors."""
        from app.services.entity_validation import validate_and_associate_entities
        from app.utils.markdown_parser import ParsedAnalysis

        db = MagicMock()
        book = MagicMock()
        book.binder_id = None
        book.publisher_id = None

        parsed = ParsedAnalysis(
            binder_identification={"name": "Unknown Binder"},
            publisher_identification={"name": "Unknown Publisher"},
        )

        # Mock no matches (which returns error in enforce mode)
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=None,
        ):
            with patch(
                "app.services.entity_validation.fuzzy_match_entity",
                return_value=[],
            ):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "enforce"
                    mock_settings.return_value.entity_match_threshold_binder = 0.80
                    mock_settings.return_value.entity_match_threshold_publisher = 0.80
                    result = validate_and_associate_entities(db, book, parsed)

        assert result.has_errors is True
        assert result.binder.error is not None
        assert result.publisher.error is not None
        # Book IDs should NOT be set
        assert book.binder_id is None
        assert book.publisher_id is None

    def test_handles_missing_binder_identification(self):
        """Handles case where binder_identification is None."""
        from app.services.entity_validation import validate_and_associate_entities
        from app.utils.markdown_parser import ParsedAnalysis

        db = MagicMock()
        book = MagicMock()
        book.binder_id = None
        book.publisher_id = None

        parsed = ParsedAnalysis(
            binder_identification=None,
            publisher_identification={"name": "Macmillan and Co."},
        )

        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=(10, "Macmillan and Co."),
        ):
            result = validate_and_associate_entities(db, book, parsed)

        assert result.binder.success is False
        assert result.binder.error is None  # Not an error, just no binder
        assert result.publisher.success is True
        assert book.publisher_id == 10
        assert book.binder_id is None

    def test_handles_missing_name_in_identification(self):
        """Handles case where identification exists but name is None/empty."""
        from app.services.entity_validation import validate_and_associate_entities
        from app.utils.markdown_parser import ParsedAnalysis

        db = MagicMock()
        book = MagicMock()
        book.binder_id = None
        book.publisher_id = None

        parsed = ParsedAnalysis(
            binder_identification={"confidence": "HIGH"},  # No name
            publisher_identification={"name": ""},  # Empty name
        )

        result = validate_and_associate_entities(db, book, parsed)

        assert result.binder.success is False
        assert result.publisher.success is False
        assert result.has_errors is False  # Empty is not an error
        assert book.binder_id is None
        assert book.publisher_id is None

    def test_returns_skipped_match_info_in_log_mode(self):
        """Returns skipped match info for visibility when in log mode."""
        from app.services.entity_validation import validate_and_associate_entities
        from app.utils.markdown_parser import ParsedAnalysis

        db = MagicMock()
        book = MagicMock()
        book.binder_id = None
        book.publisher_id = None

        parsed = ParsedAnalysis(
            binder_identification={"name": "Riviere"},  # Close but not exact
            publisher_identification=None,
        )

        match = EntityMatch(
            entity_id=5,
            name="Riviere & Son",
            tier="TIER_1",
            confidence=0.91,
            book_count=15,
        )

        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=None,
        ):
            with patch(
                "app.services.entity_validation.fuzzy_match_entity",
                return_value=[match],
            ):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "log"
                    mock_settings.return_value.entity_match_threshold_binder = 0.80
                    result = validate_and_associate_entities(db, book, parsed)

        assert result.has_skipped is True
        assert result.binder.was_skipped is True
        assert result.binder.skipped_match.name == "Riviere & Son"
        assert result.binder.skipped_match.confidence == 0.91
        # Book ID should NOT be set (skipped, not associated)
        assert book.binder_id is None


class TestEntityAssociationResultDualScenarios:
    """Test scenarios where BOTH binder and publisher have errors or skips."""

    def test_all_errors_returns_both_when_both_fail(self):
        """all_errors property returns both errors when both entities fail validation."""
        from app.services.entity_validation import (
            EntityAssociationResult,
            ValidationResult,
        )

        binder_error = EntityValidationError(
            error="unknown_entity",
            entity_type="binder",
            input="Unknown Binder",
            suggestions=None,
            resolution="Create the binder first",
        )
        publisher_error = EntityValidationError(
            error="similar_entity_exists",
            entity_type="publisher",
            input="Macmilan",
            suggestions=None,
            resolution="Use existing publisher",
        )
        result = EntityAssociationResult(
            binder=ValidationResult(error=binder_error),
            publisher=ValidationResult(error=publisher_error),
        )

        assert result.has_errors is True
        errors = result.all_errors
        assert len(errors) == 2
        assert errors[0].entity_type == "binder"
        assert errors[0].error == "unknown_entity"
        assert errors[1].entity_type == "publisher"
        assert errors[1].error == "similar_entity_exists"

    def test_all_errors_returns_single_when_one_fails(self):
        """all_errors property returns single error when only one entity fails."""
        from app.services.entity_validation import (
            EntityAssociationResult,
            ValidationResult,
        )

        binder_error = EntityValidationError(
            error="unknown_entity",
            entity_type="binder",
            input="Unknown Binder",
            suggestions=None,
            resolution="Create the binder first",
        )
        result = EntityAssociationResult(
            binder=ValidationResult(error=binder_error),
            publisher=ValidationResult(entity_id=10),
        )

        errors = result.all_errors
        assert len(errors) == 1
        assert errors[0].entity_type == "binder"

    def test_all_errors_returns_empty_when_no_errors(self):
        """all_errors property returns empty list when no errors."""
        from app.services.entity_validation import (
            EntityAssociationResult,
            ValidationResult,
        )

        result = EntityAssociationResult(
            binder=ValidationResult(entity_id=5),
            publisher=ValidationResult(entity_id=10),
        )

        assert result.all_errors == []

    def test_format_skipped_warnings_returns_both_when_both_skipped(self):
        """format_skipped_warnings returns warnings for both entities when both skipped."""
        from app.services.entity_validation import (
            EntityAssociationResult,
            ValidationResult,
        )

        binder_match = EntityMatch(
            entity_id=5,
            name="Riviere & Son",
            tier="TIER_1",
            confidence=0.94,
            book_count=12,
        )
        publisher_match = EntityMatch(
            entity_id=10,
            name="Macmillan and Co.",
            tier="TIER_1",
            confidence=0.91,
            book_count=20,
        )
        result = EntityAssociationResult(
            binder=ValidationResult(skipped_match=binder_match),
            publisher=ValidationResult(skipped_match=publisher_match),
        )

        assert result.has_skipped is True
        warnings = result.format_skipped_warnings("Riviere", "Macmilan")
        assert len(warnings) == 2
        assert "binder 'Riviere' fuzzy matches 'Riviere & Son' (94%)" in warnings[0]
        assert "publisher 'Macmilan' fuzzy matches 'Macmillan and Co.' (91%)" in warnings[1]

    def test_format_skipped_warnings_returns_single_when_one_skipped(self):
        """format_skipped_warnings returns single warning when only one entity skipped."""
        from app.services.entity_validation import (
            EntityAssociationResult,
            ValidationResult,
        )

        binder_match = EntityMatch(
            entity_id=5,
            name="Riviere & Son",
            tier="TIER_1",
            confidence=0.94,
            book_count=12,
        )
        result = EntityAssociationResult(
            binder=ValidationResult(skipped_match=binder_match),
            publisher=ValidationResult(entity_id=10),
        )

        warnings = result.format_skipped_warnings("Riviere", "Macmillan")
        assert len(warnings) == 1
        assert "binder 'Riviere'" in warnings[0]

    def test_format_skipped_warnings_returns_empty_when_no_skips(self):
        """format_skipped_warnings returns empty list when no skips."""
        from app.services.entity_validation import (
            EntityAssociationResult,
            ValidationResult,
        )

        result = EntityAssociationResult(
            binder=ValidationResult(entity_id=5),
            publisher=ValidationResult(entity_id=10),
        )

        warnings = result.format_skipped_warnings("Riviere", "Macmillan")
        assert warnings == []

    def test_binder_changed_flag_detects_actual_change(self):
        """binder_changed is True only when binder_id actually changed."""
        from app.services.entity_validation import validate_and_associate_entities
        from app.utils.markdown_parser import ParsedAnalysis

        db = MagicMock()
        book = MagicMock()
        book.binder_id = None  # Will change
        book.publisher_id = 10  # Will NOT change (same value)

        parsed = ParsedAnalysis(
            binder_identification={"name": "Riviere & Son"},
            publisher_identification={"name": "Macmillan and Co."},
        )

        def mock_get_normalized_name(db, entity_type, name):
            if entity_type == "binder":
                return (5, "Riviere & Son")
            elif entity_type == "publisher":
                return (10, "Macmillan and Co.")  # Same as existing
            return None

        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            side_effect=mock_get_normalized_name,
        ):
            result = validate_and_associate_entities(db, book, parsed)

        assert result.binder_changed is True  # Was None, now 5
        assert result.publisher_changed is False  # Already 10

    def test_no_mutation_when_either_has_error(self):
        """Book IDs not mutated when ANY validation returns error.

        This is the CRITICAL fix - validation errors prevent partial state.
        """
        from app.services.entity_validation import validate_and_associate_entities
        from app.utils.markdown_parser import ParsedAnalysis

        db = MagicMock()
        book = MagicMock()
        book.binder_id = None
        book.publisher_id = None

        parsed = ParsedAnalysis(
            binder_identification={"name": "Riviere & Son"},  # Will succeed
            publisher_identification={"name": "Unknown Press"},  # Will fail
        )

        def mock_get_normalized_name(db, entity_type, name):
            if entity_type == "binder":
                return (5, "Riviere & Son")  # Exact match
            return None  # No match for publisher

        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            side_effect=mock_get_normalized_name,
        ):
            with patch(
                "app.services.entity_validation.fuzzy_match_entity",
                return_value=[],
            ):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "enforce"
                    mock_settings.return_value.entity_match_threshold_binder = 0.80
                    mock_settings.return_value.entity_match_threshold_publisher = 0.80
                    result = validate_and_associate_entities(db, book, parsed)

        # Publisher error should prevent ANY mutation
        assert result.has_errors is True
        assert result.publisher.error is not None
        assert result.binder.success is True  # Validation succeeded
        # BUT book should NOT be mutated due to publisher error
        assert book.binder_id is None  # Not set because publisher had error
        assert book.publisher_id is None
        assert result.binder_changed is False
        assert result.publisher_changed is False
