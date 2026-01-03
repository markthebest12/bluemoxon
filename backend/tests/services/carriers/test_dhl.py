"""Tests for DHL carrier tracking client."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.services.carriers.dhl import DHLClient


class TestDHLCanHandle:
    """Tests for DHL tracking number pattern matching."""

    def test_valid_10_digit_number(self):
        """DHL tracking numbers are 10 digits."""
        assert DHLClient.can_handle("1234567890") is True

    def test_valid_10_digit_with_spaces(self):
        """Spaces should be normalized."""
        assert DHLClient.can_handle("12345 67890") is True

    def test_valid_10_digit_with_dashes(self):
        """Dashes should be normalized."""
        assert DHLClient.can_handle("12345-67890") is True

    def test_invalid_9_digits(self):
        """9 digits should not match."""
        assert DHLClient.can_handle("123456789") is False

    def test_invalid_11_digits(self):
        """11 digits should not match."""
        assert DHLClient.can_handle("12345678901") is False

    def test_invalid_with_letters(self):
        """Letters should not match."""
        assert DHLClient.can_handle("123456789A") is False

    def test_invalid_ups_format(self):
        """UPS format should not match."""
        assert DHLClient.can_handle("1Z999AA10123456784") is False

    def test_empty_string(self):
        """Empty string should not match."""
        assert DHLClient.can_handle("") is False


class TestDHLFetchTracking:
    """Tests for DHL tracking API integration."""

    @pytest.fixture
    def client(self):
        """Create a DHL client instance."""
        return DHLClient()

    def test_successful_in_transit(self, client):
        """Parse successful in-transit response."""
        mock_response = {
            "shipments": [
                {
                    "status": {
                        "statusCode": "transit",
                        "status": "In Transit",
                        "description": "Shipment is in transit",
                    },
                    "estimatedDeliveryDate": "2026-01-05",
                    "events": [
                        {
                            "location": {"address": {"addressLocality": "Cincinnati, OH"}},
                        }
                    ],
                }
            ]
        }

        with patch("httpx.Client") as mock_client:
            mock_http = MagicMock()
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_http.get.return_value = mock_response_obj
            mock_client.return_value.__enter__.return_value = mock_http

            result = client.fetch_tracking("1234567890")

        assert result.status == "In Transit"
        assert result.status_detail == "Shipment is in transit"
        assert result.estimated_delivery == date(2026, 1, 5)
        assert result.location == "Cincinnati, OH"
        assert result.error is None

    def test_successful_delivered(self, client):
        """Parse successful delivered response."""
        mock_response = {
            "shipments": [
                {
                    "status": {
                        "statusCode": "delivered",
                        "status": "Delivered",
                        "description": "Package delivered to recipient",
                    },
                    "events": [
                        {
                            "timestamp": "2026-01-03T14:30:00Z",
                            "location": {"address": {"addressLocality": "New York, NY"}},
                        }
                    ],
                }
            ]
        }

        with patch("httpx.Client") as mock_client:
            mock_http = MagicMock()
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_http.get.return_value = mock_response_obj
            mock_client.return_value.__enter__.return_value = mock_http

            result = client.fetch_tracking("1234567890")

        assert result.status == "Delivered"
        assert result.status_detail == "Package delivered to recipient"
        assert result.delivered_at == datetime(2026, 1, 3, 14, 30, 0)
        assert result.location == "New York, NY"
        assert result.error is None

    def test_exception_status(self, client):
        """Parse exception/problem status."""
        mock_response = {
            "shipments": [
                {
                    "status": {
                        "statusCode": "exception",
                        "status": "Exception",
                        "description": "Delivery attempt failed - no access",
                    },
                    "events": [],
                }
            ]
        }

        with patch("httpx.Client") as mock_client:
            mock_http = MagicMock()
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_http.get.return_value = mock_response_obj
            mock_client.return_value.__enter__.return_value = mock_http

            result = client.fetch_tracking("1234567890")

        assert result.status == "Exception"
        assert result.status_detail == "Delivery attempt failed - no access"
        assert result.error is None

    def test_tracking_not_found(self, client):
        """Handle tracking number not found."""
        mock_response = {"shipments": []}

        with patch("httpx.Client") as mock_client:
            mock_http = MagicMock()
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_http.get.return_value = mock_response_obj
            mock_client.return_value.__enter__.return_value = mock_http

            result = client.fetch_tracking("1234567890")

        assert result.status == "Unknown"
        assert result.error == "Tracking number not found"

    def test_api_error(self, client):
        """Handle API HTTP errors gracefully."""
        import httpx

        with patch("httpx.Client") as mock_client:
            mock_http = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_http.get.side_effect = httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=mock_response
            )
            mock_client.return_value.__enter__.return_value = mock_http

            result = client.fetch_tracking("1234567890")

        assert result.status == "Unknown"
        assert "500" in result.error

    def test_network_timeout(self, client):
        """Handle network timeout gracefully."""
        import httpx

        with patch("httpx.Client") as mock_client:
            mock_http = MagicMock()
            mock_http.get.side_effect = httpx.TimeoutException("Connection timed out")
            mock_client.return_value.__enter__.return_value = mock_http

            result = client.fetch_tracking("1234567890")

        assert result.status == "Unknown"
        assert "timed out" in result.error.lower()

    def test_malformed_response(self, client):
        """Handle malformed JSON response."""
        with patch("httpx.Client") as mock_client:
            mock_http = MagicMock()
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = {"unexpected": "format"}
            mock_response_obj.raise_for_status.return_value = None
            mock_http.get.return_value = mock_response_obj
            mock_client.return_value.__enter__.return_value = mock_http

            result = client.fetch_tracking("1234567890")

        assert result.status == "Unknown"
        assert result.error == "Tracking number not found"

    def test_normalizes_tracking_number(self, client):
        """Tracking number should be normalized before API call."""
        mock_response = {
            "shipments": [
                {
                    "status": {
                        "statusCode": "transit",
                        "status": "In Transit",
                    },
                    "events": [],
                }
            ]
        }

        with patch("httpx.Client") as mock_client:
            mock_http = MagicMock()
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status.return_value = None
            mock_http.get.return_value = mock_response_obj
            mock_client.return_value.__enter__.return_value = mock_http

            client.fetch_tracking("12345-67890")

            # Check that the API was called with normalized number
            call_args = mock_http.get.call_args
            assert "1234567890" in call_args[0][0]


class TestDHLClientName:
    """Tests for DHL client name attribute."""

    def test_name_is_dhl(self):
        """Client name should be 'DHL'."""
        client = DHLClient()
        assert client.name == "DHL"
