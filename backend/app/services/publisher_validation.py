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


# Publisher tier mappings based on market recognition and historical significance
# Maps variant names to (canonical_name, tier)
TIER_1_PUBLISHERS = {
    # Major Victorian/Edwardian publishers
    "Macmillan and Co.": "Macmillan and Co.",
    "Macmillan": "Macmillan and Co.",
    "Chapman & Hall": "Chapman & Hall",
    "Chapman and Hall": "Chapman & Hall",
    "Smith, Elder & Co.": "Smith, Elder & Co.",
    "Smith Elder": "Smith, Elder & Co.",
    "John Murray": "John Murray",
    "Murray": "John Murray",
    "William Blackwood and Sons": "William Blackwood and Sons",
    "Blackwood": "William Blackwood and Sons",
    "Edward Moxon and Co.": "Edward Moxon and Co.",
    "Moxon": "Edward Moxon and Co.",
    "Oxford University Press": "Oxford University Press",
    "OUP": "Oxford University Press",
    "Longmans, Green & Co.": "Longmans, Green & Co.",
    "Longmans": "Longmans, Green & Co.",
    "Longman": "Longmans, Green & Co.",
    "Harper & Brothers": "Harper & Brothers",
    "Harper": "Harper & Brothers",
    "D. Appleton and Company": "D. Appleton and Company",
    "Appleton": "D. Appleton and Company",
    "Little, Brown, and Company": "Little, Brown, and Company",
    "Little Brown": "Little, Brown, and Company",
    "Richard Bentley": "Richard Bentley",
    "Bentley": "Richard Bentley",
}

TIER_2_PUBLISHERS = {
    "Chatto and Windus": "Chatto and Windus",
    "Chatto & Windus": "Chatto and Windus",
    "George Allen": "George Allen",
    "Cassell": "Cassell, Petter & Galpin",
    "Cassell, Petter & Galpin": "Cassell, Petter & Galpin",
    "Routledge": "Routledge",
    "Ward, Lock & Co.": "Ward, Lock & Co.",
    "Ward Lock": "Ward, Lock & Co.",
    "Hurst & Company": "Hurst & Company",
    "Grosset & Dunlap": "Grosset & Dunlap",
}


def normalize_publisher_name(name: str) -> tuple[str, str | None]:
    """Normalize publisher name and determine tier.

    Applies auto-correction rules first, then matches against known publishers.

    Args:
        name: Raw publisher name from analysis

    Returns:
        Tuple of (canonical_name, tier) where tier is TIER_1, TIER_2, or None
    """
    # Apply auto-correction first
    corrected = auto_correct_publisher_name(name)

    # Check Tier 1 first
    for variant, canonical in TIER_1_PUBLISHERS.items():
        if variant.lower() == corrected.lower():
            return canonical, "TIER_1"
        # Also check if variant is contained in the name
        if variant.lower() in corrected.lower():
            return canonical, "TIER_1"

    # Check Tier 2
    for variant, canonical in TIER_2_PUBLISHERS.items():
        if variant.lower() == corrected.lower():
            return canonical, "TIER_2"
        if variant.lower() in corrected.lower():
            return canonical, "TIER_2"

    # Unknown publisher - return corrected name with no tier
    return corrected, None
