"""Carrier plugins for tracking API integration."""

from app.services.carriers.base import CarrierClient, TrackingResult, TrackingStatus
from app.services.carriers.dhl import DHLClient
from app.services.carriers.royal_mail import RoyalMailClient
from app.services.carriers.ups import UPSCarrier
from app.services.carriers.usps import USPSClient

# Registry of all carrier clients by name
_CARRIERS: dict[str, type[CarrierClient]] = {
    "UPS": UPSCarrier,
    "USPS": USPSClient,
    "DHL": DHLClient,
    "Royal Mail": RoyalMailClient,
}


def get_carrier(name: str) -> CarrierClient:
    """Get a carrier client by name.

    Args:
        name: Carrier name (case-insensitive)

    Returns:
        Instantiated carrier client

    Raises:
        KeyError: If carrier name is not registered
    """
    # Normalize name to title case for lookup
    normalized = name.upper()

    # Try exact match first
    for carrier_name, carrier_cls in _CARRIERS.items():
        if carrier_name.upper() == normalized:
            return carrier_cls()

    raise KeyError(f"Unknown carrier: {name}")


__all__ = [
    "CarrierClient",
    "TrackingResult",
    "TrackingStatus",
    "DHLClient",
    "RoyalMailClient",
    "UPSCarrier",
    "USPSClient",
    "get_carrier",
]
