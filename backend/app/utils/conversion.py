"""Conversion utilities for handling database types."""

import math
from decimal import Decimal
from typing import Any


def safe_float(value: Decimal | float | int | Any | None, default: float = 0.0) -> float:
    """Convert Decimal/float/int to float, handling None and special values.

    Args:
        value: The value to convert (Decimal, float, int, or None).
            Also accepts any numeric type that supports float() conversion.
        default: Value to return if input is None, NaN, or Infinity (default: 0.0)

    Returns:
        The value as a float, or default if None/NaN/Infinity
    """
    if value is None:
        return default

    result = float(value)

    # Guard against NaN and Infinity which can't be JSON serialized
    if math.isnan(result) or math.isinf(result):
        return default

    return result
