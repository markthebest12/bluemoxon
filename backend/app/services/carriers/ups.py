"""UPS carrier tracking client."""

import logging
import re
from datetime import datetime

import httpx

from app.services.carriers.base import CarrierClient, TrackingResult

logger = logging.getLogger(__name__)

# UPS tracking pattern: 1Z + 16 alphanumeric characters
UPS_PATTERN = re.compile(r"^1Z[A-Z0-9]{16}$")


class UPSCarrier(CarrierClient):
    """UPS tracking client using public JSON API."""

    name = "UPS"

    @classmethod
    def can_handle(cls, tracking_number: str) -> bool:
        """Check if tracking number matches UPS pattern.

        Args:
            tracking_number: The tracking number to check

        Returns:
            True if matches UPS pattern (1Z + 16 alphanumeric)
        """
        normalized = cls._normalize(tracking_number)
        return bool(UPS_PATTERN.match(normalized))

    def fetch_tracking(self, tracking_number: str) -> TrackingResult:
        """Fetch tracking info from UPS public API.

        Args:
            tracking_number: The UPS tracking number

        Returns:
            TrackingResult with status and delivery information
        """
        normalized = self._normalize(tracking_number)

        url = "https://www.ups.com/track/api/Track/GetStatus?loc=en_US"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        }
        payload = {"Locale": "en_US", "TrackingNumber": [normalized]}

        try:
            with httpx.Client(timeout=15) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

            return self._parse_response(data)

        except httpx.HTTPStatusError as e:
            logger.warning(f"UPS API error: {e.response.status_code}")
            return TrackingResult(
                status="Unknown",
                error=f"UPS API returned {e.response.status_code}",
            )
        except httpx.TimeoutException as e:
            logger.warning(f"UPS API timeout: {e}")
            return TrackingResult(
                status="Unknown",
                error="Connection timed out",
            )
        except Exception as e:
            logger.warning(f"Error fetching UPS tracking: {e}")
            return TrackingResult(
                status="Unknown",
                error=str(e),
            )

    @staticmethod
    def _normalize(tracking_number: str) -> str:
        """Normalize tracking number: uppercase, remove spaces/dashes."""
        return tracking_number.upper().replace(" ", "").replace("-", "")

    def _parse_response(self, data: dict) -> TrackingResult:
        """Parse UPS API response into TrackingResult.

        Args:
            data: JSON response from UPS API

        Returns:
            TrackingResult with parsed data
        """
        track_details = data.get("trackDetails", [])
        if not track_details:
            return TrackingResult(status="Unknown")

        detail = track_details[0]
        status = detail.get("packageStatus", "Unknown")

        # Parse estimated delivery date
        estimated_delivery = None
        scheduled_delivery = detail.get("scheduledDeliveryDate")
        if scheduled_delivery:
            try:
                estimated_delivery = datetime.strptime(scheduled_delivery, "%m/%d/%Y").date()
            except ValueError:
                pass

        # Parse delivered timestamp
        delivered_at = None
        delivered_date = detail.get("deliveredDate")
        delivered_time = detail.get("deliveredTime")
        if delivered_date:
            try:
                if delivered_time:
                    dt_str = f"{delivered_date} {delivered_time}"
                    delivered_at = datetime.strptime(dt_str, "%m/%d/%Y %I:%M %p")
                else:
                    delivered_at = datetime.strptime(delivered_date, "%m/%d/%Y")
            except ValueError:
                pass

        # Parse location
        location = None
        current_status = detail.get("currentStatus", {})
        city = current_status.get("city")
        state = current_status.get("stateProvince")
        if city and state:
            location = f"{city}, {state}"

        return TrackingResult(
            status=status,
            estimated_delivery=estimated_delivery,
            delivered_at=delivered_at,
            location=location,
        )
