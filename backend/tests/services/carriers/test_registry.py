"""Tests for carrier registry."""

import pytest


class TestGetCarrier:
    """Test get_carrier function."""

    def test_get_ups_carrier(self):
        """get_carrier('UPS') returns UPSCarrier instance."""
        from app.services.carriers import get_carrier
        from app.services.carriers.ups import UPSCarrier

        carrier = get_carrier("UPS")

        assert isinstance(carrier, UPSCarrier)
        assert carrier.name == "UPS"

    def test_get_carrier_case_insensitive(self):
        """get_carrier is case-insensitive."""
        from app.services.carriers import get_carrier
        from app.services.carriers.ups import UPSCarrier

        assert isinstance(get_carrier("ups"), UPSCarrier)
        assert isinstance(get_carrier("Ups"), UPSCarrier)
        assert isinstance(get_carrier("UPS"), UPSCarrier)

    def test_get_unknown_carrier_raises(self):
        """get_carrier with unknown name raises KeyError."""
        from app.services.carriers import get_carrier

        with pytest.raises(KeyError):
            get_carrier("UnknownCarrier")


class TestDetectAndGetCarrier:
    """Test detect_and_get_carrier function."""

    def test_detect_ups_tracking_number(self):
        """UPS tracking number returns UPSCarrier."""
        from app.services.carriers import detect_and_get_carrier
        from app.services.carriers.ups import UPSCarrier

        carrier = detect_and_get_carrier("1Z12345E0205271688")

        assert isinstance(carrier, UPSCarrier)

    def test_detect_ups_with_formatting(self):
        """UPS tracking number with spaces/dashes is detected."""
        from app.services.carriers import detect_and_get_carrier
        from app.services.carriers.ups import UPSCarrier

        carrier = detect_and_get_carrier("1Z 1234-5E02 0527-1688")

        assert isinstance(carrier, UPSCarrier)

    def test_unknown_tracking_number_returns_none(self):
        """Unknown tracking number format returns None."""
        from app.services.carriers import detect_and_get_carrier

        carrier = detect_and_get_carrier("RANDOM12345")

        assert carrier is None

    def test_empty_tracking_number_returns_none(self):
        """Empty tracking number returns None."""
        from app.services.carriers import detect_and_get_carrier

        assert detect_and_get_carrier("") is None
        assert detect_and_get_carrier("   ") is None
