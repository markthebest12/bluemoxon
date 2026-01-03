"""Pitney Bowes carrier client for eBay Global Shipping Program tracking."""

import logging
import re
from datetime import date, datetime

import httpx

from app.services.carriers.base import CarrierClient, TrackingResult

logger = logging.getLogger(__name__)

# Pitney Bowes tracking pattern: UPAA followed by digits
PITNEY_BOWES_PATTERN = re.compile(r"^UPAA\d+$", re.IGNORECASE)


class PitneyBowesClient(CarrierClient):
    """Client for fetching tracking information from Pitney Bowes.

    Pitney Bowes handles eBay Global Shipping Program packages.
    Tracking numbers start with 'UPAA' followed by digits.
    """

    name = "Pitney Bowes"

    # Base URL for Pitney Bowes tracking API
    BASE_URL = "https://trackpb.shipment.co/v1/track"

    # Status mapping from API values to normalized display values
    STATUS_MAP = {
        "IN_TRANSIT": "In Transit",
        "DELIVERED": "Delivered",
        "EXCEPTION": "Exception",
        "OUT_FOR_DELIVERY": "Out for Delivery",
        "PENDING": "Pending",
        "PROCESSING": "Processing",
        "SHIPPED": "Shipped",
    }

    def fetch_tracking(self, tracking_number: str) -> TrackingResult:
        """Fetch tracking information from Pitney Bowes API.

        Args:
            tracking_number: The Pitney Bowes tracking number (UPAA format)

        Returns:
            TrackingResult with current status and delivery information
        """
        # Normalize tracking number: uppercase, remove spaces and dashes
        normalized = tracking_number.upper().replace(" ", "").replace("-", "")

        url = f"{self.BASE_URL}/{normalized}"
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; BlueMoxon/1.0)",
        }

        try:
            with httpx.Client(timeout=15) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

            return self._parse_response(data)

        except httpx.HTTPStatusError as e:
            logger.warning(f"Pitney Bowes API error: {e.response.status_code}")
            return TrackingResult(
                status=None,
                error=f"Pitney Bowes API returned {e.response.status_code}",
            )
        except Exception as e:
            logger.warning(f"Error fetching Pitney Bowes tracking: {e}")
            return TrackingResult(
                status=None,
                error=str(e),
            )

    def _parse_response(self, data: dict) -> TrackingResult:
        """Parse the API response into a TrackingResult.

        Args:
            data: JSON response from the Pitney Bowes API

        Returns:
            TrackingResult with parsed tracking information
        """
        raw_status = data.get("status", "")
        status = self.STATUS_MAP.get(raw_status, raw_status.replace("_", " ").title())

        status_detail = data.get("statusDescription")
        location = data.get("currentLocation")

        # Parse estimated delivery date
        estimated_delivery = None
        estimated_date_str = data.get("estimatedDeliveryDate")
        if estimated_date_str:
            try:
                estimated_delivery = date.fromisoformat(estimated_date_str)
            except ValueError:
                logger.debug(
                    f"Could not parse estimated delivery date: {estimated_date_str}"
                )

        # Parse delivered timestamp
        delivered_at = None
        delivered_str = data.get("deliveredAt")
        if delivered_str:
            try:
                # Handle ISO format with Z suffix
                if delivered_str.endswith("Z"):
                    delivered_str = delivered_str[:-1]
                delivered_at = datetime.fromisoformat(delivered_str)
            except ValueError:
                logger.debug(f"Could not parse delivered timestamp: {delivered_str}")

        return TrackingResult(
            status=status,
            status_detail=status_detail,
            estimated_delivery=estimated_delivery,
            delivered_at=delivered_at,
            location=location,
        )

    @classmethod
    def can_handle(cls, tracking_number: str) -> bool:
        """Check if this is a Pitney Bowes tracking number.

        Pitney Bowes tracking numbers for eBay Global Shipping Program
        start with 'UPAA' followed by digits.

        Args:
            tracking_number: The tracking number to check

        Returns:
            True if the tracking number matches the Pitney Bowes pattern
        """
        # Normalize: uppercase, remove spaces and dashes
        normalized = tracking_number.upper().replace(" ", "").replace("-", "")
        return bool(PITNEY_BOWES_PATTERN.match(normalized))
