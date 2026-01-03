"""USPS carrier tracking client."""

import logging
import re
from datetime import date, datetime

import defusedxml.ElementTree as ET
import httpx

from app.services.carriers.base import CarrierClient, TrackingResult

logger = logging.getLogger(__name__)

# USPS tracking number patterns
# - 94xx, 93xx, 92xx prefix with 18-20 additional digits (Priority/Certified/Registered Mail)
# - 20-22 digit domestic format
USPS_PATTERNS = [
    re.compile(r"^(94|93|92)\d{18,20}$"),  # Priority/Certified/Registered Mail
    re.compile(r"^\d{20,22}$"),  # Domestic format (20-22 digits)
]

# USPS public tracking endpoint (no auth required)
USPS_TRACKING_URL = "https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_number}"


class USPSClient(CarrierClient):
    """USPS tracking client using public tracking endpoint."""

    name = "USPS"

    def __init__(self):
        """Initialize the USPS client."""
        self._timeout = 15

    @classmethod
    def can_handle(cls, tracking_number: str) -> bool:
        """Check if tracking number matches USPS patterns.

        Args:
            tracking_number: The tracking number to check

        Returns:
            True if this is a USPS tracking number
        """
        # Normalize: remove spaces, dashes, uppercase
        normalized = tracking_number.upper().replace(" ", "").replace("-", "")

        for pattern in USPS_PATTERNS:
            if pattern.match(normalized):
                return True
        return False

    def fetch_tracking(self, tracking_number: str) -> TrackingResult:
        """Fetch tracking status from USPS.

        Uses the USPS public tracking API which returns XML.

        Args:
            tracking_number: The tracking number to look up

        Returns:
            TrackingResult with current status and delivery information
        """
        # Normalize tracking number
        normalized = tracking_number.upper().replace(" ", "").replace("-", "")

        try:
            result = self._fetch_from_api(normalized)
            return result
        except httpx.HTTPStatusError as e:
            logger.warning(f"USPS API HTTP error: {e.response.status_code}")
            return TrackingResult(
                status="Unknown",
                error=f"USPS API returned {e.response.status_code}",
            )
        except httpx.ConnectError as e:
            logger.warning(f"USPS API connection error: {e}")
            return TrackingResult(
                status="Unknown",
                error=f"Connection error: {e}",
            )
        except Exception as e:
            logger.warning(f"Error fetching USPS tracking: {e}")
            return TrackingResult(
                status="Unknown",
                error=str(e),
            )

    def _fetch_from_api(self, tracking_number: str) -> TrackingResult:
        """Make the actual API request and parse response.

        Args:
            tracking_number: Normalized tracking number

        Returns:
            TrackingResult parsed from XML response
        """
        url = USPS_TRACKING_URL.format(tracking_number=tracking_number)

        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(url)
            response.raise_for_status()

        return self._parse_response(response.text)

    def _parse_response(self, xml_text: str) -> TrackingResult:
        """Parse USPS XML response.

        Args:
            xml_text: Raw XML response from USPS

        Returns:
            TrackingResult extracted from XML
        """
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            return TrackingResult(
                status="Unknown",
                error=f"Failed to parse USPS response: {e}",
            )

        # Find TrackInfo element
        track_info = root.find(".//TrackInfo")
        if track_info is None:
            return TrackingResult(
                status="Unknown",
                error="No tracking information in response",
            )

        # Check for error in response
        error_elem = track_info.find("Error/Description")
        if error_elem is not None and error_elem.text:
            return TrackingResult(
                status="Unknown",
                error=error_elem.text,
            )

        # Get track summary
        summary_elem = track_info.find("TrackSummary")
        summary_text = (
            summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ""
        )

        # Parse status from summary
        status, status_detail = self._parse_status(summary_text)

        # Extract location from summary
        location = self._extract_location(summary_text)

        # Get expected delivery date
        estimated_delivery = None
        delivery_elem = track_info.find("ExpectedDeliveryDate")
        if delivery_elem is not None and delivery_elem.text:
            estimated_delivery = self._parse_date(delivery_elem.text)

        # Check for delivered_at timestamp
        delivered_at = None
        if status == "Delivered":
            delivered_at = self._extract_delivered_time(summary_text)

        return TrackingResult(
            status=status,
            status_detail=status_detail,
            estimated_delivery=estimated_delivery,
            delivered_at=delivered_at,
            location=location,
        )

    def _parse_status(self, summary: str) -> tuple[str, str | None]:
        """Parse status from USPS track summary.

        Args:
            summary: The TrackSummary text

        Returns:
            Tuple of (status, status_detail)
        """
        summary_lower = summary.lower()

        # Check for delivered
        if "delivered" in summary_lower:
            return "Delivered", None

        # Check for out for delivery
        if "out for delivery" in summary_lower:
            return "Out for Delivery", None

        # Check for alerts/exceptions
        if "alert" in summary_lower:
            # Extract the detail after "Alert:"
            detail = summary
            if "Alert:" in summary:
                detail = summary.split("Alert:", 1)[1].strip()
                # Remove location from detail
                if "," in detail:
                    # Try to split off location (city, state zip)
                    parts = detail.rsplit(",", 2)
                    if len(parts) > 1:
                        detail = parts[0].strip()
            return "Exception", detail

        # Check for in transit
        if "in transit" in summary_lower or "arrived" in summary_lower:
            return "In Transit", None

        # Default to the summary as status
        return "In Transit", None

    def _extract_location(self, summary: str) -> str | None:
        """Extract location from USPS track summary.

        USPS typically ends summaries with "CITY, ST ZIPCODE"

        Args:
            summary: The TrackSummary text

        Returns:
            Location string if found, None otherwise
        """
        # Pattern for US location: CITY, ST ZIPCODE
        location_pattern = re.compile(r"([A-Z][A-Z\s]+),\s*([A-Z]{2})\s+(\d{5})")
        match = location_pattern.search(summary)
        if match:
            city = match.group(1).strip()
            state = match.group(2)
            zipcode = match.group(3)
            return f"{city}, {state} {zipcode}"
        return None

    def _parse_date(self, date_str: str) -> date | None:
        """Parse date from USPS format.

        Args:
            date_str: Date string like "January 3, 2026"

        Returns:
            date object or None if parsing fails
        """
        try:
            dt = datetime.strptime(date_str.strip(), "%B %d, %Y")
            return dt.date()
        except ValueError:
            pass

        # Try alternate formats
        formats = [
            "%m/%d/%Y",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.date()
            except ValueError:
                continue

        return None

    def _extract_delivered_time(self, summary: str) -> datetime | None:
        """Extract delivered timestamp from summary.

        Example: "delivered at 2:15 pm on January 2, 2026"

        Args:
            summary: The TrackSummary text

        Returns:
            datetime of delivery or None if not found
        """
        # Pattern: "at HH:MM am/pm on Month DD, YYYY"
        pattern = re.compile(
            r"at\s+(\d{1,2}):(\d{2})\s*(am|pm)\s+on\s+(\w+\s+\d{1,2},\s+\d{4})",
            re.IGNORECASE,
        )
        match = pattern.search(summary)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            ampm = match.group(3).lower()
            date_str = match.group(4)

            # Convert to 24-hour
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0

            date_obj = self._parse_date(date_str)
            if date_obj:
                return datetime(date_obj.year, date_obj.month, date_obj.day, hour, minute)

        return None
