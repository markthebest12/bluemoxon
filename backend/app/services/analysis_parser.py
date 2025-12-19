"""Parser for extracting structured metadata from AI analysis responses."""

import json
import logging
import re

logger = logging.getLogger(__name__)


def extract_analysis_metadata(analysis_text: str) -> dict | None:
    """Extract structured metadata block from analysis response.

    Looks for JSON between <!-- METADATA_START --> and <!-- METADATA_END --> markers.

    Args:
        analysis_text: Full analysis markdown text

    Returns:
        Parsed metadata dict or None if not found/invalid
    """
    pattern = r"<!-- METADATA_START -->\s*(\{.*?\})\s*<!-- METADATA_END -->"
    match = re.search(pattern, analysis_text, re.DOTALL)

    if not match:
        logger.debug("No metadata block found in analysis")
        return None

    try:
        metadata: dict = json.loads(match.group(1))
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
