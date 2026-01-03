"""DHL carrier tracking client."""

import logging
import re
from datetime import date, datetime

import httpx

from app.services.carriers.base import CarrierClient, TrackingResult

logger = logging.getLogger(__name__)

# DHL public tracking API endpoint
DHL_API_URL = "https://api-eu.dhl.com/track/shipments"


class DHLClient(CarrierClient):
    """DHL carrier client for tracking packages.

    DHL tracking numbers are 10 digits.
    Uses the DHL public JSON tracking API.
    """

    name = "DHL"

    # Pattern: exactly 10 digits
    PATTERN = re.compile(r"^\d{10}$")

    @classmethod
    def can_handle(cls, tracking_number: str) -> bool:
        """Check if tracking number matches DHL pattern (10 digits).

        Args:
            tracking_number: The tracking number to check

        Returns:
            True if this is a valid DHL tracking number format
        """
        if not tracking_number:
            return False

        # Normalize: remove spaces and dashes
        normalized = tracking_number.replace(" ", "").replace("-", "")
        return bool(cls.PATTERN.match(normalized))

    def fetch_tracking(self, tracking_number: str) -> TrackingResult:
        """Fetch tracking information from DHL public API.

        Args:
            tracking_number: The DHL tracking number

        Returns:
            TrackingResult with current status and delivery information
        """
        # Normalize tracking number
        normalized = tracking_number.replace(" ", "").replace("-", "")

        url = f"{DHL_API_URL}?trackingNumber={normalized}"
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        }

        try:
            with httpx.Client(timeout=15) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

            return self._parse_response(data)

        except httpx.HTTPStatusError as e:
            logger.warning(f"DHL API error: {e.response.status_code}")
            return TrackingResult(
                status="Unknown",
                error=f"DHL API returned {e.response.status_code}",
            )
        except httpx.TimeoutException:
            logger.warning("DHL API timeout")
            return TrackingResult(
                status="Unknown",
                error="Connection timed out",
            )
        except Exception as e:
            logger.warning(f"Error fetching DHL tracking: {e}")
            return TrackingResult(
                status="Unknown",
                error=str(e),
            )

    def _parse_response(self, data: dict) -> TrackingResult:
        """Parse DHL API response into TrackingResult.

        Args:
            data: Raw JSON response from DHL API

        Returns:
            TrackingResult parsed from the response
        """
        shipments = data.get("shipments", [])
        if not shipments:
            return TrackingResult(
                status="Unknown",
                error="Tracking number not found",
            )

        shipment = shipments[0]
        status_info = shipment.get("status", {})

        # Extract status
        status = status_info.get("status", "Unknown")
        status_detail = status_info.get("description")

        # Extract estimated delivery date
        estimated_delivery = None
        estimated_str = shipment.get("estimatedDeliveryDate")
        if estimated_str:
            try:
                estimated_delivery = date.fromisoformat(estimated_str)
            except ValueError:
                pass

        # Extract location and delivered_at from events
        location = None
        delivered_at = None
        events = shipment.get("events", [])

        if events:
            latest_event = events[0]

            # Get location
            location_info = latest_event.get("location", {})
            address = location_info.get("address", {})
            location = address.get("addressLocality")

            # If delivered, extract timestamp
            if status_info.get("statusCode") == "delivered":
                timestamp_str = latest_event.get("timestamp")
                if timestamp_str:
                    try:
                        # Parse ISO format timestamp
                        delivered_at = datetime.fromisoformat(
                            timestamp_str.replace("Z", "+00:00")
                        ).replace(tzinfo=None)
                    except ValueError:
                        pass

        return TrackingResult(
            status=status,
            status_detail=status_detail,
            estimated_delivery=estimated_delivery,
            delivered_at=delivered_at,
            location=location,
        )
