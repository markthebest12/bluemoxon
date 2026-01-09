"""Tests for entity validation error schemas."""

import pytest
from pydantic import ValidationError


class TestEntitySuggestion:
    """Tests for EntitySuggestion schema."""

    def test_creates_with_all_fields(self):
        """Should create EntitySuggestion with all required fields."""
        from app.schemas.entity_validation import EntitySuggestion

        suggestion = EntitySuggestion(
            id=1,
            name="Longmans, Green & Co.",
            tier="A",
            match=0.92,
            book_count=15,
        )

        assert suggestion.id == 1
        assert suggestion.name == "Longmans, Green & Co."
        assert suggestion.tier == "A"
        assert suggestion.match == 0.92
        assert suggestion.book_count == 15

    def test_tier_can_be_none(self):
        """Tier should be optional (None allowed)."""
        from app.schemas.entity_validation import EntitySuggestion

        suggestion = EntitySuggestion(
            id=2,
            name="Unknown Publisher",
            tier=None,
            match=0.75,
            book_count=3,
        )

        assert suggestion.tier is None

    def test_match_accepts_zero(self):
        """Match score should accept 0.0."""
        from app.schemas.entity_validation import EntitySuggestion

        suggestion = EntitySuggestion(
            id=3,
            name="No Match",
            tier="C",
            match=0.0,
            book_count=0,
        )

        assert suggestion.match == 0.0

    def test_match_accepts_one(self):
        """Match score should accept 1.0."""
        from app.schemas.entity_validation import EntitySuggestion

        suggestion = EntitySuggestion(
            id=4,
            name="Exact Match",
            tier="A",
            match=1.0,
            book_count=100,
        )

        assert suggestion.match == 1.0

    def test_requires_id(self):
        """Should require id field."""
        from app.schemas.entity_validation import EntitySuggestion

        with pytest.raises(ValidationError) as exc_info:
            EntitySuggestion(
                name="Test",
                tier="A",
                match=0.5,
                book_count=1,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("id",) for e in errors)

    def test_requires_name(self):
        """Should require name field."""
        from app.schemas.entity_validation import EntitySuggestion

        with pytest.raises(ValidationError) as exc_info:
            EntitySuggestion(
                id=1,
                tier="A",
                match=0.5,
                book_count=1,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_requires_match(self):
        """Should require match field."""
        from app.schemas.entity_validation import EntitySuggestion

        with pytest.raises(ValidationError) as exc_info:
            EntitySuggestion(
                id=1,
                name="Test",
                tier="A",
                book_count=1,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("match",) for e in errors)

    def test_requires_book_count(self):
        """Should require book_count field."""
        from app.schemas.entity_validation import EntitySuggestion

        with pytest.raises(ValidationError) as exc_info:
            EntitySuggestion(
                id=1,
                name="Test",
                tier="A",
                match=0.5,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("book_count",) for e in errors)


class TestEntityValidationError:
    """Tests for EntityValidationError schema."""

    def test_creates_similar_entity_exists_error(self):
        """Should create 'similar_entity_exists' error with suggestions."""
        from app.schemas.entity_validation import (
            EntitySuggestion,
            EntityValidationError,
        )

        suggestion = EntitySuggestion(
            id=1,
            name="Longmans, Green & Co.",
            tier="A",
            match=0.92,
            book_count=15,
        )

        error = EntityValidationError(
            error="similar_entity_exists",
            entity_type="publisher",
            input="Longman Green",
            suggestions=[suggestion],
            resolution="Use existing publisher ID 1 or choose 'force_create' to create new",
        )

        assert error.error == "similar_entity_exists"
        assert error.entity_type == "publisher"
        assert error.input == "Longman Green"
        assert len(error.suggestions) == 1
        assert error.suggestions[0].name == "Longmans, Green & Co."
        assert error.resolution.startswith("Use existing")

    def test_creates_unknown_entity_error(self):
        """Should create 'unknown_entity' error."""
        from app.schemas.entity_validation import EntityValidationError

        error = EntityValidationError(
            error="unknown_entity",
            entity_type="binder",
            input="Sangorski & Sutcliffe",
            suggestions=None,
            resolution="Entity not in database. Use 'allow_create' to add new entry.",
        )

        assert error.error == "unknown_entity"
        assert error.entity_type == "binder"
        assert error.suggestions is None

    def test_creates_entity_not_found_error(self):
        """Should create 'entity_not_found' error."""
        from app.schemas.entity_validation import EntityValidationError

        error = EntityValidationError(
            error="entity_not_found",
            entity_type="author",
            input="Nonexistent Author ID 999",
            suggestions=None,
            resolution="No author with ID 999 exists.",
        )

        assert error.error == "entity_not_found"
        assert error.entity_type == "author"

    def test_rejects_invalid_error_type(self):
        """Should reject invalid error types."""
        from app.schemas.entity_validation import EntityValidationError

        with pytest.raises(ValidationError) as exc_info:
            EntityValidationError(
                error="invalid_error_type",
                entity_type="publisher",
                input="test",
                suggestions=None,
                resolution="test",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("error",) for e in errors)

    def test_rejects_invalid_entity_type(self):
        """Should reject invalid entity types."""
        from app.schemas.entity_validation import EntityValidationError

        with pytest.raises(ValidationError) as exc_info:
            EntityValidationError(
                error="unknown_entity",
                entity_type="invalid_type",
                input="test",
                suggestions=None,
                resolution="test",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("entity_type",) for e in errors)

    def test_accepts_publisher_entity_type(self):
        """Should accept 'publisher' as entity type."""
        from app.schemas.entity_validation import EntityValidationError

        error = EntityValidationError(
            error="unknown_entity",
            entity_type="publisher",
            input="test",
            suggestions=None,
            resolution="test",
        )

        assert error.entity_type == "publisher"

    def test_accepts_binder_entity_type(self):
        """Should accept 'binder' as entity type."""
        from app.schemas.entity_validation import EntityValidationError

        error = EntityValidationError(
            error="unknown_entity",
            entity_type="binder",
            input="test",
            suggestions=None,
            resolution="test",
        )

        assert error.entity_type == "binder"

    def test_accepts_author_entity_type(self):
        """Should accept 'author' as entity type."""
        from app.schemas.entity_validation import EntityValidationError

        error = EntityValidationError(
            error="unknown_entity",
            entity_type="author",
            input="test",
            suggestions=None,
            resolution="test",
        )

        assert error.entity_type == "author"

    def test_suggestions_can_be_empty_list(self):
        """Should accept empty list for suggestions."""
        from app.schemas.entity_validation import EntityValidationError

        error = EntityValidationError(
            error="unknown_entity",
            entity_type="publisher",
            input="New Publisher",
            suggestions=[],
            resolution="No similar entities found.",
        )

        assert error.suggestions == []

    def test_suggestions_can_have_multiple_items(self):
        """Should accept multiple suggestions."""
        from app.schemas.entity_validation import (
            EntitySuggestion,
            EntityValidationError,
        )

        suggestions = [
            EntitySuggestion(id=1, name="Option A", tier="A", match=0.95, book_count=10),
            EntitySuggestion(id=2, name="Option B", tier="B", match=0.85, book_count=5),
            EntitySuggestion(id=3, name="Option C", tier=None, match=0.75, book_count=2),
        ]

        error = EntityValidationError(
            error="similar_entity_exists",
            entity_type="publisher",
            input="Test",
            suggestions=suggestions,
            resolution="Multiple similar entities found.",
        )

        assert len(error.suggestions) == 3
        assert error.suggestions[0].match > error.suggestions[1].match

    def test_requires_error_field(self):
        """Should require error field."""
        from app.schemas.entity_validation import EntityValidationError

        with pytest.raises(ValidationError) as exc_info:
            EntityValidationError(
                entity_type="publisher",
                input="test",
                suggestions=None,
                resolution="test",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("error",) for e in errors)

    def test_requires_entity_type_field(self):
        """Should require entity_type field."""
        from app.schemas.entity_validation import EntityValidationError

        with pytest.raises(ValidationError) as exc_info:
            EntityValidationError(
                error="unknown_entity",
                input="test",
                suggestions=None,
                resolution="test",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("entity_type",) for e in errors)

    def test_requires_input_field(self):
        """Should require input field."""
        from app.schemas.entity_validation import EntityValidationError

        with pytest.raises(ValidationError) as exc_info:
            EntityValidationError(
                error="unknown_entity",
                entity_type="publisher",
                suggestions=None,
                resolution="test",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("input",) for e in errors)

    def test_requires_resolution_field(self):
        """Should require resolution field."""
        from app.schemas.entity_validation import EntityValidationError

        with pytest.raises(ValidationError) as exc_info:
            EntityValidationError(
                error="unknown_entity",
                entity_type="publisher",
                input="test",
                suggestions=None,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("resolution",) for e in errors)


class TestSchemaExports:
    """Tests for schema module exports."""

    def test_schemas_exported_from_entity_validation_module(self):
        """Schemas should be importable from entity_validation module."""
        from app.schemas.entity_validation import (
            EntitySuggestion,
            EntityValidationError,
        )

        assert EntitySuggestion is not None
        assert EntityValidationError is not None

    def test_schemas_exported_from_schemas_init(self):
        """Schemas should be importable from schemas package."""
        from app.schemas import EntitySuggestion, EntityValidationError

        assert EntitySuggestion is not None
        assert EntityValidationError is not None
