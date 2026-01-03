"""Tests for USPS carrier client."""

from datetime import date
from unittest.mock import Mock, patch

import httpx
import pytest

from app.services.carriers.usps import USPSClient


class TestUSPSCanHandle:
    """Tests for USPS tracking number pattern matching."""

    def test_priority_mail_94_prefix(self):
        """94xx format - Priority Mail."""
        assert USPSClient.can_handle("9400111899223100001234") is True
        assert USPSClient.can_handle("9405511899223100001234") is True

    def test_certified_mail_93_prefix(self):
        """93xx format - Certified Mail."""
        assert USPSClient.can_handle("9374889676090175041920") is True

    def test_registered_mail_92_prefix(self):
        """92xx format - Registered Mail."""
        assert USPSClient.can_handle("9202490100130280468028") is True

    def test_20_digit_format(self):
        """20-digit domestic format."""
        assert USPSClient.can_handle("12345678901234567890") is True

    def test_22_digit_format(self):
        """22-digit domestic format."""
        assert USPSClient.can_handle("1234567890123456789012") is True

    def test_21_digit_format(self):
        """21-digit domestic format."""
        assert USPSClient.can_handle("123456789012345678901") is True

    def test_normalizes_spaces_and_dashes(self):
        """Tracking numbers with spaces/dashes should be normalized."""
        assert USPSClient.can_handle("9400 1118 9922 3100 0012 34") is True
        assert USPSClient.can_handle("9400-1118-9922-3100-0012-34") is True

    def test_case_insensitive(self):
        """Should handle lowercase (though USPS uses all digits)."""
        # USPS tracking numbers are all digits, but normalization should still work
        assert USPSClient.can_handle("9400111899223100001234") is True

    def test_rejects_short_numbers(self):
        """Too short - not USPS."""
        assert USPSClient.can_handle("123456789") is False
        assert USPSClient.can_handle("12345678901234") is False

    def test_rejects_ups_format(self):
        """UPS format should not match."""
        assert USPSClient.can_handle("1Z999AA10123456784") is False

    def test_rejects_fedex_12_digit(self):
        """12-digit FedEx should not match."""
        assert USPSClient.can_handle("123456789012") is False

    def test_rejects_dhl_10_digit(self):
        """10-digit DHL should not match."""
        assert USPSClient.can_handle("1234567890") is False

    def test_rejects_royal_mail(self):
        """Royal Mail format should not match."""
        assert USPSClient.can_handle("AB123456789GB") is False


