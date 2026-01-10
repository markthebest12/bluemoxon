"""Tests for entity validation edge cases in books API.

Tests for TOCTOU (time-of-check-to-time-of-use) race condition:
Issue #1010: Entity can vanish between validation phase and mutation phase.

The validation phase calls validate_entity_for_book() which returns an entity ID.
The mutation phase then directly sets book.binder_id = binder_id without re-checking
if the entity still exists. If another process deletes the entity between these two
phases, the code would create an orphan FK reference (or fail with FK constraint).

The fix: Before setting FK, re-fetch the entity with db.get() to verify it exists.
"""

from unittest.mock import patch

import pytest

from app.models import Binder, Book, Publisher


@pytest.fixture
def sample_book(db):
    """Create a sample book for testing."""
    book = Book(title="Test Book for Entity Validation")
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


class TestTOCTOURaceCondition:
    """Test TOCTOU race condition handling when entities vanish between validation and mutation.

    These tests verify that when validate_entity_for_book returns an entity ID,
    but the entity is deleted before the mutation phase, the code gracefully
    skips the association rather than crashing or creating orphan FK references.
    """

    def test_binder_vanishes_between_validation_and_mutation(self, client, db, sample_book):
        """If binder is deleted after validation passes, association is skipped (not crash).

        Scenario:
        1. Validation phase: validate_entity_for_book returns binder_id=999
        2. Entity is deleted (simulated by db.get returning None)
        3. Mutation phase: Should skip FK assignment, not crash
        """
        markdown = """## Executive Summary
Test summary for TOCTOU test

## Binder Identification
- **Name:** Vanishing Binder
- **Confidence:** HIGH
"""
        # Create a temporary binder, get its ID, then delete it
        temp_binder = Binder(name="Vanishing Binder", tier="A")
        db.add(temp_binder)
        db.commit()
        temp_binder_id = temp_binder.id

        # Delete the binder to simulate TOCTOU race
        db.delete(temp_binder)
        db.commit()

        # Mock validation to return the now-deleted binder's ID for binder validation
        def mock_validate(db, entity_type, name, threshold=None):
            if entity_type == "binder":
                return temp_binder_id
            return None

        with patch(
            "app.api.v1.books.validate_entity_for_book",
            side_effect=mock_validate,
        ):
            response = client.put(
                f"/api/v1/books/{sample_book.id}/analysis",
                content=markdown,
                headers={"Content-Type": "text/plain"},
            )

        # Should succeed (200), not crash with FK constraint violation
        assert response.status_code == 200

        # Binder should NOT be associated (it vanished)
        db.refresh(sample_book)
        assert sample_book.binder_id is None

    def test_publisher_vanishes_between_validation_and_mutation(self, client, db, sample_book):
        """If publisher is deleted after validation passes, association is skipped.

        Same TOCTOU scenario as binder test but for publisher entity.
        """
        markdown = """## Executive Summary
Test summary for TOCTOU test

**Publisher:** Vanishing Publisher
"""
        # Create a temporary publisher, get its ID, then delete it
        temp_publisher = Publisher(name="Vanishing Publisher")
        db.add(temp_publisher)
        db.commit()
        temp_publisher_id = temp_publisher.id

        # Delete the publisher to simulate TOCTOU race
        db.delete(temp_publisher)
        db.commit()

        # Mock validation to return the now-deleted publisher's ID for publisher validation
        def mock_validate(db, entity_type, name, threshold=None):
            if entity_type == "publisher":
                return temp_publisher_id
            return None

        with patch(
            "app.api.v1.books.validate_entity_for_book",
            side_effect=mock_validate,
        ):
            response = client.put(
                f"/api/v1/books/{sample_book.id}/analysis",
                content=markdown,
                headers={"Content-Type": "text/plain"},
            )

        # Should succeed (200), not crash with FK constraint violation
        assert response.status_code == 200

        # Publisher should NOT be associated (it vanished)
        db.refresh(sample_book)
        assert sample_book.publisher_id is None

    def test_binder_exists_during_mutation_is_associated(self, client, db, sample_book):
        """When binder still exists during mutation phase, it is associated correctly."""
        # Create a real binder that persists
        binder = Binder(name="Stable Binder", tier="A")
        db.add(binder)
        db.commit()
        db.refresh(binder)

        markdown = """## Executive Summary
Test summary

## Binder Identification
- **Name:** Stable Binder
- **Confidence:** HIGH
"""

        # Mock validation to return the real binder's ID only for binder validation
        def mock_validate(db, entity_type, name, threshold=None):
            if entity_type == "binder":
                return binder.id
            return None

        with patch(
            "app.api.v1.books.validate_entity_for_book",
            side_effect=mock_validate,
        ):
            response = client.put(
                f"/api/v1/books/{sample_book.id}/analysis",
                content=markdown,
                headers={"Content-Type": "text/plain"},
            )

        assert response.status_code == 200

        # Binder should be associated since it still exists
        db.refresh(sample_book)
        assert sample_book.binder_id == binder.id

    def test_publisher_exists_during_mutation_is_associated(self, client, db, sample_book):
        """When publisher still exists during mutation phase, it is associated correctly."""
        # Create a real publisher that persists
        publisher = Publisher(name="Stable Publisher")
        db.add(publisher)
        db.commit()
        db.refresh(publisher)

        markdown = """## Executive Summary
Test summary

**Publisher:** Stable Publisher
"""

        # Mock validation to return the real publisher's ID only for publisher validation
        def mock_validate(db, entity_type, name, threshold=None):
            if entity_type == "publisher":
                return publisher.id
            return None

        with patch(
            "app.api.v1.books.validate_entity_for_book",
            side_effect=mock_validate,
        ):
            response = client.put(
                f"/api/v1/books/{sample_book.id}/analysis",
                content=markdown,
                headers={"Content-Type": "text/plain"},
            )

        assert response.status_code == 200

        # Publisher should be associated since it still exists
        db.refresh(sample_book)
        assert sample_book.publisher_id == publisher.id


