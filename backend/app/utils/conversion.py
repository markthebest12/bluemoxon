"""Conversion utilities for handling database types."""

from decimal import Decimal


def safe_float(value: Decimal | float | int | None, default: float = 0.0) -> float:
    """Convert Decimal/float/int to float, handling None.

    Args:
        value: The value to convert (Decimal, float, int, or None)
        default: Value to return if input is None (default: 0.0)

    Returns:
        The value as a float, or default if None
    """
    if value is None:
        return default
    return float(value)
