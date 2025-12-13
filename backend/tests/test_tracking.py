"""Tests for shipment tracking service."""

import pytest

from app.services.tracking import (
    detect_carrier,
    generate_tracking_url,
    process_tracking,
)


class TestDetectCarrier:
    """Tests for carrier auto-detection from tracking numbers."""

    def test_ups_tracking_number(self):
        """UPS: 1Z followed by 16 alphanumeric characters."""
        assert detect_carrier("1Z999AA10123456784") == "UPS"
        assert detect_carrier("1Z12345E0205271688") == "UPS"

    def test_ups_with_spaces(self):
        """UPS with spaces/dashes should still be detected."""
        assert detect_carrier("1Z 999 AA1 0123 4567 84") == "UPS"
        assert detect_carrier("1Z-999-AA1-0123-4567-84") == "UPS"

    def test_usps_tracking_numbers(self):
        """USPS: 20-22 digits, or starts with 94/93/92."""
        # 20-22 digit format
        assert detect_carrier("12345678901234567890") == "USPS"
        assert detect_carrier("1234567890123456789012") == "USPS"
        # 94xx format (Priority Mail)
        assert detect_carrier("9400111899223100001234") == "USPS"
        # 93xx format (Certified Mail)
        assert detect_carrier("9374889676090175041920") == "USPS"
        # 92xx format (Registered Mail)
        assert detect_carrier("9202490100130280468028") == "USPS"

    def test_fedex_tracking_numbers(self):
        """FedEx: 12, 15, or 20 digits."""
        assert detect_carrier("123456789012") == "FedEx"
        assert detect_carrier("123456789012345") == "FedEx"
        # Note: 20 digits could be USPS or FedEx, USPS pattern matches first
        # This is expected behavior - pattern order matters

    def test_dhl_tracking_number(self):
        """DHL: 10 digits."""
        assert detect_carrier("1234567890") == "DHL"

    def test_royal_mail_tracking_number(self):
        """Royal Mail: 2 letters + 9 digits + 2 letters."""
        assert detect_carrier("AB123456789GB") == "Royal Mail"
        assert detect_carrier("CD987654321UK") == "Royal Mail"

    def test_lowercase_normalized(self):
        """Tracking numbers should be normalized to uppercase."""
        assert detect_carrier("1z999aa10123456784") == "UPS"
        assert detect_carrier("ab123456789gb") == "Royal Mail"

    def test_unknown_carrier(self):
        """Unknown formats should return None."""
        assert detect_carrier("INVALID") is None
        assert detect_carrier("12345") is None
        assert detect_carrier("ABC123") is None


class TestGenerateTrackingUrl:
    """Tests for tracking URL generation."""

    def test_ups_url(self):
        """Generate UPS tracking URL."""
        url = generate_tracking_url("1Z999AA10123456784", "UPS")
        assert url == "https://www.ups.com/track?tracknum=1Z999AA10123456784"

    def test_usps_url(self):
        """Generate USPS tracking URL."""
        url = generate_tracking_url("9400111899223100001234", "USPS")
        assert url == "https://tools.usps.com/go/TrackConfirmAction?tLabels=9400111899223100001234"

    def test_fedex_url(self):
        """Generate FedEx tracking URL."""
        url = generate_tracking_url("123456789012", "FedEx")
        assert url == "https://www.fedex.com/fedextrack/?trknbr=123456789012"

    def test_dhl_url(self):
        """Generate DHL tracking URL."""
        url = generate_tracking_url("1234567890", "DHL")
        assert url == "https://www.dhl.com/en/express/tracking.html?AWB=1234567890"

    def test_royal_mail_url(self):
        """Generate Royal Mail tracking URL."""
        url = generate_tracking_url("AB123456789GB", "Royal Mail")
        assert url == "https://www.royalmail.com/track-your-item#/tracking-results/AB123456789GB"

    def test_parcelforce_url(self):
        """Generate Parcelforce tracking URL."""
        url = generate_tracking_url("ABC123", "Parcelforce")
        assert url == "https://www.parcelforce.com/track-trace?trackNumber=ABC123"

    def test_unknown_carrier_returns_none(self):
        """Unknown carrier should return None."""
        url = generate_tracking_url("12345", "UnknownCarrier")
        assert url is None

    def test_normalizes_tracking_number(self):
        """Tracking number should be normalized (uppercase, no spaces/dashes)."""
        url = generate_tracking_url("1z-999-aa1 0123 4567 84", "UPS")
        assert url == "https://www.ups.com/track?tracknum=1Z999AA10123456784"


class TestProcessTracking:
    """Tests for the main process_tracking function."""

    def test_direct_url_passthrough(self):
        """If tracking_url provided, use it as-is."""
        number, carrier, url = process_tracking(
            tracking_number="12345",
            tracking_carrier="Custom",
            tracking_url="https://custom-tracker.com/12345",
        )
        assert number == "12345"
        assert carrier == "Custom"
        assert url == "https://custom-tracker.com/12345"

    def test_auto_detect_carrier(self):
        """Auto-detect carrier from tracking number."""
        number, carrier, url = process_tracking(
            tracking_number="1Z999AA10123456784",
            tracking_carrier=None,
            tracking_url=None,
        )
        assert number == "1Z999AA10123456784"
        assert carrier == "UPS"
        assert "ups.com" in url

    def test_explicit_carrier_override(self):
        """Explicit carrier should be used even if pattern matches another."""
        number, carrier, url = process_tracking(
            tracking_number="1234567890",  # Would match DHL
            tracking_carrier="Custom",  # But we specify Custom
            tracking_url=None,
        )
        assert number == "1234567890"
        assert carrier == "Custom"
        # URL will be None because "Custom" isn't in CARRIER_URLS
        assert url is None

    def test_no_tracking_number_returns_none(self):
        """If no tracking number, return all None."""
        number, carrier, url = process_tracking(
            tracking_number=None,
            tracking_carrier=None,
            tracking_url=None,
        )
        assert number is None
        assert carrier is None
        assert url is None

    def test_undetectable_carrier_raises_error(self):
        """If carrier can't be detected and not provided, raise error."""
        with pytest.raises(ValueError) as exc_info:
            process_tracking(
                tracking_number="INVALID123",
                tracking_carrier=None,
                tracking_url=None,
            )
        assert "Could not detect carrier" in str(exc_info.value)

    def test_normalizes_tracking_number(self):
        """Tracking number should be normalized."""
        number, carrier, url = process_tracking(
            tracking_number="1z 999 aa1-0123-4567-84",
            tracking_carrier=None,
            tracking_url=None,
        )
        assert number == "1Z999AA10123456784"

    def test_usps_full_flow(self):
        """Full flow for USPS tracking."""
        number, carrier, url = process_tracking(
            tracking_number="9400 1118 9922 3100 0012 34",
            tracking_carrier=None,
            tracking_url=None,
        )
        assert number == "9400111899223100001234"
        assert carrier == "USPS"
        assert "usps.com" in url
        assert "9400111899223100001234" in url
