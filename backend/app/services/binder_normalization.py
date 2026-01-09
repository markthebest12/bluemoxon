"""Binder normalization service for normalizing binder names for matching.

This module provides functions for normalizing binder names to enable
fuzzy matching between different formats and representations:
- Parenthetical descriptions: "Bayntun (of Bath)" -> "Bayntun"
- Square brackets: "Bedford [some note]" -> "Bedford"
- Accents: "Rivière" -> "Riviere"
- Whitespace: "  Zaehnsdorf  " -> "Zaehnsdorf"

Note: This is separate from the existing normalize_binder_name() in reference.py
which handles tier assignment and exact alias matching.
"""

import re
import unicodedata

# Pattern to match parenthetical descriptions (content in parentheses)
# Matches: (anything) including nested content
PARENTHETICAL_PATTERN = re.compile(r"\s*\([^)]*\)")

# Pattern to match square bracket descriptions
# Matches: [anything]
SQUARE_BRACKET_PATTERN = re.compile(r"\s*\[[^\]]*\]")


def _remove_diacritics(text: str) -> str:
    """Remove diacritical marks from text (accent folding).

    Converts characters like e with acute to plain e.
    Uses Unicode NFD normalization followed by stripping combining characters.

    Args:
        text: Text potentially containing diacritics

    Returns:
        Text with diacritics removed (ASCII-folded)
    """
    # NFD decomposes characters into base + combining marks
    # e.g., e with grave becomes e + combining grave
    normalized = unicodedata.normalize("NFD", text)

    # Remove combining diacritical marks (category Mn = Mark, Nonspacing)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def _normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text.

    Strips leading/trailing whitespace and collapses multiple spaces.

    Args:
        text: Text to normalize

    Returns:
        Text with normalized whitespace
    """
    return " ".join(text.split())


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


def normalize_binder_name_for_matching(name: str | None) -> str:
    """Apply normalization rules to a binder name for fuzzy matching purposes.

    Normalizes to: base name without parentheticals/brackets, ASCII-folded

    Transformations applied:
    1. Strip parenthetical descriptions: "Bayntun (of Bath)" -> "Bayntun"
    2. Strip square bracket descriptions: "Bedford [note]" -> "Bedford"
    3. ASCII-fold accents: "Rivière" -> "Riviere"
    4. Normalize whitespace: collapse multiple spaces, trim ends

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
    result = _normalize_whitespace(name)

    if not result:
        return ""

    # Step 2: Strip parenthetical descriptions
    result = _strip_parentheticals(result)

    # Step 3: Strip square bracket descriptions
    result = _strip_square_brackets(result)

    # Step 4: Remove diacritics (accent folding)
    result = _remove_diacritics(result)

    # Step 5: Final whitespace cleanup (after stripping may leave gaps)
    result = _normalize_whitespace(result)

    return result
