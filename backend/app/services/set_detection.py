"""Set completion detection service.

Detects when a new book would complete an incomplete multi-volume set
in the collection. Awards +25 STRATEGIC_COMPLETES_SET bonus points.

See docs/session-2025-12-21-set-completion-detection/design.md for design.
"""

from __future__ import annotations

import logging

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
