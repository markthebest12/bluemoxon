"""FedEx carrier tracking client."""

import logging
import re
from datetime import date, datetime

import httpx

from app.services.carriers.base import CarrierClient, TrackingResult

logger = logging.getLogger(__name__)

# FedEx tracking number patterns
# 12-digit: Standard Express
# 15-digit: Ground/Home Delivery
# 20-digit: International
FEDEX_PATTERNS = [
    re.compile(r"^\d{12}$"),
    re.compile(r"^\d{15}$"),
    re.compile(r"^\d{20}$"),
]

# FedEx public tracking API endpoint
FEDEX_TRACKING_URL = "https://www.fedex.com/trackingCal/track"


class FedExClient(CarrierClient):
    """FedEx tracking client using public tracking endpoint."""

    name = "FedEx"

    def fetch_tracking(self, tracking_number: str) -> TrackingResult:
        """Fetch tracking information from FedEx.

        Args:
            tracking_number: FedEx tracking number (12, 15, or 20 digits)

        Returns:
            TrackingResult with status and delivery information
        """
        # Normalize tracking number
        normalized = self._normalize(tracking_number)

        try:
            result = self._fetch_from_api(normalized)
            return result
        except httpx.HTTPStatusError as e:
            logger.warning(f"FedEx API HTTP error: {e.response.status_code}")
            return TrackingResult(
                status="Unknown",
                error=f"FedEx API returned {e.response.status_code}",
            )
        except httpx.ConnectError as e:
            logger.warning(f"FedEx API connection error: {e}")
            return TrackingResult(
                status="Unknown",
                error=f"Connection error: {e}",
            )
        except Exception as e:
            logger.warning(f"Error fetching FedEx tracking: {e}")
            return TrackingResult(
                status="Unknown",
                error=str(e),
            )

    def _fetch_from_api(self, tracking_number: str) -> TrackingResult:
        """Make the actual API request to FedEx.

        Args:
            tracking_number: Normalized tracking number

        Returns:
            TrackingResult parsed from API response
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        }

        payload = {
            "TrackPackagesRequest": {
                "appType": "WTRK",
                "trackingInfoList": [
                    {
                        "trackingNumber": tracking_number,
                    }
                ],
            }
        }

        with httpx.Client(timeout=15) as client:
            response = client.post(
                FEDEX_TRACKING_URL,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        return self._parse_response(data)

    def _parse_response(self, data: dict) -> TrackingResult:
        """Parse FedEx API response into TrackingResult.

        Args:
            data: JSON response from FedEx API

        Returns:
            TrackingResult with parsed information
        """
        try:
            track_response = data.get("TrackPackagesResponse", {})
            package_list = track_response.get("packageList", [])

            if not package_list:
                return TrackingResult(
                    status="Unknown",
                    error="Tracking number not found",
                )

            package = package_list[0]

            # Extract status
            key_status = package.get("keyStatus", "Unknown")
            status = self._normalize_status(key_status)
            status_detail = package.get("statusWithDetails")

            # Extract location from scan events
            location = None
            scan_events = package.get("scanEventList", [])
            if scan_events:
                location = scan_events[0].get("scanLocation")

            # Extract estimated delivery date
            estimated_delivery = None
            est_delivery_str = package.get("estDeliveryDt")
            if est_delivery_str:
                estimated_delivery = self._parse_date(est_delivery_str)

            # Extract actual delivery datetime
            delivered_at = None
            if status == "Delivered":
                delivery_dt_str = package.get("deliveryDt")
                if delivery_dt_str:
                    delivered_at = self._parse_datetime(delivery_dt_str)

            return TrackingResult(
                status=status,
                status_detail=status_detail,
                estimated_delivery=estimated_delivery,
                delivered_at=delivered_at,
                location=location,
            )

        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"Error parsing FedEx response: {e}")
            return TrackingResult(
                status="Unknown",
                error=f"Failed to parse response: {e}",
            )

    def _normalize_status(self, raw_status: str) -> str:
        """Normalize FedEx status to standard status values.

        Args:
            raw_status: Raw status string from FedEx API

        Returns:
            Normalized status: "In Transit", "Delivered", or "Exception"
        """
        status_lower = raw_status.lower()

        if "delivered" in status_lower:
            return "Delivered"
        elif "exception" in status_lower:
            return "Exception"
        elif "transit" in status_lower or "in progress" in status_lower:
            return "In Transit"
        elif "picked up" in status_lower or "shipment" in status_lower:
            return "In Transit"
        else:
            return "In Transit"  # Default to in transit for active packages

    def _parse_date(self, date_str: str) -> date | None:
        """Parse date string from FedEx API.

        Args:
            date_str: Date string in various formats

        Returns:
            date object or None if parsing fails
        """
        # Try common FedEx date formats
        formats = [
            "%Y-%m-%d",  # 2026-01-05
            "%m/%d/%Y",  # 01/05/2026
            "%B %d, %Y",  # January 5, 2026
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        logger.debug(f"Could not parse date: {date_str}")
        return None

    def _parse_datetime(self, datetime_str: str) -> datetime | None:
        """Parse datetime string from FedEx API.

        Args:
            datetime_str: Datetime string in various formats

        Returns:
            datetime object or None if parsing fails
        """
        # Try common FedEx datetime formats
        formats = [
            "%Y-%m-%dT%H:%M:%S",  # ISO format
            "%Y-%m-%d %H:%M:%S",  # Space separator
            "%m/%d/%Y %H:%M:%S",  # US format
        ]

        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue

        logger.debug(f"Could not parse datetime: {datetime_str}")
        return None

    @classmethod
    def can_handle(cls, tracking_number: str | None) -> bool:
        """Check if tracking number matches FedEx patterns.

        Args:
            tracking_number: Tracking number to check

        Returns:
            True if tracking number matches FedEx format
        """
        if not tracking_number:
            return False

        normalized = cls._normalize(tracking_number)

        for pattern in FEDEX_PATTERNS:
            if pattern.match(normalized):
                return True

        return False

    @staticmethod
    def _normalize(tracking_number: str) -> str:
        """Normalize tracking number by removing spaces and dashes.

        Args:
            tracking_number: Raw tracking number

        Returns:
            Normalized tracking number (digits only)
        """
        return tracking_number.replace(" ", "").replace("-", "")
