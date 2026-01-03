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
