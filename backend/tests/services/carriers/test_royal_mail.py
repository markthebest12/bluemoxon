"""Tests for Royal Mail carrier client."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.services.carriers.royal_mail import RoyalMailClient


class TestCanHandle:
    """Tests for Royal Mail tracking number pattern matching."""

    def test_valid_uk_domestic_pattern(self):
        """Royal Mail UK domestic: 2 letters + 9 digits + 2 letters (GB suffix)."""
        assert RoyalMailClient.can_handle("AB123456789GB") is True
        assert RoyalMailClient.can_handle("CD987654321GB") is True
        assert RoyalMailClient.can_handle("ZZ000000001GB") is True

    def test_valid_international_pattern(self):
        """Royal Mail international: 2 letters + 9 digits + 2 letters (other suffix)."""
        assert RoyalMailClient.can_handle("AB123456789UK") is True
        assert RoyalMailClient.can_handle("RR123456789CN") is True
        assert RoyalMailClient.can_handle("EE123456789DE") is True

    def test_lowercase_normalized(self):
        """Tracking numbers should be normalized to uppercase."""
        assert RoyalMailClient.can_handle("ab123456789gb") is True
        assert RoyalMailClient.can_handle("Ab123456789Gb") is True

    def test_with_spaces_and_dashes(self):
        """Should handle tracking numbers with spaces or dashes."""
        assert RoyalMailClient.can_handle("AB 123 456 789 GB") is True
        assert RoyalMailClient.can_handle("AB-123-456-789-GB") is True

    def test_invalid_patterns(self):
        """Invalid patterns should return False."""
        # Wrong prefix length
        assert RoyalMailClient.can_handle("A123456789GB") is False
        assert RoyalMailClient.can_handle("ABC123456789GB") is False
        # Wrong digit count
        assert RoyalMailClient.can_handle("AB12345678GB") is False
        assert RoyalMailClient.can_handle("AB1234567890GB") is False
        # Wrong suffix length
        assert RoyalMailClient.can_handle("AB123456789G") is False
        assert RoyalMailClient.can_handle("AB123456789GBB") is False
        # Non-matching patterns
        assert RoyalMailClient.can_handle("1Z999AA10123456784") is False  # UPS
        assert RoyalMailClient.can_handle("1234567890") is False  # DHL
        assert RoyalMailClient.can_handle("INVALID") is False

    def test_empty_and_none(self):
        """Empty or None tracking numbers should return False."""
        assert RoyalMailClient.can_handle("") is False


class TestFetchTracking:
    """Tests for Royal Mail tracking API integration."""

    @pytest.fixture
    def client(self):
        """Create a Royal Mail client instance."""
        return RoyalMailClient()

    def test_in_transit_response(self, client):
        """Parse in transit status from Royal Mail response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "mailPieces": {
                "mailPieceId": "AB123456789GB",
                "status": "IN_TRANSIT",
                "statusDescription": "Item received at delivery depot",
                "estimatedDelivery": {"date": "2026-01-05"},
                "events": [
                    {
                        "eventDateTime": "2026-01-02T10:30:00Z",
                        "eventName": "Item received",
                        "locationName": "MOUNT PLEASANT MC",
                    }
                ],
            }
        }

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = client.fetch_tracking("AB123456789GB")

            assert result.status == "In Transit"
            assert result.status_detail == "Item received at delivery depot"
            assert result.estimated_delivery == date(2026, 1, 5)
            assert result.location == "MOUNT PLEASANT MC"
            assert result.error is None

    def test_delivered_response(self, client):
        """Parse delivered status from Royal Mail response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "mailPieces": {
                "mailPieceId": "AB123456789GB",
                "status": "DELIVERED",
                "statusDescription": "Delivered to neighbour",
                "events": [
                    {
                        "eventDateTime": "2026-01-02T14:25:00Z",
                        "eventName": "Delivered",
                        "locationName": "LONDON",
                    }
                ],
            }
        }

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = client.fetch_tracking("AB123456789GB")

            assert result.status == "Delivered"
            assert result.status_detail == "Delivered to neighbour"
            assert result.delivered_at == datetime(2026, 1, 2, 14, 25, 0)
            assert result.location == "LONDON"
            assert result.error is None

    def test_exception_status(self, client):
        """Parse exception/problem status from Royal Mail response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "mailPieces": {
                "mailPieceId": "AB123456789GB",
                "status": "ISSUE",
                "statusDescription": "Unable to deliver - no access",
                "events": [
                    {
                        "eventDateTime": "2026-01-02T11:00:00Z",
                        "eventName": "Delivery attempted",
                        "locationName": "BIRMINGHAM",
                    }
                ],
            }
        }

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = client.fetch_tracking("AB123456789GB")

            assert result.status == "Exception"
            assert result.status_detail == "Unable to deliver - no access"
            assert result.location == "BIRMINGHAM"
            assert result.error is None

    def test_out_for_delivery_status(self, client):
        """Parse out for delivery status."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "mailPieces": {
                "mailPieceId": "AB123456789GB",
                "status": "OUT_FOR_DELIVERY",
                "statusDescription": "With delivery courier",
                "events": [
                    {
                        "eventDateTime": "2026-01-02T07:30:00Z",
                        "eventName": "Out for delivery",
                        "locationName": "MANCHESTER DO",
                    }
                ],
            }
        }

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = client.fetch_tracking("AB123456789GB")

            assert result.status == "In Transit"
            assert result.status_detail == "With delivery courier"

    def test_tracking_not_found(self, client):
        """Handle tracking number not found response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "mailPieces": None,
            "httpCode": "404",
            "httpMessage": "Tracking information not found",
        }

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = client.fetch_tracking("AB123456789GB")

            assert result.status == "Unknown"
            assert result.error == "Tracking information not found"

    def test_api_error_response(self, client):
        """Handle API error responses."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Internal Server Error")

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            mock_client.return_value.__enter__.return_value.get.return_value.raise_for_status.side_effect = Exception(
                "Internal Server Error"
            )

            result = client.fetch_tracking("AB123456789GB")

            assert result.status == "Unknown"
            assert "Internal Server Error" in result.error

    def test_network_timeout(self, client):
        """Handle network timeout."""
        import httpx

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = (
                httpx.TimeoutException("Timeout")
            )

            result = client.fetch_tracking("AB123456789GB")

            assert result.status == "Unknown"
            assert "Timeout" in result.error

    def test_normalizes_tracking_number(self, client):
        """Tracking number should be normalized before API call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "mailPieces": {
                "mailPieceId": "AB123456789GB",
                "status": "IN_TRANSIT",
                "statusDescription": "In transit",
                "events": [],
            }
        }

        with patch("httpx.Client") as mock_client:
            mock_instance = mock_client.return_value.__enter__.return_value
            mock_instance.get.return_value = mock_response

            client.fetch_tracking("ab 123 456 789 gb")

            # Verify the normalized tracking number was used in the URL
            call_args = mock_instance.get.call_args
            assert "AB123456789GB" in call_args[0][0]

    def test_no_estimated_delivery(self, client):
        """Handle response without estimated delivery date."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "mailPieces": {
                "mailPieceId": "AB123456789GB",
                "status": "IN_TRANSIT",
                "statusDescription": "In transit",
                "events": [
                    {
                        "eventDateTime": "2026-01-02T10:00:00Z",
                        "eventName": "Accepted",
                        "locationName": "POST OFFICE",
                    }
                ],
            }
        }

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = client.fetch_tracking("AB123456789GB")

            assert result.status == "In Transit"
            assert result.estimated_delivery is None

    def test_empty_events_list(self, client):
        """Handle response with no tracking events."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "mailPieces": {
                "mailPieceId": "AB123456789GB",
                "status": "ACCEPTED",
                "statusDescription": "We have received item",
                "events": [],
            }
        }

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            result = client.fetch_tracking("AB123456789GB")

            assert result.status == "In Transit"
            assert result.location is None


class TestClientAttributes:
    """Tests for Royal Mail client attributes."""

    def test_name_attribute(self):
        """Client should have correct name."""
        client = RoyalMailClient()
        assert client.name == "Royal Mail"

    def test_implements_carrier_client(self):
        """Should implement CarrierClient interface."""
        from app.services.carriers.base import CarrierClient

        assert issubclass(RoyalMailClient, CarrierClient)
