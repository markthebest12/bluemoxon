"""Publisher validation service for normalizing and matching publisher names."""

import re

# Location suffixes to remove (case-insensitive)
LOCATION_SUFFIXES = [
    r",?\s+New York\s*$",
    r",?\s+London\s*$",
    r",?\s+Philadelphia\s*$",
    r",?\s+Boston\s*$",
    r",?\s+Chicago\s*$",
    r",?\s+Edinburgh\s*$",
    r",?\s+Leipzig\s*$",
    r",?\s+Wien\s*$",
    r",?\s+Fleet-Street\s*$",
    r",?\s+St\.?\s*Paul\s*$",
    r",?\s+Keene\s+NH\s*$",
    r",?\s+San Francisco\s*$",
]

# Known abbreviation expansions
ABBREVIATION_EXPANSIONS = {
    "D. Bogue": "David Bogue",
    "Wm.": "William",
    "Chas.": "Charles",
    "Thos.": "Thomas",
    "Jas.": "James",
    "Jno.": "John",
}

# Dual publisher patterns - which to keep
# Format: (pattern, replacement) - replacement can reference groups
DUAL_PUBLISHER_RULES = [
    # Keep Oxford University Press over Henry Frowde
    (r"Henry Frowde\s*/\s*Oxford University Press", "Oxford University Press"),
    # Keep Humphrey Milford variant -> Oxford University Press
    (r"Oxford University Press\s*/\s*Humphrey Milford", "Oxford University Press"),
    # Default: keep first publisher before slash
    (r"^([^/]+?)\s*/\s*.+$", r"\1"),
]


def auto_correct_publisher_name(name: str) -> str:
    """Apply auto-correction rules to normalize a publisher name.

    Rules applied (in order):
    1. Strip whitespace
    2. Remove parenthetical content (edition info, series names)
    3. Handle dual publishers (keep primary)
    4. Remove location suffixes
    5. Expand known abbreviations
    6. Normalize punctuation (& Co -> & Co.)

    Args:
        name: Raw publisher name

    Returns:
        Normalized publisher name
    """
    if not name:
        return name

    # Strip whitespace
    result = name.strip()

    # Remove parenthetical content
    result = re.sub(r"\s*\([^)]+\)\s*", " ", result).strip()

    # Handle dual publishers
    for pattern, replacement in DUAL_PUBLISHER_RULES:
        result = re.sub(pattern, replacement, result).strip()

    # Remove location suffixes
    for suffix_pattern in LOCATION_SUFFIXES:
        result = re.sub(suffix_pattern, "", result, flags=re.IGNORECASE).strip()

    # Expand known abbreviations
    for abbrev, expansion in ABBREVIATION_EXPANSIONS.items():
        if result == abbrev or result.startswith(abbrev + " "):
            result = result.replace(abbrev, expansion, 1)

    # Normalize "& Co" to "& Co."
    result = re.sub(r"&\s*Co(?!\.)(\s|$)", r"& Co.\1", result)

    # Final whitespace cleanup
    result = " ".join(result.split())

    return result
