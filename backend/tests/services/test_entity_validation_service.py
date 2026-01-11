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
    """Test validate_entity_for_book function for book endpoint validation."""

    def test_exact_match_returns_entity_id(self):
        """Exact match by normalized name in DB returns entity ID (not error)."""
        from app.services.entity_validation import validate_entity_for_book

        db = MagicMock()
        # Exact match via _get_entity_by_normalized_name returns (id, name)
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=(5, "Macmillan and Co."),
        ):
            result = validate_entity_for_book(db, "publisher", "Macmillan and Co.")

        # Exact match returns the entity ID (for direct association)
        assert result == 5

    def test_fuzzy_match_returns_409_error(self):
        """Fuzzy match (80%+) returns EntityValidationError with similar_entity_exists."""
        from app.services.entity_validation import validate_entity_for_book

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

        # Fuzzy match returns error with similar_entity_exists
        assert result is not None
        assert isinstance(result, EntityValidationError)
        assert result.error == "similar_entity_exists"
        assert result.entity_type == "publisher"
        assert result.input == "Macmilan"
        assert len(result.suggestions) == 1
        assert result.suggestions[0].id == 5

    def test_no_match_returns_400_error(self):
        """No match at all returns EntityValidationError with unknown_entity."""
        from app.services.entity_validation import validate_entity_for_book

        db = MagicMock()
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name", return_value=None
        ):
            with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[]):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "enforce"
                    mock_settings.return_value.entity_match_threshold_publisher = 0.80
                    result = validate_entity_for_book(db, "publisher", "Unknown Press")

        # No match returns error with unknown_entity
        assert result is not None
        assert isinstance(result, EntityValidationError)
        assert result.error == "unknown_entity"
        assert result.entity_type == "publisher"
        assert result.input == "Unknown Press"
        assert result.suggestions is None

    def test_empty_name_returns_none(self):
        """Empty or None name returns None (skip validation)."""
        from app.services.entity_validation import validate_entity_for_book

        db = MagicMock()

        # Test None
        result = validate_entity_for_book(db, "publisher", None)
        assert result is None

        # Test empty string
        result = validate_entity_for_book(db, "publisher", "")
        assert result is None

        # Test whitespace only
        result = validate_entity_for_book(db, "publisher", "   ")
        assert result is None

    def test_log_mode_returns_none_on_fuzzy_match(self, caplog):
        """In log mode, fuzzy match logs warning but returns None (not fuzzy match ID).

        Returning the fuzzy match ID would silently "correct" the name to a different
        entity, which could corrupt data. Instead, we skip association and log.
        """
        import logging

        from app.services.entity_validation import validate_entity_for_book

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

        # Log mode returns None (skip association to avoid silent correction)
        assert result is None
        assert "would reject" in caplog.text
        assert "skipping association" in caplog.text

    def test_log_mode_returns_none_on_no_match(self, caplog):
        """In log mode, no match logs warning but returns None."""
        import logging

        from app.services.entity_validation import validate_entity_for_book

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

        # Log mode returns None (no entity to associate)
        assert result is None
        assert "unknown" in caplog.text.lower() or "not found" in caplog.text.lower()

    def test_binder_exact_match(self):
        """Binder exact match by normalized name returns entity ID."""
        from app.services.entity_validation import validate_entity_for_book

        db = MagicMock()
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=(10, "Riviere & Son"),
        ):
            result = validate_entity_for_book(db, "binder", "Riviere & Son")

        # Exact match for binder returns entity ID
        assert result == 10

    def test_author_exact_match(self):
        """Author exact match by normalized name returns entity ID."""
        from app.services.entity_validation import validate_entity_for_book

        db = MagicMock()
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=(20, "Charles Dickens"),
        ):
            result = validate_entity_for_book(db, "author", "Charles Dickens")

        # Exact match for author returns entity ID
        assert result == 20


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


