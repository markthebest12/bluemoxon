"""Tests for conversion utilities."""

import math
from decimal import Decimal

from app.utils.conversion import safe_float


class TestSafeFloat:
    """Test safe_float helper function."""

    def test_none_returns_zero(self):
        """None input returns 0.0 by default."""
        assert safe_float(None) == 0.0

    def test_none_with_custom_default(self):
        """None input with custom default returns that default."""
        assert safe_float(None, default=99.0) == 99.0

    def test_decimal_converts_to_float(self):
        """Decimal values are converted to float."""
        result = safe_float(Decimal("123.45"))
        assert result == 123.45
        assert isinstance(result, float)

    def test_float_passes_through(self):
        """Float values pass through unchanged."""
        result = safe_float(3.14)
        assert result == 3.14
        assert isinstance(result, float)

    def test_int_converts_to_float(self):
        """Integer values are converted to float."""
        result = safe_float(42)
        assert result == 42.0
        assert isinstance(result, float)

    def test_zero_decimal(self):
        """Zero Decimal returns 0.0, not default."""
        assert safe_float(Decimal("0")) == 0.0

    def test_zero_float(self):
        """Zero float returns 0.0, not default."""
        assert safe_float(0.0) == 0.0

    def test_zero_int(self):
        """Zero int returns 0.0, not default."""
        assert safe_float(0) == 0.0

    def test_negative_decimal(self):
        """Negative Decimal values work correctly."""
        assert safe_float(Decimal("-50.25")) == -50.25

    def test_large_decimal(self):
        """Large Decimal values convert correctly."""
        result = safe_float(Decimal("999999.99"))
        assert result == 999999.99


class TestSafeFloatEdgeCases:
    """Test safe_float handling of special values."""

    def test_nan_returns_default(self):
        """NaN returns default to ensure JSON serialization."""
        assert safe_float(float("nan")) == 0.0

    def test_nan_with_custom_default(self):
        """NaN with custom default returns that default."""
        assert safe_float(float("nan"), default=99.0) == 99.0

    def test_infinity_returns_default(self):
        """Positive infinity returns default."""
        assert safe_float(float("inf")) == 0.0

    def test_negative_infinity_returns_default(self):
        """Negative infinity returns default."""
        assert safe_float(float("-inf")) == 0.0

    def test_decimal_nan_returns_default(self):
        """Decimal NaN returns default."""
        assert safe_float(Decimal("NaN")) == 0.0

    def test_decimal_infinity_returns_default(self):
        """Decimal Infinity returns default."""
        assert safe_float(Decimal("Infinity")) == 0.0

    def test_decimal_negative_infinity_returns_default(self):
        """Decimal -Infinity returns default."""
        assert safe_float(Decimal("-Infinity")) == 0.0

    def test_result_is_json_serializable(self):
        """All outputs should be JSON serializable (not NaN/Inf)."""
        import json

        test_values = [
            None,
            Decimal("123.45"),
            float("nan"),
            float("inf"),
            Decimal("NaN"),
            Decimal("Infinity"),
        ]
        for val in test_values:
            result = safe_float(val)
            # Should not raise - NaN/Inf would raise ValueError
            json.dumps({"value": result})
            assert not math.isnan(result)
            assert not math.isinf(result)


class TestSafeFloatNonNumericTypes:
    """Test safe_float handling of non-numeric types (should return default, not crash)."""

    def test_string_non_numeric_returns_default(self):
        """Non-numeric string returns default instead of raising ValueError."""
        assert safe_float("not a number") == 0.0

    def test_string_non_numeric_with_custom_default(self):
        """Non-numeric string with custom default returns that default."""
        assert safe_float("hello", default=99.0) == 99.0

    def test_dict_returns_default(self):
        """Dict returns default instead of raising TypeError."""
        assert safe_float({"key": "value"}) == 0.0

    def test_list_returns_default(self):
        """List returns default instead of raising TypeError."""
        assert safe_float([1, 2, 3]) == 0.0

    def test_object_returns_default(self):
        """Arbitrary object returns default instead of raising TypeError."""
        assert safe_float(object()) == 0.0

    def test_numeric_string_converts(self):
        """Numeric string should convert successfully."""
        assert safe_float("123.45") == 123.45

    def test_empty_string_returns_default(self):
        """Empty string returns default instead of raising ValueError."""
        assert safe_float("") == 0.0
