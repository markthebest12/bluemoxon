"""Tests for analysis metadata extraction.

Tests extraction of structured metadata from AI analysis responses
and application of metadata to book models.
"""

from app.services.analysis_parser import (
    apply_metadata_to_book,
    extract_analysis_metadata,
    strip_metadata_block,
)


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


class TestStripMetadataBlock:
    """Tests for stripping metadata block from analysis text."""

    def test_strip_metadata_block(self):
        """Test stripping metadata block from analysis text."""
        analysis = """# Executive Summary

This book is a first edition with notable provenance.

---
<!-- METADATA_START -->
{
  "is_first_edition": true,
  "has_provenance": true,
  "provenance_tier": "Tier 1"
}
<!-- METADATA_END -->
"""
        result, was_stripped = strip_metadata_block(analysis)

        assert was_stripped is True
        assert "METADATA_START" not in result
        assert "METADATA_END" not in result
        assert "is_first_edition" not in result
        assert "Executive Summary" in result

    def test_strip_no_metadata_block(self):
        """Test returns unchanged text and False when no metadata block."""
        analysis = """# Executive Summary

This is analysis without any metadata block.

## Detailed Analysis

More content here...
"""
        result, was_stripped = strip_metadata_block(analysis)

        assert was_stripped is False
        # Function strips trailing whitespace, so compare stripped versions
        assert result == analysis.rstrip()

    def test_strip_metadata_preserves_content_before(self):
        """Test that content before metadata block is preserved."""
        analysis = """# Section 13

Some recommendations here.

---
<!-- METADATA_START -->
{"is_first_edition": true}
<!-- METADATA_END -->
"""
        result, was_stripped = strip_metadata_block(analysis)

        assert was_stripped is True
        assert "Section 13" in result
        assert "recommendations" in result
        assert "METADATA_START" not in result

    def test_strip_metadata_removes_leading_separator(self):
        """Test that the --- separator before metadata is also removed."""
        analysis = """# Content

Last section content.

---
<!-- METADATA_START -->
{"is_first_edition": false}
<!-- METADATA_END -->
"""
        result, was_stripped = strip_metadata_block(analysis)

        assert was_stripped is True
        # Should not have trailing --- before end of content
        assert result.strip().endswith("content.")

    def test_strip_metadata_handles_whitespace(self):
        """Test handling of extra whitespace around metadata block."""
        analysis = """# Content


---

<!-- METADATA_START -->
{
  "is_first_edition": true
}
<!-- METADATA_END -->

"""
        result, was_stripped = strip_metadata_block(analysis)

        assert was_stripped is True
        assert "METADATA_START" not in result
        assert "Content" in result

    def test_strip_nested_json(self):
        """Test stripping works correctly with nested JSON objects (P0 fix)."""
        analysis = """# Summary

Content here.

---
<!-- METADATA_START -->
{
  "is_first_edition": true,
  "provenance_details": {
    "tier": 1,
    "source": "auction",
    "verified": true
  },
  "has_provenance": true
}
<!-- METADATA_END -->
"""
        result, was_stripped = strip_metadata_block(analysis)

        assert was_stripped is True
        assert "METADATA_START" not in result
        assert "METADATA_END" not in result
        # Ensure no JSON fragments remain
        assert "provenance_details" not in result
        assert '"tier": 1' not in result
        assert '"source"' not in result
        assert "Summary" in result
        assert "Content here." in result

    def test_strip_without_separator(self):
        """Test stripping works when --- separator is NOT present."""
        analysis = """# Summary

Content here.

<!-- METADATA_START -->
{"is_first_edition": true}
<!-- METADATA_END -->
"""
        result, was_stripped = strip_metadata_block(analysis)

        assert was_stripped is True
        assert "METADATA_START" not in result
        assert "is_first_edition" not in result
        assert "Summary" in result

    def test_strip_metadata_in_middle_of_document(self):
        """Test stripping works when metadata is in the middle of document."""
        analysis = """# Summary

First section.

---
<!-- METADATA_START -->
{"is_first_edition": false}
<!-- METADATA_END -->

# Additional Section

More content after metadata.
"""
        result, was_stripped = strip_metadata_block(analysis)

        assert was_stripped is True
        assert "METADATA_START" not in result
        assert "First section" in result
        assert "Additional Section" in result
        assert "More content after metadata" in result

    def test_strip_returns_false_for_start_marker_only(self):
        """Test returns False when only start marker present (malformed)."""
        analysis = """# Summary

<!-- METADATA_START -->
{"is_first_edition": true}

Missing end marker...
"""
        result, was_stripped = strip_metadata_block(analysis)

        assert was_stripped is False
        assert "METADATA_START" in result  # Preserved because incomplete