class TestAllowUnknownParameter:
    """Test allow_unknown parameter for validate_entity_for_book function.

    The allow_unknown parameter allows analysis workflows to discover new entities
    without triggering unknown_entity errors. This is needed because analysis
    may reference entities not yet in the database.
    """

    def test_allow_unknown_returns_none_instead_of_error(self):
        """With allow_unknown=True, unknown entity returns None instead of error.

        Default behavior (allow_unknown=False) returns EntityValidationError with
        error="unknown_entity". With allow_unknown=True, returns None to allow
        the workflow to proceed.
        """
        from app.services.entity_validation import validate_entity_for_book

        db = MagicMock()

        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name", return_value=None
        ):
            with patch("app.services.entity_validation.fuzzy_match_entity", return_value=[]):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "enforce"
                    mock_settings.return_value.entity_match_threshold_publisher = 0.80

                    # Default behavior: returns error
                    result_default = validate_entity_for_book(db, "publisher", "Unknown Press")
                    assert isinstance(result_default, EntityValidationError)
                    assert result_default.error == "unknown_entity"

                    # With allow_unknown=True: returns None
                    result_allow = validate_entity_for_book(
                        db, "publisher", "Unknown Press", allow_unknown=True
                    )
                    assert result_allow is None

    def test_allow_unknown_still_returns_id_on_exact_match(self):
        """With allow_unknown=True, exact matches still return entity ID.

        The allow_unknown flag only affects the unknown_entity case.
        Exact matches should still return the entity ID for association.
        """
        from app.services.entity_validation import validate_entity_for_book

        db = MagicMock()

        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=(5, "Macmillan and Co."),
        ):
            result = validate_entity_for_book(
                db, "publisher", "Macmillan and Co.", allow_unknown=True
            )

        # Exact match returns entity ID regardless of allow_unknown
        assert result == 5

    def test_allow_unknown_still_returns_error_on_fuzzy_match(self):
        """With allow_unknown=True, fuzzy matches still return similar_entity_exists error.

        The allow_unknown flag only bypasses unknown_entity errors.
        Fuzzy matches should still return similar_entity_exists to prevent
        accidental creation of near-duplicate entities.
        """
        from app.services.entity_validation import validate_entity_for_book

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
                    mock_settings.return_value.entity_validation_mode = "enforce"
                    mock_settings.return_value.entity_match_threshold_publisher = 0.80

                    result = validate_entity_for_book(
                        db, "publisher", "Macmilan", allow_unknown=True
                    )

        # Fuzzy match still returns error even with allow_unknown=True
        assert isinstance(result, EntityValidationError)
        assert result.error == "similar_entity_exists"
        assert result.suggestions[0].id == 5


class TestEntityAssociationResult:
    """Test EntityAssociationResult dataclass for #1014 refactor."""

    def test_result_has_correct_attributes(self):
        """EntityAssociationResult should have all required attributes."""
        from app.services.entity_validation import EntityAssociationResult

        result = EntityAssociationResult()
        assert result.binder_id is None
        assert result.publisher_id is None
        assert result.errors == []
        assert result.warnings == []
        assert result.has_errors is False

    def test_has_errors_returns_true_when_errors_present(self):
        """has_errors property should return True when errors list is non-empty."""
        from app.services.entity_validation import EntityAssociationResult

        error = EntityValidationError(
            error="similar_entity_exists",
            entity_type="binder",
            input="Test",
            suggestions=None,
            resolution="Test resolution",
        )
        result = EntityAssociationResult(errors=[error])
        assert result.has_errors is True

    def test_result_with_entity_ids(self):
        """Result should correctly store entity IDs."""
        from app.services.entity_validation import EntityAssociationResult

        result = EntityAssociationResult(binder_id=10, publisher_id=20)
        assert result.binder_id == 10
        assert result.publisher_id == 20
        assert result.has_errors is False


