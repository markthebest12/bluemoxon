"""Parser for extracting structured metadata from AI analysis responses.

METADATA EXTRACTION vs DISPLAY STRIPPING:
- This module EXTRACTS metadata as JSON for storage in database fields
- markdown_parser.py STRIPS metadata for display purposes

This module handles HTML comment marker format:
<!-- METADATA_START -->
{"condition_grade": "VG+", "valuation_mid": 300}
<!-- METADATA_END -->

This format allows structured JSON extraction while remaining invisible
in rendered markdown.
"""

import json
import logging

logger = logging.getLogger(__name__)


def strip_metadata_block(analysis_text: str) -> tuple[str, bool]:
    """Strip the metadata block from analysis text before storage.

    Uses string find instead of regex to avoid issues with nested JSON.
    Removes the entire metadata section including:
    - The --- separator before the metadata (if present)
    - The <!-- METADATA_START --> marker
    - The content between markers (regardless of structure)
    - The <!-- METADATA_END --> marker
    - Any trailing whitespace

    Args:
        analysis_text: Full analysis markdown text

    Returns:
        Tuple of (cleaned text, whether stripping occurred)
    """
    start_marker = "<!-- METADATA_START -->"
    end_marker = "<!-- METADATA_END -->"

    start_idx = analysis_text.find(start_marker)
    if start_idx == -1:
        return analysis_text.rstrip(), False

    end_idx = analysis_text.find(end_marker, start_idx)
    if end_idx == -1:
        return analysis_text.rstrip(), False

    # Find leading --- separator if present (look back from start marker)
    prefix = analysis_text[:start_idx].rstrip()
    if prefix.endswith("---"):
        # Find start of the --- line (may have leading newlines)
        separator_idx = prefix.rfind("---")
        # Also strip any newlines before the ---
        while separator_idx > 0 and analysis_text[separator_idx - 1] in "\n\r":
            separator_idx -= 1
        start_idx = separator_idx

    # Build result: content before + content after (if any)
    before = analysis_text[:start_idx]
    after = analysis_text[end_idx + len(end_marker) :]

    return (before + after).rstrip(), True


def extract_analysis_metadata(analysis_text: str) -> dict | None:
    """Extract structured metadata block from analysis response.

    Uses string find to locate markers, avoiding regex issues with nested JSON.
    Looks for JSON between <!-- METADATA_START --> and <!-- METADATA_END --> markers.

    Args:
        analysis_text: Full analysis markdown text

    Returns:
        Parsed metadata dict or None if not found/invalid
    """
    start_marker = "<!-- METADATA_START -->"
    end_marker = "<!-- METADATA_END -->"

    start_idx = analysis_text.find(start_marker)
    if start_idx == -1:
        logger.debug("No metadata block found in analysis")
        return None

    end_idx = analysis_text.find(end_marker, start_idx)
    if end_idx == -1:
        logger.debug("No metadata end marker found in analysis")
        return None

    # Extract content between markers
    content_start = start_idx + len(start_marker)
    json_content = analysis_text[content_start:end_idx].strip()

    try:
        metadata: dict = json.loads(json_content)
        logger.info(f"Extracted analysis metadata: {list(metadata.keys())}")
        return metadata
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse analysis metadata JSON: {e}")
        return None


def apply_metadata_to_book(book, metadata: dict) -> list[str]:
    """Apply extracted metadata to book model.

    Args:
        book: Book model instance
        metadata: Parsed metadata dict

    Returns:
        List of field names that were updated
    """
    updated = []

    # First edition
    if "is_first_edition" in metadata:
        book.is_first_edition = metadata["is_first_edition"]
        updated.append("is_first_edition")

    # Provenance
    if "has_provenance" in metadata:
        book.has_provenance = metadata["has_provenance"]
        updated.append("has_provenance")
        # Clear tier if provenance is now False (data integrity)
        if not book.has_provenance:
            book.provenance_tier = None

    # Only set tier if has_provenance is True
    if "provenance_tier" in metadata and book.has_provenance:
        book.provenance_tier = metadata["provenance_tier"]
        updated.append("provenance_tier")

    return updated
