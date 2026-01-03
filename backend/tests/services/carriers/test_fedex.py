"""Tests for FedEx carrier tracking client."""

from datetime import date
from unittest.mock import MagicMock, patch

from app.services.carriers.fedex import FedExClient


class TestFedExCanHandle:
    """Tests for FedEx tracking number pattern matching."""

    def test_handles_12_digit_number(self):
        """FedEx accepts 12-digit tracking numbers."""
        assert FedExClient.can_handle("123456789012") is True

    def test_handles_15_digit_number(self):
        """FedEx accepts 15-digit tracking numbers."""
        assert FedExClient.can_handle("123456789012345") is True

    def test_handles_20_digit_international(self):
        """FedEx accepts 20-digit international tracking numbers."""
        assert FedExClient.can_handle("12345678901234567890") is True

    def test_rejects_invalid_length(self):
        """FedEx rejects tracking numbers with invalid length."""
        assert FedExClient.can_handle("12345678") is False  # Too short
        assert FedExClient.can_handle("12345678901") is False  # 11 digits
        assert FedExClient.can_handle("1234567890123") is False  # 13 digits
        assert FedExClient.can_handle("12345678901234") is False  # 14 digits
        assert FedExClient.can_handle("1234567890123456") is False  # 16 digits

    def test_rejects_non_numeric(self):
        """FedEx rejects tracking numbers with non-numeric characters (letters)."""
        assert FedExClient.can_handle("12345678901A") is False
        assert FedExClient.can_handle("ABCDEFGHIJKL") is False
        assert FedExClient.can_handle("123ABC789012") is False

    def test_handles_with_spaces(self):
        """FedEx accepts tracking numbers with spaces (normalized)."""
        assert FedExClient.can_handle("1234 5678 9012") is True
        assert FedExClient.can_handle("123 456 789 012 345") is True

    def test_handles_with_dashes(self):
        """FedEx accepts tracking numbers with dashes (normalized)."""
        assert FedExClient.can_handle("1234-5678-9012") is True

    def test_empty_string(self):
        """FedEx rejects empty string."""
        assert FedExClient.can_handle("") is False

    def test_none_handling(self):
        """FedEx handles None gracefully."""
        assert FedExClient.can_handle(None) is False


class TestFedExClientName:
    """Tests for FedEx client name attribute."""

    def test_client_name(self):
        """FedEx client has correct name."""
        client = FedExClient()
        assert client.name == "FedEx"


