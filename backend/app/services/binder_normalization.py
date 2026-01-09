"""Binder normalization service for normalizing binder names for matching.

This module provides functions for normalizing binder names to enable
fuzzy matching between different formats and representations:
- Parenthetical descriptions: "Bayntun (of Bath)" -> "Bayntun"
- Square brackets: "Bedford [some note]" -> "Bedford"
- Location suffixes: "Birdsall of Northampton" -> "Birdsall"
- Comma locations: "Birdsall, Northampton" -> "Birdsall"
- Accents: "Rivière" -> "Riviere"
- Whitespace: "  Zaehnsdorf  " -> "Zaehnsdorf"

Note: This is separate from the existing normalize_binder_name() in reference.py
which handles tier assignment and exact alias matching.
"""

import re

from app.services.text_normalization import normalize_whitespace, remove_diacritics

# Pattern to match parenthetical descriptions (content in parentheses)
# Matches: (anything) including nested content
PARENTHETICAL_PATTERN = re.compile(r"\s*\([^)]*\)")

# Pattern to match square bracket descriptions
# Matches: [anything]
SQUARE_BRACKET_PATTERN = re.compile(r"\s*\[[^\]]*\]")

# Pattern to match "of [Location]" suffix at end of name
# Matches: "of Bath", "of Northampton", etc.
# Only matches at end to avoid stripping from names like "Roger de Coverly"
OF_LOCATION_PATTERN = re.compile(r"\s+of\s+[A-Z][a-zA-Z]+$")

# Pattern to match ", [Location]" suffix at end of name
# Matches: ", Northampton", ", Bath", etc.
COMMA_LOCATION_PATTERN = re.compile(r",\s+[A-Z][a-zA-Z]+$")


def _strip_parentheticals(text: str) -> str:
    """Remove parenthetical descriptions from text.

    Strips content in parentheses: "Bayntun (of Bath)" -> "Bayntun"

    Args:
        text: Text potentially containing parenthetical descriptions

    Returns:
        Text with parentheticals removed
    """
    return PARENTHETICAL_PATTERN.sub("", text)


def _strip_square_brackets(text: str) -> str:
    """Remove square bracket descriptions from text.

    Strips content in square brackets: "Bedford [some note]" -> "Bedford"

    Args:
        text: Text potentially containing square bracket descriptions

    Returns:
        Text with square brackets removed
    """
    return SQUARE_BRACKET_PATTERN.sub("", text)


def _strip_location_suffix(text: str) -> str:
    """Remove location suffix from binder name.

    Handles both "of [Location]" and ", [Location]" patterns:
    - "Birdsall of Northampton" -> "Birdsall"
    - "Birdsall, Northampton" -> "Birdsall"

    Only matches at end of name and requires capitalized location
    to avoid false positives (e.g., "Roger de Coverly" unchanged).

    Args:
        text: Text potentially containing location suffix

    Returns:
        Text with location suffix removed
    """
    result = OF_LOCATION_PATTERN.sub("", text)
    result = COMMA_LOCATION_PATTERN.sub("", result)
    return result


def normalize_binder_name_for_matching(name: str | None) -> str:
    """Apply normalization rules to a binder name for fuzzy matching purposes.

    Normalizes to: base name without location suffixes/parentheticals/brackets, ASCII-folded

    Transformations applied:
    1. Strip parenthetical descriptions: "Bayntun (of Bath)" -> "Bayntun"
    2. Strip square bracket descriptions: "Bedford [note]" -> "Bedford"
    3. Strip location suffixes: "Birdsall of Northampton" -> "Birdsall"
    4. Strip comma locations: "Birdsall, Northampton" -> "Birdsall"
    5. ASCII-fold accents: "Rivière" -> "Riviere"
    6. Normalize whitespace: collapse multiple spaces, trim ends

    Case is preserved - matching should be case-insensitive elsewhere.

    Note: This is for matching purposes, separate from the existing
    normalize_binder_name() in reference.py which handles tier assignment.

    Args:
        name: Raw binder name in any format

    Returns:
        Normalized binder name, or empty string if input is None/empty
    """
    if not name:
        return ""

    # Step 1: Basic whitespace normalization first
    result = normalize_whitespace(name)

    if not result:
        return ""

    # Step 2: Strip parenthetical descriptions
    result = _strip_parentheticals(result)

    # Step 3: Strip square bracket descriptions
    result = _strip_square_brackets(result)

    # Step 4: Strip location suffixes ("of X" and ", X")
    result = _strip_location_suffix(result)

    # Step 5: Remove diacritics (accent folding)
    result = remove_diacritics(result)

    # Step 6: Final whitespace cleanup (after stripping may leave gaps)
    result = normalize_whitespace(result)

    return result
