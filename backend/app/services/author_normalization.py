"""Author normalization service for normalizing and matching author names.

This module provides functions for normalizing author names to enable
matching between different formats and representations:
- Name order: "Dickens, Charles" <-> "Charles Dickens"
- Honorifics: "Sir Walter Scott" <-> "Walter Scott"
- Accents: "Bronte" <-> "Brontë"
"""

import re

from app.services.text_normalization import normalize_whitespace, remove_diacritics

# Honorific prefixes to remove (case-insensitive)
# Order matters: longer patterns first to avoid partial matches
HONORIFICS = [
    r"Reverend\s+",
    r"Professor\s+",
    r"Rev\.\s*",
    r"Prof\.\s*",
    r"Dame\s+",
    r"Lady\s+",
    r"Lord\s+",
    r"Mrs\.\s*",
    r"Miss\s+",
    r"Mr\.\s*",
    r"Ms\.\s*",
    r"Sir\s+",
    r"Dr\.\s*",
]

# Compile regex for honorifics (case-insensitive, at start of string)
HONORIFIC_PATTERN = re.compile(
    r"^(?:" + "|".join(HONORIFICS) + ")",
    re.IGNORECASE,
)

# Name suffixes that should stay with the last name (case-insensitive)
# These come AFTER the last name, not before
NAME_SUFFIXES = {
    "jr",
    "jr.",
    "sr",
    "sr.",
    "ii",
    "iii",
    "iv",
    "v",
    "esq",
    "esq.",
    "phd",
    "ph.d",
    "ph.d.",
    "md",
    "m.d",
    "m.d.",
}


def _remove_honorifics(name: str) -> str:
    """Remove honorific prefixes from a name.

    Handles Sir, Dame, Dr., Rev., Mr., Mrs., etc.

    Args:
        name: Name potentially containing honorific prefix

    Returns:
        Name with honorific removed
    """
    return HONORIFIC_PATTERN.sub("", name)


def _strip_suffix(name: str) -> tuple[str, str | None]:
    """Strip name suffix (Jr., Sr., III, etc.) from the end of a name.

    Args:
        name: Name potentially containing a suffix at the end

    Returns:
        Tuple of (name_without_suffix, suffix) where suffix may be None
    """
    parts = name.split()
    if not parts:
        return name, None

    # Check if last part is a suffix
    if parts[-1].lower() in NAME_SUFFIXES:
        suffix = parts[-1]
        name_without = " ".join(parts[:-1])
        return name_without, suffix

    return name, None


def _parse_comma_format(name: str) -> tuple[str, str]:
    """Parse "Last, First Middle" format into parts.

    Args:
        name: Name in "Last, First" or "Last, First Middle" format

    Returns:
        Tuple of (last_name, first_and_middle) where first_and_middle
        may contain middle name(s)
    """
    parts = name.split(",", 1)
    if len(parts) == 2:
        last = parts[0].strip()
        first_middle = parts[1].strip()
        return last, first_middle
    return "", name


def _convert_to_first_last(name: str) -> str:
    """Convert "Last, First" format to "First Last" format.

    If name contains a comma, treats text before comma as last name
    and text after comma as first name (with optional middle).

    Also handles honorifics that may appear after the comma, e.g.:
    "Scott, Sir Walter" -> "Walter Scott"

    Args:
        name: Name in any format

    Returns:
        Name in "First [Middle] Last" format
    """
    if "," not in name:
        return name

    last, first_middle = _parse_comma_format(name)

    if not first_middle:
        return last

    # Remove any honorifics from first_middle part
    # (handles "Scott, Sir Walter" case)
    first_middle = _remove_honorifics(first_middle).strip()

    # Normalize whitespace in the first_middle part
    first_middle = normalize_whitespace(first_middle)

    return f"{first_middle} {last}"