class TestFedExFetchTrackingSuccess:
    """Tests for successful FedEx tracking responses."""

    @patch("app.services.carriers.fedex.httpx.Client")
    def test_fetch_in_transit_status(self, mock_client_class):
        """Parse in-transit status from FedEx response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "TrackPackagesResponse": {
                "packageList": [
                    {
                        "keyStatus": "In transit",
                        "statusWithDetails": "In transit - Package in transit to destination",
                        "estDeliveryDt": "2026-01-05",
                        "scanEventList": [
                            {
                                "scanLocation": "Memphis, TN",
                                "date": "2026-01-02",
                                "status": "Departed FedEx location",
                            }
                        ],
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = FedExClient()
        result = client.fetch_tracking("123456789012")

        assert result.status == "In Transit"
        assert result.estimated_delivery == date(2026, 1, 5)
        assert result.location == "Memphis, TN"
        assert result.error is None

    @patch("app.services.carriers.fedex.httpx.Client")
    def test_fetch_delivered_status(self, mock_client_class):
        """Parse delivered status from FedEx response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "TrackPackagesResponse": {
                "packageList": [
                    {
                        "keyStatus": "Delivered",
                        "statusWithDetails": "Delivered - Left at front door",
                        "deliveryDt": "2026-01-02T14:30:00",
                        "scanEventList": [
                            {
                                "scanLocation": "New York, NY",
                                "date": "2026-01-02",
                                "status": "Delivered",
                            }
                        ],
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = FedExClient()
        result = client.fetch_tracking("123456789012")

        assert result.status == "Delivered"
        assert result.status_detail == "Delivered - Left at front door"
        assert result.delivered_at is not None
        assert result.location == "New York, NY"
        assert result.error is None

    @patch("app.services.carriers.fedex.httpx.Client")
    def test_fetch_exception_status(self, mock_client_class):
        """Parse exception status from FedEx response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "TrackPackagesResponse": {
                "packageList": [
                    {
                        "keyStatus": "Delivery exception",
                        "statusWithDetails": "Delivery exception - Customer not available",
                        "scanEventList": [
                            {
                                "scanLocation": "Los Angeles, CA",
                                "date": "2026-01-02",
                                "status": "Exception",
                            }
                        ],
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = FedExClient()
        result = client.fetch_tracking("123456789012")

        assert result.status == "Exception"
        assert result.status_detail == "Delivery exception - Customer not available"
        assert result.location == "Los Angeles, CA"

    @patch("app.services.carriers.fedex.httpx.Client")
    def test_fetch_normalizes_tracking_number(self, mock_client_class):
        """Tracking number is normalized before API call."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "TrackPackagesResponse": {
                "packageList": [
                    {
                        "keyStatus": "In transit",
                        "scanEventList": [],
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = FedExClient()
        client.fetch_tracking("1234 5678 9012")

        # Verify the API was called with normalized number
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert (
            payload["TrackPackagesRequest"]["trackingInfoList"][0]["trackingNumber"]
            == "123456789012"
        )


class TestFedExFetchTrackingErrors:
    """Tests for FedEx tracking error handling."""

    @patch("app.services.carriers.fedex.httpx.Client")
    def test_fetch_http_error(self, mock_client_class):
        """Handle HTTP errors gracefully."""
        import httpx

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client.post.side_effect = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_response
        )
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = FedExClient()
        result = client.fetch_tracking("123456789012")

        assert result.status == "Unknown"
        assert result.error is not None
        assert "500" in result.error

    @patch("app.services.carriers.fedex.httpx.Client")
    def test_fetch_network_error(self, mock_client_class):
        """Handle network errors gracefully."""
        import httpx

        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = FedExClient()
        result = client.fetch_tracking("123456789012")

        assert result.status == "Unknown"
        assert result.error is not None

    @patch("app.services.carriers.fedex.httpx.Client")
    def test_fetch_invalid_json_response(self, mock_client_class):
        """Handle malformed JSON responses gracefully."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = FedExClient()
        result = client.fetch_tracking("123456789012")

        assert result.status == "Unknown"
        assert result.error is not None

    @patch("app.services.carriers.fedex.httpx.Client")
    def test_fetch_empty_package_list(self, mock_client_class):
        """Handle empty package list in response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"TrackPackagesResponse": {"packageList": []}}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = FedExClient()
        result = client.fetch_tracking("123456789012")

        assert result.status == "Unknown"
        assert result.error is not None
        assert "not found" in result.error.lower()

    @patch("app.services.carriers.fedex.httpx.Client")
    def test_fetch_missing_response_keys(self, mock_client_class):
        """Handle missing keys in response gracefully."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"someOtherKey": "value"}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = FedExClient()
        result = client.fetch_tracking("123456789012")

        assert result.status == "Unknown"
        assert result.error is not None


class TestFedExDateParsing:
    """Tests for FedEx date parsing edge cases."""

    @patch("app.services.carriers.fedex.httpx.Client")
    def test_parse_various_date_formats(self, mock_client_class):
        """Handle various date formats from FedEx API."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "TrackPackagesResponse": {
                "packageList": [
                    {
                        "keyStatus": "In transit",
                        "estDeliveryDt": "January 5, 2026",  # Alternative format
                        "scanEventList": [],
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = FedExClient()
        result = client.fetch_tracking("123456789012")

        # Should handle gracefully even if date parsing fails
        assert result.status == "In Transit"
        # Date might be None if format is unexpected, but no error

    @patch("app.services.carriers.fedex.httpx.Client")
    def test_missing_estimated_delivery(self, mock_client_class):
        """Handle missing estimated delivery date."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "TrackPackagesResponse": {
                "packageList": [
                    {
                        "keyStatus": "In transit",
                        "scanEventList": [],
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        client = FedExClient()
        result = client.fetch_tracking("123456789012")

        assert result.status == "In Transit"
        assert result.estimated_delivery is None
        assert result.error is None