class TestForceParameterAnalysis:
    """Test force parameter bypasses entity validation in analysis."""

    def test_force_bypasses_similar_entity_409(self, client, db, sample_book):
        """With force=true, similar entity conflict is ignored."""
        from app.schemas.entity_validation import EntitySuggestion, EntityValidationError

        markdown = """## Executive Summary
Test

## Binder Identification
- **Name:** Riviere and Son
"""
        error = EntityValidationError(
            error="similar_entity_exists",
            entity_type="binder",
            input="Riviere and Son",
            suggestions=[
                EntitySuggestion(
                    id=1, name="Riviere & Son", tier="TIER_1", match=0.95, book_count=10
                )
            ],
            resolution="Use existing",
        )

        with patch("app.api.v1.books.validate_entity_for_book", return_value=error):
            # Without force - should get 409
            response = client.put(
                f"/api/v1/books/{sample_book.id}/analysis",
                content=markdown,
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 409

            # With force=true - should succeed
            response = client.put(
                f"/api/v1/books/{sample_book.id}/analysis?force=true",
                content=markdown,
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 200

    def test_force_bypasses_unknown_entity_400(self, client, db, sample_book):
        """With force=true, unknown entity error is ignored."""
        from app.schemas.entity_validation import EntityValidationError

        markdown = """## Executive Summary
Test

## Binder Identification
- **Name:** Brand New Binder
"""
        error = EntityValidationError(
            error="unknown_entity",
            entity_type="binder",
            input="Brand New Binder",
            suggestions=None,
            resolution="Create first",
        )

        with patch("app.api.v1.books.validate_entity_for_book", return_value=error):
            # Without force - should get 400
            response = client.put(
                f"/api/v1/books/{sample_book.id}/analysis",
                content=markdown,
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 400

            # With force=true - should succeed (skip association)
            response = client.put(
                f"/api/v1/books/{sample_book.id}/analysis?force=true",
                content=markdown,
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 200

    def test_force_bypasses_publisher_validation_error(self, client, db, sample_book):
        """With force=true, publisher validation errors are also bypassed."""
        from app.schemas.entity_validation import EntitySuggestion, EntityValidationError

        markdown = """## Executive Summary
Test

**Publisher:** Kegan Paul
"""
        error = EntityValidationError(
            error="similar_entity_exists",
            entity_type="publisher",
            input="Kegan Paul",
            suggestions=[
                EntitySuggestion(
                    id=5, name="Kegan Paul & Co.", tier=None, match=0.90, book_count=3
                )
            ],
            resolution="Use existing",
        )

        with patch("app.api.v1.books.validate_entity_for_book", return_value=error):
            # Without force - should get 409
            response = client.put(
                f"/api/v1/books/{sample_book.id}/analysis",
                content=markdown,
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 409

            # With force=true - should succeed
            response = client.put(
                f"/api/v1/books/{sample_book.id}/analysis?force=true",
                content=markdown,
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 200

    def test_force_false_does_not_bypass_validation(self, client, db, sample_book):
        """With force=false (default), validation errors are raised."""
        from app.schemas.entity_validation import EntityValidationError

        markdown = """## Executive Summary
Test

## Binder Identification
- **Name:** Mysterious Binder
"""
        error = EntityValidationError(
            error="unknown_entity",
            entity_type="binder",
            input="Mysterious Binder",
            suggestions=None,
            resolution="Create first",
        )

        with patch("app.api.v1.books.validate_entity_for_book", return_value=error):
            # Explicit force=false - should still get 400
            response = client.put(
                f"/api/v1/books/{sample_book.id}/analysis?force=false",
                content=markdown,
                headers={"Content-Type": "text/plain"},
            )
            assert response.status_code == 400