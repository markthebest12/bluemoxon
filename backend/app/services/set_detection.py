"""Set completion detection service.

Detects when a new book would complete an incomplete multi-volume set
in the collection. Awards +25 STRATEGIC_COMPLETES_SET bonus points.

See docs/session-2025-12-21-set-completion-detection/design.md for design.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Roman numeral values (supports I-XII only)
ROMAN_VALUES = {"I": 1, "V": 5, "X": 10}
MAX_ROMAN_VALUE = 12  # Only support volumes 1-12


def roman_to_int(s: str) -> int | None:
    """Convert Roman numeral string to integer.

    Args:
        s: Roman numeral string (case-insensitive)

    Returns:
        Integer value, or None if invalid or > 12
    """
    s = s.upper().strip()
    if not s or not all(c in "IVXLCDM" for c in s):
        return None

    result = 0
    prev_value = 0

    for char in reversed(s):
        value = ROMAN_VALUES.get(char, 0)
        if value == 0:
            return None  # Invalid Roman numeral character for our subset
        if value < prev_value:
            result -= value
        else:
            result += value
        prev_value = value

    if result <= 0 or result > MAX_ROMAN_VALUE:
        return None

    return result


# Patterns to extract volume numbers from titles
VOLUME_PATTERNS = [
    # Vol. 3, Vol 12, Vol. IV (both digits and roman)
    re.compile(r"\bVol\.?\s*(\w+)\b", re.IGNORECASE),
    # Volume 2, Volume VIII
    re.compile(r"\bVolume\s+(\w+)\b", re.IGNORECASE),
    # Part 1, Part 2
    re.compile(r"\bPart\s+(\d+)\b", re.IGNORECASE),
]


def extract_volume_number(title: str) -> int | None:
    """Extract volume number from a book title.

    Supports patterns:
    - Vol. 3, Vol 12
    - Volume 2, Volume VIII (Roman numerals)
    - Part 1, Part 2

    Args:
        title: Book title string

    Returns:
        Volume number as integer, or None if not found
    """
    for pattern in VOLUME_PATTERNS:
        match = pattern.search(title)
        if match:
            value = match.group(1)
            # Try as integer first
            if value.isdigit():
                return int(value)
            # Try as Roman numeral
            roman_value = roman_to_int(value)
            if roman_value is not None:
                return roman_value
    return None
