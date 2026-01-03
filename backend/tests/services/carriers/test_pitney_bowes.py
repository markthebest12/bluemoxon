"""Tests for Pitney Bowes carrier client."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.services.carriers.pitney_bowes import PitneyBowesClient


class TestCanHandle:
    """Tests for PitneyBowesClient.can_handle()."""

    def test_can_handle_valid_upaa_tracking_number(self):
        """Should handle tracking numbers starting with UPAA."""
        assert PitneyBowesClient.can_handle("UPAA1234567890") is True

    def test_can_handle_lowercase_upaa(self):
        """Should handle lowercase tracking numbers."""
        assert PitneyBowesClient.can_handle("upaa1234567890") is True

    def test_can_handle_mixed_case_upaa(self):
        """Should handle mixed case tracking numbers."""
        assert PitneyBowesClient.can_handle("UpAa1234567890") is True

    def test_cannot_handle_non_upaa_tracking(self):
        """Should not handle non-UPAA tracking numbers."""
        assert PitneyBowesClient.can_handle("1Z12345E0291980793") is False  # UPS
        assert PitneyBowesClient.can_handle("9400111899223456789012") is False  # USPS
        assert PitneyBowesClient.can_handle("123456789012") is False  # FedEx

    def test_cannot_handle_partial_upaa(self):
        """Should not handle tracking numbers that only start with UP or UPA."""
        assert PitneyBowesClient.can_handle("UPA1234567890") is False
        assert PitneyBowesClient.can_handle("UP1234567890") is False

    def test_cannot_handle_upaa_in_middle(self):
        """Should not handle tracking numbers with UPAA in the middle."""
        assert PitneyBowesClient.can_handle("XXUPAA1234567890") is False

    def test_can_handle_with_spaces(self):
        """Should handle tracking numbers with spaces."""
        assert PitneyBowesClient.can_handle("UPAA 1234 5678 90") is True

    def test_can_handle_with_dashes(self):
        """Should handle tracking numbers with dashes."""
        assert PitneyBowesClient.can_handle("UPAA-1234-5678-90") is True


class TestFetchTracking:
    """Tests for PitneyBowesClient.fetch_tracking()."""

    @pytest.fixture
    def client(self):
        """Create a PitneyBowesClient instance."""
        return PitneyBowesClient()

    def test_fetch_tracking_in_transit(self, client):
        """Should parse in-transit status correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "trackingNumber": "UPAA1234567890",
            "status": "IN_TRANSIT",
            "statusDescription": "Package is in transit to destination",
            "currentLocation": "Memphis, TN",
            "estimatedDeliveryDate": "2026-01-05",
        }

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = client.fetch_tracking("UPAA1234567890")

            assert result.status == "In Transit"
            assert result.location == "Memphis, TN"
            assert result.estimated_delivery == date(2026, 1, 5)
            assert result.error is None

    def test_fetch_tracking_delivered(self, client):
        """Should parse delivered status correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "trackingNumber": "UPAA1234567890",
            "status": "DELIVERED",
            "statusDescription": "Package delivered",
            "currentLocation": "New York, NY",
            "deliveredAt": "2026-01-04T14:30:00Z",
        }

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = client.fetch_tracking("UPAA1234567890")

            assert result.status == "Delivered"
            assert result.location == "New York, NY"
            assert result.delivered_at == datetime(2026, 1, 4, 14, 30, 0)
            assert result.error is None

    def test_fetch_tracking_exception(self, client):
        """Should parse exception status correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "trackingNumber": "UPAA1234567890",
            "status": "EXCEPTION",
            "statusDescription": "Delivery attempted, recipient not available",
            "currentLocation": "Los Angeles, CA",
        }

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = client.fetch_tracking("UPAA1234567890")

            assert result.status == "Exception"
            assert result.status_detail == "Delivery attempted, recipient not available"
            assert result.location == "Los Angeles, CA"
            assert result.error is None

    def test_fetch_tracking_http_error(self, client):
        """Should handle HTTP errors gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Internal Server Error")

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            mock_client.return_value.__enter__.return_value.get.return_value.raise_for_status.side_effect = Exception(
                "Internal Server Error"
            )

            result = client.fetch_tracking("UPAA1234567890")

            assert result.status is None
            assert result.error is not None
            assert "Internal Server Error" in result.error

    def test_fetch_tracking_not_found(self, client):
        """Should handle tracking number not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("Not Found")

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            mock_client.return_value.__enter__.return_value.get.return_value.raise_for_status.side_effect = Exception(
                "Not Found"
            )

            result = client.fetch_tracking("UPAA0000000000")

            assert result.error is not None

    def test_fetch_tracking_normalizes_tracking_number(self, client):
        """Should normalize tracking number before API call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "trackingNumber": "UPAA1234567890",
            "status": "IN_TRANSIT",
        }

        with patch("httpx.Client") as mock_client:
            mock_http_client = mock_client.return_value.__enter__.return_value
            mock_http_client.get.return_value = mock_response

            client.fetch_tracking("upaa-1234-5678-90")

            # Verify the URL contains the normalized tracking number
            call_args = mock_http_client.get.call_args
            url = call_args[0][0]
            assert "UPAA1234567890" in url

    def test_fetch_tracking_uses_correct_endpoint(self, client):
        """Should use the trackpb.shipment.co endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "trackingNumber": "UPAA1234567890",
            "status": "IN_TRANSIT",
        }

        with patch("httpx.Client") as mock_client:
            mock_http_client = mock_client.return_value.__enter__.return_value
            mock_http_client.get.return_value = mock_response

            client.fetch_tracking("UPAA1234567890")

            call_args = mock_http_client.get.call_args
            url = call_args[0][0]
            assert "trackpb.shipment.co" in url

    def test_fetch_tracking_unknown_status(self, client):
        """Should handle unknown status values."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "trackingNumber": "UPAA1234567890",
            "status": "PROCESSING",
            "statusDescription": "Order is being processed",
        }

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = client.fetch_tracking("UPAA1234567890")

            # Unknown statuses should be passed through
            assert result.status == "Processing"

    def test_fetch_tracking_missing_fields(self, client):
        """Should handle responses with missing optional fields."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "trackingNumber": "UPAA1234567890",
            "status": "IN_TRANSIT",
            # No location, estimatedDeliveryDate, or statusDescription
        }

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = client.fetch_tracking("UPAA1234567890")

            assert result.status == "In Transit"
            assert result.location is None
            assert result.estimated_delivery is None
            assert result.status_detail is None
            assert result.error is None


class TestClientProperties:
    """Tests for PitneyBowesClient class properties."""

    def test_client_name(self):
        """Should have correct carrier name."""
        client = PitneyBowesClient()
        assert client.name == "Pitney Bowes"

    def test_client_is_carrier_client(self):
        """Should be an instance of CarrierClient."""
        from app.services.carriers.base import CarrierClient

        client = PitneyBowesClient()
        assert isinstance(client, CarrierClient)
