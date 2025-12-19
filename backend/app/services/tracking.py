"""Shipment tracking utilities."""

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime

import httpx

logger = logging.getLogger(__name__)

# Carrier URL templates
CARRIER_URLS = {
    "USPS": "https://tools.usps.com/go/TrackConfirmAction?tLabels={number}",
    "UPS": "https://www.ups.com/track?tracknum={number}",
    "FedEx": "https://www.fedex.com/fedextrack/?trknbr={number}",
    "DHL": "https://www.dhl.com/en/express/tracking.html?AWB={number}",
    "Royal Mail": "https://www.royalmail.com/track-your-item#/tracking-results/{number}",
    "Parcelforce": "https://www.parcelforce.com/track-trace?trackNumber={number}",
}

# Carrier detection patterns
CARRIER_PATTERNS = [
    # UPS: 1Z followed by 16 alphanumeric characters
    (r"^1Z[A-Z0-9]{16}$", "UPS"),
    # USPS: 20-22 digits, or starts with 94/93/92
    (r"^(94|93|92)\d{18,20}$", "USPS"),
    (r"^\d{20,22}$", "USPS"),
    # FedEx: 12, 15, or 20 digits
    (r"^\d{12}$", "FedEx"),
    (r"^\d{15}$", "FedEx"),
    (r"^\d{20}$", "FedEx"),
    # DHL: 10 digits
    (r"^\d{10}$", "DHL"),
    # Royal Mail: 2 letters + 9 digits + 2 letters (e.g., AB123456789GB)
    (r"^[A-Z]{2}\d{9}[A-Z]{2}$", "Royal Mail"),
]


def detect_carrier(tracking_number: str) -> str | None:
    """
    Auto-detect carrier from tracking number format.

    Args:
        tracking_number: The tracking number to analyze

    Returns:
        Carrier name if detected, None otherwise
    """
    # Normalize: uppercase, remove spaces/dashes
    normalized = tracking_number.upper().replace(" ", "").replace("-", "")

    for pattern, carrier in CARRIER_PATTERNS:
        if re.match(pattern, normalized):
            return carrier

    return None


def generate_tracking_url(tracking_number: str, carrier: str) -> str | None:
    """
    Generate tracking URL for a given carrier.

    Args:
        tracking_number: The tracking number
        carrier: The carrier name

    Returns:
        Tracking URL if carrier is supported, None otherwise
    """
    template = CARRIER_URLS.get(carrier)
    if not template:
        return None

    # Normalize tracking number for URL
    normalized = tracking_number.upper().replace(" ", "").replace("-", "")
    return template.format(number=normalized)


def process_tracking(
    tracking_number: str | None,
    tracking_carrier: str | None,
    tracking_url: str | None,
) -> tuple[str | None, str | None, str | None]:
    """
    Process tracking input and return normalized values.

    Logic:
    1. If tracking_url provided directly, use it as-is
    2. If tracking_number provided:
       a. Auto-detect carrier if not provided
       b. Generate URL from carrier template

    Args:
        tracking_number: Raw tracking number
        tracking_carrier: Carrier name (optional)
        tracking_url: Direct URL (optional)

    Returns:
        Tuple of (tracking_number, tracking_carrier, tracking_url)

    Raises:
        ValueError: If tracking_number provided but carrier cannot be determined
    """
    # If direct URL provided, return it with whatever number/carrier given
    if tracking_url:
        return tracking_number, tracking_carrier, tracking_url

    # If no tracking number, nothing to process
    if not tracking_number:
        return None, None, None

    # Normalize tracking number
    normalized_number = tracking_number.upper().replace(" ", "").replace("-", "")

    # Determine carrier
    carrier = tracking_carrier
    if not carrier:
        carrier = detect_carrier(normalized_number)

    if not carrier:
        raise ValueError(
            "Could not detect carrier from tracking number. "
            "Please specify tracking_carrier or provide tracking_url directly."
        )

    # Generate URL
    url = generate_tracking_url(normalized_number, carrier)

    return normalized_number, carrier, url


@dataclass
class TrackingInfo:
    """Tracking status information from carrier."""

    status: str | None = None
    estimated_delivery: date | None = None
    estimated_delivery_end: date | None = None
    last_checked: datetime | None = None
    error: str | None = None


def fetch_ups_tracking(tracking_number: str) -> TrackingInfo:
    """Fetch tracking info from UPS public API.

    UPS has a public JSON endpoint that doesn't require authentication.
    """
    url = "https://www.ups.com/track/api/Track/GetStatus?loc=en_US"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    }
    payload = {"Locale": "en_US", "TrackingNumber": [tracking_number]}

    try:
        with httpx.Client(timeout=15) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        # Parse UPS response
        track_details = data.get("trackDetails", [{}])[0]
        status = track_details.get("packageStatus", "Unknown")

        # Try to get delivery date
        delivery_date = None
        delivery_end = None

        # UPS provides estimated delivery in various formats
        scheduled_delivery = track_details.get("scheduledDeliveryDate")
        if scheduled_delivery:
            try:
                delivery_date = datetime.strptime(scheduled_delivery, "%m/%d/%Y").date()
            except ValueError:
                pass

        return TrackingInfo(
            status=status,
            estimated_delivery=delivery_date,
            estimated_delivery_end=delivery_end,
            last_checked=datetime.utcnow(),
        )

    except httpx.HTTPStatusError as e:
        logger.warning(f"UPS API error: {e.response.status_code}")
        return TrackingInfo(
            last_checked=datetime.utcnow(),
            error=f"UPS API returned {e.response.status_code}",
        )
    except Exception as e:
        logger.warning(f"Error fetching UPS tracking: {e}")
        return TrackingInfo(
            last_checked=datetime.utcnow(),
            error=str(e),
        )


def fetch_tracking_status(
    tracking_number: str,
    carrier: str,
) -> TrackingInfo:
    """Fetch current tracking status from carrier.

    Args:
        tracking_number: The tracking number
        carrier: The carrier name

    Returns:
        TrackingInfo with status and estimated delivery date
    """
    normalized = tracking_number.upper().replace(" ", "").replace("-", "")

    if carrier == "UPS":
        return fetch_ups_tracking(normalized)

    # For other carriers, return a placeholder
    # TODO: Add support for USPS, FedEx, etc.
    return TrackingInfo(
        status="Check carrier website",
        last_checked=datetime.utcnow(),
        error=f"Live tracking not yet supported for {carrier}",
    )
