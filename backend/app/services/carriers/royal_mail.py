"""Royal Mail carrier client for UK shipment tracking."""

import logging
import re
from datetime import date, datetime

import httpx

from app.services.carriers.base import CarrierClient, TrackingResult

logger = logging.getLogger(__name__)

# Royal Mail tracking number pattern: 2 letters + 9 digits + 2 letters
# Examples: AB123456789GB, RR123456789CN
ROYAL_MAIL_PATTERN = re.compile(r"^[A-Z]{2}\d{9}[A-Z]{2}$")

# Royal Mail public tracking endpoint
TRACKING_URL = "https://www.royalmail.com/track-your-item/api/tracking/{tracking_number}"

# Map Royal Mail statuses to our standard statuses
STATUS_MAP = {
    "DELIVERED": "Delivered",
    "IN_TRANSIT": "In Transit",
    "OUT_FOR_DELIVERY": "In Transit",
    "ACCEPTED": "In Transit",
    "COLLECTED": "In Transit",
    "RECEIVED": "In Transit",
    "ISSUE": "Exception",
    "RETURN_TO_SENDER": "Exception",
    "DAMAGED": "Exception",
    "UNKNOWN": "Unknown",
}


class RoyalMailClient(CarrierClient):
    """Client for Royal Mail tracking API.

    Uses Royal Mail's public tracking endpoint to fetch package status.
    No authentication required for basic tracking lookups.
    """

    name = "Royal Mail"

    def fetch_tracking(self, tracking_number: str) -> TrackingResult:
        """Fetch tracking information from Royal Mail.

        Args:
            tracking_number: Royal Mail tracking number.

        Returns:
            TrackingResult with current status and delivery information.
        """
        # Normalize tracking number
        normalized = self._normalize_tracking_number(tracking_number)

        url = TRACKING_URL.format(tracking_number=normalized)
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

        except httpx.TimeoutException as e:
            logger.warning(f"Royal Mail API timeout for {normalized}: {e}")
            return TrackingResult(
                status="Unknown",
                error=f"Timeout: {e}",
            )
        except httpx.HTTPStatusError as e:
            logger.warning(f"Royal Mail API error for {normalized}: {e.response.status_code}")
            return TrackingResult(
                status="Unknown",
                error=f"HTTP {e.response.status_code}",
            )
        except Exception as e:
            logger.warning(f"Error fetching Royal Mail tracking for {normalized}: {e}")
            return TrackingResult(
                status="Unknown",
                error=str(e),
            )

    def _parse_response(self, data: dict) -> TrackingResult:
        """Parse Royal Mail API response.

        Args:
            data: JSON response from Royal Mail API.

        Returns:
            TrackingResult with parsed data.
        """
        mail_pieces = data.get("mailPieces")

        # Handle not found response
        if mail_pieces is None:
            error_message = data.get("httpMessage", "Tracking information not found")
            return TrackingResult(
                status="Unknown",
                error=error_message,
            )

        # Extract status
        raw_status = mail_pieces.get("status", "UNKNOWN")
        status = STATUS_MAP.get(raw_status, "Unknown")
        status_detail = mail_pieces.get("statusDescription")

        # Extract estimated delivery date
        estimated_delivery = None
        est_delivery_data = mail_pieces.get("estimatedDelivery", {})
        if est_delivery_data and est_delivery_data.get("date"):
            try:
                estimated_delivery = date.fromisoformat(est_delivery_data["date"])
            except (ValueError, TypeError):
                pass

        # Extract location and delivery time from most recent event
        location = None
        delivered_at = None
        events = mail_pieces.get("events", [])

        if events:
            latest_event = events[0]
            location = latest_event.get("locationName")

            # If delivered, extract delivery timestamp
            if status == "Delivered":
                event_datetime = latest_event.get("eventDateTime")
                if event_datetime:
                    try:
                        # Handle ISO format with Z suffix
                        if event_datetime.endswith("Z"):
                            event_datetime = event_datetime[:-1]
                        delivered_at = datetime.fromisoformat(event_datetime)
                    except (ValueError, TypeError):
                        pass

        return TrackingResult(
            status=status,
            status_detail=status_detail,
            estimated_delivery=estimated_delivery,
            delivered_at=delivered_at,
            location=location,
        )

    @classmethod
    def can_handle(cls, tracking_number: str) -> bool:
        """Check if tracking number matches Royal Mail pattern.

        Royal Mail tracking numbers follow the format:
        - 2 uppercase letters (service type)
        - 9 digits
        - 2 uppercase letters (country code, typically GB for UK)

        Examples: AB123456789GB, RR123456789CN

        Args:
            tracking_number: The tracking number to check.

        Returns:
            True if this is a Royal Mail tracking number.
        """
        if not tracking_number:
            return False

        # Normalize: uppercase, remove spaces/dashes
        normalized = cls._normalize_tracking_number(tracking_number)

        return bool(ROYAL_MAIL_PATTERN.match(normalized))

    @staticmethod
    def _normalize_tracking_number(tracking_number: str) -> str:
        """Normalize tracking number for API calls.

        Args:
            tracking_number: Raw tracking number input.

        Returns:
            Normalized uppercase tracking number without spaces/dashes.
        """
        return tracking_number.upper().replace(" ", "").replace("-", "")
