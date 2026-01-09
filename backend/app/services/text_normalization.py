"""Shared text normalization utilities.

Common text transformation functions used across entity normalization services
(author, binder, publisher). Extracting these reduces duplication and ensures
consistent behavior.
"""

import unicodedata


def remove_diacritics(text: str) -> str:
    """Remove diacritical marks from text (accent folding).

    Converts accented characters to their ASCII base equivalent:
    - é → e
    - ë → e
    - ñ → n
    - ç → c

    Uses Unicode NFD normalization followed by stripping combining characters.

    Args:
        text: Text potentially containing diacritics

    Returns:
        Text with diacritics removed (ASCII-folded)
    """
    # NFD decomposes characters into base + combining marks
    # e.g., é becomes e + combining acute accent
    normalized = unicodedata.normalize("NFD", text)

    # Remove combining diacritical marks (category Mn = Mark, Nonspacing)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn")


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text.

    Strips leading/trailing whitespace and collapses multiple spaces to single space.

    Args:
        text: Text to normalize

    Returns:
        Text with normalized whitespace
    """
    return " ".join(text.split())
