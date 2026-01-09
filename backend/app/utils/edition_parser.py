"""Edition text parsing utility.

Parses edition text strings to infer whether a book is a first edition.
Handles formats commonly found in antiquarian book records.
"""

import re


def is_first_edition_text(edition_text: str | None) -> bool | None:
    """Determine if edition text indicates a first edition.

    Handles common edition text formats:
    - "First Edition", "first edition", "FIRST EDITION" -> True
    - "1st Edition", "1st ed.", "1st" -> True
    - "First", "First ed." -> True
    - "First American Edition", "First UK Edition" -> True
    - "First Printing", "First Impression" -> True
    - "True First", "True First Edition" -> True
    - "First Edition, Second State" -> True (still first edition)
    - "First Edition, Second Printing" -> True (still first edition)
    - "Second Edition", "2nd ed." -> False
    - "Third Edition", "3rd" -> False
    - "New Edition", "Revised Edition" -> False
    - "Reprint", "Later Printing" -> False
    - None, "", "   " -> None (unknown)
    - Random text without edition info -> None (unknown)

    Args:
        edition_text: Edition string to parse

    Returns:
        True: Text indicates first edition
        False: Text indicates NOT first edition (2nd, 3rd, revised, etc.)
        None: Cannot determine (no edition info or empty input)
    """
    # Handle None and empty/whitespace-only strings
    if not edition_text or not edition_text.strip():
        return None

    # Normalize: lowercase and collapse whitespace
    text = " ".join(edition_text.lower().split())

    # Check for first edition indicators FIRST
    # Important: "First Edition, Second State" or "First Edition, Second Printing"
    # are STILL first editions (the "second" refers to state/printing, not edition)
    first_patterns = [
        # "First Edition", "First ed.", "First ed"
        r"\bfirst\s+(?:edition|ed\.?|printing|impression)\b",
        # "1st Edition", "1st ed.", "1st ed"
        r"\b1st\s+(?:edition|ed\.?|printing|impression)\b",
        # "First American Edition", "First UK Edition", etc.
        r"\bfirst\s+\w+\s+edition\b",
        # Just "First" or "1st" at word boundary (common shorthand)
        r"^first$",
        r"^1st$",
        # "True First" or "True First Edition"
        r"\btrue\s+first\b",
        # First Edition Thus, First Separate Edition, First Collected Edition
        r"\bfirst\s+(?:edition\s+)?(?:thus|separate|collected|trade)\b",
    ]

    for pattern in first_patterns:
        if re.search(pattern, text):
            return True

    # Check for non-first edition indicators
    # These patterns indicate the EDITION (not state/printing) is not first
    non_first_patterns = [
        # Second/2nd edition (not state/printing - those go with first edition)
        r"\b(?:second|2nd)\s+(?:edition|ed\.?)\b",
        r"\b(?:third|3rd)\s+(?:edition|ed\.?)\b",
        r"\b(?:fourth|4th)\s+(?:edition|ed\.?)\b",
        r"\b(?:fifth|5th)\s+(?:edition|ed\.?)\b",
        r"\b(?:sixth|6th)\s+(?:edition|ed\.?)\b",
        r"\b(?:seventh|7th)\s+(?:edition|ed\.?)\b",
        r"\b(?:eighth|8th)\s+(?:edition|ed\.?)\b",
        r"\b(?:ninth|9th)\s+(?:edition|ed\.?)\b",
        r"\b(?:tenth|10th)\s+(?:edition|ed\.?)\b",
        # Standalone ordinals that don't follow "first edition"
        r"^(?:second|2nd)$",
        r"^(?:third|3rd)$",
        r"^(?:fourth|4th)$",
        r"^(?:fifth|5th)$",
        # New/Revised/Enlarged editions
        r"\bnew\s+edition\b",
        r"\brevised\b",
        r"\benlarged\b",
        # Reprints
        r"\breprint\b",
        r"\blater\s+(?:printing|impression)\b",
    ]

    for pattern in non_first_patterns:
        if re.search(pattern, text):
            return False

    # No edition info found - return None (unknown)
    return None