def normalize_author_name(name: str | None) -> str:
    """Apply normalization rules to an author name for matching purposes.

    Normalizes to: "First Middle Last" format with:
    - No honorifics (Sir, Dr., etc.)
    - No suffixes (Jr., Sr., III, etc.) - stripped for matching
    - ASCII-folded (diacritics removed)
    - Whitespace normalized

    Case is preserved - matching should be case-insensitive elsewhere.

    Args:
        name: Raw author name in any format

    Returns:
        Normalized author name, or empty string if input is None/empty
    """
    if not name:
        return ""

    # Step 1: Basic whitespace normalization first
    result = normalize_whitespace(name)

    if not result:
        return ""

    # Step 2: Remove honorifics (before comma conversion to handle both positions)
    result = _remove_honorifics(result)
    result = normalize_whitespace(result)

    # Step 3: Convert "Last, First" to "First Last"
    result = _convert_to_first_last(result)

    # Step 4: Strip suffixes (Jr., Sr., III, etc.) for matching
    result, _ = _strip_suffix(result)

    # Step 5: Remove diacritics (accent folding)
    result = remove_diacritics(result)

    # Step 6: Final whitespace cleanup
    result = normalize_whitespace(result)

    return result


def extract_author_name_parts(name: str | None) -> tuple[str | None, str | None, str | None]:
    """Extract (first, middle, last) from various author name formats.

    Handles:
    - "Last, First" -> ("First", None, "Last")
    - "Last, First Middle" -> ("First", "Middle", "Last")
    - "First Last" -> ("First", None, "Last")
    - "First Middle Last" -> ("First", "Middle", "Last")
    - "First Last Jr." -> ("First", None, "Last Jr.") - suffix stays with last
    - "SingleName" -> (None, None, "SingleName")

    Note: Does NOT normalize or remove honorifics - returns parts as-is.
    For matching purposes, call normalize_author_name() first.

    Args:
        name: Author name in any format

    Returns:
        Tuple of (first, middle, last) where any component may be None
    """
    if not name:
        return None, None, None

    # Normalize whitespace first
    cleaned = normalize_whitespace(name)

    if not cleaned:
        return None, None, None

    # Check for comma format: "Last, First [Middle]"
    if "," in cleaned:
        last, first_middle = _parse_comma_format(cleaned)

        if not first_middle:
            # Just "Last," with nothing after
            return None, None, last if last else None

        # Split first_middle into first and optional middle
        parts = first_middle.split(None)  # Split on whitespace

        if len(parts) == 1:
            return parts[0], None, last
        elif len(parts) == 2:
            return parts[0], parts[1], last
        else:
            # Multiple middle names: first, then rest as middle
            return parts[0], " ".join(parts[1:]), last

    # No comma: "First [Middle...] Last [Suffix]" format
    parts = cleaned.split(None)  # Split on whitespace

    if len(parts) == 1:
        # Single name (like "Voltaire") - treat as last name
        return None, None, parts[0]

    # Check if last part is a suffix (Jr., Sr., III, etc.)
    # If so, combine it with the preceding word as the last name
    if len(parts) >= 2 and parts[-1].lower() in NAME_SUFFIXES:
        suffix = parts[-1]
        name_parts = parts[:-1]  # Everything except suffix

        if len(name_parts) == 1:
            # "James Jr." -> (None, None, "James Jr.")
            return None, None, f"{name_parts[0]} {suffix}"
        elif len(name_parts) == 2:
            # "Henry James Jr." -> ("Henry", None, "James Jr.")
            return name_parts[0], None, f"{name_parts[1]} {suffix}"
        else:
            # "Henry William James Jr." -> ("Henry", "William", "James Jr.")
            return name_parts[0], " ".join(name_parts[1:-1]), f"{name_parts[-1]} {suffix}"

    # No suffix detected - standard parsing
    if len(parts) == 2:
        # "First Last"
        return parts[0], None, parts[1]
    else:
        # "First Middle... Last"
        # Last word is last name, first word is first name,
        # everything in between is middle
        return parts[0], " ".join(parts[1:-1]), parts[-1]