class TestValidateAndAssociateEntities:
    """Test validate_and_associate_entities function for #1014 refactor.

    This function extracts duplicate validation logic from books.py and worker.py.
    It validates multiple entities at once and returns a structured result.
    """

    def test_returns_entity_ids_on_exact_match(self):
        """Exact matches should return entity IDs in result."""
        from app.services.entity_validation import validate_and_associate_entities

        db = MagicMock()
        # Both binder and publisher have exact matches
        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
        ) as mock_exact:
            mock_exact.side_effect = [
                (10, "Riviere & Son"),  # binder exact match
                (20, "Macmillan"),  # publisher exact match
            ]

            result = validate_and_associate_entities(
                db,
                binder_name="Riviere & Son",
                publisher_name="Macmillan",
            )

        assert result.binder_id == 10
        assert result.publisher_id == 20
        assert result.has_errors is False
        assert result.warnings == []

    def test_returns_errors_on_fuzzy_match_enforce_mode(self):
        """Fuzzy matches should return errors in enforce mode."""
        from app.services.entity_validation import validate_and_associate_entities

        db = MagicMock()
        binder_match = EntityMatch(
            entity_id=10,
            name="Riviere & Son",
            tier="TIER_1",
            confidence=0.92,
            book_count=5,
        )

        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=None,
        ):
            with patch(
                "app.services.entity_validation.fuzzy_match_entity",
                return_value=[binder_match],
            ):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "enforce"
                    mock_settings.return_value.entity_match_threshold_binder = 0.80

                    result = validate_and_associate_entities(
                        db,
                        binder_name="Rivere & Son",  # typo
                        publisher_name=None,
                    )

        assert result.binder_id is None
        assert result.has_errors is True
        assert len(result.errors) == 1
        assert result.errors[0].error == "similar_entity_exists"
        assert result.errors[0].entity_type == "binder"

    def test_collects_all_errors_at_once(self):
        """Should validate all entities and collect all errors, not fail fast."""
        from app.services.entity_validation import validate_and_associate_entities

        db = MagicMock()
        binder_match = EntityMatch(
            entity_id=10,
            name="Riviere & Son",
            tier="TIER_1",
            confidence=0.92,
            book_count=5,
        )
        publisher_match = EntityMatch(
            entity_id=20,
            name="Macmillan and Co.",
            tier="TIER_1",
            confidence=0.88,
            book_count=12,
        )

        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=None,
        ):
            with patch(
                "app.services.entity_validation.fuzzy_match_entity",
            ) as mock_fuzzy:
                # Return different matches for binder vs publisher
                mock_fuzzy.side_effect = [[binder_match], [publisher_match]]

                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "enforce"
                    mock_settings.return_value.entity_match_threshold_binder = 0.80
                    mock_settings.return_value.entity_match_threshold_publisher = 0.80

                    result = validate_and_associate_entities(
                        db,
                        binder_name="Rivere & Son",
                        publisher_name="Macmilan",
                    )

        # Both errors should be collected
        assert result.has_errors is True
        assert len(result.errors) == 2
        entity_types = {e.entity_type for e in result.errors}
        assert entity_types == {"binder", "publisher"}

    def test_log_mode_collects_warnings_for_fuzzy_match(self, caplog):
        """In log mode, fuzzy matches should generate warnings instead of errors (#1013).

        This addresses issue #1013: Log mode silently skips entity associations.
        The user should get visibility into what was skipped via warnings.
        """
        import logging

        from app.services.entity_validation import validate_and_associate_entities

        db = MagicMock()
        binder_match = EntityMatch(
            entity_id=10,
            name="Riviere & Son",
            tier="TIER_1",
            confidence=0.92,
            book_count=5,
        )

        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=None,
        ):
            with patch(
                "app.services.entity_validation.fuzzy_match_entity",
                return_value=[binder_match],
            ):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "log"
                    mock_settings.return_value.entity_match_threshold_binder = 0.80

                    with caplog.at_level(logging.WARNING):
                        result = validate_and_associate_entities(
                            db,
                            binder_name="Rivere & Son",
                            publisher_name=None,
                        )

        # No errors in log mode
        assert result.has_errors is False
        # But should have warning for visibility
        assert len(result.warnings) == 1
        assert "Rivere & Son" in result.warnings[0]
        assert "Riviere & Son" in result.warnings[0]  # The match
        # Still no ID (don't silently associate to fuzzy match)
        assert result.binder_id is None

    def test_log_mode_collects_warnings_for_unknown_entity(self, caplog):
        """In log mode, unknown entities should generate warnings (#1013)."""
        import logging

        from app.services.entity_validation import validate_and_associate_entities

        db = MagicMock()

        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
            return_value=None,
        ):
            with patch(
                "app.services.entity_validation.fuzzy_match_entity",
                return_value=[],  # No matches at all
            ):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "log"
                    mock_settings.return_value.entity_match_threshold_binder = 0.80

                    with caplog.at_level(logging.WARNING):
                        result = validate_and_associate_entities(
                            db,
                            binder_name="Unknown Binder",
                            publisher_name=None,
                        )

        # No errors in log mode
        assert result.has_errors is False
        # But should have warning for visibility
        assert len(result.warnings) == 1
        assert "Unknown Binder" in result.warnings[0]
        assert "not found" in result.warnings[0].lower()

    def test_skips_validation_for_none_names(self):
        """None or empty names should be skipped without errors or warnings."""
        from app.services.entity_validation import validate_and_associate_entities

        db = MagicMock()

        result = validate_and_associate_entities(
            db,
            binder_name=None,
            publisher_name="",
        )

        assert result.binder_id is None
        assert result.publisher_id is None
        assert result.has_errors is False
        assert result.warnings == []

    def test_mixed_exact_and_fuzzy_matches(self):
        """Should handle one exact match and one fuzzy match correctly."""
        from app.services.entity_validation import validate_and_associate_entities

        db = MagicMock()
        publisher_match = EntityMatch(
            entity_id=20,
            name="Macmillan and Co.",
            tier="TIER_1",
            confidence=0.88,
            book_count=12,
        )

        with patch(
            "app.services.entity_validation._get_entity_by_normalized_name",
        ) as mock_exact:
            # Binder has exact match, publisher doesn't
            mock_exact.side_effect = [
                (10, "Riviere & Son"),  # binder exact match
                None,  # publisher no exact match
            ]

            with patch(
                "app.services.entity_validation.fuzzy_match_entity",
                return_value=[publisher_match],
            ):
                with patch("app.services.entity_validation.get_settings") as mock_settings:
                    mock_settings.return_value.entity_validation_mode = "enforce"
                    mock_settings.return_value.entity_match_threshold_publisher = 0.80

                    result = validate_and_associate_entities(
                        db,
                        binder_name="Riviere & Son",
                        publisher_name="Macmilan",
                    )

        # Binder should have ID (exact match)
        assert result.binder_id == 10
        # Publisher should have error (fuzzy match)
        assert result.publisher_id is None
        assert result.has_errors is True
        assert len(result.errors) == 1
        assert result.errors[0].entity_type == "publisher"
