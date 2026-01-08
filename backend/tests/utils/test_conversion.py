"""Tests for conversion utilities."""

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
        """Large Decimal values convert without precision loss."""
        result = safe_float(Decimal("999999.99"))
        assert result == 999999.99
