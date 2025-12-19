"""Tests for analysis metadata extraction.

Tests extraction of structured metadata from AI analysis responses
and application of metadata to book models.
"""

from app.services.analysis_parser import apply_metadata_to_book, extract_analysis_metadata


class MockBook:
    """Mock book model for testing metadata application."""

    def __init__(self):
        self.is_first_edition = None
        self.has_provenance = False
        self.provenance_tier = None


class TestExtractAnalysisMetadata:
    """Tests for extracting metadata from analysis responses."""

    def test_extract_valid_metadata(self):
        """Test extracting valid JSON metadata block."""
        analysis = """# Executive Summary

This book is a first edition with notable provenance.

<!-- METADATA_START -->
{
  "is_first_edition": true,
  "has_provenance": true,
  "provenance_tier": "Tier 1"
}
<!-- METADATA_END -->

## Detailed Analysis

More content here...
"""
        metadata = extract_analysis_metadata(analysis)

        assert metadata is not None
        assert metadata["is_first_edition"] is True
        assert metadata["has_provenance"] is True
        assert metadata["provenance_tier"] == "Tier 1"

    def test_extract_no_markers(self):
        """Test returns None when no metadata markers present."""
        analysis = """# Executive Summary

This is analysis without any metadata block.

## Detailed Analysis

More content here...
"""
        metadata = extract_analysis_metadata(analysis)
        assert metadata is None

    def test_extract_invalid_json(self):
        """Test returns None when metadata JSON is malformed."""
        analysis = """# Executive Summary

<!-- METADATA_START -->
{
  "is_first_edition": true,
  "has_provenance": INVALID_JSON
}
<!-- METADATA_END -->

## Content
"""
        metadata = extract_analysis_metadata(analysis)
        assert metadata is None

    def test_extract_null_values(self):
        """Test handles null values in metadata gracefully."""
        analysis = """# Executive Summary

<!-- METADATA_START -->
{
  "is_first_edition": null,
  "has_provenance": false,
  "provenance_tier": null
}
<!-- METADATA_END -->

## Content
"""
        metadata = extract_analysis_metadata(analysis)

        assert metadata is not None
        assert metadata["is_first_edition"] is None
        assert metadata["has_provenance"] is False
        assert metadata["provenance_tier"] is None

    def test_extract_multiline_json(self):
        """Test handles multiline JSON formatting."""
        analysis = """# Executive Summary

<!-- METADATA_START -->
{
  "is_first_edition": false,
  "has_provenance": true,
  "provenance_tier": "Tier 2"
}
<!-- METADATA_END -->

## Content
"""
        metadata = extract_analysis_metadata(analysis)

        assert metadata is not None
        assert metadata["is_first_edition"] is False
        assert metadata["has_provenance"] is True
        assert metadata["provenance_tier"] == "Tier 2"

    def test_extract_whitespace_tolerance(self):
        """Test handles extra whitespace between markers and JSON."""
        analysis = """# Executive Summary

<!-- METADATA_START -->

  {"is_first_edition": true}

<!-- METADATA_END -->

## Content
"""
        metadata = extract_analysis_metadata(analysis)

        assert metadata is not None
        assert metadata["is_first_edition"] is True