class TestExtractAndStripIntegration:
    """Integration tests for extract-then-strip workflow."""

    def test_extract_then_strip_workflow(self):
        """Test both functions work together on same input."""
        analysis = """# Summary

Book analysis content.

---
<!-- METADATA_START -->
{
  "is_first_edition": true,
  "has_provenance": true,
  "provenance_tier": "Tier 1"
}
<!-- METADATA_END -->
"""
        # Extract metadata FIRST
        metadata = extract_analysis_metadata(analysis)
        assert metadata is not None
        assert metadata["is_first_edition"] is True
        assert metadata["has_provenance"] is True
        assert metadata["provenance_tier"] == "Tier 1"

        # THEN strip (extraction should have worked before stripping removed it)
        clean, was_stripped = strip_metadata_block(analysis)
        assert was_stripped is True
        assert "METADATA_START" not in clean
        assert "Book analysis content" in clean

    def test_extract_nested_json(self):
        """Test extraction works correctly with nested JSON (P0 fix)."""
        analysis = """# Summary

---
<!-- METADATA_START -->
{
  "is_first_edition": true,
  "provenance_details": {
    "tier": 1,
    "source": "auction"
  }
}
<!-- METADATA_END -->
"""
        metadata = extract_analysis_metadata(analysis)

        assert metadata is not None
        assert metadata["is_first_edition"] is True
        assert metadata["provenance_details"]["tier"] == 1
        assert metadata["provenance_details"]["source"] == "auction"

    def test_extract_deeply_nested_json(self):
        """Test extraction handles deeply nested JSON structures."""
        analysis = """# Summary

<!-- METADATA_START -->
{
  "is_first_edition": false,
  "analysis": {
    "provenance": {
      "tier": 2,
      "sources": ["auction", "dealer", "private"],
      "details": {
        "verified": true,
        "notes": "From notable collection"
      }
    }
  }
}
<!-- METADATA_END -->
"""
        metadata = extract_analysis_metadata(analysis)

        assert metadata is not None
        assert metadata["is_first_edition"] is False
        assert metadata["analysis"]["provenance"]["tier"] == 2
        assert "auction" in metadata["analysis"]["provenance"]["sources"]
        assert metadata["analysis"]["provenance"]["details"]["verified"] is True

    def test_both_functions_recognize_same_format(self):
        """Test extract and strip both handle the same format correctly."""
        # This catches cases where one function matches but the other doesn't
        test_cases = [
            # With separator
            """# Summary

---
<!-- METADATA_START -->
{"key": "value"}
<!-- METADATA_END -->
""",
            # Without separator
            """# Summary

<!-- METADATA_START -->
{"key": "value"}
<!-- METADATA_END -->
""",
            # Extra whitespace
            """# Summary


<!-- METADATA_START -->

{"key": "value"}

<!-- METADATA_END -->

""",
        ]

        for analysis in test_cases:
            # Both should succeed on the same input
            metadata = extract_analysis_metadata(analysis)
            clean, was_stripped = strip_metadata_block(analysis)

            assert metadata is not None, f"Extract failed on: {analysis[:50]}..."
            assert was_stripped is True, f"Strip failed on: {analysis[:50]}..."
            assert "METADATA_START" not in clean
