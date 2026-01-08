"""Conversion utilities for handling database types."""

import logging
import math
from decimal import Decimal

logger = logging.getLogger(__name__)


def safe_float(value: Decimal | float | int | str | None, default: float = 0.0) -> float:
    """Convert numeric types to float, handling None and special values.

    Args:
        value: The value to convert (Decimal, float, int, str, or None).
        default: Value to return if input is None, unconvertible, NaN, or Infinity.

    Returns:
        The value as a float, or default if conversion fails or result is NaN/Infinity.
    """
    if value is None:
        return default

    try:
        result = float(value)
    except (TypeError, ValueError):
        return default

    # Guard against NaN and Infinity which can't be JSON serialized
    if math.isnan(result) or math.isinf(result):
        logger.warning("safe_float received NaN/Inf value, returning default: %s", value)
        return default

    return result