class TestApplyMetadataToBook:
    """Tests for applying extracted metadata to book models."""

    def test_apply_first_edition_true(self):
        """Test setting is_first_edition to true."""
        book = MockBook()
        metadata = {"is_first_edition": True}

        updated = apply_metadata_to_book(book, metadata)

        assert book.is_first_edition is True
        assert "is_first_edition" in updated

    def test_apply_first_edition_false(self):
        """Test setting is_first_edition to false."""
        book = MockBook()
        metadata = {"is_first_edition": False}

        updated = apply_metadata_to_book(book, metadata)

        assert book.is_first_edition is False
        assert "is_first_edition" in updated

    def test_apply_first_edition_null(self):
        """Test setting is_first_edition to null."""
        book = MockBook()
        book.is_first_edition = True  # Start with a value
        metadata = {"is_first_edition": None}

        updated = apply_metadata_to_book(book, metadata)

        assert book.is_first_edition is None
        assert "is_first_edition" in updated

    def test_apply_provenance_with_tier(self):
        """Test setting has_provenance=true with tier."""
        book = MockBook()
        metadata = {"has_provenance": True, "provenance_tier": "Tier 1"}

        updated = apply_metadata_to_book(book, metadata)

        assert book.has_provenance is True
        assert book.provenance_tier == "Tier 1"
        assert "has_provenance" in updated
        assert "provenance_tier" in updated

    def test_apply_provenance_tier_requires_has_provenance(self):
        """Test that provenance_tier is only set if has_provenance is true."""
        book = MockBook()
        metadata = {"has_provenance": False, "provenance_tier": "Tier 1"}

        updated = apply_metadata_to_book(book, metadata)

        assert book.has_provenance is False
        assert book.provenance_tier is None  # Tier should not be set
        assert "has_provenance" in updated
        assert "provenance_tier" not in updated  # Should not be marked as updated

    def test_clear_tier_when_has_provenance_becomes_false(self):
        """Test that tier is cleared when has_provenance changes to false."""
        book = MockBook()
        # Start with provenance and tier
        book.has_provenance = True
        book.provenance_tier = "Tier 1"

        # Update to has_provenance=false
        metadata = {"has_provenance": False}

        updated = apply_metadata_to_book(book, metadata)

        assert book.has_provenance is False
        assert book.provenance_tier is None  # Tier should be cleared
        assert "has_provenance" in updated

    def test_apply_tier_when_book_already_has_provenance(self):
        """Test setting tier when book already has has_provenance=true."""
        book = MockBook()
        book.has_provenance = True  # Already set

        metadata = {"provenance_tier": "Tier 2"}

        updated = apply_metadata_to_book(book, metadata)

        assert book.provenance_tier == "Tier 2"
        assert "provenance_tier" in updated

    def test_apply_all_fields(self):
        """Test applying all metadata fields together."""
        book = MockBook()
        metadata = {
            "is_first_edition": True,
            "has_provenance": True,
            "provenance_tier": "Tier 1",
        }

        updated = apply_metadata_to_book(book, metadata)

        assert book.is_first_edition is True
        assert book.has_provenance is True
        assert book.provenance_tier == "Tier 1"
        assert len(updated) == 3
        assert "is_first_edition" in updated
        assert "has_provenance" in updated
        assert "provenance_tier" in updated

    def test_apply_empty_metadata(self):
        """Test applying empty metadata dict."""
        book = MockBook()
        metadata = {}

        updated = apply_metadata_to_book(book, metadata)

        assert book.is_first_edition is None
        assert book.has_provenance is False
        assert book.provenance_tier is None
        assert len(updated) == 0

    def test_apply_only_first_edition(self):
        """Test applying only is_first_edition field."""
        book = MockBook()
        metadata = {"is_first_edition": True}

        updated = apply_metadata_to_book(book, metadata)

        assert book.is_first_edition is True
        assert book.has_provenance is False  # Default
        assert book.provenance_tier is None  # Default
        assert updated == ["is_first_edition"]

    def test_apply_only_has_provenance(self):
        """Test applying only has_provenance field."""
        book = MockBook()
        metadata = {"has_provenance": True}

        updated = apply_metadata_to_book(book, metadata)

        assert book.is_first_edition is None  # Default
        assert book.has_provenance is True
        assert book.provenance_tier is None  # Not set without tier in metadata
        assert updated == ["has_provenance"]

    def test_tier_values(self):
        """Test all valid tier values."""
        for tier in ["Tier 1", "Tier 2", "Tier 3"]:
            book = MockBook()
            book.has_provenance = True
            metadata = {"provenance_tier": tier}

            updated = apply_metadata_to_book(book, metadata)

            assert book.provenance_tier == tier
            assert "provenance_tier" in updated

    def test_clearing_tier_explicitly_with_null(self):
        """Test explicitly clearing tier with null value."""
        book = MockBook()
        book.has_provenance = True
        book.provenance_tier = "Tier 1"

        # Metadata can explicitly set tier to null
        metadata = {"provenance_tier": None}

        updated = apply_metadata_to_book(book, metadata)

        # Tier should be set to None, but only if has_provenance is true
        # Since metadata doesn't include has_provenance, book.has_provenance stays true
        assert book.has_provenance is True
        assert book.provenance_tier is None
        assert "provenance_tier" in updated
