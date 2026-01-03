"""Tests for UPS carrier client."""

from datetime import date
from unittest.mock import MagicMock, patch


class TestUPSCarrierCanHandle:
    """Test UPS tracking number detection."""

    def test_valid_ups_tracking_number(self):
        """Valid UPS tracking number returns True."""
        from app.services.carriers.ups import UPSCarrier

        # Standard UPS format: 1Z + 16 alphanumeric
        assert UPSCarrier.can_handle("1Z12345E0205271688") is True
        assert UPSCarrier.can_handle("1ZABCDEF0123456789") is True

    def test_lowercase_ups_tracking_number(self):
        """Lowercase UPS tracking number returns True (normalized)."""
        from app.services.carriers.ups import UPSCarrier

        assert UPSCarrier.can_handle("1z12345e0205271688") is True

    def test_ups_tracking_with_spaces(self):
        """UPS tracking number with spaces returns True (normalized)."""
        from app.services.carriers.ups import UPSCarrier

        assert UPSCarrier.can_handle("1Z 1234 5E02 0527 1688") is True

    def test_ups_tracking_with_dashes(self):
        """UPS tracking number with dashes returns True (normalized)."""
        from app.services.carriers.ups import UPSCarrier

        assert UPSCarrier.can_handle("1Z-12345E02-05271688") is True

    def test_non_ups_tracking_number(self):
        """Non-UPS tracking numbers return False."""
        from app.services.carriers.ups import UPSCarrier

        # FedEx (12 digits)
        assert UPSCarrier.can_handle("123456789012") is False
        # USPS (20+ digits)
        assert UPSCarrier.can_handle("94001234567890123456") is False
        # Random string
        assert UPSCarrier.can_handle("NOTAUPS12345") is False

    def test_ups_tracking_wrong_length(self):
        """UPS tracking number with wrong length returns False."""
        from app.services.carriers.ups import UPSCarrier

        # Too short
        assert UPSCarrier.can_handle("1Z12345E020527") is False
        # Too long
        assert UPSCarrier.can_handle("1Z12345E02052716889999") is False


class TestUPSCarrierProperties:
    """Test UPS carrier properties."""

    def test_name_is_ups(self):
        """UPSCarrier.name is 'UPS'."""
        from app.services.carriers.ups import UPSCarrier

        carrier = UPSCarrier()
        assert carrier.name == "UPS"


class TestUPSCarrierFetchTracking:
    """Test UPS tracking fetch with mocked HTTP responses."""

    def test_in_transit_status(self):
        """In transit response is parsed correctly."""
        from app.services.carriers.ups import UPSCarrier

        mock_response = {
            "trackDetails": [
                {
                    "packageStatus": "In Transit",
                    "scheduledDeliveryDate": "01/05/2026",
                }
            ]
        }

        with patch("httpx.Client") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response_obj

            carrier = UPSCarrier()
            result = carrier.fetch_tracking("1Z12345E0205271688")

            assert result.status == "In Transit"
            assert result.estimated_delivery == date(2026, 1, 5)
            assert result.error is None

    def test_delivered_status(self):
        """Delivered response includes delivered_at timestamp."""
        from app.services.carriers.ups import UPSCarrier

        mock_response = {
            "trackDetails": [
                {
                    "packageStatus": "Delivered",
                    "deliveredDate": "01/02/2026",
                    "deliveredTime": "2:30 PM",
                }
            ]
        }

        with patch("httpx.Client") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response_obj

            carrier = UPSCarrier()
            result = carrier.fetch_tracking("1Z12345E0205271688")

            assert result.status == "Delivered"
            assert result.delivered_at is not None
            assert result.error is None

    def test_status_with_location(self):
        """Response with location is parsed correctly."""
        from app.services.carriers.ups import UPSCarrier

        mock_response = {
            "trackDetails": [
                {
                    "packageStatus": "In Transit",
                    "currentStatus": {"city": "Louisville", "stateProvince": "KY"},
                }
            ]
        }

        with patch("httpx.Client") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response_obj

            carrier = UPSCarrier()
            result = carrier.fetch_tracking("1Z12345E0205271688")

            assert result.location == "Louisville, KY"

    def test_api_http_error(self):
        """HTTP error returns TrackingResult with error."""
        import httpx

        from app.services.carriers.ups import UPSCarrier

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client.return_value.__enter__.return_value.post.side_effect = (
                httpx.HTTPStatusError(
                    message="Server Error",
                    request=MagicMock(),
                    response=mock_response,
                )
            )

            carrier = UPSCarrier()
            result = carrier.fetch_tracking("1Z12345E0205271688")

            assert result.error is not None
            assert "500" in result.error
            assert result.status == "Unknown"

    def test_api_timeout_error(self):
        """Timeout error returns TrackingResult with error."""
        import httpx

        from app.services.carriers.ups import UPSCarrier

        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post.side_effect = (
                httpx.TimeoutException("Connection timed out")
            )

            carrier = UPSCarrier()
            result = carrier.fetch_tracking("1Z12345E0205271688")

            assert result.error is not None
            assert result.status == "Unknown"

    def test_empty_track_details(self):
        """Empty trackDetails returns Unknown status."""
        from app.services.carriers.ups import UPSCarrier

        mock_response = {"trackDetails": []}

        with patch("httpx.Client") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response_obj

            carrier = UPSCarrier()
            result = carrier.fetch_tracking("1Z12345E0205271688")

            assert result.status == "Unknown"

    def test_normalizes_tracking_number(self):
        """Tracking number is normalized before API call."""
        from app.services.carriers.ups import UPSCarrier

        mock_response = {"trackDetails": [{"packageStatus": "In Transit"}]}

        with patch("httpx.Client") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response_obj

            carrier = UPSCarrier()
            carrier.fetch_tracking("1z 1234-5e02 0527-1688")

            # Verify the API was called with normalized number
            call_args = mock_client.return_value.__enter__.return_value.post.call_args
            payload = call_args[1]["json"]
            assert payload["TrackingNumber"] == ["1Z12345E0205271688"]