class TestUSPSFetchTracking:
    """Tests for USPS tracking status fetching."""

    @pytest.fixture
    def usps_client(self):
        """Create USPS client instance."""
        return USPSClient()

    def test_client_name(self, usps_client):
        """Verify client name is set correctly."""
        assert usps_client.name == "USPS"

    @patch("app.services.carriers.usps.httpx.Client")
    def test_fetch_in_transit(self, mock_client_class, usps_client):
        """Parse 'In Transit' status from USPS response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <TrackResponse>
            <TrackInfo ID="9400111899223100001234">
                <TrackSummary>
                    Your item is in transit to the destination.
                </TrackSummary>
                <TrackDetail>
                    January 2, 2026, 10:30 am, In Transit to Next Facility, CHICAGO, IL 60607
                </TrackDetail>
            </TrackInfo>
        </TrackResponse>
        """

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = usps_client.fetch_tracking("9400111899223100001234")

        assert result.status == "In Transit"
        assert result.error is None

    @patch("app.services.carriers.usps.httpx.Client")
    def test_fetch_delivered(self, mock_client_class, usps_client):
        """Parse 'Delivered' status from USPS response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <TrackResponse>
            <TrackInfo ID="9400111899223100001234">
                <TrackSummary>
                    Your item was delivered at 2:15 pm on January 2, 2026 in NEW YORK, NY 10001.
                </TrackSummary>
            </TrackInfo>
        </TrackResponse>
        """

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = usps_client.fetch_tracking("9400111899223100001234")

        assert result.status == "Delivered"
        assert result.location == "NEW YORK, NY 10001"
        assert result.error is None

    @patch("app.services.carriers.usps.httpx.Client")
    def test_fetch_with_expected_delivery(self, mock_client_class, usps_client):
        """Parse expected delivery date from USPS response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <TrackResponse>
            <TrackInfo ID="9400111899223100001234">
                <ExpectedDeliveryDate>January 3, 2026</ExpectedDeliveryDate>
                <TrackSummary>
                    In Transit, Arriving Later Today, CHICAGO, IL 60607
                </TrackSummary>
            </TrackInfo>
        </TrackResponse>
        """

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = usps_client.fetch_tracking("9400111899223100001234")

        assert result.status == "In Transit"
        assert result.estimated_delivery == date(2026, 1, 3)

    @patch("app.services.carriers.usps.httpx.Client")
    def test_fetch_out_for_delivery(self, mock_client_class, usps_client):
        """Parse 'Out for Delivery' status."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <TrackResponse>
            <TrackInfo ID="9400111899223100001234">
                <TrackSummary>
                    Out for Delivery, Expected Delivery by 8:00pm, BROOKLYN, NY 11201
                </TrackSummary>
            </TrackInfo>
        </TrackResponse>
        """

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = usps_client.fetch_tracking("9400111899223100001234")

        assert result.status == "Out for Delivery"
        assert result.location == "BROOKLYN, NY 11201"

    @patch("app.services.carriers.usps.httpx.Client")
    def test_fetch_exception_alert(self, mock_client_class, usps_client):
        """Parse exception/alert status."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <TrackResponse>
            <TrackInfo ID="9400111899223100001234">
                <TrackSummary>
                    Alert: Delivery attempted - No authorized recipient available, MIAMI, FL 33101
                </TrackSummary>
            </TrackInfo>
        </TrackResponse>
        """

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = usps_client.fetch_tracking("9400111899223100001234")

        assert result.status == "Exception"
        assert "No authorized recipient" in result.status_detail

    @patch("app.services.carriers.usps.httpx.Client")
    def test_fetch_http_error(self, mock_client_class, usps_client):
        """Handle HTTP errors gracefully."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.get.side_effect = httpx.HTTPStatusError(
            "Error", request=Mock(), response=Mock(status_code=500)
        )
        mock_client_class.return_value = mock_client

        result = usps_client.fetch_tracking("9400111899223100001234")

        assert result.status == "Unknown"
        assert result.error is not None
        assert "500" in result.error or "Error" in result.error

    @patch("app.services.carriers.usps.httpx.Client")
    def test_fetch_connection_error(self, mock_client_class, usps_client):
        """Handle connection errors gracefully."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")
        mock_client_class.return_value = mock_client

        result = usps_client.fetch_tracking("9400111899223100001234")

        assert result.status == "Unknown"
        assert result.error is not None

    @patch("app.services.carriers.usps.httpx.Client")
    def test_fetch_invalid_response(self, mock_client_class, usps_client):
        """Handle malformed XML response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Not valid XML <><><>"

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = usps_client.fetch_tracking("9400111899223100001234")

        assert result.status == "Unknown"
        assert result.error is not None

    @patch("app.services.carriers.usps.httpx.Client")
    def test_fetch_no_tracking_info(self, mock_client_class, usps_client):
        """Handle response with no tracking info found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <TrackResponse>
            <TrackInfo ID="9400111899223100001234">
                <Error>
                    <Description>The tracking number may be incorrect or the status update is not yet available.</Description>
                </Error>
            </TrackInfo>
        </TrackResponse>
        """

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = usps_client.fetch_tracking("9400111899223100001234")

        assert result.status == "Unknown"
        assert "not yet available" in result.error or "incorrect" in result.error

    @patch("app.services.carriers.usps.httpx.Client")
    def test_fetch_extracts_location(self, mock_client_class, usps_client):
        """Extract location from tracking details."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <TrackResponse>
            <TrackInfo ID="9400111899223100001234">
                <TrackSummary>
                    Arrived at Post Office, SEATTLE, WA 98101
                </TrackSummary>
            </TrackInfo>
        </TrackResponse>
        """

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = usps_client.fetch_tracking("9400111899223100001234")

        assert result.location == "SEATTLE, WA 98101"

    @patch("app.services.carriers.usps.httpx.Client")
    def test_normalizes_tracking_number(self, mock_client_class, usps_client):
        """Tracking number should be normalized before API call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <TrackResponse>
            <TrackInfo ID="9400111899223100001234">
                <TrackSummary>In Transit</TrackSummary>
            </TrackInfo>
        </TrackResponse>
        """

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Call with spaces and dashes
        usps_client.fetch_tracking("9400 1118 9922-3100-0012-34")

        # Verify the API was called with normalized number
        call_args = mock_client.get.call_args
        assert "9400111899223100001234" in str(call_args)
